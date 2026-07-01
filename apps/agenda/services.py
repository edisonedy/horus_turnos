from datetime import datetime, timedelta

from django.db import connection, transaction
from django.db.models import Q
from django.utils import timezone

from apps.core.utils import combinar_fecha_hora, normalizar_telefono
from apps.negocios.models import HorarioAtencion
from .models import BloqueoHorario, Cliente, ListaEspera, PedidoWhatsApp, Profesional, Turno
from .selectors import ESTADOS_TURNO_ACTIVOS, bloqueos_solapados, profesionales_activos, turnos_solapados


def obtener_o_crear_cliente(negocio, telefono, nombre=''):
    telefono_normalizado = normalizar_telefono(telefono)
    cliente, creado = Cliente.objects.get_or_create(
        negocio=negocio,
        telefono=telefono_normalizado,
        defaults={'nombre': nombre or ''},
    )
    if nombre and not cliente.nombre:
        cliente.nombre = nombre
        cliente.save(update_fields=['nombre'])
    return cliente


def calcular_fecha_fin(fecha_hora_inicio, servicio):
    return fecha_hora_inicio + timedelta(minutes=servicio.duracion_minutos)


def _bloquear_slot(negocio_id, fecha_hora_inicio):
    """Serializa los intentos de reserva concurrentes para un mismo negocio y
    horario usando un advisory lock transaccional de Postgres.

    Sin esto, dos webhooks simultáneos pueden pasar ambos la verificación de
    disponibilidad y crear turnos solapados (doble reserva). El lock se libera
    automáticamente al cerrar la transacción. En motores que no sean Postgres
    (p. ej. SQLite en tests) simplemente no aplica.
    """
    if connection.vendor != 'postgresql':
        return
    slot_key = fecha_hora_inicio.replace(second=0, microsecond=0).isoformat()
    with connection.cursor() as cursor:
        cursor.execute('SELECT pg_advisory_xact_lock(%s, hashtext(%s))', [int(negocio_id), slot_key])


def _profesional_disponible(negocio, inicio, fin, sucursal=None, excluir_turno=None):
    profesionales = list(profesionales_activos(negocio, sucursal=sucursal))
    if profesionales:
        for profesional in profesionales:
            tiene_turnos = turnos_solapados(
                negocio,
                inicio,
                fin,
                profesional=profesional,
                sucursal=sucursal,
                excluir_turno=excluir_turno,
            ).exists()
            tiene_bloqueos = bloqueos_solapados(
                negocio,
                inicio,
                fin,
                profesional=profesional,
                sucursal=sucursal,
            ).exists()
            if not tiene_turnos and not tiene_bloqueos:
                return profesional
        return None

    tiene_turnos = turnos_solapados(
        negocio,
        inicio,
        fin,
        profesional=None,
        sucursal=sucursal,
        excluir_turno=excluir_turno,
    ).exists()
    tiene_bloqueos = bloqueos_solapados(negocio, inicio, fin, profesional=None, sucursal=sucursal).exists()
    return None if tiene_turnos or tiene_bloqueos else False


def obtener_horarios_disponibles(negocio, servicio, fecha, sucursal=None, excluir_turno=None):
    duracion = timedelta(minutes=servicio.duracion_minutos)
    horarios_qs = HorarioAtencion.objects.filter(negocio=negocio, activo=True, dia_semana=fecha.weekday())
    if sucursal:
        horarios_qs = horarios_qs.filter(Q(sucursal=sucursal) | Q(sucursal__isnull=True))
    horarios_qs = horarios_qs.select_related('sucursal').order_by('hora_inicio')

    disponibles = []
    ahora = timezone.now()
    for horario in horarios_qs:
        sucursal_slot = sucursal or horario.sucursal
        inicio = combinar_fecha_hora(fecha, horario.hora_inicio)
        fin_jornada = combinar_fecha_hora(fecha, horario.hora_fin)
        cursor = inicio
        while cursor + duracion <= fin_jornada:
            fin = cursor + duracion
            if cursor > ahora:
                profesional = _profesional_disponible(
                    negocio,
                    cursor,
                    fin,
                    sucursal=sucursal_slot,
                    excluir_turno=excluir_turno,
                )
                if profesional is not None:
                    disponibles.append({
                        'inicio': cursor,
                        'fin': fin,
                        'sucursal_id': sucursal_slot.id if sucursal_slot else None,
                        'profesional_id': profesional.id if isinstance(profesional, Profesional) else None,
                    })
            cursor = cursor + duracion
    return disponibles


@transaction.atomic
def crear_turno_desde_whatsapp(negocio, cliente, servicio, fecha_hora_inicio, sucursal=None, estado=None, observacion=''):
    _bloquear_slot(negocio.id, fecha_hora_inicio)
    fecha_hora_fin = calcular_fecha_fin(fecha_hora_inicio, servicio)
    profesional = _profesional_disponible(negocio, fecha_hora_inicio, fecha_hora_fin, sucursal=sucursal)
    if profesional is None and profesionales_activos(negocio, sucursal=sucursal).exists():
        raise ValueError('El horario ya no está disponible.')
    if profesional is False:
        profesional = None

    turno = Turno.objects.create(
        negocio=negocio,
        sucursal=sucursal,
        profesional=profesional,
        cliente=cliente,
        servicio=servicio,
        fecha_hora_inicio=fecha_hora_inicio,
        fecha_hora_fin=fecha_hora_fin,
        estado=estado or Turno.Estado.PENDIENTE,
        origen=Turno.Origen.WHATSAPP,
        observacion=observacion,
    )
    crear_recordatorios_turno(turno)
    return turno


@transaction.atomic
def reagendar_turno(turno, nueva_fecha_hora_inicio, observacion_extra=''):
    _bloquear_slot(turno.negocio_id, nueva_fecha_hora_inicio)
    fecha_anterior = timezone.localtime(turno.fecha_hora_inicio).strftime('%d/%m/%Y %H:%M')
    fecha_hora_fin = calcular_fecha_fin(nueva_fecha_hora_inicio, turno.servicio)
    profesional = _profesional_disponible(
        turno.negocio,
        nueva_fecha_hora_inicio,
        fecha_hora_fin,
        sucursal=turno.sucursal,
        excluir_turno=turno,
    )
    if profesional is None and profesionales_activos(turno.negocio, sucursal=turno.sucursal).exists():
        raise ValueError('El horario ya no está disponible.')
    if profesional is False:
        profesional = None

    nota = f'Reagendado desde {fecha_anterior}.'
    if observacion_extra:
        nota = f'{nota} {observacion_extra}'
    turno.fecha_hora_inicio = nueva_fecha_hora_inicio
    turno.fecha_hora_fin = fecha_hora_fin
    turno.profesional = profesional
    turno.estado = Turno.Estado.REAGENDADO
    turno.observacion = f'{turno.observacion}\n{nota}'.strip()
    turno.save(update_fields=['fecha_hora_inicio', 'fecha_hora_fin', 'profesional', 'estado', 'observacion'])
    turno.recordatorios_whatsapp.filter(enviado=False).delete()
    crear_recordatorios_turno(turno)
    return turno


@transaction.atomic
def cancelar_turno(turno, motivo='Cancelado por WhatsApp'):
    turno.estado = Turno.Estado.CANCELADO
    turno.observacion = f'{turno.observacion}\n{motivo}'.strip()
    turno.save(update_fields=['estado', 'observacion'])
    turno.recordatorios_whatsapp.filter(enviado=False).delete()
    return turno


def crear_lista_espera(negocio, cliente, servicio, fecha_deseada):
    lista, _ = ListaEspera.objects.get_or_create(
        negocio=negocio,
        cliente=cliente,
        servicio=servicio,
        fecha_deseada=fecha_deseada,
        defaults={'estado': ListaEspera.Estado.PENDIENTE},
    )
    return lista


def crear_pedido_whatsapp(negocio, cliente, producto, cantidad=1, observacion=''):
    total = producto.precio * cantidad
    return PedidoWhatsApp.objects.create(
        negocio=negocio,
        cliente=cliente,
        producto=producto,
        cantidad=cantidad,
        precio_unitario=producto.precio,
        total=total,
        observacion=observacion,
    )


def crear_bloqueo_horario(negocio, fecha_hora_inicio, duracion_minutos=60, motivo='', profesional=None, sucursal=None):
    return BloqueoHorario.objects.create(
        negocio=negocio,
        sucursal=sucursal,
        profesional=profesional,
        fecha_hora_inicio=fecha_hora_inicio,
        fecha_hora_fin=fecha_hora_inicio + timedelta(minutes=duracion_minutos),
        motivo=motivo,
        activo=True,
    )


def liberar_bloqueo_horario(negocio, bloqueo_id):
    bloqueo = BloqueoHorario.objects.filter(negocio=negocio, pk=bloqueo_id, activo=True).first()
    if not bloqueo:
        return None
    bloqueo.activo = False
    bloqueo.save(update_fields=['activo'])
    return bloqueo


def bloqueos_futuros(negocio):
    return BloqueoHorario.objects.filter(negocio=negocio, activo=True, fecha_hora_fin__gte=timezone.now()).order_by('fecha_hora_inicio')


def mensaje_recordatorio(turno):
    fecha = timezone.localtime(turno.fecha_hora_inicio)
    return (
        f'Hola {turno.cliente.nombre or turno.cliente.telefono}, te recordamos tu turno en {turno.negocio.nombre}.\n\n'
        f'Servicio: {turno.servicio.nombre}\n'
        f'Fecha: {fecha:%d/%m/%Y}\n'
        f'Hora: {fecha:%H:%M}\n\n'
        '¿Confirmas que vienes?\n\n'
        'Responde:\n1. Confirmar\n2. Reagendar\n3. Cancelar'
    )


def crear_recordatorios_turno(turno):
    from apps.whatsapp_api.models import RecordatorioWhatsApp

    config = getattr(turno.negocio, 'configuracion_bot', None)
    if not config:
        return 0

    ahora = timezone.now()
    recordatorios = []
    if config.envia_recordatorio_24h:
        # Recordatorio 1 día antes.
        recordatorios.append((RecordatorioWhatsApp.Tipo.HORAS_24, turno.fecha_hora_inicio - timedelta(hours=24)))
    if config.envia_recordatorio_2h:
        # Recordatorio 1 hora antes.
        recordatorios.append((RecordatorioWhatsApp.Tipo.HORAS_2, turno.fecha_hora_inicio - timedelta(hours=1)))

    creados = 0
    for tipo, fecha_programada in recordatorios:
        if fecha_programada < ahora - timedelta(minutes=5):
            continue
        _, creado = RecordatorioWhatsApp.objects.get_or_create(
            turno=turno,
            tipo=tipo,
            defaults={
                'mensaje': mensaje_recordatorio(turno),
                'fecha_programada': fecha_programada,
            },
        )
        if creado:
            creados += 1
    return creados


def turnos_activos_para_recordatorios():
    return Turno.objects.filter(
        estado__in=ESTADOS_TURNO_ACTIVOS,
        fecha_hora_inicio__gt=timezone.now(),
    ).select_related('negocio', 'cliente', 'servicio', 'negocio__configuracion_bot')

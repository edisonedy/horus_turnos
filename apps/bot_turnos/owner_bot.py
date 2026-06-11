from datetime import time, timedelta

from django.db.models import Sum
from django.utils import timezone

from apps.agenda.models import BloqueoHorario, Turno
from apps.agenda.selectors import servicios_activos, turnos_en_rango, turnos_por_estado
from apps.agenda.services import bloqueos_futuros, crear_bloqueo_horario, liberar_bloqueo_horario
from apps.core.selectors import rango_dia
from apps.core.utils import combinar_fecha_hora, normalizar_texto, parsear_fecha_natural, parsear_hora
from apps.whatsapp_api.services import WhatsAppService


def procesar_mensaje_dueno(negocio, telefono, texto):
    comando = normalizar_texto(texto)

    if comando in {'ayuda', 'menu', 'hola', 'inicio'}:
        return _enviar(negocio, telefono, _mensaje_ayuda_dueno())
    if comando.startswith('agenda hoy'):
        return _enviar(negocio, telefono, _agenda_fecha(negocio, timezone.localdate(), 'Agenda de hoy'))
    if comando.startswith('agenda manana') or comando.startswith('agenda mañana'):
        return _enviar(negocio, telefono, _agenda_fecha(negocio, timezone.localdate() + timedelta(days=1), 'Agenda de mañana'))
    if comando.startswith('turnos pendientes'):
        return _enviar(negocio, telefono, _turnos_estado(negocio, Turno.Estado.PENDIENTE, 'Turnos pendientes'))
    if comando.startswith('turnos confirmados'):
        return _enviar(negocio, telefono, _turnos_estado(negocio, Turno.Estado.CONFIRMADO, 'Turnos confirmados'))
    if comando.startswith('clientes nuevos'):
        return _enviar(negocio, telefono, _clientes_nuevos(negocio))
    if comando.startswith('resumen dia') or comando.startswith('resumen día'):
        return _enviar(negocio, telefono, _resumen_dia(negocio))
    if comando == 'servicios' or comando.startswith('servicios'):
        return _enviar(negocio, telefono, _servicios(negocio))
    if comando.startswith('bloquear horario'):
        return _enviar(negocio, telefono, _bloquear_horario(negocio, comando))
    if comando.startswith('liberar horario'):
        return _enviar(negocio, telefono, _liberar_horario(negocio, comando))

    return _enviar(negocio, telefono, 'No reconocí ese comando. Escribe ayuda para ver comandos disponibles.')


def _enviar(negocio, telefono, mensaje):
    try:
        WhatsAppService(negocio=negocio).enviar_texto(telefono, mensaje)
    except Exception:
        pass
    return mensaje


def _mensaje_ayuda_dueno():
    return (
        'Comandos disponibles:\n\n'
        '- agenda hoy\n'
        '- agenda mañana\n'
        '- turnos pendientes\n'
        '- turnos confirmados\n'
        '- clientes nuevos\n'
        '- resumen día\n'
        '- servicios\n'
        '- bloquear horario hoy 15:00 60\n'
        '- liberar horario\n'
        '- liberar horario ID'
    )


def _agenda_fecha(negocio, fecha, titulo):
    inicio, fin = rango_dia(fecha)
    turnos = turnos_en_rango(negocio, inicio, fin)
    if not turnos.exists():
        return f'{titulo}:\n\nNo hay turnos registrados.'
    lineas = [f'{titulo}:', '']
    for turno in turnos:
        hora = timezone.localtime(turno.fecha_hora_inicio).strftime('%H:%M')
        cliente = turno.cliente.nombre or turno.cliente.telefono
        lineas.append(f'{hora} - {cliente} - {turno.servicio.nombre} - {turno.get_estado_display()}')
    return '\n'.join(lineas)


def _turnos_estado(negocio, estado, titulo):
    turnos = turnos_por_estado(negocio, estado).filter(fecha_hora_inicio__gte=timezone.now())[:20]
    if not turnos:
        return f'{titulo}: no hay turnos.'
    lineas = [f'{titulo}:', '']
    for turno in turnos:
        fecha = timezone.localtime(turno.fecha_hora_inicio)
        cliente = turno.cliente.nombre or turno.cliente.telefono
        lineas.append(f'{fecha:%d/%m %H:%M} - {cliente} - {turno.servicio.nombre}')
    return '\n'.join(lineas)


def _clientes_nuevos(negocio):
    inicio, fin = rango_dia()
    clientes = negocio.clientes.filter(fecha_creacion__range=(inicio, fin)).order_by('-fecha_creacion')
    if not clientes.exists():
        return 'Clientes nuevos de hoy: 0'
    lineas = [f'Clientes nuevos de hoy: {clientes.count()}', '']
    for cliente in clientes[:20]:
        lineas.append(f'- {cliente.nombre or "Sin nombre"} - {cliente.telefono}')
    return '\n'.join(lineas)


def _resumen_dia(negocio):
    inicio, fin = rango_dia()
    turnos = negocio.turnos.filter(fecha_hora_inicio__range=(inicio, fin)).select_related('servicio')
    total = turnos.count()
    confirmados = turnos.filter(estado=Turno.Estado.CONFIRMADO).count()
    pendientes = turnos.filter(estado=Turno.Estado.PENDIENTE).count()
    cancelados = turnos.filter(estado=Turno.Estado.CANCELADO).count()
    ingresos = turnos.exclude(estado=Turno.Estado.CANCELADO).aggregate(total=Sum('servicio__precio'))['total'] or 0
    return (
        'Resumen de hoy:\n\n'
        f'Turnos totales: {total}\n'
        f'Confirmados: {confirmados}\n'
        f'Pendientes: {pendientes}\n'
        f'Cancelados: {cancelados}\n'
        f'Ingresos estimados: ${ingresos}'
    )


def _servicios(negocio):
    servicios = servicios_activos(negocio)
    if not servicios.exists():
        return 'No hay servicios activos configurados.'
    lineas = ['Servicios activos:', '']
    for servicio in servicios:
        lineas.append(f'- {servicio.nombre} - {servicio.duracion_minutos} min - ${servicio.precio}')
    return '\n'.join(lineas)


def _bloquear_horario(negocio, comando):
    resto = comando.replace('bloquear horario', '', 1).strip()
    if not resto:
        return 'Uso: bloquear horario hoy 15:00 60\nEl último número es la duración en minutos.'

    partes = resto.split()
    if len(partes) < 2:
        return 'Uso: bloquear horario 10/06/2026 15:00 60'

    if len(partes) >= 3 and partes[0] == 'pasado' and partes[1] == 'manana':
        fecha_texto = 'pasado manana'
        hora_texto = partes[2]
        duracion_texto = partes[3] if len(partes) > 3 else '60'
    else:
        fecha_texto = partes[0]
        hora_texto = partes[1]
        duracion_texto = partes[2] if len(partes) > 2 else '60'

    fecha = parsear_fecha_natural(fecha_texto)
    hora = parsear_hora(hora_texto)
    if not fecha or not hora:
        return 'No pude interpretar fecha u hora. Ejemplo: bloquear horario hoy 15:00 60'
    try:
        duracion = int(duracion_texto)
    except ValueError:
        duracion = 60

    fecha_hora = combinar_fecha_hora(fecha, time(hour=hora[0], minute=hora[1]))
    bloqueo = crear_bloqueo_horario(negocio, fecha_hora, duracion_minutos=duracion, motivo='Bloqueado por WhatsApp')
    inicio = timezone.localtime(bloqueo.fecha_hora_inicio)
    fin = timezone.localtime(bloqueo.fecha_hora_fin)
    return f'Horario bloqueado #{bloqueo.id}: {inicio:%d/%m/%Y %H:%M} a {fin:%H:%M}'


def _liberar_horario(negocio, comando):
    partes = comando.split()
    if len(partes) >= 3 and partes[-1].isdigit():
        bloqueo = liberar_bloqueo_horario(negocio, int(partes[-1]))
        if not bloqueo:
            return 'No encontré un bloqueo activo con ese ID.'
        return f'Bloqueo #{bloqueo.id} liberado.'

    bloqueos = bloqueos_futuros(negocio)[:20]
    if not bloqueos:
        return 'No hay bloqueos futuros activos.'
    lineas = ['Bloqueos activos:', '']
    for bloqueo in bloqueos:
        inicio = timezone.localtime(bloqueo.fecha_hora_inicio)
        fin = timezone.localtime(bloqueo.fecha_hora_fin)
        lineas.append(f'#{bloqueo.id} - {inicio:%d/%m %H:%M} a {fin:%H:%M}')
    lineas.append('\nPara liberar: liberar horario ID')
    return '\n'.join(lineas)

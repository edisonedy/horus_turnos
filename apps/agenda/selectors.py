from datetime import timedelta

from django.db.models import Count, F, Max, Q, Sum
from django.utils import timezone
from .models import BloqueoHorario, Cliente, ListaEspera, PedidoWhatsApp, PreguntaFrecuente, Producto, Profesional, PromocionWhatsApp, RegistroAtencion, Servicio, Turno

ESTADOS_TURNO_ACTIVOS = [Turno.Estado.PENDIENTE, Turno.Estado.CONFIRMADO, Turno.Estado.REAGENDADO]

DIAS_DORMIDA = 45


def clientes_segmentados(negocio, segmento=None):
    """Clientas anotadas con su última cita y segmento (Nueva/Activa/Dormida).
    Si se pasa `segmento`, filtra solo esas."""
    limite = timezone.now() - timedelta(days=DIAS_DORMIDA)
    qs = negocio.clientes.annotate(ultima_cita=Max('turnos__fecha_hora_inicio')).order_by('-ultima_cita')

    if segmento == 'nueva':
        qs = qs.filter(ultima_cita__isnull=True)
    elif segmento == 'activa':
        qs = qs.filter(ultima_cita__gte=limite)
    elif segmento == 'dormida':
        qs = qs.filter(ultima_cita__lt=limite)
    return qs


DIAS_EN_RIESGO = 30


def tablero_retencion(negocio):
    """Datos para el tablero de retención: en riesgo, dormidas, cumpleaños, top clientas."""
    ahora = timezone.now()
    hoy = ahora.date()
    lim_riesgo = ahora - timedelta(days=DIAS_EN_RIESGO)
    lim_dormida = ahora - timedelta(days=DIAS_DORMIDA)

    con_cita_futura = Turno.objects.filter(
        fecha_hora_inicio__gte=ahora, estado__in=ESTADOS_TURNO_ACTIVOS
    ).values_list('cliente_id', flat=True)

    base = negocio.clientes.annotate(
        ultima=Max('turnos__fecha_hora_inicio'),
        citas=Count('turnos', distinct=True),
        gasto=Sum('pedidos_whatsapp__total'),
    )
    en_riesgo = base.filter(ultima__lt=lim_riesgo, ultima__gte=lim_dormida).exclude(id__in=con_cita_futura)
    dormidas = base.filter(ultima__lt=lim_dormida).exclude(id__in=con_cita_futura)
    cumples = negocio.clientes.filter(fecha_nacimiento__month=hoy.month).order_by('fecha_nacimiento__day')
    top = base.filter(gasto__gt=0).order_by('-gasto')[:5]

    inicio_mes = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    citas_mes = negocio.turnos.filter(fecha_hora_inicio__gte=inicio_mes).count()

    return {
        'en_riesgo': en_riesgo.order_by('ultima'),
        'dormidas': dormidas.order_by('ultima')[:20],
        'cumples': cumples,
        'top': top,
        'n_en_riesgo': en_riesgo.count(),
        'n_dormidas': dormidas.count(),
        'n_cumples': cumples.count(),
        'citas_mes': citas_mes,
        'total_clientas': negocio.clientes.count(),
    }


def conteo_segmentos(negocio):
    limite = timezone.now() - timedelta(days=DIAS_DORMIDA)
    qs = negocio.clientes.annotate(ultima_cita=Max('turnos__fecha_hora_inicio'))
    return {
        'total': qs.count(),
        'activa': qs.filter(ultima_cita__gte=limite).count(),
        'dormida': qs.filter(ultima_cita__lt=limite).count(),
        'nueva': qs.filter(ultima_cita__isnull=True).count(),
    }


def ficha_cliente(cliente):
    """Toda la información de una clienta para la ficha CRM del panel."""
    ahora = timezone.now()
    turnos = cliente.turnos.select_related('servicio').order_by('-fecha_hora_inicio')
    pedidos = cliente.pedidos_whatsapp.select_related('producto').order_by('-fecha_creacion')
    mensajes = cliente.mensajes_whatsapp.order_by('-fecha_creacion')[:20]
    atenciones = cliente.atenciones.select_related('servicio', 'producto', 'profesional', 'turno').order_by('-fecha', '-fecha_creacion')
    proximo_control = (cliente.atenciones.filter(proximo_control__gte=ahora.date())
                       .order_by('proximo_control').values_list('proximo_control', flat=True).first())

    proxima = (turnos.filter(fecha_hora_inicio__gte=ahora, estado__in=ESTADOS_TURNO_ACTIVOS)
               .order_by('fecha_hora_inicio').first())
    ultima_visita = turnos.filter(estado=Turno.Estado.ATENDIDO).order_by('-fecha_hora_inicio').first()
    dias_ultima = (ahora.date() - ultima_visita.fecha_hora_inicio.date()).days if ultima_visita else None
    gastado_pedidos = pedidos.exclude(estado=PedidoWhatsApp.Estado.CANCELADO).aggregate(t=Sum('total'))['t'] or 0
    gastado_visitas = (atenciones.filter(producto_accion=RegistroAtencion.Accion.VENDIDO)
                       .aggregate(t=Sum(F('producto_cantidad') * F('producto_precio')))['t'] or 0)
    gastado = gastado_pedidos + gastado_visitas

    if dias_ultima is None:
        segmento = 'Nueva'
    elif dias_ultima <= 45:
        segmento = 'Activa'
    else:
        segmento = 'Dormida'

    return {
        'turnos': turnos[:15],
        'pedidos': pedidos[:15],
        'mensajes': mensajes,
        'atenciones': atenciones,
        'proximo_control': proximo_control,
        'proxima_cita': proxima,
        'ultima_visita': ultima_visita,
        'dias_ultima': dias_ultima,
        'total_citas': turnos.count(),
        'atendidas': turnos.filter(estado=Turno.Estado.ATENDIDO).count(),
        'no_shows': turnos.filter(estado=Turno.Estado.NO_ASISTIO).count(),
        'total_gastado': gastado,
        'segmento': segmento,
    }


def servicios_activos(negocio):
    return Servicio.objects.filter(negocio=negocio, activo=True).order_by('nombre')


def obtener_servicio_por_posicion(negocio, posicion):
    servicios = list(servicios_activos(negocio))
    index = posicion - 1
    if index < 0 or index >= len(servicios):
        return None
    return servicios[index]


def productos_activos(negocio):
    return Producto.objects.filter(negocio=negocio, activo=True).order_by('nombre')


def obtener_producto_por_posicion(negocio, posicion):
    productos = list(productos_activos(negocio))
    index = posicion - 1
    if index < 0 or index >= len(productos):
        return None
    return productos[index]


def preguntas_frecuentes_activas(negocio):
    return PreguntaFrecuente.objects.filter(negocio=negocio, activo=True).order_by('orden', 'pregunta')


def promociones_activas(negocio):
    hoy = timezone.localdate()
    return PromocionWhatsApp.objects.filter(
        Q(fecha_inicio__isnull=True) | Q(fecha_inicio__lte=hoy),
        Q(fecha_fin__isnull=True) | Q(fecha_fin__gte=hoy),
        negocio=negocio,
        activo=True,
    ).order_by('orden', 'titulo')


def profesionales_activos(negocio, sucursal=None):
    qs = Profesional.objects.filter(negocio=negocio, activo=True)
    if sucursal:
        qs = qs.filter(Q(sucursal=sucursal) | Q(sucursal__isnull=True))
    return qs.order_by('nombre')


def clientes_negocio(negocio):
    return Cliente.objects.filter(negocio=negocio).order_by('-fecha_creacion')


def controles_pendientes(negocio, dias=14):
    """Clientas con un control/seguimiento programado (próximo control) que ya
    llegó o llega dentro de `dias`, y que todavía no han vuelto. Una fila por
    clienta (su atención más reciente con control)."""
    hoy = timezone.localdate()
    horizonte = hoy + timedelta(days=dias)
    registros = (RegistroAtencion.objects
                 .filter(negocio=negocio, proximo_control__isnull=False, proximo_control__lte=horizonte)
                 .select_related('cliente', 'servicio')
                 .order_by('cliente_id', '-fecha', '-fecha_creacion'))
    vistos, pendientes = set(), []
    for r in registros:
        if r.cliente_id in vistos:
            continue
        vistos.add(r.cliente_id)
        ya_volvio = r.cliente.turnos.filter(
            fecha_hora_inicio__date__gte=r.proximo_control,
            estado=Turno.Estado.ATENDIDO).exists()
        if not ya_volvio:
            r.vencido = r.proximo_control < hoy
            r.dias = (r.proximo_control - hoy).days
            pendientes.append(r)
    pendientes.sort(key=lambda r: r.proximo_control)
    return pendientes


def turnos_negocio(negocio):
    return Turno.objects.filter(negocio=negocio).select_related('cliente', 'servicio', 'profesional', 'sucursal')


def turnos_por_estado(negocio, estado):
    return turnos_negocio(negocio).filter(estado=estado).order_by('fecha_hora_inicio')


def turnos_en_rango(negocio, inicio, fin):
    return turnos_negocio(negocio).filter(fecha_hora_inicio__gte=inicio, fecha_hora_inicio__lt=fin).order_by('fecha_hora_inicio')


def proximo_turno_activo_cliente(negocio, cliente):
    return Turno.objects.filter(
        negocio=negocio,
        cliente=cliente,
        estado__in=ESTADOS_TURNO_ACTIVOS,
        fecha_hora_inicio__gte=timezone.now(),
    ).select_related('servicio', 'profesional', 'sucursal').order_by('fecha_hora_inicio').first()


def turnos_solapados(negocio, inicio, fin, profesional=None, sucursal=None, excluir_turno=None):
    qs = Turno.objects.filter(
        negocio=negocio,
        estado__in=ESTADOS_TURNO_ACTIVOS,
        fecha_hora_inicio__lt=fin,
        fecha_hora_fin__gt=inicio,
    )
    if profesional:
        qs = qs.filter(profesional=profesional)
    if sucursal:
        qs = qs.filter(sucursal=sucursal)
    if excluir_turno:
        qs = qs.exclude(pk=excluir_turno.pk)
    return qs


def bloqueos_solapados(negocio, inicio, fin, profesional=None, sucursal=None):
    qs = BloqueoHorario.objects.filter(
        negocio=negocio,
        activo=True,
        fecha_hora_inicio__lt=fin,
        fecha_hora_fin__gt=inicio,
    )
    if profesional:
        qs = qs.filter(Q(profesional=profesional) | Q(profesional__isnull=True))
    if sucursal:
        qs = qs.filter(Q(sucursal=sucursal) | Q(sucursal__isnull=True))
    return qs


def lista_espera_pendiente(negocio):
    return ListaEspera.objects.filter(negocio=negocio, estado=ListaEspera.Estado.PENDIENTE).select_related('cliente', 'servicio')

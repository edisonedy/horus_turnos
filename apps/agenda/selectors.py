from django.db.models import Q, Sum
from django.utils import timezone
from .models import BloqueoHorario, Cliente, ListaEspera, PedidoWhatsApp, PreguntaFrecuente, Producto, Profesional, PromocionWhatsApp, Servicio, Turno

ESTADOS_TURNO_ACTIVOS = [Turno.Estado.PENDIENTE, Turno.Estado.CONFIRMADO, Turno.Estado.REAGENDADO]


def ficha_cliente(cliente):
    """Toda la información de una clienta para la ficha CRM del panel."""
    ahora = timezone.now()
    turnos = cliente.turnos.select_related('servicio').order_by('-fecha_hora_inicio')
    pedidos = cliente.pedidos_whatsapp.select_related('producto').order_by('-fecha_creacion')
    mensajes = cliente.mensajes_whatsapp.order_by('-fecha_creacion')[:20]

    proxima = (turnos.filter(fecha_hora_inicio__gte=ahora, estado__in=ESTADOS_TURNO_ACTIVOS)
               .order_by('fecha_hora_inicio').first())
    ultima_visita = turnos.filter(estado=Turno.Estado.ATENDIDO).order_by('-fecha_hora_inicio').first()
    dias_ultima = (ahora.date() - ultima_visita.fecha_hora_inicio.date()).days if ultima_visita else None
    gastado = pedidos.exclude(estado=PedidoWhatsApp.Estado.CANCELADO).aggregate(t=Sum('total'))['t'] or 0

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

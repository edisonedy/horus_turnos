from django.db.models import Q
from django.utils import timezone
from .models import BloqueoHorario, Cliente, ListaEspera, PreguntaFrecuente, Producto, Profesional, PromocionWhatsApp, Servicio, Turno

ESTADOS_TURNO_ACTIVOS = [Turno.Estado.PENDIENTE, Turno.Estado.CONFIRMADO, Turno.Estado.REAGENDADO]


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

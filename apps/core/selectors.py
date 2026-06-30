from datetime import timedelta

from django.db.models import Count, Sum
from django.utils import timezone

from apps.agenda.models import PedidoWhatsApp, Turno
from apps.whatsapp_api.models import ErrorWebhookWhatsApp, RecordatorioWhatsApp


def rango_dia(fecha=None):
    fecha = fecha or timezone.localdate()
    inicio = timezone.make_aware(timezone.datetime.combine(fecha, timezone.datetime.min.time()))
    fin = timezone.make_aware(timezone.datetime.combine(fecha, timezone.datetime.max.time()))
    return inicio, fin


def resumen_dashboard(negocio):
    if not negocio:
        return {
            'turnos_hoy': [],
            'turnos_por_estado': {},
            'clientes_total': 0,
            'conversaciones_recientes': [],
            'errores_whatsapp': [],
            'recordatorios_pendientes': [],
            'pedidos_recientes': [],
        }

    inicio, fin = rango_dia()
    turnos_hoy_qs = Turno.objects.filter(negocio=negocio, fecha_hora_inicio__range=(inicio, fin)).select_related(
        'cliente', 'servicio', 'profesional'
    )
    turnos_por_estado = {
        estado: turnos_hoy_qs.filter(estado=estado).count()
        for estado, _ in Turno.Estado.choices
    }
    return {
        'turnos_hoy': turnos_hoy_qs.order_by('fecha_hora_inicio')[:20],
        'turnos_por_estado': turnos_por_estado,
        'clientes_total': negocio.clientes.count(),
        'conversaciones_recientes': negocio.conversaciones_whatsapp.select_related('cliente').order_by('-actualizado')[:8],
        'errores_whatsapp': ErrorWebhookWhatsApp.objects.filter(negocio=negocio, resuelto=False)[:8],
        'recordatorios_pendientes': RecordatorioWhatsApp.objects.filter(turno__negocio=negocio, enviado=False).select_related(
            'turno', 'turno__cliente', 'turno__servicio'
        )[:8],
        'pedidos_recientes': negocio.pedidos_whatsapp.select_related('cliente', 'producto').order_by('-fecha_creacion')[:8],
    }


def rango_fechas(desde=None, hasta=None):
    """Normaliza un rango de fechas a datetimes aware. Por defecto, últimos 30 días."""
    hoy = timezone.localdate()
    hasta = hasta or hoy
    desde = desde or (hasta - timedelta(days=29))
    inicio = timezone.make_aware(timezone.datetime.combine(desde, timezone.datetime.min.time()))
    fin = timezone.make_aware(timezone.datetime.combine(hasta, timezone.datetime.max.time()))
    return desde, hasta, inicio, fin


def reporte_negocio(negocio, desde=None, hasta=None):
    """Métricas del negocio en un rango de fechas para la página de reportes."""
    desde, hasta, inicio, fin = rango_fechas(desde, hasta)
    base = {'desde': desde, 'hasta': hasta}
    if not negocio:
        return {**base, 'turnos': [], 'turnos_total': 0, 'turnos_por_estado': [],
                'ingresos_servicios': 0, 'top_servicios': [], 'pedidos_total': 0,
                'ventas_productos': 0, 'clientes_nuevos': 0}

    turnos = (Turno.objects.filter(negocio=negocio, fecha_hora_inicio__range=(inicio, fin))
              .select_related('cliente', 'servicio').order_by('fecha_hora_inicio'))

    etiquetas_estado = dict(Turno.Estado.choices)
    turnos_por_estado = [
        {'estado': fila['estado'], 'label': etiquetas_estado.get(fila['estado'], fila['estado']), 'total': fila['total']}
        for fila in turnos.values('estado').annotate(total=Count('id')).order_by('-total')
    ]
    atendidos = turnos.filter(estado=Turno.Estado.ATENDIDO)
    ingresos_servicios = atendidos.aggregate(t=Sum('servicio__precio'))['t'] or 0
    top_servicios = list(turnos.values('servicio__nombre').annotate(total=Count('id')).order_by('-total')[:5])

    pedidos = PedidoWhatsApp.objects.filter(negocio=negocio, fecha_creacion__range=(inicio, fin))
    ventas_productos = pedidos.exclude(estado=PedidoWhatsApp.Estado.CANCELADO).aggregate(t=Sum('total'))['t'] or 0
    clientes_nuevos = negocio.clientes.filter(fecha_creacion__range=(inicio, fin)).count()

    return {
        **base,
        'turnos': turnos,
        'turnos_total': turnos.count(),
        'turnos_por_estado': turnos_por_estado,
        'ingresos_servicios': ingresos_servicios,
        'top_servicios': top_servicios,
        'pedidos_total': pedidos.count(),
        'ventas_productos': ventas_productos,
        'clientes_nuevos': clientes_nuevos,
    }



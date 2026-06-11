from django.utils import timezone
from apps.agenda.models import Turno
from apps.whatsapp_api.models import ConfiguracionWhatsApp, ErrorWebhookWhatsApp, RecordatorioWhatsApp


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
            'onboarding': [],
            'onboarding_porcentaje': 0,
        }

    inicio, fin = rango_dia()
    turnos_hoy_qs = Turno.objects.filter(negocio=negocio, fecha_hora_inicio__range=(inicio, fin)).select_related(
        'cliente', 'servicio', 'profesional'
    )
    turnos_por_estado = {
        estado: turnos_hoy_qs.filter(estado=estado).count()
        for estado, _ in Turno.Estado.choices
    }
    onboarding = estado_onboarding(negocio)
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
        'onboarding': onboarding,
        'onboarding_porcentaje': porcentaje_onboarding(onboarding),
    }


def estado_onboarding(negocio):
    whatsapp = ConfiguracionWhatsApp.objects.filter(negocio=negocio, activo=True).first()
    config_bot = getattr(negocio, 'configuracion_bot', None)
    return [
        {
            'titulo': 'Negocio configurado',
            'descripcion': 'Nombre, teléfono y dirección listos.',
            'completo': bool(negocio.nombre and negocio.telefono_principal),
            'url_name': 'configuracion_negocio',
        },
        {
            'titulo': 'Servicios cargados',
            'descripcion': 'Al menos un servicio activo con precio y duración.',
            'completo': negocio.servicios.filter(activo=True).exists(),
            'url_name': 'servicios',
        },
        {
            'titulo': 'Horarios disponibles',
            'descripcion': 'Días y horas de atención para calcular disponibilidad.',
            'completo': negocio.horarios_atencion.filter(activo=True).exists(),
            'url_name': 'horarios',
        },
        {
            'titulo': 'Catálogo comercial',
            'descripcion': 'Productos o preguntas frecuentes para vender y responder dudas por WhatsApp.',
            'completo': negocio.productos.filter(activo=True).exists() or negocio.preguntas_frecuentes.filter(activo=True).exists(),
            'url_name': 'productos',
        },
        {
            'titulo': 'WhatsApp conectado',
            'descripcion': 'Token, phone number id y webhook configurados.',
            'completo': bool(whatsapp and whatsapp.phone_number_id and whatsapp.access_token),
            'url_name': 'configuracion_whatsapp',
        },
        {
            'titulo': 'Dueño recibirá alertas',
            'descripcion': 'Notificaciones internas y comandos administrativos.',
            'completo': bool(config_bot and config_bot.notificar_dueno_whatsapp and config_bot.telefono_notificacion_dueno),
            'url_name': 'configuracion_negocio',
        },
        {
            'titulo': 'Demo probada',
            'descripcion': 'Ya entró al menos una conversación por WhatsApp.',
            'completo': negocio.conversaciones_whatsapp.exists(),
            'url_name': 'conversaciones',
        },
    ]


def porcentaje_onboarding(pasos):
    if not pasos:
        return 0
    completados = sum(1 for paso in pasos if paso['completo'])
    return round((completados / len(pasos)) * 100)

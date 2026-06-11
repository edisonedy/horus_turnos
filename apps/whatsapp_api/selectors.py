from .models import ConfiguracionWhatsApp, ConversacionWhatsApp, ErrorWebhookWhatsApp, MensajeWhatsApp, RecordatorioWhatsApp


def configuracion_activa_por_phone_number_id(phone_number_id):
    return ConfiguracionWhatsApp.objects.filter(phone_number_id=phone_number_id, activo=True).select_related('negocio').first()


def obtener_configuracion_whatsapp(negocio):
    return ConfiguracionWhatsApp.objects.filter(negocio=negocio, activo=True).first()


def obtener_o_crear_conversacion(negocio, cliente):
    conversacion, _ = ConversacionWhatsApp.objects.get_or_create(negocio=negocio, cliente=cliente)
    return conversacion


def mensajes_conversacion(negocio, cliente):
    return MensajeWhatsApp.objects.filter(negocio=negocio, cliente=cliente).order_by('fecha_creacion')


def conversaciones_negocio(negocio):
    return ConversacionWhatsApp.objects.filter(negocio=negocio).select_related('cliente').order_by('-actualizado')


def errores_webhook_negocio(negocio):
    return ErrorWebhookWhatsApp.objects.filter(negocio=negocio).order_by('-fecha_creacion')


def recordatorios_negocio(negocio):
    return RecordatorioWhatsApp.objects.filter(turno__negocio=negocio).select_related('turno', 'turno__cliente', 'turno__servicio').order_by('fecha_programada')

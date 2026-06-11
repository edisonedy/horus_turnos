import json

from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from apps.agenda.services import obtener_o_crear_cliente
from apps.bot_turnos.bot import procesar_mensaje_entrante
from .models import ConfiguracionWhatsApp, ErrorWebhookWhatsApp, MensajeWhatsApp
from .selectors import configuracion_activa_por_phone_number_id
from .services import actualizar_estado_mensaje_desde_status
from .utils import extraer_mensajes_payload, extraer_phone_number_id, extraer_statuses_payload


@csrf_exempt
@require_http_methods(['GET', 'POST'])
def whatsapp_webhook(request):
    if request.method == 'GET':
        return validar_webhook(request)
    return recibir_webhook(request)


def validar_webhook(request):
    mode = request.GET.get('hub.mode')
    verify_token = request.GET.get('hub.verify_token')
    challenge = request.GET.get('hub.challenge')

    token_valido_env = verify_token == settings.WHATSAPP_VERIFY_TOKEN
    token_valido_db = ConfiguracionWhatsApp.objects.filter(verify_token=verify_token, activo=True).exists()
    token_valido = token_valido_env or token_valido_db
    if mode == 'subscribe' and token_valido and challenge:
        return HttpResponse(challenge)
    return HttpResponseForbidden('Token de verificación inválido')


def recibir_webhook(request):
    payload = {}
    configuracion = None
    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
        phone_number_id = extraer_phone_number_id(payload)
        configuracion = configuracion_activa_por_phone_number_id(phone_number_id)
        if not configuracion:
            ErrorWebhookWhatsApp.objects.create(
                phone_number_id=phone_number_id,
                error='No existe configuración WhatsApp activa para el phone_number_id recibido.',
                payload=payload,
            )
            return JsonResponse({'status': 'ignored', 'reason': 'configuracion_no_encontrada'})

        for status in extraer_statuses_payload(payload):
            actualizar_estado_mensaje_desde_status(status)

        mensajes = extraer_mensajes_payload(payload)
        for mensaje in mensajes:
            whatsapp_message_id = mensaje.get('id', '')
            if whatsapp_message_id and MensajeWhatsApp.objects.filter(whatsapp_message_id=whatsapp_message_id).exists():
                continue

            telefono = mensaje.get('from', '')
            texto = mensaje.get('texto', '')
            cliente = obtener_o_crear_cliente(configuracion.negocio, telefono, nombre=mensaje.get('nombre', ''))
            MensajeWhatsApp.objects.create(
                negocio=configuracion.negocio,
                cliente=cliente,
                tipo=MensajeWhatsApp.Tipo.ENTRANTE,
                telefono=telefono,
                mensaje=texto,
                whatsapp_message_id=whatsapp_message_id,
                estado=MensajeWhatsApp.Estado.ENTREGADO,
                payload=mensaje.get('payload') or payload,
            )
            procesar_mensaje_entrante(configuracion.negocio, telefono, texto, nombre=mensaje.get('nombre', ''))

        return JsonResponse({'status': 'ok'})
    except Exception as exc:
        ErrorWebhookWhatsApp.objects.create(
            negocio=configuracion.negocio if configuracion else None,
            phone_number_id=extraer_phone_number_id(payload) if payload else '',
            error=str(exc),
            payload=payload,
        )
        return JsonResponse({'status': 'error'}, status=500)

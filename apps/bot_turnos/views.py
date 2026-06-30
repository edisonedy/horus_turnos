# El bot se expone por el webhook de WhatsApp en producción.
# Aquí añadimos un SIMULADOR para probar el flujo del bot (agendar, productos,
# reagendar, etc.) localmente, sin necesidad de conectar WhatsApp/Meta.
import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.agenda.models import Cliente
from apps.agenda.services import obtener_o_crear_cliente
from apps.bot_turnos.agent import responder_agente
from apps.bot_turnos.bot import procesar_mensaje_entrante
from apps.negocios.selectors import obtener_negocio_usuario
from apps.whatsapp_api.models import ConversacionWhatsApp
from apps.whatsapp_api.selectors import obtener_o_crear_conversacion

# Número ficticio usado solo para las pruebas del simulador.
TELEFONO_SIMULADOR = '19295550100'
NOMBRE_SIMULADOR = 'Cliente de prueba'


@login_required
def simulador(request):
    negocio = obtener_negocio_usuario(request.user)
    return render(request, 'bot_turnos/simulador.html', {
        'negocio': negocio,
        'telefono_simulador': TELEFONO_SIMULADOR,
    })


@login_required
@require_POST
def simulador_mensaje(request):
    negocio = obtener_negocio_usuario(request.user)
    if not negocio:
        return JsonResponse({'ok': False, 'error': 'No hay negocio configurado.'}, status=400)
    try:
        datos = json.loads(request.body or '{}')
    except ValueError:
        datos = {}
    texto = (datos.get('texto') or '').strip()
    if not texto:
        return JsonResponse({'ok': False, 'error': 'Escribe un mensaje.'}, status=400)

    # Modo "agente" (Opción B, experimental): LLM con memoria + herramientas.
    if datos.get('modo') == 'agente':
        cliente = obtener_o_crear_cliente(negocio, TELEFONO_SIMULADOR, nombre=NOMBRE_SIMULADOR)
        conversacion = obtener_o_crear_conversacion(negocio, cliente)
        respuesta = responder_agente(negocio, cliente, texto, conversacion=conversacion)
        if respuesta is None:
            respuesta = 'La IA (agente) no está disponible. Revisa la configuración de DeepSeek/OpenAI.'
        return JsonResponse({'ok': True, 'reply': respuesta, 'modo': 'agente'})

    # Modo normal: bot híbrido (reglas + clasificador). Intenta enviar por WhatsApp
    # (falla en silencio si no está configurado) y devuelve el texto de la respuesta.
    respuesta = procesar_mensaje_entrante(negocio, TELEFONO_SIMULADOR, texto, nombre=NOMBRE_SIMULADOR)
    return JsonResponse({'ok': True, 'reply': respuesta or '(sin respuesta)'})


@login_required
@require_POST
def simulador_reset(request):
    negocio = obtener_negocio_usuario(request.user)
    if negocio:
        cliente = Cliente.objects.filter(negocio=negocio, telefono=TELEFONO_SIMULADOR).first()
        if cliente:
            ConversacionWhatsApp.objects.filter(negocio=negocio, cliente=cliente).delete()
            cliente.turnos.all().delete()
            cliente.pedidos_whatsapp.all().delete()
    return JsonResponse({'ok': True})

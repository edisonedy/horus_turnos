import json

from django.conf import settings
from django.utils import timezone

from apps.agenda.selectors import servicios_activos

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None

INTENCIONES_VALIDAS = {
    'menu',
    'agendar',
    'reagendar',
    'cancelar',
    'servicios',
    'productos',
    'faq',
    'promociones',
    'ubicacion',
    'humano',
    'mi_turno',
    'ayuda',
    'confirmar',
    'no_puede',
    'lista_espera_si',
    'lista_espera_no',
    'desconocido',
}


def openai_disponible():
    return bool(settings.BOT_USA_OPENAI and settings.OPENAI_API_KEY and OpenAI)


def interpretar_mensaje(negocio, texto, estado_conversacion='inicio'):
    if not openai_disponible():
        return {}

    servicios = list(servicios_activos(negocio))
    servicios_contexto = [
        {'index': index, 'id': servicio.id, 'nombre': servicio.nombre, 'duracion_minutos': servicio.duracion_minutos}
        for index, servicio in enumerate(servicios, start=1)
    ]
    payload = {
        'negocio': negocio.nombre,
        'estado_conversacion': estado_conversacion,
        'fecha_actual': timezone.localdate().isoformat(),
        'servicios': servicios_contexto,
        'mensaje_cliente': texto,
    }

    system = (
        'Eres un clasificador para una recepcionista virtual por WhatsApp. '
        'No agendes ni inventes disponibilidad. Devuelve solo JSON válido, sin markdown. '
        'Campos: intent, service_index, date_iso, time_hhmm, waitlist_yes. '
        'intent debe ser uno de: menu, agendar, reagendar, cancelar, servicios, productos, faq, promociones, '
        'ubicacion, humano, mi_turno, ayuda, confirmar, no_puede, lista_espera_si, lista_espera_no, desconocido. '
        'Usa ayuda cuando el cliente pregunte qué puedes hacer o cómo funciona la recepción. '
        'Usa humano solo cuando pida hablar con una persona, asesor o recepcionista humana. '
        'service_index debe coincidir con la lista de servicios o ser null. '
        'date_iso debe ser YYYY-MM-DD o null. time_hhmm debe ser HH:MM o null. '
        'waitlist_yes debe ser true, false o null.'
    )

    user = json.dumps(payload, ensure_ascii=False)
    try:
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.responses.create(
            model=settings.OPENAI_MODEL,
            input=[
                {'role': 'system', 'content': system},
                {'role': 'user', 'content': user},
            ],
        )
        data = json.loads(response.output_text)
    except Exception:
        return {}

    intent = data.get('intent') or 'desconocido'
    if intent not in INTENCIONES_VALIDAS:
        data['intent'] = 'desconocido'
    return {
        'intent': data.get('intent', 'desconocido'),
        'service_index': _entero_o_none(data.get('service_index')),
        'date_iso': data.get('date_iso') or None,
        'time_hhmm': data.get('time_hhmm') or None,
        'waitlist_yes': data.get('waitlist_yes') if isinstance(data.get('waitlist_yes'), bool) else None,
    }


def _entero_o_none(valor):
    try:
        return int(valor) if valor is not None else None
    except (TypeError, ValueError):
        return None

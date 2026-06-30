import json
import logging

from django.conf import settings
from django.utils import timezone

from apps.agenda.selectors import servicios_activos

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None

logger = logging.getLogger('horus.ai')

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
        # Compatible con OpenAI y con cualquier proveedor con API estilo OpenAI
        # (DeepSeek, etc.) cambiando OPENAI_BASE_URL. Usamos chat.completions +
        # JSON mode porque es el estándar soportado por todos.
        client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL or None,
        )
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {'role': 'system', 'content': system + ' Responde únicamente con un objeto JSON válido.'},
                {'role': 'user', 'content': user},
            ],
            response_format={'type': 'json_object'},
            temperature=0,
        )
        data = json.loads(response.choices[0].message.content)
    except Exception as exc:
        logger.warning('IA no disponible (cae a reglas): %s: %s', type(exc).__name__, str(exc)[:200])
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


def respuesta_humana(negocio, texto, estado_conversacion='inicio', nombre_cliente=''):
    """Genera una respuesta cálida y natural (tono de recepcionista real) para
    mensajes conversacionales que no calzan con un comando. No inventa precios,
    horarios ni disponibilidad: para eso invita a agendar o consultar. Devuelve
    None si la IA no está disponible (entonces el bot usa el menú clásico)."""
    if not openai_disponible():
        return None

    servicios = ', '.join(servicio.nombre for servicio in list(servicios_activos(negocio))[:12])
    contexto = (
        f'Negocio: {negocio.nombre}. {(negocio.descripcion or "").strip()} '
        f'Dirección: {negocio.direccion or "—"}. '
        f'Servicios que ofrece: {servicios}.'
    )
    saludo_nombre = (
        f'El cliente se llama {nombre_cliente}; puedes saludarlo por su nombre con naturalidad. '
        if nombre_cliente else ''
    )
    system = (
        'Eres la recepcionista de Daya Facial Care, un centro de estética facial. Atiendes por '
        'WhatsApp como una persona real del equipo: cálida, cercana y profesional. '
        'NUNCA digas que eres un asistente virtual, un bot, una IA o un sistema automático; '
        'compórtate como una persona de verdad. NO uses menús numerados ni frases tipo '
        '"elige una opción" o "escríbeme tal"; conversa de forma natural. '
        'Hablas español neutro, con naturalidad y amabilidad, en 1 a 3 frases cortas. '
        'NO inventes precios, horarios exactos ni disponibilidad; si te preguntan eso, ofrece agendar '
        'o consultarlo. Puedes ayudar a: agendar, reagendar o cancelar citas, contar sobre los '
        'tratamientos, productos, promociones, ubicación y horarios, o pasar con una persona del equipo. '
        'Cierra invitando con suavidad al siguiente paso (por ejemplo, agendar). '
        f'Usa como máximo un emoji. {saludo_nombre}Contexto del negocio: {contexto}'
    )
    try:
        client = OpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL or None)
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {'role': 'system', 'content': system},
                {'role': 'user', 'content': texto},
            ],
            temperature=0.6,
            max_tokens=180,
        )
        contenido = (response.choices[0].message.content or '').strip()
        return contenido or None
    except Exception as exc:
        logger.warning('respuesta_humana no disponible: %s: %s', type(exc).__name__, str(exc)[:160])
        return None


def _entero_o_none(valor):
    try:
        return int(valor) if valor is not None else None
    except (TypeError, ValueError):
        return None

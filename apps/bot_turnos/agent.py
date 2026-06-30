"""Opción B (experimental): agente conversacional con memoria.

A diferencia del bot híbrido (reglas + clasificador), aquí el LLM (DeepSeek) recibe
el HISTORIAL de la conversación y un set de HERRAMIENTAS reales. El modelo decide
qué hacer y conversa con naturalidad, pero solo puede agendar/consultar a través de
las herramientas, que validan contra la base de datos (nunca inventa disponibilidad).

Se usa solo cuando se activa explícitamente (simulador en "modo agente" o
settings.BOT_USA_AGENTE), para no afectar el bot que ya opera en WhatsApp.
"""
import json
import logging
from datetime import time

from django.conf import settings
from django.utils import timezone

from apps.agenda.selectors import productos_activos, proximo_turno_activo_cliente, servicios_activos
from apps.agenda.services import (
    cancelar_turno,
    crear_turno_desde_whatsapp,
    obtener_horarios_disponibles,
    reagendar_turno,
)
from apps.core.utils import (
    combinar_fecha_hora,
    formatear_fecha,
    formatear_hora,
    normalizar_texto,
    parsear_fecha_natural,
    parsear_hora,
)

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None

logger = logging.getLogger('horus.ai')

MAX_HISTORIAL = 16   # turnos de texto que recordamos
MAX_ITER = 6         # tope de llamadas a herramientas por mensaje


def agente_disponible():
    return bool(settings.BOT_USA_OPENAI and settings.OPENAI_API_KEY and OpenAI)


# ----------------------------- Herramientas -----------------------------

def _match_servicio(negocio, nombre):
    if not nombre:
        return None
    n = normalizar_texto(nombre)
    servicios = list(servicios_activos(negocio))
    for s in servicios:
        if normalizar_texto(s.nombre) == n:
            return s
    for s in servicios:
        sn = normalizar_texto(s.nombre)
        if n in sn or sn in n:
            return s
    # match por palabra distintiva
    palabras = {p for p in n.split() if len(p) >= 4}
    for s in servicios:
        if palabras & {p for p in normalizar_texto(s.nombre).split() if len(p) >= 4}:
            return s
    return None


def _to_time(hhmm):
    h = parsear_hora(hhmm or '')
    return time(h[0], h[1]) if h else None


def tool_listar_servicios(negocio, cliente, args):
    return [{'nombre': s.nombre, 'duracion_min': s.duracion_minutos,
             'precio': float(s.precio) if s.precio else None} for s in servicios_activos(negocio)]


def tool_listar_productos(negocio, cliente, args):
    return [{'nombre': p.nombre, 'precio': float(p.precio)} for p in productos_activos(negocio)]


def tool_info_negocio(negocio, cliente, args):
    horarios = [
        {'dia': h.get_dia_semana_display(),
         'abre': h.hora_inicio.strftime('%H:%M'), 'cierra': h.hora_fin.strftime('%H:%M')}
        for h in negocio.horarios_atencion.filter(activo=True).order_by('dia_semana', 'hora_inicio')
    ]
    promos = [{'titulo': pr.titulo, 'descripcion': pr.descripcion}
              for pr in negocio.promociones_whatsapp.filter(activo=True)[:5]]
    return {'nombre': negocio.nombre, 'direccion': negocio.direccion,
            'horarios': horarios, 'promociones': promos}


def tool_ver_disponibilidad(negocio, cliente, args):
    servicio = _match_servicio(negocio, args.get('servicio'))
    if not servicio:
        return {'error': 'No reconozco ese tratamiento. Pide la lista de tratamientos.'}
    fecha = parsear_fecha_natural(args.get('fecha', ''))
    if not fecha:
        return {'error': 'Fecha no válida. Pide la fecha al cliente (ej: mañana, viernes, 2026-07-05).'}
    disp = obtener_horarios_disponibles(negocio, servicio, fecha)
    horas = [formatear_hora(d['inicio']) for d in disp]
    return {'servicio': servicio.nombre, 'fecha': fecha.isoformat(),
            'horas_disponibles': horas, 'hay_cupo': bool(horas)}


def tool_agendar_cita(negocio, cliente, args):
    servicio = _match_servicio(negocio, args.get('servicio'))
    if not servicio:
        return {'error': 'Tratamiento no reconocido.'}
    fecha = parsear_fecha_natural(args.get('fecha', ''))
    hora = _to_time(args.get('hora'))
    if not fecha or not hora:
        return {'error': 'Falta fecha u hora válida.'}
    inicio = combinar_fecha_hora(fecha, hora)
    # Validar que esa hora esté realmente disponible
    disponibles = obtener_horarios_disponibles(negocio, servicio, fecha)
    if not any(formatear_hora(d['inicio']) == hora.strftime('%H:%M') for d in disponibles):
        horas = [formatear_hora(d['inicio']) for d in disponibles]
        return {'error': 'Ese horario no está disponible.', 'horas_disponibles': horas}
    try:
        turno = crear_turno_desde_whatsapp(negocio, cliente, servicio, inicio)
    except Exception as exc:
        return {'error': f'No se pudo agendar: {exc}'}
    return {'ok': True, 'servicio': servicio.nombre,
            'fecha': formatear_fecha(turno.fecha_hora_inicio),
            'hora': formatear_hora(turno.fecha_hora_inicio)}


def tool_mi_proxima_cita(negocio, cliente, args):
    turno = proximo_turno_activo_cliente(negocio, cliente)
    if not turno:
        return {'tiene_cita': False}
    return {'tiene_cita': True, 'servicio': turno.servicio.nombre,
            'fecha': formatear_fecha(turno.fecha_hora_inicio),
            'hora': formatear_hora(turno.fecha_hora_inicio),
            'estado': turno.get_estado_display()}


def tool_reagendar_cita(negocio, cliente, args):
    turno = proximo_turno_activo_cliente(negocio, cliente)
    if not turno:
        return {'error': 'No tiene una cita activa para reagendar.'}
    fecha = parsear_fecha_natural(args.get('fecha', ''))
    hora = _to_time(args.get('hora'))
    if not fecha or not hora:
        return {'error': 'Falta nueva fecha u hora válida.'}
    nueva = combinar_fecha_hora(fecha, hora)
    disponibles = obtener_horarios_disponibles(negocio, turno.servicio, fecha, excluir_turno=turno)
    if not any(formatear_hora(d['inicio']) == hora.strftime('%H:%M') for d in disponibles):
        return {'error': 'Ese horario no está disponible.',
                'horas_disponibles': [formatear_hora(d['inicio']) for d in disponibles]}
    reagendar_turno(turno, nueva)
    return {'ok': True, 'servicio': turno.servicio.nombre,
            'fecha': formatear_fecha(nueva), 'hora': formatear_hora(nueva)}


def tool_cancelar_cita(negocio, cliente, args):
    turno = proximo_turno_activo_cliente(negocio, cliente)
    if not turno:
        return {'error': 'No tiene una cita activa.'}
    cancelar_turno(turno)
    return {'ok': True}


HERRAMIENTAS = {
    'listar_servicios': tool_listar_servicios,
    'listar_productos': tool_listar_productos,
    'info_negocio': tool_info_negocio,
    'ver_disponibilidad': tool_ver_disponibilidad,
    'agendar_cita': tool_agendar_cita,
    'mi_proxima_cita': tool_mi_proxima_cita,
    'reagendar_cita': tool_reagendar_cita,
    'cancelar_cita': tool_cancelar_cita,
}

TOOLS_SCHEMA = [
    {'type': 'function', 'function': {'name': 'listar_servicios',
        'description': 'Lista los tratamientos disponibles con duración y precio.', 'parameters': {'type': 'object', 'properties': {}}}},
    {'type': 'function', 'function': {'name': 'listar_productos',
        'description': 'Lista los productos a la venta con precio.', 'parameters': {'type': 'object', 'properties': {}}}},
    {'type': 'function', 'function': {'name': 'info_negocio',
        'description': 'Dirección, horarios de atención y promociones del negocio.', 'parameters': {'type': 'object', 'properties': {}}}},
    {'type': 'function', 'function': {'name': 'ver_disponibilidad',
        'description': 'Consulta los horarios libres de un tratamiento en una fecha. Úsalo SIEMPRE antes de agendar.',
        'parameters': {'type': 'object', 'properties': {
            'servicio': {'type': 'string', 'description': 'Nombre del tratamiento'},
            'fecha': {'type': 'string', 'description': 'Fecha natural o ISO, ej: "mañana", "viernes", "2026-07-05"'}},
            'required': ['servicio', 'fecha']}}},
    {'type': 'function', 'function': {'name': 'agendar_cita',
        'description': 'Agenda una cita. Solo úsalo tras confirmar la hora con ver_disponibilidad.',
        'parameters': {'type': 'object', 'properties': {
            'servicio': {'type': 'string'}, 'fecha': {'type': 'string'},
            'hora': {'type': 'string', 'description': 'Hora en formato HH:MM'}},
            'required': ['servicio', 'fecha', 'hora']}}},
    {'type': 'function', 'function': {'name': 'mi_proxima_cita',
        'description': 'Devuelve la próxima cita activa del cliente.', 'parameters': {'type': 'object', 'properties': {}}}},
    {'type': 'function', 'function': {'name': 'reagendar_cita',
        'description': 'Reagenda la cita activa del cliente a una nueva fecha y hora.',
        'parameters': {'type': 'object', 'properties': {
            'fecha': {'type': 'string'}, 'hora': {'type': 'string', 'description': 'HH:MM'}},
            'required': ['fecha', 'hora']}}},
    {'type': 'function', 'function': {'name': 'cancelar_cita',
        'description': 'Cancela la cita activa del cliente.', 'parameters': {'type': 'object', 'properties': {}}}},
]


def _system_prompt(negocio, cliente):
    nombre = (cliente.nombre or '').split(' ')[0]
    hoy = timezone.localdate()
    return (
        f'Eres la recepcionista de {negocio.nombre}, un centro de estética facial en Queens, NY. '
        'Atiendes por WhatsApp como una persona real del equipo: cálida, cercana y profesional. '
        'NUNCA digas que eres un bot, IA, asistente virtual o sistema; eres una persona del equipo. '
        'Hablas español neutro, natural, en frases cortas, máximo un emoji. '
        'Usa SIEMPRE las herramientas para datos reales: nunca inventes tratamientos, precios, '
        'horarios ni disponibilidad. Antes de agendar, confirma el horario con ver_disponibilidad. '
        'Si el cliente cambia de tema (de una cita a productos, etc.), síguelo con naturalidad. '
        f'La fecha de hoy es {hoy.isoformat()}. '
        + (f'El cliente se llama {nombre}; salúdalo por su nombre con naturalidad. ' if nombre else '')
    )


def responder_agente(negocio, cliente, texto, conversacion=None):
    """Procesa un mensaje con el agente. Devuelve el texto de respuesta (o None si la IA no está)."""
    if not agente_disponible():
        return None

    historial = []
    if conversacion is not None:
        historial = (conversacion.datos or {}).get('agente_historial', [])

    mensajes = [{'role': 'system', 'content': _system_prompt(negocio, cliente)}]
    mensajes += historial
    mensajes.append({'role': 'user', 'content': texto})

    client = OpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL or None)
    final = ''
    try:
        for _ in range(MAX_ITER):
            resp = client.chat.completions.create(
                model=settings.OPENAI_MODEL, messages=mensajes,
                tools=TOOLS_SCHEMA, tool_choice='auto', temperature=0.4, max_tokens=400,
            )
            msg = resp.choices[0].message
            if not msg.tool_calls:
                final = (msg.content or '').strip()
                break
            mensajes.append({'role': 'assistant', 'content': msg.content or '',
                             'tool_calls': [{'id': tc.id, 'type': 'function',
                                             'function': {'name': tc.function.name, 'arguments': tc.function.arguments}}
                                            for tc in msg.tool_calls]})
            for tc in msg.tool_calls:
                fn = HERRAMIENTAS.get(tc.function.name)
                try:
                    args = json.loads(tc.function.arguments or '{}')
                except ValueError:
                    args = {}
                try:
                    resultado = fn(negocio, cliente, args) if fn else {'error': 'herramienta desconocida'}
                except Exception as exc:
                    logger.exception('Error en herramienta %s', tc.function.name)
                    resultado = {'error': str(exc)[:150]}
                mensajes.append({'role': 'tool', 'tool_call_id': tc.id,
                                 'content': json.dumps(resultado, ensure_ascii=False)})
    except Exception as exc:
        logger.warning('Agente no disponible: %s: %s', type(exc).__name__, str(exc)[:160])
        return None

    if not final:
        final = 'Disculpa, ¿me lo repites? 😊'

    # Guardar historial (solo texto, recortado)
    if conversacion is not None:
        historial = historial + [{'role': 'user', 'content': texto}, {'role': 'assistant', 'content': final}]
        historial = historial[-MAX_HISTORIAL:]
        datos = conversacion.datos or {}
        datos['agente_historial'] = historial
        conversacion.datos = datos
        conversacion.save(update_fields=['datos', 'actualizado'])

    return final

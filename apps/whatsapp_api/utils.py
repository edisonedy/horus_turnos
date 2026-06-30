import hashlib
import hmac

from apps.core.utils import normalizar_telefono


def firma_webhook_valida(cuerpo_bytes, cabecera_firma, app_secret):
    """Valida la firma X-Hub-Signature-256 que envía Meta en el webhook.

    Meta firma el cuerpo crudo del request con HMAC-SHA256 usando el App Secret.
    Devuelve True si la firma coincide. Si no hay app_secret configurado se
    considera que la validación no aplica (lo decide el llamador).
    """
    if not app_secret:
        return False
    if not cabecera_firma or not cabecera_firma.startswith('sha256='):
        return False
    firma_recibida = cabecera_firma.split('sha256=', 1)[1].strip()
    firma_esperada = hmac.new(
        app_secret.encode('utf-8'),
        msg=cuerpo_bytes,
        digestmod=hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(firma_recibida, firma_esperada)


def extraer_phone_number_id(payload):
    try:
        return payload['entry'][0]['changes'][0]['value']['metadata']['phone_number_id']
    except (KeyError, IndexError, TypeError):
        return ''


def extraer_mensajes_payload(payload):
    mensajes = []
    entries = payload.get('entry', []) if isinstance(payload, dict) else []
    for entry in entries:
        for change in entry.get('changes', []):
            value = change.get('value', {})
            contactos = value.get('contacts', [])
            nombre = ''
            if contactos:
                nombre = contactos[0].get('profile', {}).get('name', '')
            for message in value.get('messages', []):
                texto = ''
                tipo = message.get('type')
                if tipo == 'text':
                    texto = message.get('text', {}).get('body', '')
                elif tipo == 'interactive':
                    interactive = message.get('interactive', {})
                    texto = (
                        interactive.get('button_reply', {}).get('title')
                        or interactive.get('button_reply', {}).get('id')
                        or interactive.get('list_reply', {}).get('title')
                        or interactive.get('list_reply', {}).get('id')
                    )
                elif tipo == 'button':
                    texto = message.get('button', {}).get('text', '')

                mensajes.append({
                    'id': message.get('id', ''),
                    'from': normalizar_telefono(message.get('from', '')),
                    'texto': texto or '',
                    'tipo': tipo or '',
                    'nombre': nombre,
                    'payload': message,
                })
    return mensajes


def extraer_statuses_payload(payload):
    statuses = []
    entries = payload.get('entry', []) if isinstance(payload, dict) else []
    for entry in entries:
        for change in entry.get('changes', []):
            value = change.get('value', {})
            statuses.extend(value.get('statuses', []))
    return statuses

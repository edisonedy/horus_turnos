import logging

import requests
from django.conf import settings
from django.utils import timezone

from apps.agenda.models import Cliente
from apps.core.utils import normalizar_telefono
from .models import ConfiguracionWhatsApp, MensajeWhatsApp

logger = logging.getLogger('horus.whatsapp')

TOKEN_PLACEHOLDER = 'PEGAR_AQUI_TOKEN_NUEVO_GENERADO_EN_META'


class WhatsAppService:
    def __init__(self, access_token=None, phone_number_id=None, negocio=None, configuracion=None):
        self.negocio = negocio or (configuracion.negocio if configuracion else None)
        self.configuracion = configuracion

        if self.configuracion is None and self.negocio:
            self.configuracion = self._obtener_configuracion()

        if self.configuracion:
            access_token = access_token or self.configuracion.access_token
            phone_number_id = phone_number_id or self.configuracion.phone_number_id

        self.access_token = access_token or settings.WHATSAPP_ACCESS_TOKEN
        self.phone_number_id = phone_number_id or settings.WHATSAPP_PHONE_NUMBER_ID
        self.graph_api_version = settings.WHATSAPP_GRAPH_API_VERSION

    def _obtener_configuracion(self):
        configuracion = ConfiguracionWhatsApp.objects.filter(negocio=self.negocio, activo=True).first()
        if not configuracion:
            return None
        return configuracion

    @property
    def base_url(self):
        return f'https://graph.facebook.com/{self.graph_api_version}/{self.phone_number_id}/messages'

    @staticmethod
    def normalizar_telefono(telefono):
        return normalizar_telefono(telefono)

    def _headers(self):
        return {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
        }

    def _validar_configuracion(self):
        if not self.access_token or self.access_token == TOKEN_PLACEHOLDER:
            return 'Falta WHATSAPP_ACCESS_TOKEN en .env o sigue usando el placeholder.'
        if not self.phone_number_id or str(self.phone_number_id).startswith('CONFIGURA_'):
            return 'Falta WHATSAPP_PHONE_NUMBER_ID en .env o en la configuración activa.'
        return ''

    def _post(self, payload):
        error_config = self._validar_configuracion()
        if error_config:
            return {'ok': False, 'status_code': None, 'data': {}, 'error': error_config}

        try:
            response = requests.post(
                self.base_url,
                json=payload,
                headers=self._headers(),
                timeout=settings.WHATSAPP_REQUEST_TIMEOUT,
            )
        except requests.RequestException as exc:
            logger.error('Fallo de red al enviar WhatsApp (to=%s): %s', payload.get('to'), exc)
            return {'ok': False, 'status_code': None, 'data': {}, 'error': str(exc)}
        resultado = self.procesar_respuesta(response)
        if not resultado.get('ok'):
            logger.error(
                'WhatsApp respondió error (to=%s, status=%s): %s',
                payload.get('to'), resultado.get('status_code'), resultado.get('error'),
            )
        return resultado

    def _registrar_salida(self, telefono, mensaje, resultado, turno=None):
        if not self.negocio:
            return None
        telefono_normalizado = self.normalizar_telefono(telefono)
        cliente = Cliente.objects.filter(negocio=self.negocio, telefono=telefono_normalizado).first()
        estado = MensajeWhatsApp.Estado.ENVIADO if resultado.get('ok') else MensajeWhatsApp.Estado.ERROR
        whatsapp_message_id = ''
        data = resultado.get('data') or {}
        try:
            whatsapp_message_id = data.get('messages', [{}])[0].get('id', '')
        except (AttributeError, IndexError):
            whatsapp_message_id = ''
        return MensajeWhatsApp.objects.create(
            negocio=self.negocio,
            cliente=cliente,
            turno=turno,
            tipo=MensajeWhatsApp.Tipo.SALIENTE,
            telefono=telefono_normalizado,
            mensaje=mensaje,
            whatsapp_message_id=whatsapp_message_id,
            estado=estado,
            payload=data or resultado,
        )

    def enviar_texto(self, telefono, mensaje):
        telefono_normalizado = self.normalizar_telefono(telefono)
        payload = {
            'messaging_product': 'whatsapp',
            'to': telefono_normalizado,
            'type': 'text',
            'text': {'body': mensaje},
        }
        resultado = self._post(payload)
        self._registrar_salida(telefono_normalizado, mensaje, resultado)
        return resultado

    def enviar_template_hello_world(self, telefono):
        return self.enviar_template_generico(
            telefono=telefono,
            template_name='hello_world',
            language_code='en_US',
        )

    def enviar_template_generico(self, telefono, template_name, language_code='en_US', components=None):
        telefono_normalizado = self.normalizar_telefono(telefono)
        payload = {
            'messaging_product': 'whatsapp',
            'to': telefono_normalizado,
            'type': 'template',
            'template': {
                'name': template_name,
                'language': {'code': language_code},
            },
        }
        if components:
            payload['template']['components'] = components
        resultado = self._post(payload)
        self._registrar_salida(telefono_normalizado, f'Template: {template_name}', resultado)
        return resultado

    def enviar_plantilla(self, telefono, template_name, language_code, components=None):
        return self.enviar_template_generico(telefono, template_name, language_code, components)

    def _enviar_plantilla_con_params(self, telefono, template_name, parametros):
        componentes = [{
            'type': 'body',
            'parameters': [{'type': 'text', 'text': str(p)} for p in parametros],
        }]
        return self.enviar_template_generico(
            telefono, template_name, settings.WHATSAPP_TEMPLATE_IDIOMA, componentes)

    def enviar_plantilla_recordatorio(self, telefono, parametros):
        """Recordatorio de cita (nombre, negocio, fecha, hora). Llega fuera de la ventana de 24h."""
        return self._enviar_plantilla_con_params(telefono, settings.WHATSAPP_TEMPLATE_RECORDATORIO, parametros)

    def enviar_plantilla_reactivacion(self, telefono, parametros):
        """Reactivación/seguimiento (nombre, negocio). Llega fuera de la ventana de 24h."""
        return self._enviar_plantilla_con_params(telefono, settings.WHATSAPP_TEMPLATE_REACTIVACION, parametros)

    def enviar_menu_texto(self, telefono, mensaje, opciones):
        lineas = [mensaje, '']
        for index, opcion in enumerate(opciones, start=1):
            lineas.append(f'{index}. {opcion}')
        return self.enviar_texto(telefono, '\n'.join(lineas))

    def enviar_resumen_turno(self, telefono, turno):
        fecha_hora = timezone.localtime(turno.fecha_hora_inicio)
        fecha = fecha_hora.strftime('%d/%m/%Y')
        hora = fecha_hora.strftime('%H:%M')
        mensaje = (
            f'Servicio: {turno.servicio.nombre}\n'
            f'Fecha: {fecha}\n'
            f'Hora: {hora}\n'
            f'Cliente: {turno.cliente.nombre or turno.cliente.telefono}\n'
            f'Estado: {turno.get_estado_display()}'
        )
        telefono_normalizado = self.normalizar_telefono(telefono)
        payload = {
            'messaging_product': 'whatsapp',
            'to': telefono_normalizado,
            'type': 'text',
            'text': {'body': mensaje},
        }
        resultado = self._post(payload)
        self._registrar_salida(telefono, mensaje, resultado, turno=turno)
        return resultado

    def enviar_notificacion_dueno(self, negocio, mensaje):
        configuracion_bot = getattr(negocio, 'configuracion_bot', None)
        if not configuracion_bot or not configuracion_bot.notificar_dueno_whatsapp:
            return {'ok': False, 'reason': 'notificaciones_dueno_desactivadas'}
        telefono = configuracion_bot.telefono_notificacion_dueno or negocio.telefono_whatsapp or negocio.telefono_principal
        if not telefono:
            return {'ok': False, 'reason': 'telefono_dueno_no_configurado'}
        if self.negocio != negocio:
            service = WhatsAppService(negocio=negocio)
            return service.enviar_texto(telefono, mensaje)
        return self.enviar_texto(telefono, mensaje)

    def procesar_respuesta(self, response):
        try:
            data = response.json()
        except ValueError:
            data = {'raw': response.text}
        ok = 200 <= response.status_code < 300
        error = ''
        if not ok:
            error_data = data.get('error') if isinstance(data, dict) else data
            error = str(error_data or data)
        return {
            'ok': ok,
            'status_code': response.status_code,
            'data': data,
            'error': error,
        }

    def procesar_respuesta_api(self, response):
        return self.procesar_respuesta(response)


def actualizar_estado_mensaje_desde_status(status):
    whatsapp_message_id = status.get('id', '')
    estado_api = status.get('status', '')
    mapa = {
        'sent': MensajeWhatsApp.Estado.ENVIADO,
        'delivered': MensajeWhatsApp.Estado.ENTREGADO,
        'read': MensajeWhatsApp.Estado.LEIDO,
        'failed': MensajeWhatsApp.Estado.ERROR,
    }
    estado = mapa.get(estado_api)
    if not whatsapp_message_id or not estado:
        return None
    mensaje = MensajeWhatsApp.objects.filter(whatsapp_message_id=whatsapp_message_id).first()
    if not mensaje:
        return None
    mensaje.estado = estado
    mensaje.payload = {**(mensaje.payload or {}), 'status': status}
    mensaje.save(update_fields=['estado', 'payload'])
    return mensaje

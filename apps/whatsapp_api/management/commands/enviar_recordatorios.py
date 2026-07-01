import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.whatsapp_api.models import ConversacionWhatsApp, RecordatorioWhatsApp
from apps.whatsapp_api.services import WhatsAppService

logger = logging.getLogger('horus.recordatorios')


class Command(BaseCommand):
    help = 'Envía recordatorios WhatsApp pendientes cuya fecha programada ya venció.'

    def handle(self, *args, **options):
        enviados = 0
        errores = 0
        recordatorios = RecordatorioWhatsApp.objects.filter(
            enviado=False,
            fecha_programada__lte=timezone.now(),
            turno__fecha_hora_inicio__gt=timezone.now(),
        ).select_related('turno', 'turno__negocio', 'turno__cliente', 'turno__servicio').order_by('fecha_programada')[:100]

        for recordatorio in recordatorios:
            recordatorio.intentos += 1
            try:
                turno = recordatorio.turno
                service = WhatsAppService(negocio=turno.negocio)
                fecha_local = timezone.localtime(turno.fecha_hora_inicio)
                parametros = [
                    (turno.cliente.nombre or 'Hola').split(' ')[0],
                    turno.negocio.nombre,
                    fecha_local.strftime('%d/%m/%Y'),
                    fecha_local.strftime('%H:%M'),
                ]
                # Plantilla primero (llega fuera de la ventana de 24h). Si falla
                # (p. ej. aún no está aprobada), cae a texto libre (dentro de 24h).
                resultado = service.enviar_plantilla_recordatorio(turno.cliente.telefono, parametros)
                if not resultado.get('ok'):
                    resultado = service.enviar_texto(turno.cliente.telefono, recordatorio.mensaje)
                if resultado.get('ok'):
                    recordatorio.enviado = True
                    recordatorio.fecha_envio = timezone.now()
                    recordatorio.error = ''
                    _esperar_confirmacion(recordatorio)
                    enviados += 1
                else:
                    recordatorio.error = str(resultado.get('error') or resultado)
                    logger.warning('Recordatorio %s no enviado: %s', recordatorio.id, recordatorio.error)
                    errores += 1
            except Exception as exc:
                recordatorio.error = str(exc)
                logger.exception('Error enviando recordatorio %s: %s', recordatorio.id, exc)
                errores += 1
            recordatorio.save(update_fields=['intentos', 'enviado', 'fecha_envio', 'error'])

        logger.info('Recordatorios enviados: %s. Errores: %s', enviados, errores)
        self.stdout.write(self.style.SUCCESS(f'Recordatorios enviados: {enviados}. Errores: {errores}'))


def _esperar_confirmacion(recordatorio):
    conversacion, _ = ConversacionWhatsApp.objects.get_or_create(
        negocio=recordatorio.turno.negocio,
        cliente=recordatorio.turno.cliente,
    )
    conversacion.estado = ConversacionWhatsApp.Estado.ESPERANDO_CONFIRMACION_TURNO
    conversacion.datos = {
        'turno_id': recordatorio.turno_id,
        'recordatorio_id': recordatorio.id,
    }
    conversacion.save(update_fields=['estado', 'datos', 'actualizado'])

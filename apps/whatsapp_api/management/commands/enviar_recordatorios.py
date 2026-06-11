from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.whatsapp_api.models import ConversacionWhatsApp, RecordatorioWhatsApp
from apps.whatsapp_api.services import WhatsAppService


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
                service = WhatsAppService(negocio=recordatorio.turno.negocio)
                resultado = service.enviar_texto(recordatorio.turno.cliente.telefono, recordatorio.mensaje)
                if resultado.get('ok'):
                    recordatorio.enviado = True
                    recordatorio.fecha_envio = timezone.now()
                    recordatorio.error = ''
                    _esperar_confirmacion(recordatorio)
                    enviados += 1
                else:
                    recordatorio.error = str(resultado.get('error') or resultado)
                    errores += 1
            except Exception as exc:
                recordatorio.error = str(exc)
                errores += 1
            recordatorio.save(update_fields=['intentos', 'enviado', 'fecha_envio', 'error'])

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

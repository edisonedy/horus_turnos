from django.core.management.base import BaseCommand, CommandError

from apps.whatsapp_api.services import WhatsAppService


class Command(BaseCommand):
    help = 'Envía la plantilla hello_world por WhatsApp Cloud API al teléfono indicado.'

    def add_arguments(self, parser):
        parser.add_argument('telefono', help='Teléfono internacional sin + ni espacios. Ejemplo Ecuador: 59399XXXXXXX')

    def handle(self, *args, **options):
        telefono = options['telefono'].strip()
        if not telefono:
            raise CommandError('Debe indicar un teléfono. Ejemplo: python manage.py probar_whatsapp 59399XXXXXXX')

        resultado = WhatsAppService().enviar_template_hello_world(telefono)
        if resultado.get('ok'):
            self.stdout.write(self.style.SUCCESS('Mensaje hello_world enviado correctamente.'))
        else:
            self.stdout.write(self.style.ERROR('No se pudo enviar el mensaje.'))
            self.stdout.write(f"status_code={resultado.get('status_code')}")
            self.stdout.write(f"error={resultado.get('error')}")

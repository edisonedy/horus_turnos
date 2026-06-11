from time import sleep

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Genera y envía recordatorios WhatsApp en un loop local.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--intervalo',
            type=int,
            default=60,
            help='Segundos entre cada revisión. Por defecto: 60.',
        )

    def handle(self, *args, **options):
        intervalo = max(10, options['intervalo'])
        self.stdout.write(self.style.SUCCESS(f'Worker de recordatorios activo cada {intervalo} segundos.'))
        while True:
            call_command('generar_recordatorios')
            call_command('enviar_recordatorios')
            sleep(intervalo)

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
        # Los seguimientos (post-cita/reactivación) se generan más espaciado (~1 vez/hora).
        ciclos_por_seguimiento = max(1, 3600 // intervalo)
        ciclo = 0
        while True:
            call_command('generar_recordatorios')
            if ciclo % ciclos_por_seguimiento == 0:
                call_command('generar_seguimientos')
            call_command('enviar_recordatorios')
            ciclo += 1
            sleep(intervalo)

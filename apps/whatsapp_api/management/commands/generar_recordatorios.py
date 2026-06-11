from django.core.management.base import BaseCommand

from apps.agenda.services import crear_recordatorios_turno, turnos_activos_para_recordatorios


class Command(BaseCommand):
    help = 'Genera recordatorios WhatsApp 24h y 2h antes de los turnos activos.'

    def handle(self, *args, **options):
        creados = 0
        turnos = turnos_activos_para_recordatorios()

        for turno in turnos:
            creados += crear_recordatorios_turno(turno)

        self.stdout.write(self.style.SUCCESS(f'Recordatorios generados: {creados}'))

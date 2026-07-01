"""Genera seguimientos de retención (lo que hace que las clientas VUELVAN):
- POST_CITA: días después de una cita, invita a agendar la próxima (rebooking).
- REACTIVACION: clientas dormidas (sin venir hace tiempo) → invita a volver.

Se crean como RecordatorioWhatsApp (fecha_programada = ahora) para que
enviar_recordatorios los mande en el próximo ciclo.
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Max
from django.utils import timezone

from apps.agenda.models import Turno
from apps.whatsapp_api.models import RecordatorioWhatsApp

DIAS_POST_CITA = 21        # invita a la próxima ~3 semanas después
DIAS_REACTIVACION = 45     # dormida
ESTADOS_ACTIVOS = [Turno.Estado.PENDIENTE, Turno.Estado.CONFIRMADO, Turno.Estado.REAGENDADO]


def _nombre(cliente):
    return (cliente.nombre or '').split(' ')[0] or 'hola'


class Command(BaseCommand):
    help = 'Genera seguimientos post-cita y de reactivación de clientas dormidas.'

    def handle(self, *args, **options):
        ahora = timezone.now()
        creados = 0

        # ---- POST_CITA (rebooking) ----
        desde = ahora - timedelta(days=60)
        hasta = ahora - timedelta(days=DIAS_POST_CITA)
        turnos = (Turno.objects.filter(fecha_hora_inicio__gte=desde, fecha_hora_inicio__lte=hasta)
                  .exclude(estado__in=[Turno.Estado.CANCELADO, Turno.Estado.NO_ASISTIO])
                  .select_related('cliente', 'negocio', 'servicio'))
        for turno in turnos:
            # si ya tiene una cita futura, no molestar
            if turno.cliente.turnos.filter(fecha_hora_inicio__gte=ahora, estado__in=ESTADOS_ACTIVOS).exists():
                continue
            mensaje = (
                f'Hola {_nombre(turno.cliente)} 🌸 ¿Cómo quedó tu piel después de tu {turno.servicio.nombre}? '
                f'Ya es buen momento para tu próxima sesión. ¿Te agendo? Escríbenos y con gusto te damos un horario 💆‍♀️'
            )
            _, creado = RecordatorioWhatsApp.objects.get_or_create(
                turno=turno, tipo=RecordatorioWhatsApp.Tipo.POST_CITA,
                defaults={'mensaje': mensaje, 'fecha_programada': ahora},
            )
            if creado:
                creados += 1

        # ---- REACTIVACION (dormidas) ----
        limite = ahora - timedelta(days=DIAS_REACTIVACION)
        from apps.agenda.models import Cliente
        clientes = (Cliente.objects.annotate(ultima=Max('turnos__fecha_hora_inicio'))
                    .filter(ultima__lt=limite))
        for cliente in clientes.select_related('negocio'):
            if cliente.turnos.filter(fecha_hora_inicio__gte=ahora, estado__in=ESTADOS_ACTIVOS).exists():
                continue
            ultimo = cliente.turnos.order_by('-fecha_hora_inicio').first()
            if not ultimo:
                continue
            mensaje = (
                f'Hola {_nombre(cliente)} 🌸 Hace tiempo no te vemos en {cliente.negocio.nombre}. '
                f'¿Te gustaría agendar un facial? Con gusto te damos un horario y cuidamos tu piel 💆‍♀️'
            )
            _, creado = RecordatorioWhatsApp.objects.get_or_create(
                turno=ultimo, tipo=RecordatorioWhatsApp.Tipo.REACTIVACION,
                defaults={'mensaje': mensaje, 'fecha_programada': ahora},
            )
            if creado:
                creados += 1

        # ---- CONTROL (próximo control de una atención registrada) ----
        from apps.agenda.models import RegistroAtencion
        hoy = ahora.date()
        atenciones = (RegistroAtencion.objects
                      .filter(proximo_control__lte=hoy, turno__isnull=False)
                      .select_related('cliente', 'negocio', 'servicio', 'turno'))
        for at in atenciones:
            cliente = at.cliente
            # si ya tiene una cita futura, no molestar
            if cliente.turnos.filter(fecha_hora_inicio__gte=ahora, estado__in=ESTADOS_ACTIVOS).exists():
                continue
            servicio = at.servicio or at.turno.servicio
            detalle = f' de {servicio.nombre}' if servicio else ''
            mensaje = (
                f'Hola {_nombre(cliente)} 🌸 ya es momento de tu control de seguimiento{detalle}. '
                f'¿Te agendo? Escríbenos y coordinamos tu próxima visita 💆‍♀️'
            )
            _, creado = RecordatorioWhatsApp.objects.get_or_create(
                turno=at.turno, tipo=RecordatorioWhatsApp.Tipo.CONTROL,
                defaults={'mensaje': mensaje, 'fecha_programada': ahora},
            )
            if creado:
                creados += 1

        self.stdout.write(self.style.SUCCESS(f'Seguimientos generados: {creados}'))

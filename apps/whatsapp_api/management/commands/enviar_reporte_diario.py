from django.core.management.base import BaseCommand
from django.db.models import Sum

from apps.agenda.models import Turno
from apps.core.selectors import rango_dia
from apps.negocios.models import Negocio
from apps.whatsapp_api.services import WhatsAppService


class Command(BaseCommand):
    help = 'Envía al dueño un resumen diario de turnos y ventas estimadas por WhatsApp.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--negocio',
            type=str,
            default='',
            help='Slug del negocio. Si se omite, envía a todos los negocios activos.',
        )

    def handle(self, *args, **options):
        negocios = Negocio.objects.filter(activo=True).select_related('configuracion_bot')
        if options['negocio']:
            negocios = negocios.filter(slug=options['negocio'])

        enviados = 0
        omitidos = 0
        for negocio in negocios:
            mensaje = _mensaje_reporte_diario(negocio)
            resultado = WhatsAppService(negocio=negocio).enviar_notificacion_dueno(negocio, mensaje)
            if resultado.get('ok'):
                enviados += 1
            else:
                omitidos += 1

        self.stdout.write(self.style.SUCCESS(f'Reportes enviados: {enviados}. Omitidos/errores: {omitidos}'))


def _mensaje_reporte_diario(negocio):
    inicio, fin = rango_dia()
    turnos = negocio.turnos.filter(fecha_hora_inicio__range=(inicio, fin)).select_related('servicio')
    total = turnos.count()
    confirmados = turnos.filter(estado=Turno.Estado.CONFIRMADO).count()
    pendientes = turnos.filter(estado=Turno.Estado.PENDIENTE).count()
    reagendados = turnos.filter(estado=Turno.Estado.REAGENDADO).count()
    cancelados = turnos.filter(estado=Turno.Estado.CANCELADO).count()
    atendidos = turnos.filter(estado=Turno.Estado.ATENDIDO).count()
    no_asistio = turnos.filter(estado=Turno.Estado.NO_ASISTIO).count()
    ingresos = turnos.exclude(estado=Turno.Estado.CANCELADO).aggregate(total=Sum('servicio__precio'))['total'] or 0
    clientes_nuevos = negocio.clientes.filter(fecha_creacion__range=(inicio, fin)).count()

    return (
        f'Reporte diario - {negocio.nombre}\n\n'
        f'Turnos totales: {total}\n'
        f'Confirmados: {confirmados}\n'
        f'Pendientes: {pendientes}\n'
        f'Reagendados: {reagendados}\n'
        f'Cancelados: {cancelados}\n'
        f'Atendidos: {atendidos}\n'
        f'No asistieron: {no_asistio}\n'
        f'Clientes nuevos: {clientes_nuevos}\n'
        f'Ingresos estimados: ${ingresos}\n\n'
        'Para ver detalle escribe: agenda hoy'
    )

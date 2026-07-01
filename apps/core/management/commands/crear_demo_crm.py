"""Crea clientas de PRUEBA para ver el tablero de retención con datos.
Úsalo para probar; luego bórralas con: manage.py crear_demo_crm --borrar
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.agenda.models import Cliente, PedidoWhatsApp, Turno
from apps.agenda.services import calcular_fecha_fin
from apps.negocios.selectors import negocio_principal

PREFIJO = '900001'  # teléfonos de prueba

# (nombre, días desde última visita, día de cumpleaños este mes o None, gastó)
DEMO = [
    ('Ana Torres', 5, 15, 51),
    ('Lucia Vera', 12, None, 0),
    ('Maria Paz', 35, 8, 0),      # en riesgo
    ('Sofia Ruiz', 40, None, 74), # en riesgo
    ('Carla Díaz', 60, 20, 125),  # dormida
    ('Elena Mora', 80, None, 0),  # dormida
    ('Rosa León', 20, None, 32),
    ('Julia Sanz', 55, 3, 43),    # dormida + cumple
]


class Command(BaseCommand):
    help = 'Crea (o borra con --borrar) clientas demo para el tablero de retención.'

    def add_arguments(self, parser):
        parser.add_argument('--borrar', action='store_true', help='Elimina las clientas demo.')

    def handle(self, *args, **options):
        neg = negocio_principal()
        if not neg:
            self.stderr.write('No hay negocio.')
            return

        if options['borrar']:
            qs = Cliente.objects.filter(negocio=neg, telefono__startswith=PREFIJO)
            n = qs.count()
            for c in qs:
                c.turnos.all().delete()
                c.pedidos_whatsapp.all().delete()
            qs.delete()
            self.stdout.write(self.style.SUCCESS(f'Clientas demo eliminadas: {n}'))
            return

        servicio = neg.servicios.first()
        producto = neg.productos.first()
        hoy = timezone.now()
        creados = 0
        for i, (nombre, dias, cumple_dia, gasto) in enumerate(DEMO):
            tel = f'{PREFIJO}{i:03d}'
            nac = None
            if cumple_dia:
                nac = hoy.date().replace(day=min(cumple_dia, 28)).replace(year=1995)
            cli, _ = Cliente.objects.get_or_create(
                negocio=neg, telefono=tel,
                defaults={'nombre': nombre, 'fecha_nacimiento': nac})
            cli.nombre = nombre
            cli.fecha_nacimiento = nac
            cli.save()
            # última cita hace `dias` días (atendida)
            cli.turnos.all().delete()
            if servicio:
                inicio = hoy - timedelta(days=dias)
                Turno.objects.create(negocio=neg, cliente=cli, servicio=servicio,
                                     fecha_hora_inicio=inicio, fecha_hora_fin=calcular_fecha_fin(inicio, servicio),
                                     estado=Turno.Estado.ATENDIDO)
            cli.pedidos_whatsapp.all().delete()
            if gasto and producto:
                PedidoWhatsApp.objects.create(negocio=neg, cliente=cli, producto=producto,
                                              cantidad=1, precio_unitario=gasto, total=gasto,
                                              estado=PedidoWhatsApp.Estado.ENTREGADO)
            creados += 1
        self.stdout.write(self.style.SUCCESS(f'Clientas demo creadas: {creados}. Mira el Panel -> Retencion.'))
        self.stdout.write(self.style.WARNING('Para borrarlas: manage.py crear_demo_crm --borrar'))

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from apps.agenda.models import Cliente, Producto, RegistroAtencion, Servicio, Turno
from apps.agenda.selectors import controles_pendientes, ficha_cliente
from apps.negocios.models import Negocio
from apps.whatsapp_api.models import RecordatorioWhatsApp


class BaseAtencionTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_superuser('tester', 'tester@example.com', 'x')
        self.negocio = Negocio.objects.create(
            propietario=self.user, nombre='Estetica Test',
            telefono_principal='100', activo=True)
        self.servicio = Servicio.objects.create(negocio=self.negocio, nombre='Facial', precio=50)
        self.producto = Producto.objects.create(negocio=self.negocio, nombre='Crema', precio=74)
        self.cliente = Cliente.objects.create(negocio=self.negocio, nombre='Rosa', telefono='19295550000')
        self.client.force_login(self.user)

    def url(self):
        return f'/panel/clientes/{self.cliente.id}/'

    def _turno(self, dias, estado=Turno.Estado.ATENDIDO):
        ini = timezone.now() + timedelta(days=dias)
        return Turno.objects.create(
            negocio=self.negocio, cliente=self.cliente, servicio=self.servicio,
            fecha_hora_inicio=ini, fecha_hora_fin=ini + timedelta(minutes=30), estado=estado)


class CrudAtencionTests(BaseAtencionTest):
    def test_crear_atencion(self):
        resp = self.client.post(self.url(), {
            'accion': 'atencion', 'fecha': timezone.localdate().isoformat(),
            'descripcion': 'Limpieza profunda', 'producto_accion': 'aplicado',
            'producto_libre': 'Mascarilla', 'producto_cantidad': 1, 'producto_precio': '0',
        }, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(RegistroAtencion.objects.filter(cliente=self.cliente).count(), 1)
        reg = RegistroAtencion.objects.get(cliente=self.cliente)
        self.assertEqual(reg.descripcion, 'Limpieza profunda')
        self.assertEqual(reg.producto_texto, 'Mascarilla')

    def test_editar_no_duplica(self):
        reg = RegistroAtencion.objects.create(
            negocio=self.negocio, cliente=self.cliente, fecha=timezone.localdate(),
            descripcion='Original', producto_cantidad=1)
        self.client.post(self.url(), {
            'accion': 'atencion', 'atencion_id': reg.id,
            'fecha': timezone.localdate().isoformat(), 'descripcion': 'Editada',
            'producto_accion': 'ninguno', 'producto_cantidad': 1, 'producto_precio': '0',
        }, follow=True)
        self.assertEqual(RegistroAtencion.objects.filter(cliente=self.cliente).count(), 1)
        reg.refresh_from_db()
        self.assertEqual(reg.descripcion, 'Editada')

    def test_eliminar(self):
        reg = RegistroAtencion.objects.create(
            negocio=self.negocio, cliente=self.cliente, fecha=timezone.localdate(),
            descripcion='Borrar')
        self.client.post(self.url(), {'accion': 'eliminar_atencion', 'atencion_id': reg.id}, follow=True)
        self.assertFalse(RegistroAtencion.objects.filter(pk=reg.id).exists())

    def test_prefill_desde_turno(self):
        turno = self._turno(dias=-2)
        resp = self.client.get(f'{self.url()}?turno={turno.id}')
        self.assertContains(resp, 'collapse show')
        self.assertContains(resp, f'value="{turno.id}" selected')


class VentaProductoTests(BaseAtencionTest):
    def test_precio_autocompleta_y_suma_gastado(self):
        self.client.post(self.url(), {
            'accion': 'atencion', 'fecha': timezone.localdate().isoformat(),
            'descripcion': 'Venta', 'producto': self.producto.id,
            'producto_accion': 'vendido', 'producto_cantidad': 2, 'producto_precio': '0',
        }, follow=True)
        reg = RegistroAtencion.objects.get(cliente=self.cliente)
        self.assertEqual(reg.producto_precio, self.producto.precio)   # tomado del catalogo
        self.assertEqual(reg.producto_total, self.producto.precio * 2)
        self.assertEqual(ficha_cliente(self.cliente)['total_gastado'], self.producto.precio * 2)

    def test_aplicado_no_suma_gastado(self):
        RegistroAtencion.objects.create(
            negocio=self.negocio, cliente=self.cliente, fecha=timezone.localdate(),
            descripcion='Aplicado', producto=self.producto, producto_accion='aplicado',
            producto_cantidad=1, producto_precio=74)
        self.assertEqual(ficha_cliente(self.cliente)['total_gastado'], 0)


class ControlesTests(BaseAtencionTest):
    def _atencion_con_control(self, dias_control):
        return RegistroAtencion.objects.create(
            negocio=self.negocio, cliente=self.cliente, turno=self._turno(dias=-30),
            servicio=self.servicio, fecha=timezone.localdate() - timedelta(days=20),
            descripcion='Control', proximo_control=timezone.localdate() + timedelta(days=dias_control))

    def test_control_vencido_aparece(self):
        self._atencion_con_control(dias_control=-1)
        pendientes = controles_pendientes(self.negocio)
        self.assertEqual(len(pendientes), 1)
        self.assertTrue(pendientes[0].vencido)

    def test_control_lejano_no_aparece(self):
        self._atencion_con_control(dias_control=60)
        self.assertEqual(len(controles_pendientes(self.negocio)), 0)

    def test_excluye_si_ya_volvio(self):
        self._atencion_con_control(dias_control=-1)
        self._turno(dias=0, estado=Turno.Estado.ATENDIDO)  # volvio hoy (>= control)
        self.assertEqual(len(controles_pendientes(self.negocio)), 0)

    def test_generar_seguimientos_crea_control(self):
        at = self._atencion_con_control(dias_control=-1)
        call_command('generar_seguimientos')
        self.assertTrue(RecordatorioWhatsApp.objects.filter(
            turno=at.turno, tipo=RecordatorioWhatsApp.Tipo.CONTROL).exists())

    def test_no_manda_control_si_tiene_cita_futura(self):
        at = self._atencion_con_control(dias_control=-1)
        self._turno(dias=5, estado=Turno.Estado.CONFIRMADO)  # cita futura
        call_command('generar_seguimientos')
        self.assertFalse(RecordatorioWhatsApp.objects.filter(
            turno=at.turno, tipo=RecordatorioWhatsApp.Tipo.CONTROL).exists())

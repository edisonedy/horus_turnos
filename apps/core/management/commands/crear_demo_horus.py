from datetime import time

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.agenda.models import PreguntaFrecuente, Producto, PromocionWhatsApp, Servicio
from apps.negocios.models import ConfiguracionNegocioBot, HorarioAtencion, Negocio
from apps.whatsapp_api.models import ConfiguracionWhatsApp


class Command(BaseCommand):
    help = 'Crea superusuario edison/edison y datos de ejemplo para HORUS TURNOS.'

    def handle(self, *args, **options):
        User = get_user_model()
        usuario, creado_usuario = User.objects.get_or_create(
            username='edison',
            defaults={'email': 'edison@example.com', 'is_staff': True, 'is_superuser': True},
        )
        usuario.is_staff = True
        usuario.is_superuser = True
        usuario.set_password('edison')
        usuario.save(update_fields=['is_staff', 'is_superuser', 'password'])

        negocio, creado_negocio = Negocio.objects.get_or_create(
            slug='barberia-demo-horus',
            defaults={
                'propietario': usuario,
                'nombre': 'Barbería Demo HORUS',
                'telefono_principal': '593999999999',
                'telefono_whatsapp': '593999999999',
                'direccion': 'Av. Principal 123 y Calle Demo',
                'descripcion': 'Negocio demo para probar HORUS TURNOS por WhatsApp.',
                'activo': True,
            },
        )
        if negocio.propietario_id != usuario.id:
            negocio.propietario = usuario
            negocio.save(update_fields=['propietario'])

        config_bot, _ = ConfiguracionNegocioBot.objects.get_or_create(
            negocio=negocio,
            defaults={
                'telefono_notificacion_dueno': negocio.telefono_whatsapp,
                'notificar_dueno_whatsapp': True,
            },
        )
        config_bot.mensaje_bienvenida = (
            'Hola, soy la recepción virtual de {negocio}. '
            'Puedo ayudarte a agendar, consultar precios, ver productos, promociones o hablar con una persona.'
        )
        if not config_bot.telefono_notificacion_dueno:
            config_bot.telefono_notificacion_dueno = negocio.telefono_whatsapp
        config_bot.notificar_dueno_whatsapp = True
        config_bot.save(update_fields=['mensaje_bienvenida', 'telefono_notificacion_dueno', 'notificar_dueno_whatsapp'])

        servicios = [
            ('Corte de cabello', 30, 5),
            ('Barba', 20, 3),
            ('Limpieza facial', 60, 20),
        ]
        for nombre, duracion, precio in servicios:
            Servicio.objects.get_or_create(
                negocio=negocio,
                nombre=nombre,
                defaults={
                    'descripcion': f'Servicio demo: {nombre}',
                    'duracion_minutos': duracion,
                    'precio': precio,
                    'activo': True,
                },
            )

        productos = [
            (
                'Shampoo profesional',
                'Shampoo para mantener el cabello limpio y con mejor acabado despues del corte.',
                12.50,
                8,
            ),
            (
                'Cera para peinar',
                'Cera de fijacion media para peinados con acabado natural.',
                7.00,
                15,
            ),
            (
                'Kit barba',
                'Kit basico para cuidado de barba: aceite, peine y balsamo.',
                18.00,
                5,
            ),
        ]
        for nombre, descripcion, precio, stock in productos:
            Producto.objects.get_or_create(
                negocio=negocio,
                nombre=nombre,
                defaults={
                    'descripcion': descripcion,
                    'precio': precio,
                    'stock': stock,
                    'activo': True,
                    'permite_pedido_whatsapp': True,
                },
            )

        preguntas = [
            (
                '¿Aceptan transferencia?',
                'Si, aceptamos efectivo y transferencia. El negocio confirma los datos de pago antes de cerrar el pedido o turno.',
                'pago pagos transferencia efectivo metodo metodos',
                1,
            ),
            (
                '¿Atienden sin cita?',
                'Recomendamos agendar para asegurar disponibilidad. Si escribes "agendar", puedo buscar un horario libre.',
                'sin cita cita disponibilidad atender atienden',
                2,
            ),
            (
                '¿Tienen domicilio?',
                'Por ahora atendemos en el local. Si necesitas algo especial, escribe "humano" y el negocio te responde.',
                'domicilio envio entrega local',
                3,
            ),
            (
                '¿Dónde están ubicados?',
                f'Estamos ubicados en {negocio.direccion}.',
                'ubicacion ubicados direccion donde llegar',
                4,
            ),
        ]
        for pregunta, respuesta, palabras_clave, orden in preguntas:
            PreguntaFrecuente.objects.get_or_create(
                negocio=negocio,
                pregunta=pregunta,
                defaults={
                    'respuesta': respuesta,
                    'palabras_clave': palabras_clave,
                    'orden': orden,
                    'activo': True,
                },
            )

        promociones = [
            (
                'Combo corte + barba',
                'Agenda corte y barba juntos y pregunta por precio especial en caja.',
                'COMBOBARBA',
                1,
            ),
            (
                'Producto recomendado',
                'Llévate una cera para peinar junto con tu corte y conserva mejor el acabado.',
                'CERA7',
                2,
            ),
        ]
        for titulo, descripcion, codigo, orden in promociones:
            PromocionWhatsApp.objects.get_or_create(
                negocio=negocio,
                titulo=titulo,
                defaults={
                    'descripcion': descripcion,
                    'codigo': codigo,
                    'orden': orden,
                    'activo': True,
                },
            )

        for dia in range(0, 6):
            HorarioAtencion.objects.get_or_create(
                negocio=negocio,
                dia_semana=dia,
                hora_inicio=time(9, 0),
                hora_fin=time(18, 0),
                defaults={'activo': True},
            )

        ConfiguracionWhatsApp.objects.get_or_create(
            negocio=negocio,
            defaults={
                'phone_number_id': 'CONFIGURA_PHONE_NUMBER_ID',
                'business_account_id': 'CONFIGURA_BUSINESS_ACCOUNT_ID',
                'access_token': 'CONFIGURA_ACCESS_TOKEN',
                'verify_token': 'horus_verify_token_demo',
                'numero_whatsapp': negocio.telefono_whatsapp,
                'activo': False,
            },
        )

        self.stdout.write(self.style.SUCCESS('Superusuario: edison / edison'))
        self.stdout.write(self.style.SUCCESS(f'Negocio demo: {negocio.nombre}'))
        self.stdout.write(self.style.SUCCESS('Servicios demo: Corte de cabello, Barba, Limpieza facial'))
        self.stdout.write(self.style.SUCCESS('Productos demo: Shampoo profesional, Cera para peinar, Kit barba'))
        self.stdout.write(self.style.SUCCESS('Preguntas frecuentes demo: pagos, cita, domicilio, ubicacion'))
        self.stdout.write(self.style.SUCCESS('Promociones demo: Combo corte + barba, Producto recomendado'))
        self.stdout.write(self.style.SUCCESS('Horarios demo: lunes a sábado, 09:00 a 18:00'))
        self.stdout.write(self.style.WARNING('Configura WhatsApp API real en el panel antes de enviar mensajes.'))

from datetime import time

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.agenda.models import PreguntaFrecuente, Producto, PromocionWhatsApp, Servicio
from apps.negocios.models import ConfiguracionNegocioBot, HorarioAtencion, Negocio
from apps.whatsapp_api.models import ConfiguracionWhatsApp

SLUG = 'daya-facial-care'
WHATSAPP = '19297731659'


class Command(BaseCommand):
    help = 'Crea/actualiza el negocio Daya Facial Care con sus servicios, productos y horarios reales.'

    def handle(self, *args, **options):
        User = get_user_model()
        usuario, _ = User.objects.get_or_create(
            username='daya',
            defaults={'email': 'contacto@dayafacialcare.com', 'is_staff': True, 'is_superuser': True,
                      'first_name': 'Erika', 'last_name': 'Dayana'},
        )
        usuario.is_staff = True
        usuario.is_superuser = True
        usuario.set_password('daya')
        usuario.save()

        negocio, _ = Negocio.objects.get_or_create(
            slug=SLUG,
            defaults={
                'propietario': usuario,
                'nombre': 'Daya Facial Care',
                'telefono_principal': '+1 929-773-1659',
                'telefono_whatsapp': WHATSAPP,
                'direccion': '105-05 Northern Blvd, Flushing, NY 11368',
                'descripcion': (
                    'Más de 7 años de experiencia ofreciendo tratamientos faciales y estéticos '
                    'personalizados que realzan tu belleza natural y tu confianza, en un ambiente '
                    'cómodo y profesional en Queens, NY.'
                ),
                'activo': True,
            },
        )
        negocio.propietario = usuario
        negocio.nombre = 'Daya Facial Care'
        negocio.telefono_principal = '+1 929-773-1659'
        negocio.telefono_whatsapp = WHATSAPP
        negocio.direccion = '105-05 Northern Blvd, Flushing, NY 11368'
        negocio.activo = True
        negocio.save()

        # Instalación single-tenant: Daya es el único negocio activo.
        otros = Negocio.objects.exclude(pk=negocio.pk).filter(activo=True)
        desactivados = otros.update(activo=False)
        if desactivados:
            self.stdout.write(self.style.WARNING(f'Otros negocios desactivados: {desactivados}'))

        config_bot, _ = ConfiguracionNegocioBot.objects.get_or_create(negocio=negocio)
        config_bot.mensaje_bienvenida = (
            'Hola, soy la recepción virtual de Daya Facial Care 💆‍♀️. '
            'Puedo ayudarte a agendar tu cita, ver tratamientos y precios, productos, '
            'promociones o hablar con Erika directamente.'
        )
        config_bot.telefono_notificacion_dueno = WHATSAPP
        config_bot.notificar_dueno_whatsapp = True
        config_bot.save()

        servicios = [
            ('Limpieza Facial Profesional', 'Limpieza profunda para una piel radiante y saludable.', 60, 0),
            ('Tratamiento para Acné', 'Tratamiento especializado para controlar y eliminar el acné.', 60, 0),
            ('Tratamiento de Hiperpigmentación', 'Reduce manchas y unifica el tono de tu piel.', 60, 0),
            ('Rejuvenecimiento Facial', 'Tratamiento para una piel más firme y joven.', 75, 0),
            ('Depilación Láser (Laser Hair Removal)', 'Eliminación de vello de forma segura y duradera.', 45, 0),
            ('Lifting de Pestañas', 'Realza la curvatura natural de tus pestañas.', 60, 0),
            ('Diseño de Cejas 3D + Pigmento Semipermanente', 'Cejas perfectas con técnica 3D y pigmento semipermanente.', 90, 0),
            ('Depilación con Cera', 'Depilación con cera para un acabado suave.', 30, 0),
        ]
        for nombre, descripcion, duracion, precio in servicios:
            Servicio.objects.update_or_create(
                negocio=negocio, nombre=nombre,
                defaults={'descripcion': descripcion, 'duracion_minutos': duracion,
                          'precio': precio, 'activo': True},
            )

        productos = [
            ('Crema Anti-Pigment', 'Crema para reducir manchas e hiperpigmentación.', 51.00, 10),
            ('Vitamina C', 'Sérum de Vitamina C para iluminar y proteger la piel.', 43.00, 10),
            ('Tea Tree Oil', 'Aceite de árbol de té, ideal para piel con acné.', 32.00, 10),
            ('Kit Green Tea para piel luminosa', 'Kit de té verde para una piel luminosa y fresca.', 115.00, 8),
            ('Kit para piel Acneica', 'Kit completo para el cuidado de piel acneica.', 125.00, 8),
            ('Colágeno', 'Colágeno para nutrir y dar firmeza a la piel.', 74.00, 10),
        ]
        for nombre, descripcion, precio, stock in productos:
            Producto.objects.update_or_create(
                negocio=negocio, nombre=nombre,
                defaults={'descripcion': descripcion, 'precio': precio, 'stock': stock,
                          'activo': True, 'permite_pedido_whatsapp': True},
            )

        preguntas = [
            ('¿Dónde están ubicados?',
             'Estamos en 105-05 Northern Blvd, Flushing, NY 11368. ¡Te esperamos!',
             'ubicacion ubicados direccion donde llegar local', 1),
            ('¿Cómo agendo una cita?',
             'Escribe "agendar" o el tratamiento que deseas (por ejemplo "limpieza facial") y te busco un horario disponible.',
             'agendar cita reservar turno hora disponibilidad', 2),
            ('¿Qué métodos de pago aceptan?',
             'Aceptamos efectivo y tarjeta. Confirmamos los detalles de pago antes de tu cita.',
             'pago pagos tarjeta efectivo metodo metodos', 3),
            ('¿Tienen promociones?',
             'Sí. Escribe "promociones" para ver las ofertas activas. Suscríbete y obtén 10% de descuento en servicios.',
             'promocion promociones descuento oferta ofertas', 4),
            ('¿Cuáles son sus redes sociales?',
             'Instagram: @dayafacialcare · TikTok: @erika_dayana1 · Facebook: Daya Facial Care.',
             'redes instagram tiktok facebook social', 5),
        ]
        for pregunta, respuesta, palabras_clave, orden in preguntas:
            PreguntaFrecuente.objects.update_or_create(
                negocio=negocio, pregunta=pregunta,
                defaults={'respuesta': respuesta, 'palabras_clave': palabras_clave,
                          'orden': orden, 'activo': True},
            )

        PromocionWhatsApp.objects.update_or_create(
            negocio=negocio, titulo='10% de descuento en servicios',
            defaults={'descripcion': 'Suscríbete y recibe 10% de descuento en tu próximo tratamiento facial.',
                      'codigo': 'BIENVENIDA10', 'orden': 1, 'activo': True},
        )

        # Lunes a viernes 10:00-20:00, sábado y domingo 11:00-18:00
        horarios = {0: (10, 20), 1: (10, 20), 2: (10, 20), 3: (10, 20), 4: (10, 20),
                    5: (11, 18), 6: (11, 18)}
        for dia, (h_ini, h_fin) in horarios.items():
            HorarioAtencion.objects.update_or_create(
                negocio=negocio, dia_semana=dia,
                defaults={'hora_inicio': time(h_ini, 0), 'hora_fin': time(h_fin, 0), 'activo': True},
            )

        ConfiguracionWhatsApp.objects.get_or_create(
            negocio=negocio,
            defaults={
                'phone_number_id': 'CONFIGURA_PHONE_NUMBER_ID',
                'business_account_id': 'CONFIGURA_BUSINESS_ACCOUNT_ID',
                'access_token': 'CONFIGURA_ACCESS_TOKEN',
                'verify_token': 'daya_verify_token',
                'numero_whatsapp': WHATSAPP,
                'activo': False,
            },
        )

        self.stdout.write(self.style.SUCCESS('Negocio: Daya Facial Care'))
        self.stdout.write(self.style.SUCCESS('Admin: daya / daya'))
        self.stdout.write(self.style.SUCCESS(f'Servicios: {len(servicios)} · Productos: {len(productos)}'))
        self.stdout.write(self.style.WARNING('Configura el WhatsApp API real en el panel antes de enviar mensajes.'))

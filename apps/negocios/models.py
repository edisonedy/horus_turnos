from django.conf import settings
from django.db import models
from django.utils.text import slugify


class Negocio(models.Model):
    propietario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='negocios')
    nombre = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    telefono_principal = models.CharField(max_length=32)
    telefono_whatsapp = models.CharField(max_length=32, blank=True)
    direccion = models.TextField(blank=True)
    descripcion = models.TextField(blank=True)
    logo = models.ImageField(upload_to='negocios/logos/', blank=True, null=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nombre']
        verbose_name = 'negocio'
        verbose_name_plural = 'negocios'

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.nombre) or 'negocio'
            slug = base_slug
            counter = 2
            while Negocio.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base_slug}-{counter}'
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre


class Sucursal(models.Model):
    negocio = models.ForeignKey(Negocio, on_delete=models.CASCADE, related_name='sucursales')
    nombre = models.CharField(max_length=160)
    direccion = models.TextField(blank=True)
    telefono = models.CharField(max_length=32, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['nombre']
        verbose_name = 'sucursal'
        verbose_name_plural = 'sucursales'

    def __str__(self):
        return f'{self.nombre} - {self.negocio.nombre}'


class HorarioAtencion(models.Model):
    class DiaSemana(models.IntegerChoices):
        LUNES = 0, 'Lunes'
        MARTES = 1, 'Martes'
        MIERCOLES = 2, 'Miércoles'
        JUEVES = 3, 'Jueves'
        VIERNES = 4, 'Viernes'
        SABADO = 5, 'Sábado'
        DOMINGO = 6, 'Domingo'

    negocio = models.ForeignKey(Negocio, on_delete=models.CASCADE, related_name='horarios_atencion')
    sucursal = models.ForeignKey(Sucursal, on_delete=models.CASCADE, related_name='horarios_atencion', blank=True, null=True)
    dia_semana = models.PositiveSmallIntegerField(choices=DiaSemana.choices)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['dia_semana', 'hora_inicio']
        verbose_name = 'horario de atención'
        verbose_name_plural = 'horarios de atención'

    def __str__(self):
        return f'{self.negocio.nombre} - {self.get_dia_semana_display()} {self.hora_inicio:%H:%M}-{self.hora_fin:%H:%M}'


class ConfiguracionNegocioBot(models.Model):
    negocio = models.OneToOneField(Negocio, on_delete=models.CASCADE, related_name='configuracion_bot')
    mensaje_bienvenida = models.TextField(
        default='Hola, soy la recepción virtual de {negocio}. Puedo ayudarte a agendar, consultar precios, ver productos, promociones o hablar con una persona.'
    )
    mensaje_fuera_horario = models.TextField(
        default='En este momento estamos fuera de horario. Puedes dejar tu solicitud y te responderemos pronto.'
    )
    permite_agendar_automatico = models.BooleanField(default=True)
    requiere_confirmacion_manual = models.BooleanField(default=False)
    envia_recordatorio_24h = models.BooleanField(default=True)
    envia_recordatorio_2h = models.BooleanField(default=True)
    notificar_dueno_whatsapp = models.BooleanField(default=True)
    telefono_notificacion_dueno = models.CharField(max_length=32, blank=True)

    class Meta:
        verbose_name = 'configuración del bot del negocio'
        verbose_name_plural = 'configuraciones del bot del negocio'

    def __str__(self):
        return f'Bot - {self.negocio.nombre}'

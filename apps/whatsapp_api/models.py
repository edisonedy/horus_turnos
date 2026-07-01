from django.db import models


class ConfiguracionWhatsApp(models.Model):
    negocio = models.OneToOneField('negocios.Negocio', on_delete=models.CASCADE, related_name='configuracion_whatsapp')
    phone_number_id = models.CharField(max_length=128)
    business_account_id = models.CharField(max_length=128, blank=True)
    access_token = models.TextField()
    verify_token = models.CharField(max_length=255)
    app_secret = models.CharField(
        max_length=255,
        blank=True,
        help_text='App Secret de la app de Meta. Si se define, se valida la firma X-Hub-Signature-256 del webhook.',
    )
    numero_whatsapp = models.CharField(max_length=32, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'configuración WhatsApp'
        verbose_name_plural = 'configuraciones WhatsApp'

    def __str__(self):
        return f'WhatsApp - {self.negocio.nombre}'


class MensajeWhatsApp(models.Model):
    class Tipo(models.TextChoices):
        ENTRANTE = 'entrante', 'Entrante'
        SALIENTE = 'saliente', 'Saliente'

    class Estado(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente'
        ENVIADO = 'enviado', 'Enviado'
        ENTREGADO = 'entregado', 'Entregado'
        LEIDO = 'leido', 'Leído'
        ERROR = 'error', 'Error'

    negocio = models.ForeignKey('negocios.Negocio', on_delete=models.CASCADE, related_name='mensajes_whatsapp')
    cliente = models.ForeignKey('agenda.Cliente', on_delete=models.SET_NULL, related_name='mensajes_whatsapp', blank=True, null=True)
    turno = models.ForeignKey('agenda.Turno', on_delete=models.SET_NULL, related_name='mensajes_whatsapp', blank=True, null=True)
    tipo = models.CharField(max_length=16, choices=Tipo.choices)
    telefono = models.CharField(max_length=32)
    mensaje = models.TextField(blank=True)
    whatsapp_message_id = models.CharField(max_length=128, blank=True)
    estado = models.CharField(max_length=16, choices=Estado.choices, default=Estado.PENDIENTE)
    payload = models.JSONField(default=dict, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_creacion']
        indexes = [
            models.Index(fields=['negocio', 'telefono']),
            models.Index(fields=['whatsapp_message_id']),
        ]
        verbose_name = 'mensaje WhatsApp'
        verbose_name_plural = 'mensajes WhatsApp'

    def __str__(self):
        return f'{self.get_tipo_display()} {self.telefono} - {self.fecha_creacion:%Y-%m-%d %H:%M}'


class ConversacionWhatsApp(models.Model):
    class Estado(models.TextChoices):
        INICIO = 'inicio', 'Inicio'
        MENU_PRINCIPAL = 'menu_principal', 'Menú principal'
        ESPERANDO_SERVICIO = 'esperando_servicio', 'Esperando servicio'
        ESPERANDO_FECHA = 'esperando_fecha', 'Esperando fecha'
        ESPERANDO_HORA = 'esperando_hora', 'Esperando hora'
        ESPERANDO_CONFIRMACION_TURNO = 'esperando_confirmacion_turno', 'Esperando confirmación de turno'
        ESPERANDO_PRODUCTO = 'esperando_producto', 'Esperando producto'
        ESPERANDO_CANTIDAD_PRODUCTO = 'esperando_cantidad_producto', 'Esperando cantidad de producto'
        ESPERANDO_CONFIRMACION_PEDIDO = 'esperando_confirmacion_pedido', 'Esperando confirmación de pedido'
        ESPERANDO_REAGENDAR_FECHA = 'esperando_reagendar_fecha', 'Esperando reagendar fecha'
        ESPERANDO_REAGENDAR_HORA = 'esperando_reagendar_hora', 'Esperando reagendar hora'
        ESPERANDO_CANCELACION = 'esperando_cancelacion', 'Esperando cancelación'
        ESPERANDO_CONFIRMACION_CANCELACION = 'esperando_confirmacion_cancelacion', 'Esperando confirmación de cancelación'
        ESPERANDO_HUMANO = 'esperando_humano', 'Esperando humano'
        FINALIZADO = 'finalizado', 'Finalizado'

    negocio = models.ForeignKey('negocios.Negocio', on_delete=models.CASCADE, related_name='conversaciones_whatsapp')
    cliente = models.ForeignKey('agenda.Cliente', on_delete=models.CASCADE, related_name='conversaciones_whatsapp')
    estado = models.CharField(max_length=48, choices=Estado.choices, default=Estado.INICIO)
    datos = models.JSONField(default=dict, blank=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-actualizado']
        constraints = [
            models.UniqueConstraint(fields=['negocio', 'cliente'], name='conversacion_unica_por_negocio_cliente')
        ]
        verbose_name = 'conversación WhatsApp'
        verbose_name_plural = 'conversaciones WhatsApp'

    def __str__(self):
        return f'{self.cliente} - {self.estado}'


class RecordatorioWhatsApp(models.Model):
    class Tipo(models.TextChoices):
        CONFIRMACION = 'confirmacion', 'Confirmación'
        HORAS_24 = '24h', '24 horas'
        HORAS_2 = '2h', '1 hora'
        POST_CITA = 'post_cita', 'Post cita'
        NO_ASISTIO = 'no_asistio', 'No asistió'
        REACTIVACION = 'reactivacion', 'Reactivación'

    turno = models.ForeignKey('agenda.Turno', on_delete=models.CASCADE, related_name='recordatorios_whatsapp')
    tipo = models.CharField(max_length=24, choices=Tipo.choices)
    mensaje = models.TextField()
    fecha_programada = models.DateTimeField()
    enviado = models.BooleanField(default=False)
    fecha_envio = models.DateTimeField(blank=True, null=True)
    intentos = models.PositiveIntegerField(default=0)
    error = models.TextField(blank=True)

    class Meta:
        ordering = ['fecha_programada']
        constraints = [
            models.UniqueConstraint(fields=['turno', 'tipo'], name='recordatorio_unico_por_turno_tipo')
        ]
        indexes = [models.Index(fields=['enviado', 'fecha_programada'])]
        verbose_name = 'recordatorio WhatsApp'
        verbose_name_plural = 'recordatorios WhatsApp'

    def __str__(self):
        return f'{self.turno} - {self.tipo}'


class ErrorWebhookWhatsApp(models.Model):
    negocio = models.ForeignKey('negocios.Negocio', on_delete=models.SET_NULL, related_name='errores_webhook_whatsapp', blank=True, null=True)
    phone_number_id = models.CharField(max_length=128, blank=True)
    error = models.TextField()
    payload = models.JSONField(default=dict, blank=True)
    resuelto = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_creacion']
        verbose_name = 'error de webhook WhatsApp'
        verbose_name_plural = 'errores de webhook WhatsApp'

    def __str__(self):
        return f'Webhook error {self.fecha_creacion:%Y-%m-%d %H:%M}'

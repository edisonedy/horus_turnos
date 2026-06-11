from django.db import models


class Profesional(models.Model):
    negocio = models.ForeignKey('negocios.Negocio', on_delete=models.CASCADE, related_name='profesionales')
    sucursal = models.ForeignKey('negocios.Sucursal', on_delete=models.SET_NULL, related_name='profesionales', blank=True, null=True)
    nombre = models.CharField(max_length=160)
    telefono = models.CharField(max_length=32, blank=True)
    especialidad = models.CharField(max_length=160, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['nombre']
        verbose_name = 'profesional'
        verbose_name_plural = 'profesionales'

    def __str__(self):
        return f'{self.nombre} - {self.negocio.nombre}'


class Servicio(models.Model):
    negocio = models.ForeignKey('negocios.Negocio', on_delete=models.CASCADE, related_name='servicios')
    nombre = models.CharField(max_length=160)
    descripcion = models.TextField(blank=True)
    duracion_minutos = models.PositiveIntegerField(default=30)
    precio = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['nombre']
        verbose_name = 'servicio'
        verbose_name_plural = 'servicios'

    def __str__(self):
        return f'{self.nombre} - {self.negocio.nombre}'


class Producto(models.Model):
    negocio = models.ForeignKey('negocios.Negocio', on_delete=models.CASCADE, related_name='productos')
    nombre = models.CharField(max_length=160)
    descripcion = models.TextField(blank=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stock = models.PositiveIntegerField(default=0)
    activo = models.BooleanField(default=True)
    permite_pedido_whatsapp = models.BooleanField(default=True)

    class Meta:
        ordering = ['nombre']
        verbose_name = 'producto'
        verbose_name_plural = 'productos'

    def __str__(self):
        return f'{self.nombre} - {self.negocio.nombre}'


class PreguntaFrecuente(models.Model):
    negocio = models.ForeignKey('negocios.Negocio', on_delete=models.CASCADE, related_name='preguntas_frecuentes')
    pregunta = models.CharField(max_length=220)
    respuesta = models.TextField()
    palabras_clave = models.CharField(max_length=255, blank=True)
    orden = models.PositiveIntegerField(default=0)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['orden', 'pregunta']
        verbose_name = 'pregunta frecuente'
        verbose_name_plural = 'preguntas frecuentes'

    def __str__(self):
        return f'{self.pregunta} - {self.negocio.nombre}'


class PromocionWhatsApp(models.Model):
    negocio = models.ForeignKey('negocios.Negocio', on_delete=models.CASCADE, related_name='promociones_whatsapp')
    titulo = models.CharField(max_length=160)
    descripcion = models.TextField()
    codigo = models.CharField(max_length=40, blank=True)
    fecha_inicio = models.DateField(blank=True, null=True)
    fecha_fin = models.DateField(blank=True, null=True)
    orden = models.PositiveIntegerField(default=0)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['orden', 'titulo']
        verbose_name = 'promoción WhatsApp'
        verbose_name_plural = 'promociones WhatsApp'

    def __str__(self):
        return f'{self.titulo} - {self.negocio.nombre}'


class Cliente(models.Model):
    negocio = models.ForeignKey('negocios.Negocio', on_delete=models.CASCADE, related_name='clientes')
    nombre = models.CharField(max_length=160, blank=True)
    telefono = models.CharField(max_length=32)
    email = models.EmailField(blank=True)
    observacion = models.TextField(blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_creacion']
        constraints = [
            models.UniqueConstraint(fields=['negocio', 'telefono'], name='cliente_unico_por_negocio_telefono')
        ]
        verbose_name = 'cliente'
        verbose_name_plural = 'clientes'

    def __str__(self):
        nombre = self.nombre or self.telefono
        return f'{nombre} - {self.negocio.nombre}'


class PedidoWhatsApp(models.Model):
    class Estado(models.TextChoices):
        NUEVO = 'nuevo', 'Nuevo'
        CONTACTADO = 'contactado', 'Contactado'
        ENTREGADO = 'entregado', 'Entregado'
        CANCELADO = 'cancelado', 'Cancelado'

    negocio = models.ForeignKey('negocios.Negocio', on_delete=models.CASCADE, related_name='pedidos_whatsapp')
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='pedidos_whatsapp')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name='pedidos_whatsapp')
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    estado = models.CharField(max_length=24, choices=Estado.choices, default=Estado.NUEVO)
    observacion = models.TextField(blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_creacion']
        verbose_name = 'pedido WhatsApp'
        verbose_name_plural = 'pedidos WhatsApp'

    def __str__(self):
        return f'{self.cliente} - {self.producto.nombre} x {self.cantidad}'


class Turno(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente'
        CONFIRMADO = 'confirmado', 'Confirmado'
        REAGENDADO = 'reagendado', 'Reagendado'
        CANCELADO = 'cancelado', 'Cancelado'
        ATENDIDO = 'atendido', 'Atendido'
        NO_ASISTIO = 'no_asistio', 'No asistió'

    class Origen(models.TextChoices):
        WHATSAPP = 'whatsapp', 'WhatsApp'
        PANEL = 'panel', 'Panel'
        MANUAL = 'manual', 'Manual'

    negocio = models.ForeignKey('negocios.Negocio', on_delete=models.CASCADE, related_name='turnos')
    sucursal = models.ForeignKey('negocios.Sucursal', on_delete=models.SET_NULL, related_name='turnos', blank=True, null=True)
    profesional = models.ForeignKey(Profesional, on_delete=models.SET_NULL, related_name='turnos', blank=True, null=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='turnos')
    servicio = models.ForeignKey(Servicio, on_delete=models.PROTECT, related_name='turnos')
    fecha_hora_inicio = models.DateTimeField()
    fecha_hora_fin = models.DateTimeField()
    estado = models.CharField(max_length=24, choices=Estado.choices, default=Estado.PENDIENTE)
    origen = models.CharField(max_length=24, choices=Origen.choices, default=Origen.WHATSAPP)
    observacion = models.TextField(blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['fecha_hora_inicio']
        indexes = [
            models.Index(fields=['negocio', 'fecha_hora_inicio']),
            models.Index(fields=['cliente', 'estado']),
            models.Index(fields=['profesional', 'fecha_hora_inicio']),
        ]
        verbose_name = 'turno'
        verbose_name_plural = 'turnos'

    def __str__(self):
        return f'{self.cliente} - {self.servicio.nombre} - {self.fecha_hora_inicio:%Y-%m-%d %H:%M}'


class ListaEspera(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente'
        NOTIFICADO = 'notificado', 'Notificado'
        TOMADO = 'tomado', 'Tomado'
        CANCELADO = 'cancelado', 'Cancelado'

    negocio = models.ForeignKey('negocios.Negocio', on_delete=models.CASCADE, related_name='lista_espera')
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='lista_espera')
    servicio = models.ForeignKey(Servicio, on_delete=models.CASCADE, related_name='lista_espera')
    fecha_deseada = models.DateField()
    estado = models.CharField(max_length=24, choices=Estado.choices, default=Estado.PENDIENTE)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['fecha_deseada', 'fecha_creacion']
        verbose_name = 'lista de espera'
        verbose_name_plural = 'listas de espera'

    def __str__(self):
        return f'{self.cliente} - {self.servicio.nombre} - {self.fecha_deseada}'


class BloqueoHorario(models.Model):
    negocio = models.ForeignKey('negocios.Negocio', on_delete=models.CASCADE, related_name='bloqueos_horario')
    sucursal = models.ForeignKey('negocios.Sucursal', on_delete=models.SET_NULL, related_name='bloqueos_horario', blank=True, null=True)
    profesional = models.ForeignKey(Profesional, on_delete=models.SET_NULL, related_name='bloqueos_horario', blank=True, null=True)
    fecha_hora_inicio = models.DateTimeField()
    fecha_hora_fin = models.DateTimeField()
    motivo = models.CharField(max_length=255, blank=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['fecha_hora_inicio']
        indexes = [models.Index(fields=['negocio', 'activo', 'fecha_hora_inicio'])]
        verbose_name = 'bloqueo de horario'
        verbose_name_plural = 'bloqueos de horario'

    def __str__(self):
        return f'{self.negocio.nombre} - {self.fecha_hora_inicio:%Y-%m-%d %H:%M}'

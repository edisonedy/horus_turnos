from django import forms
from django.utils import timezone
from .models import BloqueoHorario, Cliente, PedidoWhatsApp, PreguntaFrecuente, Producto, Profesional, PromocionWhatsApp, RegistroAtencion, Servicio, Turno


class BootstrapModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css_class = 'form-check-input' if isinstance(field.widget, forms.CheckboxInput) else 'form-control'
            existing = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = f'{existing} {css_class}'.strip()


class ProfesionalForm(BootstrapModelForm):
    class Meta:
        model = Profesional
        fields = ['sucursal', 'nombre', 'telefono', 'especialidad', 'activo']

    def __init__(self, *args, negocio=None, **kwargs):
        super().__init__(*args, **kwargs)
        if negocio:
            self.fields['sucursal'].queryset = negocio.sucursales.filter(activo=True)
        self.fields['sucursal'].required = False


class ServicioForm(BootstrapModelForm):
    class Meta:
        model = Servicio
        fields = ['nombre', 'descripcion', 'duracion_minutos', 'precio', 'activo']
        widgets = {'descripcion': forms.Textarea(attrs={'rows': 2})}


class ProductoForm(BootstrapModelForm):
    class Meta:
        model = Producto
        fields = ['nombre', 'descripcion', 'precio', 'stock', 'activo', 'permite_pedido_whatsapp']
        widgets = {'descripcion': forms.Textarea(attrs={'rows': 2})}


class PreguntaFrecuenteForm(BootstrapModelForm):
    class Meta:
        model = PreguntaFrecuente
        fields = ['pregunta', 'respuesta', 'palabras_clave', 'orden', 'activo']
        widgets = {
            'respuesta': forms.Textarea(attrs={'rows': 3}),
            'palabras_clave': forms.TextInput(attrs={'placeholder': 'Ej: horario, pago, domicilio'}),
        }


class PromocionWhatsAppForm(BootstrapModelForm):
    class Meta:
        model = PromocionWhatsApp
        fields = ['titulo', 'descripcion', 'codigo', 'fecha_inicio', 'fecha_fin', 'orden', 'activo']
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 3}),
            'fecha_inicio': forms.DateInput(attrs={'type': 'date'}),
            'fecha_fin': forms.DateInput(attrs={'type': 'date'}),
        }


class ClienteForm(BootstrapModelForm):
    class Meta:
        model = Cliente
        fields = ['nombre', 'telefono', 'email', 'observacion']
        widgets = {'observacion': forms.Textarea(attrs={'rows': 2})}


class TurnoForm(BootstrapModelForm):
    class Meta:
        model = Turno
        fields = ['sucursal', 'profesional', 'cliente', 'servicio', 'fecha_hora_inicio', 'fecha_hora_fin', 'estado', 'origen', 'observacion']
        widgets = {
            'fecha_hora_inicio': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'fecha_hora_fin': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'observacion': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, negocio=None, **kwargs):
        super().__init__(*args, **kwargs)
        if negocio:
            self.fields['sucursal'].queryset = negocio.sucursales.filter(activo=True)
            self.fields['profesional'].queryset = Profesional.objects.filter(negocio=negocio, activo=True)
            self.fields['cliente'].queryset = Cliente.objects.filter(negocio=negocio)
            self.fields['servicio'].queryset = Servicio.objects.filter(negocio=negocio, activo=True)
        self.fields['sucursal'].required = False
        self.fields['profesional'].required = False


class PedidoWhatsAppForm(BootstrapModelForm):
    class Meta:
        model = PedidoWhatsApp
        fields = ['estado', 'observacion']
        widgets = {'observacion': forms.Textarea(attrs={'rows': 2})}


class RegistroAtencionForm(BootstrapModelForm):
    class Meta:
        model = RegistroAtencion
        fields = ['fecha', 'turno', 'servicio', 'descripcion', 'producto', 'producto_libre',
                  'producto_accion', 'producto_cantidad', 'producto_precio', 'profesional',
                  'proximo_control', 'foto_antes', 'foto_despues']
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date'}),
            'proximo_control': forms.DateInput(attrs={'type': 'date'}),
            'descripcion': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Ej: Limpieza facial profunda + extracción. Piel reaccionó bien.'}),
            'producto_libre': forms.TextInput(attrs={'placeholder': 'Producto fuera del catálogo (opcional)'}),
        }

    def __init__(self, *args, negocio=None, cliente=None, **kwargs):
        super().__init__(*args, **kwargs)
        if negocio:
            self.fields['servicio'].queryset = Servicio.objects.filter(negocio=negocio, activo=True)
            self.fields['producto'].queryset = Producto.objects.filter(negocio=negocio, activo=True)
            self.fields['profesional'].queryset = Profesional.objects.filter(negocio=negocio, activo=True)
        if cliente is not None:
            self.fields['turno'].queryset = cliente.turnos.select_related('servicio').order_by('-fecha_hora_inicio')
        for nombre in ['turno', 'servicio', 'producto', 'profesional', 'proximo_control', 'foto_antes', 'foto_despues']:
            self.fields[nombre].required = False
        self.fields['turno'].empty_label = 'Sin cita asociada'
        self.fields['servicio'].empty_label = 'Sin servicio'
        self.fields['producto'].empty_label = 'Ninguno del catálogo'
        self.fields['profesional'].empty_label = 'Sin asignar'
        # los ImageField usan clase de input file, no form-control
        for nombre in ['foto_antes', 'foto_despues']:
            self.fields[nombre].widget.attrs['class'] = 'form-control'
        if not self.instance.pk and not self.initial.get('fecha'):
            self.fields['fecha'].initial = timezone.localdate()


class BloqueoHorarioForm(BootstrapModelForm):
    class Meta:
        model = BloqueoHorario
        fields = ['sucursal', 'profesional', 'fecha_hora_inicio', 'fecha_hora_fin', 'motivo', 'activo']
        widgets = {
            'fecha_hora_inicio': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'fecha_hora_fin': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def __init__(self, *args, negocio=None, **kwargs):
        super().__init__(*args, **kwargs)
        if negocio:
            self.fields['sucursal'].queryset = negocio.sucursales.filter(activo=True)
            self.fields['profesional'].queryset = Profesional.objects.filter(negocio=negocio, activo=True)
        self.fields['sucursal'].required = False
        self.fields['profesional'].required = False

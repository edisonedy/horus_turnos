from django import forms
from .models import ConfiguracionNegocioBot, HorarioAtencion, Negocio, Sucursal


class BootstrapModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css_class = 'form-check-input' if isinstance(field.widget, forms.CheckboxInput) else 'form-control'
            existing = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = f'{existing} {css_class}'.strip()


class NegocioForm(BootstrapModelForm):
    class Meta:
        model = Negocio
        fields = [
            'nombre',
            'slug',
            'telefono_principal',
            'telefono_whatsapp',
            'direccion',
            'descripcion',
            'logo',
            'activo',
        ]


class SucursalForm(BootstrapModelForm):
    class Meta:
        model = Sucursal
        fields = ['nombre', 'direccion', 'telefono', 'activo']


class HorarioAtencionForm(BootstrapModelForm):
    class Meta:
        model = HorarioAtencion
        fields = ['sucursal', 'dia_semana', 'hora_inicio', 'hora_fin', 'activo']
        widgets = {
            'hora_inicio': forms.TimeInput(attrs={'type': 'time'}),
            'hora_fin': forms.TimeInput(attrs={'type': 'time'}),
        }

    def __init__(self, *args, negocio=None, **kwargs):
        super().__init__(*args, **kwargs)
        if negocio:
            self.fields['sucursal'].queryset = Sucursal.objects.filter(negocio=negocio, activo=True)
        self.fields['sucursal'].required = False


class ConfiguracionNegocioBotForm(BootstrapModelForm):
    class Meta:
        model = ConfiguracionNegocioBot
        fields = [
            'mensaje_bienvenida',
            'mensaje_fuera_horario',
            'permite_agendar_automatico',
            'requiere_confirmacion_manual',
            'envia_recordatorio_24h',
            'envia_recordatorio_2h',
            'notificar_dueno_whatsapp',
            'telefono_notificacion_dueno',
        ]
        widgets = {
            'mensaje_bienvenida': forms.Textarea(attrs={'rows': 3}),
            'mensaje_fuera_horario': forms.Textarea(attrs={'rows': 3}),
        }

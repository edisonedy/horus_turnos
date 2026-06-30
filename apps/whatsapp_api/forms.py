from django import forms
from .models import ConfiguracionWhatsApp


class ConfiguracionWhatsAppForm(forms.ModelForm):
    class Meta:
        model = ConfiguracionWhatsApp
        fields = [
            'phone_number_id',
            'business_account_id',
            'access_token',
            'verify_token',
            'app_secret',
            'numero_whatsapp',
            'activo',
        ]
        widgets = {
            'access_token': forms.PasswordInput(render_value=True),
            'verify_token': forms.TextInput(),
            'app_secret': forms.PasswordInput(render_value=True),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css_class = 'form-check-input' if isinstance(field.widget, forms.CheckboxInput) else 'form-control'
            existing = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = f'{existing} {css_class}'.strip()

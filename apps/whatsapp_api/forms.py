from django import forms

from apps.core.forms import BootstrapModelForm
from .models import ConfiguracionWhatsApp


class ConfiguracionWhatsAppForm(BootstrapModelForm):
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

"""Registra (override) la URL del webhook directamente en la cuenta de WhatsApp (WABA),
usando el token y el business_account_id de la configuración activa. Útil cuando el
túnel cambia de URL: así no hay que entrar a Meta a mano.

Uso:  python manage.py registrar_webhook https://TU-TUNEL/whatsapp/webhook/
"""
import requests
from django.conf import settings
from django.core.management.base import BaseCommand

from apps.whatsapp_api.models import ConfiguracionWhatsApp


class Command(BaseCommand):
    help = 'Registra la URL del webhook en la cuenta de WhatsApp (override) con el token activo.'

    def add_arguments(self, parser):
        parser.add_argument('url', help='URL completa del webhook (termina en /whatsapp/webhook/)')

    def handle(self, *args, **options):
        url = options['url']
        cfg = ConfiguracionWhatsApp.objects.filter(activo=True).first()
        if not cfg or not cfg.access_token or not cfg.business_account_id:
            self.stderr.write(self.style.ERROR(
                'No hay configuración WhatsApp activa con token y business_account_id. '
                'Configúrala en el panel (/panel/whatsapp/).'))
            return

        verify = cfg.verify_token or settings.WHATSAPP_VERIFY_TOKEN
        version = settings.WHATSAPP_GRAPH_API_VERSION
        endpoint = f'https://graph.facebook.com/{version}/{cfg.business_account_id}/subscribed_apps'
        try:
            resp = requests.post(
                endpoint,
                headers={'Authorization': f'Bearer {cfg.access_token}'},
                json={'override_callback_uri': url, 'verify_token': verify},
                timeout=20,
            )
        except requests.RequestException as exc:
            self.stderr.write(self.style.ERROR(f'Error de red: {exc}'))
            return

        if resp.ok and resp.json().get('success'):
            self.stdout.write(self.style.SUCCESS(f'Webhook registrado: {url}'))
        else:
            self.stderr.write(self.style.ERROR(f'Falló ({resp.status_code}): {resp.text[:200]}'))

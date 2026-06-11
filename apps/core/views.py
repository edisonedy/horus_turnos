from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.core.selectors import resumen_dashboard
from apps.negocios.selectors import obtener_negocio_usuario
from apps.whatsapp_api.models import ConfiguracionWhatsApp


def landing(request):
    configuracion = ConfiguracionWhatsApp.objects.filter(activo=True).first()
    numero_demo = configuracion.numero_whatsapp if configuracion else ''
    return render(request, 'core/landing.html', {
        'public_page': True,
        'numero_demo': numero_demo,
    })


def demo(request):
    configuracion = ConfiguracionWhatsApp.objects.filter(activo=True).select_related('negocio').first()
    numero_demo = configuracion.numero_whatsapp if configuracion else ''
    texto_demo = 'Hola'
    wa_link = f'https://wa.me/{numero_demo}?text={texto_demo}' if numero_demo else ''
    return render(request, 'core/demo.html', {
        'public_page': True,
        'configuracion': configuracion,
        'numero_demo': numero_demo,
        'texto_demo': texto_demo,
        'wa_link': wa_link,
    })


@login_required
def dashboard(request):
    negocio = obtener_negocio_usuario(request.user)
    contexto = {'negocio': negocio, **resumen_dashboard(negocio)}
    return render(request, 'core/dashboard.html', contexto)

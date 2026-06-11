from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET

from apps.negocios.selectors import obtener_negocio_usuario
from .forms import ConfiguracionWhatsAppForm
from .models import ConfiguracionWhatsApp, ConversacionWhatsApp
from .selectors import conversaciones_negocio, errores_webhook_negocio, mensajes_conversacion, recordatorios_negocio
from .services import WhatsAppService


@login_required
@require_GET
def probar_envio_whatsapp(request):
    telefono = request.GET.get('telefono', '').strip()
    if not telefono:
        return JsonResponse({
            'ok': False,
            'error': 'Debe enviar el parámetro telefono. Ejemplo: /whatsapp/probar-envio/?telefono=59399XXXXXXX',
        }, status=400)

    resultado = WhatsAppService().enviar_template_hello_world(telefono)
    status = 200 if resultado.get('ok') else 400
    return JsonResponse(resultado, status=status)


@login_required
def configuracion_whatsapp(request):
    negocio = obtener_negocio_usuario(request.user)
    if not negocio:
        messages.warning(request, 'Primero configura un negocio.')
        return redirect('configuracion_negocio')

    configuracion = ConfiguracionWhatsApp.objects.filter(negocio=negocio).first()
    if request.method == 'POST':
        form = ConfiguracionWhatsAppForm(request.POST, instance=configuracion)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.negocio = negocio
            obj.save()
            messages.success(request, 'Configuración WhatsApp guardada.')
            return redirect('configuracion_whatsapp')
    else:
        form = ConfiguracionWhatsAppForm(instance=configuracion)

    webhook_url = request.build_absolute_uri('/whatsapp/webhook/')
    return render(request, 'whatsapp_api/configuracion.html', {
        'negocio': negocio,
        'form': form,
        'webhook_url': webhook_url,
    })


@login_required
def conversaciones(request):
    negocio = obtener_negocio_usuario(request.user)
    if not negocio:
        return redirect('configuracion_negocio')
    return render(request, 'whatsapp_api/conversaciones.html', {
        'negocio': negocio,
        'conversaciones': conversaciones_negocio(negocio),
    })


@login_required
def conversacion_detalle(request, conversacion_id):
    negocio = obtener_negocio_usuario(request.user)
    if not negocio:
        return redirect('configuracion_negocio')
    conversacion = get_object_or_404(ConversacionWhatsApp, pk=conversacion_id, negocio=negocio)
    return render(request, 'whatsapp_api/conversacion_detalle.html', {
        'negocio': negocio,
        'conversacion': conversacion,
        'mensajes': mensajes_conversacion(negocio, conversacion.cliente),
    })


@login_required
def recordatorios(request):
    negocio = obtener_negocio_usuario(request.user)
    if not negocio:
        return redirect('configuracion_negocio')
    return render(request, 'whatsapp_api/recordatorios.html', {
        'negocio': negocio,
        'recordatorios': recordatorios_negocio(negocio)[:200],
    })


@login_required
def errores_webhook(request):
    negocio = obtener_negocio_usuario(request.user)
    if not negocio:
        return redirect('configuracion_negocio')
    return render(request, 'whatsapp_api/errores.html', {
        'negocio': negocio,
        'errores': errores_webhook_negocio(negocio)[:200],
    })

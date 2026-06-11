from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.negocios.forms import ConfiguracionNegocioBotForm, HorarioAtencionForm, NegocioForm
from apps.negocios.models import ConfiguracionNegocioBot, HorarioAtencion
from apps.negocios.selectors import horarios_activos, obtener_configuracion_bot, obtener_negocio_usuario


@login_required
def configuracion_negocio(request):
    negocio = obtener_negocio_usuario(request.user)
    bot_config = obtener_configuracion_bot(negocio) if negocio else None

    if request.method == 'POST':
        negocio_form = NegocioForm(request.POST, request.FILES, instance=negocio)
        bot_form = ConfiguracionNegocioBotForm(request.POST, instance=bot_config) if bot_config else None
        negocio_valido = negocio_form.is_valid()
        bot_valido = True if bot_form is None else bot_form.is_valid()
        if negocio_valido and bot_valido:
            negocio_guardado = negocio_form.save(commit=False)
            if not negocio_guardado.pk:
                negocio_guardado.propietario = request.user
            negocio_guardado.save()
            if bot_form:
                bot = bot_form.save(commit=False)
                bot.negocio = negocio_guardado
                bot.save()
            else:
                ConfiguracionNegocioBot.objects.get_or_create(negocio=negocio_guardado)
            messages.success(request, 'Configuración del negocio guardada.')
            return redirect('configuracion_negocio')
    else:
        negocio_form = NegocioForm(instance=negocio)
        bot_form = ConfiguracionNegocioBotForm(instance=bot_config) if bot_config else None

    return render(request, 'negocios/configuracion.html', {
        'negocio': negocio,
        'negocio_form': negocio_form,
        'bot_form': bot_form,
    })


@login_required
def horarios(request, horario_id=None):
    negocio = obtener_negocio_usuario(request.user)
    if not negocio:
        messages.warning(request, 'Primero configura un negocio.')
        return redirect('configuracion_negocio')

    horario = None
    if horario_id:
        horario = get_object_or_404(HorarioAtencion, pk=horario_id, negocio=negocio)

    if request.method == 'POST':
        form = HorarioAtencionForm(request.POST, instance=horario, negocio=negocio)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.negocio = negocio
            obj.save()
            messages.success(request, 'Horario guardado.')
            return redirect('horarios')
    else:
        form = HorarioAtencionForm(instance=horario, negocio=negocio)

    return render(request, 'negocios/horarios.html', {
        'negocio': negocio,
        'form': form,
        'horario_editando': horario,
        'horarios': horarios_activos(negocio),
    })

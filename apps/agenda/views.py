from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.agenda.forms import PedidoWhatsAppForm, PreguntaFrecuenteForm, ProductoForm, ProfesionalForm, PromocionWhatsAppForm, RegistroAtencionForm, ServicioForm, TurnoForm
from apps.agenda.models import Cliente, PedidoWhatsApp, PreguntaFrecuente, Producto, Profesional, PromocionWhatsApp, RegistroAtencion, Servicio, Turno
from apps.agenda.selectors import clientes_negocio, clientes_segmentados, conteo_segmentos, ficha_cliente, tablero_retencion, turnos_negocio
from apps.negocios.selectors import obtener_negocio_usuario


def _negocio_requerido(request):
    negocio = obtener_negocio_usuario(request.user)
    if not negocio:
        messages.warning(request, 'Primero configura un negocio.')
    return negocio


@login_required
def servicios(request, servicio_id=None):
    negocio = _negocio_requerido(request)
    if not negocio:
        return redirect('configuracion_negocio')

    servicio = get_object_or_404(Servicio, pk=servicio_id, negocio=negocio) if servicio_id else None
    if request.method == 'POST':
        form = ServicioForm(request.POST, instance=servicio)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.negocio = negocio
            obj.save()
            messages.success(request, 'Servicio guardado.')
            return redirect('servicios')
    else:
        form = ServicioForm(instance=servicio)

    return render(request, 'agenda/servicios.html', {
        'negocio': negocio,
        'form': form,
        'servicio_editando': servicio,
        'servicios': Servicio.objects.filter(negocio=negocio).order_by('nombre'),
    })


@login_required
def productos(request, producto_id=None):
    negocio = _negocio_requerido(request)
    if not negocio:
        return redirect('configuracion_negocio')

    producto = get_object_or_404(Producto, pk=producto_id, negocio=negocio) if producto_id else None
    if request.method == 'POST':
        form = ProductoForm(request.POST, instance=producto)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.negocio = negocio
            obj.save()
            messages.success(request, 'Producto guardado.')
            return redirect('productos')
    else:
        form = ProductoForm(instance=producto)

    return render(request, 'agenda/productos.html', {
        'negocio': negocio,
        'form': form,
        'producto_editando': producto,
        'productos': Producto.objects.filter(negocio=negocio).order_by('nombre'),
    })


@login_required
def preguntas_frecuentes(request, pregunta_id=None):
    negocio = _negocio_requerido(request)
    if not negocio:
        return redirect('configuracion_negocio')

    pregunta = get_object_or_404(PreguntaFrecuente, pk=pregunta_id, negocio=negocio) if pregunta_id else None
    if request.method == 'POST':
        form = PreguntaFrecuenteForm(request.POST, instance=pregunta)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.negocio = negocio
            obj.save()
            messages.success(request, 'Pregunta frecuente guardada.')
            return redirect('preguntas_frecuentes')
    else:
        form = PreguntaFrecuenteForm(instance=pregunta)

    return render(request, 'agenda/preguntas_frecuentes.html', {
        'negocio': negocio,
        'form': form,
        'pregunta_editando': pregunta,
        'preguntas': PreguntaFrecuente.objects.filter(negocio=negocio).order_by('orden', 'pregunta'),
    })


@login_required
def promociones(request, promocion_id=None):
    negocio = _negocio_requerido(request)
    if not negocio:
        return redirect('configuracion_negocio')

    promocion = get_object_or_404(PromocionWhatsApp, pk=promocion_id, negocio=negocio) if promocion_id else None
    if request.method == 'POST':
        form = PromocionWhatsAppForm(request.POST, instance=promocion)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.negocio = negocio
            obj.save()
            messages.success(request, 'Promoción guardada.')
            return redirect('promociones')
    else:
        form = PromocionWhatsAppForm(instance=promocion)

    return render(request, 'agenda/promociones.html', {
        'negocio': negocio,
        'form': form,
        'promocion_editando': promocion,
        'promociones': PromocionWhatsApp.objects.filter(negocio=negocio).order_by('orden', 'titulo'),
    })


@login_required
def pedidos(request, pedido_id=None):
    negocio = _negocio_requerido(request)
    if not negocio:
        return redirect('configuracion_negocio')

    pedido = get_object_or_404(PedidoWhatsApp, pk=pedido_id, negocio=negocio) if pedido_id else None
    if request.method == 'POST' and pedido:
        form = PedidoWhatsAppForm(request.POST, instance=pedido)
        if form.is_valid():
            form.save()
            messages.success(request, 'Pedido actualizado.')
            return redirect('pedidos')
    else:
        form = PedidoWhatsAppForm(instance=pedido) if pedido else None

    return render(request, 'agenda/pedidos.html', {
        'negocio': negocio,
        'form': form,
        'pedido_editando': pedido,
        'pedidos': PedidoWhatsApp.objects.filter(negocio=negocio).select_related('cliente', 'producto')[:150],
    })


@login_required
def profesionales(request, profesional_id=None):
    negocio = _negocio_requerido(request)
    if not negocio:
        return redirect('configuracion_negocio')

    profesional = get_object_or_404(Profesional, pk=profesional_id, negocio=negocio) if profesional_id else None
    if request.method == 'POST':
        form = ProfesionalForm(request.POST, instance=profesional, negocio=negocio)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.negocio = negocio
            obj.save()
            messages.success(request, 'Profesional guardado.')
            return redirect('profesionales')
    else:
        form = ProfesionalForm(instance=profesional, negocio=negocio)

    return render(request, 'agenda/profesionales.html', {
        'negocio': negocio,
        'form': form,
        'profesional_editando': profesional,
        'profesionales': Profesional.objects.filter(negocio=negocio).select_related('sucursal').order_by('nombre'),
    })


@login_required
def clientes(request):
    negocio = _negocio_requerido(request)
    if not negocio:
        return redirect('configuracion_negocio')
    return render(request, 'agenda/clientes.html', {
        'negocio': negocio,
        'clientes': clientes_negocio(negocio),
    })


@login_required
def cliente_detalle(request, cliente_id):
    negocio = _negocio_requerido(request)
    if not negocio:
        return redirect('configuracion_negocio')
    cliente = get_object_or_404(Cliente, pk=cliente_id, negocio=negocio)

    atencion_form = RegistroAtencionForm(negocio=negocio, cliente=cliente)
    if request.method == 'POST':
        accion = request.POST.get('accion', 'ficha')
        if accion == 'eliminar_atencion':
            RegistroAtencion.objects.filter(pk=request.POST.get('atencion_id'), cliente=cliente).delete()
            messages.success(request, 'Registro de atención eliminado.')
            return redirect('cliente_detalle', cliente_id=cliente.id)
        if accion == 'atencion':
            atencion_form = RegistroAtencionForm(request.POST, request.FILES, negocio=negocio, cliente=cliente)
            if atencion_form.is_valid():
                registro = atencion_form.save(commit=False)
                registro.negocio = negocio
                registro.cliente = cliente
                registro.save()
                messages.success(request, 'Atención registrada en el historial.')
                return redirect('cliente_detalle', cliente_id=cliente.id)
        else:
            cliente.nombre = request.POST.get('nombre', '').strip()
            cliente.email = request.POST.get('email', '').strip()
            cliente.observacion = request.POST.get('observacion', '').strip()
            cliente.fecha_nacimiento = request.POST.get('fecha_nacimiento') or None
            cliente.save(update_fields=['nombre', 'email', 'observacion', 'fecha_nacimiento'])
            messages.success(request, 'Ficha del cliente actualizada.')
            return redirect('cliente_detalle', cliente_id=cliente.id)

    wa = f"https://wa.me/{cliente.telefono}" if cliente.telefono else ''
    return render(request, 'agenda/cliente_detalle.html', {
        'negocio': negocio,
        'cliente': cliente,
        'wa_link': wa,
        'atencion_form': atencion_form,
        **ficha_cliente(cliente),
    })


@login_required
def retencion(request):
    negocio = _negocio_requerido(request)
    if not negocio:
        return redirect('configuracion_negocio')
    return render(request, 'agenda/retencion.html', {
        'negocio': negocio,
        **tablero_retencion(negocio),
    })


@login_required
def reactivar(request):
    negocio = _negocio_requerido(request)
    if not negocio:
        return redirect('configuracion_negocio')

    segmento = request.GET.get('segmento', 'dormida')
    if request.method == 'POST':
        segmento = request.POST.get('segmento', 'dormida')
        mensaje = (request.POST.get('mensaje') or '').strip()
        if not mensaje:
            messages.warning(request, 'Escribe un mensaje para enviar.')
            return redirect(f"{reverse('reactivar')}?segmento={segmento}")
        from apps.whatsapp_api.services import WhatsAppService
        servicio = WhatsAppService(negocio=negocio)
        enviados = fallidos = 0
        for cli in clientes_segmentados(negocio, segmento)[:100]:
            nombre = (cli.nombre or '').split(' ')[0] or 'Hola'
            resultado = servicio.enviar_texto(cli.telefono, mensaje.replace('{nombre}', nombre))
            if resultado.get('ok'):
                enviados += 1
            else:
                fallidos += 1
        messages.success(request, f'Enviados: {enviados}. Fallidos: {fallidos}. '
                                  f'(Los fallidos suelen ser por la ventana de 24h de WhatsApp: para llegar a clientas '
                                  f'sin contacto reciente se necesita una plantilla aprobada por Meta.)')
        return redirect(f"{reverse('reactivar')}?segmento={segmento}")

    return render(request, 'agenda/reactivar.html', {
        'negocio': negocio,
        'segmento': segmento,
        'conteo': conteo_segmentos(negocio),
        'clientes': clientes_segmentados(negocio, segmento)[:100],
    })


@login_required
def turnos(request, turno_id=None):
    negocio = _negocio_requerido(request)
    if not negocio:
        return redirect('configuracion_negocio')

    turno = get_object_or_404(Turno, pk=turno_id, negocio=negocio) if turno_id else None
    if request.method == 'POST':
        form = TurnoForm(request.POST, instance=turno, negocio=negocio)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.negocio = negocio
            obj.save()
            messages.success(request, 'Turno guardado.')
            return redirect('turnos')
    else:
        form = TurnoForm(instance=turno, negocio=negocio)

    return render(request, 'agenda/turnos.html', {
        'negocio': negocio,
        'form': form,
        'turno_editando': turno,
        'turnos': turnos_negocio(negocio).order_by('-fecha_hora_inicio')[:100],
    })

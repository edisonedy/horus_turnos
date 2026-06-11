from datetime import datetime

from django.utils import timezone

from apps.agenda.models import ListaEspera, Servicio, Turno
from apps.agenda.selectors import (
    obtener_producto_por_posicion,
    obtener_servicio_por_posicion,
    preguntas_frecuentes_activas,
    promociones_activas,
    productos_activos,
    proximo_turno_activo_cliente,
    servicios_activos,
)
from apps.agenda.services import (
    cancelar_turno,
    crear_lista_espera,
    crear_pedido_whatsapp,
    crear_turno_desde_whatsapp,
    obtener_horarios_disponibles,
    obtener_o_crear_cliente,
    reagendar_turno,
)
from apps.core.utils import formatear_fecha, formatear_hora, normalizar_telefono, normalizar_texto, parsear_fecha_natural, respuesta_afirmativa, respuesta_negativa
from apps.negocios.selectors import obtener_configuracion_bot
from apps.negocios.models import Sucursal
from apps.whatsapp_api.models import ConversacionWhatsApp
from apps.whatsapp_api.selectors import obtener_o_crear_conversacion
from apps.whatsapp_api.services import WhatsAppService
from .ai import interpretar_mensaje
from .owner_bot import procesar_mensaje_dueno

MENU_OPCIONES = [
    'Agendar un turno',
    'Cambiar o reagendar mi turno',
    'Cancelar mi turno',
    'Ver servicios y precios',
    'Ver productos o cotizar',
    'Preguntas frecuentes',
    'Ubicación y horarios',
    'Promociones disponibles',
    'Consultar mi próximo turno',
    'Hablar con una persona',
]

INTENCIONES_AGENDAR = {
    'quiero una cita', 'quiero agendar', 'necesito un turno', 'hay espacio', 'quiero reservar',
    'agendar', 'reservar', 'cita', 'turno', '1'
}
INTENCIONES_REAGENDAR = {
    'reagendar', 'cambiar cita', 'cambiar turno', 'no puedo ir', 'quiero cambiar la hora',
    'quiero cambiar la fecha', 'cambiar', '2'
}
INTENCIONES_CANCELAR = {'cancelar', 'ya no voy', 'quiero cancelar', 'anular cita', 'anular', '3'}
INTENCIONES_SERVICIOS = {'servicios', 'precios de servicios', 'que servicios', 'qué servicios', '4'}
INTENCIONES_PRODUCTOS = {'productos', 'producto', 'catalogo', 'catálogo', 'comprar', 'venta', 'venden', '5'}
INTENCIONES_FAQ = {'preguntas', 'preguntas frecuentes', 'faq', 'dudas', 'formas de pago', 'metodos de pago', 'métodos de pago', 'garantia', 'garantía', 'domicilio', 'envio', 'envío', '6'}
INTENCIONES_UBICACION = {'ubicacion', 'ubicación', 'direccion', 'dirección', 'donde estan', 'dónde están', 'como llego', 'cómo llego', 'horario', 'horarios', '7'}
INTENCIONES_PROMOCIONES = {'promociones', 'promos', 'promo', 'ofertas', 'oferta', 'descuento', 'descuentos', '8'}
INTENCIONES_MI_TURNO = {'mi turno', 'mis turnos', 'mi cita', 'mi reserva', 'proximo turno', 'próximo turno', '9'}
INTENCIONES_HUMANO = {'asesor', 'persona', 'humano', 'hablar con alguien', 'hablar con una persona', 'recepcionista humana', '10'}
INTENCIONES_AYUDA = {
    'ayuda', 'que puedes hacer', 'qué puedes hacer', 'como funciona', 'cómo funciona',
    'opciones', 'recepcionista', 'que haces', 'qué haces', 'informacion', 'información'
}
INTENCIONES_PRECIO = {'precio', 'precios', 'cuanto cuesta', 'cuánto cuesta', 'costo', 'valor', 'vale'}
INTENCIONES_CONSULTA_PRODUCTO = {'tienen', 'tiene', 'hay', 'venden', 'vende', 'disponible', 'stock'}
INTENCIONES_PEDIDO_PRODUCTO = {'comprar', 'cotizar', 'pedido', 'pedir', 'apartar'}
INTENCIONES_CONFIRMAR = {'confirmar', 'confirmo', 'si', 'sí', 'ok', 'voy'}
INTENCIONES_NO_PUEDE = {'no puedo', 'no voy', 'no asistire', 'no asistiré'}
COMANDOS_DUENO = {
    'ayuda',
    'menu dueno',
    'menu dueño',
    'agenda hoy',
    'agenda manana',
    'agenda mañana',
    'turnos pendientes',
    'turnos confirmados',
    'clientes nuevos',
    'resumen dia',
    'resumen día',
    'servicios dueno',
    'servicios dueño',
    'bloquear horario',
    'liberar horario',
}


def procesar_mensaje_entrante(negocio, telefono, texto, nombre=''):
    telefono_normalizado = normalizar_telefono(telefono)
    if es_mensaje_dueno(negocio, telefono_normalizado) and es_comando_dueno(texto):
        return procesar_mensaje_dueno(negocio, telefono_normalizado, texto)
    cliente = obtener_o_crear_cliente(negocio, telefono_normalizado, nombre=nombre)
    return procesar_mensaje_cliente(negocio, cliente, texto)


def procesar_mensaje_cliente(negocio, cliente, texto):
    texto_normalizado = normalizar_texto(texto)
    conversacion = obtener_o_crear_conversacion(negocio, cliente)

    if not texto_normalizado:
        return _mostrar_menu(negocio, cliente, conversacion)

    if texto_normalizado in {'hola', 'buenas', 'buenos dias', 'buenas tardes', 'buenas noches', 'menu', 'inicio'}:
        return _mostrar_menu(negocio, cliente, conversacion)

    if not texto_normalizado.isdigit():
        if _contiene_intencion(texto_normalizado, INTENCIONES_AYUDA):
            return _enviar(negocio, cliente.telefono, _mensaje_recepcionista(negocio))
        if _contiene_intencion(texto_normalizado, INTENCIONES_MI_TURNO):
            return _mostrar_proximo_turno(negocio, cliente)
        if _contiene_intencion(texto_normalizado, INTENCIONES_PROMOCIONES):
            return _enviar(negocio, cliente.telefono, _mensaje_promociones(negocio))
        if _contiene_intencion(texto_normalizado, INTENCIONES_HUMANO):
            return _pasar_a_humano(negocio, cliente, conversacion)

    if conversacion.datos.get('post_cancelacion'):
        if respuesta_afirmativa(texto):
            conversacion.datos = {}
            conversacion.save(update_fields=['datos', 'actualizado'])
            return _iniciar_agendamiento(negocio, cliente, conversacion)
        conversacion.datos = {}
        conversacion.estado = ConversacionWhatsApp.Estado.FINALIZADO
        conversacion.save(update_fields=['estado', 'datos', 'actualizado'])
        return _enviar(negocio, cliente.telefono, 'Entendido. Si necesitas otro turno, escribe agendar.')

    if conversacion.estado == ConversacionWhatsApp.Estado.ESPERANDO_SERVICIO:
        return _seleccionar_servicio(negocio, cliente, conversacion, texto)
    if conversacion.estado == ConversacionWhatsApp.Estado.ESPERANDO_FECHA:
        return _seleccionar_fecha(negocio, cliente, conversacion, texto)
    if conversacion.estado == ConversacionWhatsApp.Estado.ESPERANDO_HORA:
        return _seleccionar_hora(negocio, cliente, conversacion, texto)
    if conversacion.estado == ConversacionWhatsApp.Estado.ESPERANDO_CONFIRMACION_TURNO:
        return _responder_confirmacion_recordatorio(negocio, cliente, conversacion, texto)
    if conversacion.estado == ConversacionWhatsApp.Estado.ESPERANDO_PRODUCTO:
        return _seleccionar_producto(negocio, cliente, conversacion, texto)
    if conversacion.estado == ConversacionWhatsApp.Estado.ESPERANDO_CANTIDAD_PRODUCTO:
        return _seleccionar_cantidad_producto(negocio, cliente, conversacion, texto)
    if conversacion.estado == ConversacionWhatsApp.Estado.ESPERANDO_CONFIRMACION_PEDIDO:
        return _confirmar_pedido(negocio, cliente, conversacion, texto)
    if conversacion.estado == ConversacionWhatsApp.Estado.ESPERANDO_REAGENDAR_FECHA:
        return _seleccionar_fecha_reagendamiento(negocio, cliente, conversacion, texto)
    if conversacion.estado == ConversacionWhatsApp.Estado.ESPERANDO_REAGENDAR_HORA:
        return _seleccionar_hora_reagendamiento(negocio, cliente, conversacion, texto)
    if conversacion.estado == ConversacionWhatsApp.Estado.ESPERANDO_CONFIRMACION_CANCELACION:
        return _confirmar_cancelacion(negocio, cliente, conversacion, texto)
    if conversacion.estado == ConversacionWhatsApp.Estado.ESPERANDO_HUMANO:
        return _enviar(negocio, cliente.telefono, 'Tu solicitud ya fue enviada. Una persona del negocio te ayudará por este chat.')

    respuesta_comercial = _resolver_consulta_comercial(negocio, cliente, texto)
    if respuesta_comercial:
        return respuesta_comercial

    if _contiene_intencion(texto_normalizado, INTENCIONES_MI_TURNO):
        return _mostrar_proximo_turno(negocio, cliente)

    if _contiene_intencion(texto_normalizado, INTENCIONES_PROMOCIONES):
        return _enviar(negocio, cliente.telefono, _mensaje_promociones(negocio))
    if _contiene_intencion(texto_normalizado, INTENCIONES_AYUDA):
        return _enviar(negocio, cliente.telefono, _mensaje_recepcionista(negocio))

    producto_exacto = _producto_exacto_desde_texto(negocio, texto)
    if producto_exacto:
        return _pedir_cantidad_producto(negocio, cliente, conversacion, producto_exacto)

    ai_data = interpretar_mensaje(negocio, texto, conversacion.estado)
    respuesta_inteligente = _resolver_agendamiento_inteligente(negocio, cliente, conversacion, texto, ai_data)
    if respuesta_inteligente:
        return respuesta_inteligente

    if _contiene_intencion(texto_normalizado, INTENCIONES_AGENDAR):
        return _iniciar_agendamiento(negocio, cliente, conversacion)
    if _contiene_intencion(texto_normalizado, INTENCIONES_REAGENDAR) or _contiene_intencion(texto_normalizado, INTENCIONES_NO_PUEDE):
        return _iniciar_reagendamiento(negocio, cliente, conversacion)
    if _contiene_intencion(texto_normalizado, INTENCIONES_CANCELAR):
        return _iniciar_cancelacion(negocio, cliente, conversacion)
    if _contiene_intencion(texto_normalizado, INTENCIONES_SERVICIOS):
        return _enviar(negocio, cliente.telefono, _mensaje_servicios(negocio))
    producto_para_pedido = _producto_desde_texto(negocio, texto)
    if producto_para_pedido and _contiene_intencion(texto_normalizado, INTENCIONES_PEDIDO_PRODUCTO):
        return _pedir_cantidad_producto(negocio, cliente, conversacion, producto_para_pedido)
    if _contiene_intencion(texto_normalizado, INTENCIONES_PRODUCTOS):
        return _iniciar_productos(negocio, cliente, conversacion)
    if _contiene_intencion(texto_normalizado, INTENCIONES_FAQ):
        return _resolver_faq(negocio, cliente, texto)
    if _contiene_intencion(texto_normalizado, INTENCIONES_UBICACION):
        return _enviar(negocio, cliente.telefono, _mensaje_ubicacion(negocio))
    if _contiene_intencion(texto_normalizado, INTENCIONES_HUMANO):
        return _pasar_a_humano(negocio, cliente, conversacion)
    if _contiene_intencion(texto_normalizado, INTENCIONES_CONFIRMAR):
        return _confirmar_proximo_turno(negocio, cliente)

    servicio_directo = _servicio_desde_texto(negocio, texto)
    if servicio_directo:
        return _pedir_fecha_para_servicio(negocio, cliente, conversacion, servicio_directo)

    producto_directo = _producto_desde_texto(negocio, texto)
    if producto_directo:
        return _pedir_cantidad_producto(negocio, cliente, conversacion, producto_directo)

    respuesta_faq = _respuesta_faq_desde_texto(negocio, texto)
    if respuesta_faq:
        return _enviar(negocio, cliente.telefono, respuesta_faq)

    intent = ai_data.get('intent')
    if intent == 'agendar':
        return _iniciar_agendamiento(negocio, cliente, conversacion)
    if intent in {'reagendar', 'no_puede'}:
        return _iniciar_reagendamiento(negocio, cliente, conversacion)
    if intent == 'cancelar':
        return _iniciar_cancelacion(negocio, cliente, conversacion)
    if intent == 'servicios':
        return _enviar(negocio, cliente.telefono, _mensaje_servicios(negocio))
    if intent == 'productos':
        return _iniciar_productos(negocio, cliente, conversacion)
    if intent == 'faq':
        return _resolver_faq(negocio, cliente, texto)
    if intent == 'promociones':
        return _enviar(negocio, cliente.telefono, _mensaje_promociones(negocio))
    if intent == 'mi_turno':
        return _mostrar_proximo_turno(negocio, cliente)
    if intent == 'ayuda':
        return _enviar(negocio, cliente.telefono, _mensaje_recepcionista(negocio))
    if intent == 'ubicacion':
        return _enviar(negocio, cliente.telefono, _mensaje_ubicacion(negocio))
    if intent == 'humano':
        return _pasar_a_humano(negocio, cliente, conversacion)
    if intent == 'confirmar':
        return _confirmar_proximo_turno(negocio, cliente)

    return _mostrar_menu(negocio, cliente, conversacion)


def es_mensaje_dueno(negocio, telefono):
    telefono = normalizar_telefono(telefono)
    candidatos = [negocio.telefono_whatsapp, negocio.telefono_principal]
    config = getattr(negocio, 'configuracion_bot', None)
    if config:
        candidatos.append(config.telefono_notificacion_dueno)
    return telefono in {normalizar_telefono(valor) for valor in candidatos if valor}


def es_comando_dueno(texto):
    texto_normalizado = normalizar_texto(texto)
    return any(
        texto_normalizado == comando or texto_normalizado.startswith(f'{comando} ')
        for comando in COMANDOS_DUENO
    )


def _contiene_intencion(texto_normalizado, intenciones):
    if texto_normalizado in intenciones:
        return True
    return any(intent in texto_normalizado for intent in intenciones if not intent.isdigit())


def _resolver_consulta_comercial(negocio, cliente, texto):
    texto_normalizado = normalizar_texto(texto)
    if texto_normalizado.isdigit():
        return None

    servicio = _servicio_desde_texto(negocio, texto)
    if servicio and _contiene_intencion(texto_normalizado, INTENCIONES_PRECIO):
        return _enviar(negocio, cliente.telefono, _mensaje_precio_servicio(servicio))

    producto = _producto_desde_texto(negocio, texto)
    if producto and (
        _contiene_intencion(texto_normalizado, INTENCIONES_PRECIO)
        or _contiene_intencion(texto_normalizado, INTENCIONES_CONSULTA_PRODUCTO)
    ):
        return _enviar(negocio, cliente.telefono, _mensaje_detalle_producto(producto))

    return None


def _enviar(negocio, telefono, mensaje):
    try:
        WhatsAppService(negocio=negocio).enviar_texto(telefono, mensaje)
    except Exception:
        pass
    return mensaje


def _notificar_dueno(negocio, mensaje):
    try:
        WhatsAppService(negocio=negocio).enviar_notificacion_dueno(negocio, mensaje)
    except Exception:
        pass


def _mostrar_menu(negocio, cliente, conversacion):
    config = obtener_configuracion_bot(negocio)
    encabezado = config.mensaje_bienvenida.format(negocio=negocio.nombre)
    mensaje = (
        f'{encabezado}\n\n'
        'Puedes escribirme como hablarías con recepción. Por ejemplo:\n'
        '- Quiero corte mañana a las 10\n'
        '- ¿Cuánto cuesta barba?\n'
        '- Quiero cambiar mi cita\n'
        '- ¿Tienen promociones?\n'
        '- Quiero comprar cera para peinar\n\n'
        'También puedes elegir una opción:\n\n'
        + '\n'.join(f'{index}. {opcion}' for index, opcion in enumerate(MENU_OPCIONES, start=1))
        + '\n\nSi no sé resolver algo, te paso con una persona.'
    )
    conversacion.estado = ConversacionWhatsApp.Estado.MENU_PRINCIPAL
    conversacion.datos = {}
    conversacion.save(update_fields=['estado', 'datos', 'actualizado'])
    return _enviar(negocio, cliente.telefono, mensaje)


def _mensaje_recepcionista(negocio):
    return (
        f'Soy la recepción virtual de {negocio.nombre}. Puedo ayudarte por aquí mismo, sin formularios.\n\n'
        'Puedo hacer esto:\n'
        '1. Agendar turnos según disponibilidad.\n'
        '2. Decirte servicios, precios y duración.\n'
        '3. Reagendar si no puedes asistir.\n'
        '4. Cancelar tu turno.\n'
        '5. Confirmar asistencia cuando recibas recordatorio.\n'
        '6. Mostrar tu próximo turno.\n'
        '7. Responder preguntas frecuentes: pagos, ubicación, domicilio, horarios.\n'
        '8. Mostrar productos y levantar cotizaciones/pedidos.\n'
        '9. Mostrar promociones activas.\n'
        '10. Avisar al dueño cuando necesites atención humana.\n\n'
        'Puedes escribir natural, por ejemplo:\n'
        '- Necesito una cita para mañana en la tarde\n'
        '- ¿Hay espacio hoy para barba?\n'
        '- ¿Cuánto cuesta limpieza facial?\n'
        '- No puedo ir, quiero cambiar mi cita\n'
        '- ¿Dónde están ubicados?\n'
        '- Quiero ver productos\n'
        '- Quiero hablar con una persona\n\n'
        'Si quieres empezar ahora, dime qué necesitas.'
    )


def _iniciar_agendamiento(negocio, cliente, conversacion):
    conversacion.estado = ConversacionWhatsApp.Estado.ESPERANDO_SERVICIO
    conversacion.datos = {}
    conversacion.save(update_fields=['estado', 'datos', 'actualizado'])
    return _enviar(negocio, cliente.telefono, _mensaje_servicios(negocio, pedir_numero=True))


def _mensaje_servicios(negocio, pedir_numero=False):
    servicios = list(servicios_activos(negocio))
    if not servicios:
        return 'Por ahora no tengo servicios activos configurados. Si necesitas ayuda, escribe "humano" y aviso al negocio.'
    lineas = ['Claro. Estos son los servicios disponibles:', '']
    for index, servicio in enumerate(servicios, start=1):
        lineas.append(f'{index}. {servicio.nombre} - {servicio.duracion_minutos} min - ${servicio.precio}')
    if pedir_numero:
        lineas.append('\nResponde con el número del servicio o escríbeme algo como: "quiero corte mañana a las 10".')
    else:
        lineas.append('\nSi quieres reservar, dime el servicio y el día. Ejemplo: "quiero barba mañana".')
    return '\n'.join(lineas)


def _mensaje_precio_servicio(servicio):
    return (
        f'{servicio.nombre}\n'
        f'Duración: {servicio.duracion_minutos} min\n'
        f'Precio: ${servicio.precio}\n\n'
        f'Si deseas reservar, puedes escribirme: "quiero {servicio.nombre} mañana".'
    )


def _iniciar_productos(negocio, cliente, conversacion):
    mensaje = _mensaje_productos(negocio, pedir_numero=True)
    if mensaje.startswith('Por ahora'):
        return _enviar(negocio, cliente.telefono, mensaje)
    conversacion.estado = ConversacionWhatsApp.Estado.ESPERANDO_PRODUCTO
    conversacion.datos = {}
    conversacion.save(update_fields=['estado', 'datos', 'actualizado'])
    return _enviar(negocio, cliente.telefono, mensaje)


def _mensaje_productos(negocio, pedir_numero=False):
    productos = list(productos_activos(negocio))
    if not productos:
        return 'Por ahora no tengo productos activos configurados. Si buscas algo específico, escribe "humano" y aviso al negocio.'
    lineas = ['Sí. Estos productos están disponibles para cotizar por WhatsApp:', '']
    for index, producto in enumerate(productos, start=1):
        stock = f' - stock: {producto.stock}' if producto.stock else ''
        lineas.append(f'{index}. {producto.nombre} - ${producto.precio}{stock}')
        if producto.descripcion:
            lineas.append(f'   {producto.descripcion[:120]}')
    if pedir_numero:
        lineas.append('\nResponde con el número del producto, o escribe algo como: "quiero comprar cera para peinar".')
    else:
        lineas.append('\nSi quieres cotizar, dime cuál producto y cuántas unidades necesitas.')
    return '\n'.join(lineas)


def _mensaje_promociones(negocio):
    promociones = list(promociones_activas(negocio)[:8])
    if not promociones:
        return 'Por ahora no hay promociones activas. Igual puedo ayudarte con servicios, productos o turnos.'

    lineas = ['Estas son las promociones activas:', '']
    for index, promocion in enumerate(promociones, start=1):
        codigo = f'\nCódigo: {promocion.codigo}' if promocion.codigo else ''
        vigencia = f'\nVálida hasta: {formatear_fecha(promocion.fecha_fin)}' if promocion.fecha_fin else ''
        lineas.append(f'{index}. {promocion.titulo}\n{promocion.descripcion}{codigo}{vigencia}')
    lineas.append('\nSi quieres usar una promoción, dime cuál te interesa y para qué día quieres reservar.')
    return '\n\n'.join(lineas)


def _mensaje_detalle_producto(producto):
    stock = f'\nStock disponible: {producto.stock}' if producto.stock else ''
    accion = 'Si quieres cotizar o reservar, escribe: comprar ' + producto.nombre
    if not producto.permite_pedido_whatsapp:
        accion = 'Si quieres más información, escribe humano.'
    return (
        f'{producto.nombre}\n'
        f'{producto.descripcion or "Producto disponible."}\n'
        f'Precio: ${producto.precio}'
        f'{stock}\n\n'
        f'{accion}'
    )


def _seleccionar_producto(negocio, cliente, conversacion, texto):
    producto = _producto_desde_texto(negocio, texto)
    if not producto:
        return _enviar(negocio, cliente.telefono, 'No logré identificar qué producto necesitas. Te dejo el catálogo para que elijas:\n\n' + _mensaje_productos(negocio, pedir_numero=True))
    return _pedir_cantidad_producto(negocio, cliente, conversacion, producto)


def _producto_desde_texto(negocio, texto):
    texto_normalizado = normalizar_texto(texto)
    if texto_normalizado.isdigit():
        return obtener_producto_por_posicion(negocio, int(texto_normalizado))
    productos = list(productos_activos(negocio))
    for producto in productos:
        nombre_normalizado = normalizar_texto(producto.nombre)
        if nombre_normalizado in texto_normalizado or texto_normalizado in nombre_normalizado:
            return producto

    palabras_texto = {palabra for palabra in texto_normalizado.split() if len(palabra) >= 4}
    for producto in productos:
        palabras_producto = {palabra for palabra in normalizar_texto(producto.nombre).split() if len(palabra) >= 4}
        if palabras_texto.intersection(palabras_producto):
            return producto
    return None


def _producto_exacto_desde_texto(negocio, texto):
    texto_normalizado = normalizar_texto(texto)
    if texto_normalizado.isdigit():
        return None

    for producto in productos_activos(negocio):
        nombre_normalizado = normalizar_texto(producto.nombre)
        if nombre_normalizado in texto_normalizado:
            return producto

        # Si el cliente escribe solo "barba", debe agendar el servicio Barba,
        # no pedir el producto "Kit barba". Para productos aceptamos el match
        # inverso solo cuando el texto trae mas de una palabra.
        if len(texto_normalizado.split()) > 1 and texto_normalizado in nombre_normalizado:
            return producto
    return None


def _pedir_cantidad_producto(negocio, cliente, conversacion, producto):
    if not producto.permite_pedido_whatsapp:
        return _enviar(
            negocio,
            cliente.telefono,
            f'{producto.nombre}\n\n{producto.descripcion or "Producto disponible."}\nPrecio: ${producto.precio}\n\nSi quieres más información, escribe humano.',
        )
    conversacion.estado = ConversacionWhatsApp.Estado.ESPERANDO_CANTIDAD_PRODUCTO
    conversacion.datos = {'producto_id': producto.id}
    conversacion.save(update_fields=['estado', 'datos', 'actualizado'])
    return _enviar(
        negocio,
        cliente.telefono,
        f'Perfecto, revisemos {producto.nombre}.\n\n{producto.descripcion or "Producto disponible."}\nPrecio: ${producto.precio}\n\n¿Cuántas unidades deseas cotizar o reservar?',
    )


def _seleccionar_cantidad_producto(negocio, cliente, conversacion, texto):
    texto_normalizado = normalizar_texto(texto)
    cantidad = int(texto_normalizado) if texto_normalizado.isdigit() else None
    if not cantidad or cantidad < 1:
        return _enviar(negocio, cliente.telefono, 'Indícame la cantidad en número, por favor. Ejemplo: 1, 2 o 3.')

    producto = productos_activos(negocio).filter(pk=conversacion.datos.get('producto_id')).first()
    if not producto:
        return _iniciar_productos(negocio, cliente, conversacion)

    if producto.stock and cantidad > producto.stock:
        return _enviar(negocio, cliente.telefono, f'Tengo registradas {producto.stock} unidades disponibles. ¿Deseas cotizar una cantidad menor?')

    total = producto.precio * cantidad
    conversacion.estado = ConversacionWhatsApp.Estado.ESPERANDO_CONFIRMACION_PEDIDO
    conversacion.datos.update({'cantidad': cantidad})
    conversacion.save(update_fields=['estado', 'datos', 'actualizado'])
    return _enviar(
        negocio,
        cliente.telefono,
        f'Te confirmo la cotización:\n\nProducto: {producto.nombre}\nCantidad: {cantidad}\nTotal estimado: ${total}\n\n¿Deseas que lo registre y avise al negocio? Responde SI o NO.',
    )


def _confirmar_pedido(negocio, cliente, conversacion, texto):
    if respuesta_negativa(texto):
        conversacion.estado = ConversacionWhatsApp.Estado.FINALIZADO
        conversacion.datos = {}
        conversacion.save(update_fields=['estado', 'datos', 'actualizado'])
        return _enviar(negocio, cliente.telefono, 'Sin problema. Si quieres ver el catálogo otra vez, escribe "productos".')

    if not respuesta_afirmativa(texto):
        return _enviar(negocio, cliente.telefono, 'Para dejarlo claro: responde SI para registrar la cotización o NO para cancelarla.')

    producto = productos_activos(negocio).filter(pk=conversacion.datos.get('producto_id')).first()
    cantidad = int(conversacion.datos.get('cantidad') or 1)
    if not producto:
        return _iniciar_productos(negocio, cliente, conversacion)

    pedido = crear_pedido_whatsapp(negocio, cliente, producto, cantidad=cantidad)
    conversacion.estado = ConversacionWhatsApp.Estado.FINALIZADO
    conversacion.datos = {'pedido_id': pedido.id}
    conversacion.save(update_fields=['estado', 'datos', 'actualizado'])
    _notificar_dueno(
        negocio,
        f'Nuevo pedido/cotización por WhatsApp.\n\nCliente: {cliente.nombre or cliente.telefono}\nTeléfono: {cliente.telefono}\nProducto: {producto.nombre}\nCantidad: {cantidad}\nTotal: ${pedido.total}',
    )
    return _enviar(
        negocio,
        cliente.telefono,
        f'Listo, dejé registrada tu cotización #{pedido.id}.\n\nProducto: {producto.nombre}\nCantidad: {cantidad}\nTotal estimado: ${pedido.total}\n\nAvisé al negocio para que confirme disponibilidad, entrega o forma de pago.',
    )


def _resolver_faq(negocio, cliente, texto):
    respuesta = _respuesta_faq_desde_texto(negocio, texto)
    if respuesta:
        return _enviar(negocio, cliente.telefono, respuesta)
    faqs = list(preguntas_frecuentes_activas(negocio)[:8])
    if not faqs:
        return _enviar(negocio, cliente.telefono, 'Aún no tengo preguntas frecuentes configuradas. Si quieres, escribe "humano" y aviso al negocio.')
    lineas = ['Puedo ayudarte con estas dudas frecuentes:', '']
    for index, faq in enumerate(faqs, start=1):
        lineas.append(f'{index}. {faq.pregunta}')
    lineas.append('\nTambién puedes escribir tu pregunta con tus palabras.')
    return _enviar(negocio, cliente.telefono, '\n'.join(lineas))


def _respuesta_faq_desde_texto(negocio, texto):
    texto_normalizado = normalizar_texto(texto)
    if texto_normalizado.isdigit():
        faqs = list(preguntas_frecuentes_activas(negocio))
        index = int(texto_normalizado) - 1
        if 0 <= index < len(faqs):
            faq = faqs[index]
            return f'{faq.pregunta}\n\n{faq.respuesta}'

    palabras_texto = {palabra for palabra in texto_normalizado.split() if len(palabra) >= 4}
    if not palabras_texto:
        return ''

    mejor = None
    mejor_score = 0
    for faq in preguntas_frecuentes_activas(negocio):
        base = f'{faq.pregunta} {faq.palabras_clave}'
        palabras_faq = {palabra for palabra in normalizar_texto(base).split() if len(palabra) >= 4}
        score = len(palabras_texto.intersection(palabras_faq))
        if score > mejor_score:
            mejor = faq
            mejor_score = score
    if mejor and mejor_score:
        return f'{mejor.pregunta}\n\n{mejor.respuesta}'
    return ''


def _seleccionar_servicio(negocio, cliente, conversacion, texto):
    servicio = _servicio_desde_texto(negocio, texto)
    if not servicio:
        ai_data = interpretar_mensaje(negocio, texto, conversacion.estado)
        if ai_data.get('service_index'):
            servicio = obtener_servicio_por_posicion(negocio, ai_data['service_index'])
    if not servicio:
        return _enviar(negocio, cliente.telefono, 'No logré identificar qué servicio deseas. Te dejo las opciones:\n\n' + _mensaje_servicios(negocio, pedir_numero=True))
    return _pedir_fecha_para_servicio(negocio, cliente, conversacion, servicio)


def _servicio_desde_texto(negocio, texto):
    texto_normalizado = normalizar_texto(texto)
    if texto_normalizado.isdigit():
        return obtener_servicio_por_posicion(negocio, int(texto_normalizado))
    servicios = list(Servicio.objects.filter(negocio=negocio, activo=True))
    for servicio in servicios:
        nombre_normalizado = normalizar_texto(servicio.nombre)
        if nombre_normalizado in texto_normalizado or texto_normalizado in nombre_normalizado:
            return servicio

    palabras_texto = {palabra for palabra in texto_normalizado.split() if len(palabra) >= 4}
    for servicio in servicios:
        palabras_servicio = {palabra for palabra in normalizar_texto(servicio.nombre).split() if len(palabra) >= 4}
        if palabras_texto.intersection(palabras_servicio):
            return servicio
    return None


def _pedir_fecha_para_servicio(negocio, cliente, conversacion, servicio):
    conversacion.estado = ConversacionWhatsApp.Estado.ESPERANDO_FECHA
    conversacion.datos = {'servicio_id': servicio.id}
    conversacion.save(update_fields=['estado', 'datos', 'actualizado'])
    return _enviar(
        negocio,
        cliente.telefono,
        f'Perfecto, te ayudo con {servicio.nombre}.\n\n'
        '¿Para qué día deseas el turno?\n'
        'Puedes escribir natural: hoy, mañana, viernes, o una fecha como 10/06/2026.',
    )


def _resolver_agendamiento_inteligente(negocio, cliente, conversacion, texto, ai_data):
    servicio = None
    if ai_data.get('service_index'):
        servicio = obtener_servicio_por_posicion(negocio, ai_data['service_index'])
    if not servicio:
        servicio = _servicio_desde_texto(negocio, texto)

    fecha = parsear_fecha_natural(ai_data.get('date_iso')) if ai_data.get('date_iso') else parsear_fecha_natural(texto)
    hora_texto = ai_data.get('time_hhmm')
    intent = ai_data.get('intent')

    if intent not in {'agendar', 'desconocido', None} and not servicio:
        return None
    if not servicio:
        return None
    if not fecha:
        return _pedir_fecha_para_servicio(negocio, cliente, conversacion, servicio)

    disponibles = obtener_horarios_disponibles(negocio, servicio, fecha)
    if not disponibles:
        conversacion.estado = ConversacionWhatsApp.Estado.ESPERANDO_HORA
        conversacion.datos = {'servicio_id': servicio.id, 'fecha': fecha.isoformat(), 'sin_horarios': True}
        conversacion.save(update_fields=['estado', 'datos', 'actualizado'])
        return _enviar(
            negocio,
            cliente.telefono,
            f'Para {servicio.nombre} no veo horarios disponibles el {formatear_fecha(fecha)}.\n\n'
            '¿Quieres que te deje en lista de espera por si se libera un espacio?',
        )

    horarios_serializados = _serializar_horarios(disponibles)
    if hora_texto:
        seleccion = _horario_desde_texto(horarios_serializados, hora_texto)
        if seleccion:
            return _crear_turno_con_seleccion(negocio, cliente, conversacion, servicio, seleccion)

    conversacion.estado = ConversacionWhatsApp.Estado.ESPERANDO_HORA
    conversacion.datos = {
        'servicio_id': servicio.id,
        'fecha': fecha.isoformat(),
        'horarios': horarios_serializados,
        'sin_horarios': False,
    }
    conversacion.save(update_fields=['estado', 'datos', 'actualizado'])
    mensaje = (
        f'Perfecto. Busqué {servicio.nombre} para el {formatear_fecha(fecha)}.\n\n'
        + _mensaje_horarios(disponibles)
    )
    return _enviar(negocio, cliente.telefono, mensaje)


def _seleccionar_fecha(negocio, cliente, conversacion, texto):
    fecha = parsear_fecha_natural(texto)
    if not fecha:
        ai_data = interpretar_mensaje(negocio, texto, conversacion.estado)
        fecha = parsear_fecha_natural(ai_data.get('date_iso'))
    if not fecha:
        return _enviar(negocio, cliente.telefono, 'No logré entender la fecha. Puedes escribir: hoy, mañana, viernes o una fecha como 10/06/2026.')
    servicio = Servicio.objects.filter(pk=conversacion.datos.get('servicio_id'), negocio=negocio, activo=True).first()
    if not servicio:
        return _iniciar_agendamiento(negocio, cliente, conversacion)
    disponibles = obtener_horarios_disponibles(negocio, servicio, fecha)
    if not disponibles:
        conversacion.estado = ConversacionWhatsApp.Estado.ESPERANDO_HORA
        conversacion.datos.update({'fecha': fecha.isoformat(), 'sin_horarios': True})
        conversacion.save(update_fields=['estado', 'datos', 'actualizado'])
        return _enviar(
            negocio,
            cliente.telefono,
            'No veo horarios disponibles para ese día.\n¿Quieres que te deje en lista de espera si se libera un espacio?',
        )
    conversacion.estado = ConversacionWhatsApp.Estado.ESPERANDO_HORA
    conversacion.datos.update({'fecha': fecha.isoformat(), 'horarios': _serializar_horarios(disponibles), 'sin_horarios': False})
    conversacion.save(update_fields=['estado', 'datos', 'actualizado'])
    return _enviar(negocio, cliente.telefono, _mensaje_horarios(disponibles))


def _seleccionar_hora(negocio, cliente, conversacion, texto):
    if conversacion.datos.get('sin_horarios'):
        return _resolver_lista_espera(negocio, cliente, conversacion, texto)

    seleccion = _horario_desde_texto(conversacion.datos.get('horarios', []), texto)
    if not seleccion:
        ai_data = interpretar_mensaje(negocio, texto, conversacion.estado)
        if ai_data.get('time_hhmm'):
            seleccion = _horario_desde_texto(conversacion.datos.get('horarios', []), ai_data['time_hhmm'])
    if not seleccion:
        return _enviar(negocio, cliente.telefono, 'No logré identificar la hora. Responde con el número de la opción que prefieres.')

    servicio = Servicio.objects.filter(pk=conversacion.datos.get('servicio_id'), negocio=negocio, activo=True).first()
    if not servicio:
        return _iniciar_agendamiento(negocio, cliente, conversacion)
    return _crear_turno_con_seleccion(negocio, cliente, conversacion, servicio, seleccion)


def _crear_turno_con_seleccion(negocio, cliente, conversacion, servicio, seleccion):
    sucursal = Sucursal.objects.filter(pk=seleccion.get('sucursal_id'), negocio=negocio).first() if seleccion.get('sucursal_id') else None
    estado = _estado_inicial_turno(negocio)
    try:
        turno = crear_turno_desde_whatsapp(negocio, cliente, servicio, seleccion['inicio'], sucursal=sucursal, estado=estado)
    except ValueError as exc:
        return _enviar(negocio, cliente.telefono, f'{exc}\nEscribe agendar para buscar otro horario.')

    conversacion.estado = ConversacionWhatsApp.Estado.FINALIZADO
    conversacion.datos = {'turno_id': turno.id}
    conversacion.save(update_fields=['estado', 'datos', 'actualizado'])
    _notificar_dueno(negocio, _mensaje_nuevo_turno_dueno(turno))
    return _enviar(negocio, cliente.telefono, _mensaje_confirmacion_turno(turno))


def _estado_inicial_turno(negocio):
    config = obtener_configuracion_bot(negocio)
    if not config.permite_agendar_automatico or config.requiere_confirmacion_manual:
        return Turno.Estado.PENDIENTE
    return Turno.Estado.CONFIRMADO


def _mensaje_horarios(disponibles):
    lineas = ['Tengo estos horarios disponibles:', '']
    for index, item in enumerate(disponibles, start=1):
        lineas.append(f'{index}. {formatear_hora(item["inicio"])}')
    lineas.append('\nResponde con el número de la hora que prefieres, o escribe la hora si te resulta más cómodo.')
    return '\n'.join(lineas)


def _serializar_horarios(disponibles):
    return [
        {
            'inicio': item['inicio'].isoformat(),
            'fin': item['fin'].isoformat(),
            'sucursal_id': item.get('sucursal_id'),
            'profesional_id': item.get('profesional_id'),
        }
        for item in disponibles
    ]


def _horario_desde_texto(horarios, texto):
    texto_normalizado = normalizar_texto(texto)
    if texto_normalizado.isdigit():
        index = int(texto_normalizado) - 1
        if 0 <= index < len(horarios):
            return _deserializar_horario(horarios[index])
    for item in horarios:
        deserializado = _deserializar_horario(item)
        if formatear_hora(deserializado['inicio']) == texto.strip():
            return deserializado
    return None


def _deserializar_horario(item):
    return {
        'inicio': datetime.fromisoformat(item['inicio']),
        'fin': datetime.fromisoformat(item['fin']),
        'sucursal_id': item.get('sucursal_id'),
        'profesional_id': item.get('profesional_id'),
    }


def _resolver_lista_espera(negocio, cliente, conversacion, texto):
    ai_data = interpretar_mensaje(negocio, texto, conversacion.estado)
    acepta_lista = respuesta_afirmativa(texto) or ai_data.get('waitlist_yes') is True or ai_data.get('intent') == 'lista_espera_si'
    rechaza_lista = respuesta_negativa(texto) or ai_data.get('waitlist_yes') is False or ai_data.get('intent') == 'lista_espera_no'
    if not acepta_lista and rechaza_lista:
        conversacion.estado = ConversacionWhatsApp.Estado.FINALIZADO
        conversacion.datos = {}
        conversacion.save(update_fields=['estado', 'datos', 'actualizado'])
        return _enviar(negocio, cliente.telefono, 'Entendido. Si quieres buscar otra fecha, escríbeme "agendar".')
    if not acepta_lista:
        return _enviar(negocio, cliente.telefono, 'Responde SI para dejarte en lista de espera o NO para buscar otra fecha.')

    servicio = Servicio.objects.filter(pk=conversacion.datos.get('servicio_id'), negocio=negocio).first()
    fecha = parsear_fecha_natural(conversacion.datos.get('fecha'))
    if not servicio or not fecha:
        return _iniciar_agendamiento(negocio, cliente, conversacion)
    lista = crear_lista_espera(negocio, cliente, servicio, fecha)
    conversacion.estado = ConversacionWhatsApp.Estado.FINALIZADO
    conversacion.datos = {'lista_espera_id': lista.id}
    conversacion.save(update_fields=['estado', 'datos', 'actualizado'])
    _notificar_dueno(
        negocio,
        f'Cliente en lista de espera.\n\nCliente: {cliente.nombre or cliente.telefono}\nServicio: {servicio.nombre}\nFecha deseada: {formatear_fecha(fecha)}',
    )
    return _enviar(negocio, cliente.telefono, 'Listo, te dejé en lista de espera. Te avisaremos si se libera un horario.')


def _iniciar_reagendamiento(negocio, cliente, conversacion):
    turno = proximo_turno_activo_cliente(negocio, cliente)
    if not turno:
        return _enviar(negocio, cliente.telefono, 'No encontré un turno activo para reagendar. Si deseas reservar uno nuevo, escribe "agendar".')
    conversacion.estado = ConversacionWhatsApp.Estado.ESPERANDO_REAGENDAR_FECHA
    conversacion.datos = {'turno_id': turno.id, 'servicio_id': turno.servicio_id}
    conversacion.save(update_fields=['estado', 'datos', 'actualizado'])
    return _enviar(
        negocio,
        cliente.telefono,
        f'Encontré este turno a tu nombre:\n\nServicio: {turno.servicio.nombre}\nFecha: {formatear_fecha(turno.fecha_hora_inicio)}\nHora: {formatear_hora(turno.fecha_hora_inicio)}\n\n¿Para qué nueva fecha deseas moverlo?',
    )


def _seleccionar_fecha_reagendamiento(negocio, cliente, conversacion, texto):
    fecha = parsear_fecha_natural(texto)
    if not fecha:
        ai_data = interpretar_mensaje(negocio, texto, conversacion.estado)
        fecha = parsear_fecha_natural(ai_data.get('date_iso'))
    if not fecha:
        return _enviar(negocio, cliente.telefono, 'No logré entender la fecha. Puedes escribir: hoy, mañana, viernes o 10/06/2026.')
    turno = Turno.objects.filter(pk=conversacion.datos.get('turno_id'), negocio=negocio, cliente=cliente).select_related('servicio').first()
    if not turno:
        return _enviar(negocio, cliente.telefono, 'No encontré el turno que quieres mover. Escribe "reagendar" para intentarlo de nuevo.')
    disponibles = obtener_horarios_disponibles(negocio, turno.servicio, fecha, sucursal=turno.sucursal, excluir_turno=turno)
    if not disponibles:
        conversacion.estado = ConversacionWhatsApp.Estado.ESPERANDO_REAGENDAR_HORA
        conversacion.datos.update({'fecha': fecha.isoformat(), 'sin_horarios': True})
        conversacion.save(update_fields=['estado', 'datos', 'actualizado'])
        return _enviar(negocio, cliente.telefono, 'No veo horarios disponibles para ese día.\n¿Quieres que te deje en lista de espera?')
    conversacion.estado = ConversacionWhatsApp.Estado.ESPERANDO_REAGENDAR_HORA
    conversacion.datos.update({'fecha': fecha.isoformat(), 'horarios': _serializar_horarios(disponibles), 'sin_horarios': False})
    conversacion.save(update_fields=['estado', 'datos', 'actualizado'])
    return _enviar(negocio, cliente.telefono, _mensaje_horarios(disponibles))


def _seleccionar_hora_reagendamiento(negocio, cliente, conversacion, texto):
    if conversacion.datos.get('sin_horarios'):
        return _resolver_lista_espera(negocio, cliente, conversacion, texto)

    seleccion = _horario_desde_texto(conversacion.datos.get('horarios', []), texto)
    if not seleccion:
        ai_data = interpretar_mensaje(negocio, texto, conversacion.estado)
        if ai_data.get('time_hhmm'):
            seleccion = _horario_desde_texto(conversacion.datos.get('horarios', []), ai_data['time_hhmm'])
    if not seleccion:
        return _enviar(negocio, cliente.telefono, 'No logré identificar la hora. Responde con el número de la opción que prefieres.')
    turno = Turno.objects.filter(pk=conversacion.datos.get('turno_id'), negocio=negocio, cliente=cliente).select_related('servicio').first()
    if not turno:
        return _enviar(negocio, cliente.telefono, 'No encontré el turno que quieres mover. Escribe "reagendar" para intentarlo de nuevo.')
    try:
        turno = reagendar_turno(turno, seleccion['inicio'], observacion_extra='Reagendado por WhatsApp.')
    except ValueError as exc:
        return _enviar(negocio, cliente.telefono, f'{exc}\nEscribe reagendar para buscar otro horario.')
    conversacion.estado = ConversacionWhatsApp.Estado.FINALIZADO
    conversacion.datos = {'turno_id': turno.id}
    conversacion.save(update_fields=['estado', 'datos', 'actualizado'])
    _notificar_dueno(negocio, _mensaje_reagendado_dueno(turno))
    return _enviar(negocio, cliente.telefono, 'Listo, tu turno fue reagendado.\n\n' + _resumen_turno(turno))


def _iniciar_cancelacion(negocio, cliente, conversacion):
    turno = proximo_turno_activo_cliente(negocio, cliente)
    if not turno:
        return _enviar(negocio, cliente.telefono, 'No encontré un turno activo para cancelar. Si necesitas ayuda, escribe "humano".')
    conversacion.estado = ConversacionWhatsApp.Estado.ESPERANDO_CONFIRMACION_CANCELACION
    conversacion.datos = {'turno_id': turno.id}
    conversacion.save(update_fields=['estado', 'datos', 'actualizado'])
    return _enviar(
        negocio,
        cliente.telefono,
        f'Encontré tu turno:\n\nServicio: {turno.servicio.nombre}\nFecha: {formatear_fecha(turno.fecha_hora_inicio)}\nHora: {formatear_hora(turno.fecha_hora_inicio)}\n\n¿Seguro que deseas cancelarlo?\nResponde SI para cancelarlo o NO para mantenerlo.',
    )


def _confirmar_cancelacion(negocio, cliente, conversacion, texto):
    turno = Turno.objects.filter(pk=conversacion.datos.get('turno_id'), negocio=negocio, cliente=cliente).select_related('servicio').first()
    if not turno:
        conversacion.estado = ConversacionWhatsApp.Estado.FINALIZADO
        conversacion.datos = {}
        conversacion.save(update_fields=['estado', 'datos', 'actualizado'])
        return _enviar(negocio, cliente.telefono, 'No encontré el turno. Escribe "cancelar" para intentarlo de nuevo.')
    if respuesta_afirmativa(texto):
        cancelar_turno(turno)
        conversacion.estado = ConversacionWhatsApp.Estado.FINALIZADO
        conversacion.datos = {'post_cancelacion': True}
        conversacion.save(update_fields=['estado', 'datos', 'actualizado'])
        _notificar_dueno(negocio, _mensaje_cancelado_dueno(turno))
        return _enviar(negocio, cliente.telefono, 'Tu turno fue cancelado.\n¿Deseas que busquemos otro día?')
    if respuesta_negativa(texto):
        conversacion.estado = ConversacionWhatsApp.Estado.FINALIZADO
        conversacion.datos = {}
        conversacion.save(update_fields=['estado', 'datos', 'actualizado'])
        return _enviar(negocio, cliente.telefono, 'Perfecto, tu turno se mantiene activo.')
    return _enviar(negocio, cliente.telefono, 'Responde SI para cancelar o NO para mantener tu turno.')


def _responder_confirmacion_recordatorio(negocio, cliente, conversacion, texto):
    texto_normalizado = normalizar_texto(texto)
    turno = Turno.objects.filter(
        pk=conversacion.datos.get('turno_id'),
        negocio=negocio,
        cliente=cliente,
    ).select_related('servicio').first()
    if not turno:
        conversacion.estado = ConversacionWhatsApp.Estado.FINALIZADO
        conversacion.datos = {}
        conversacion.save(update_fields=['estado', 'datos', 'actualizado'])
        return _enviar(negocio, cliente.telefono, 'No encontré el turno del recordatorio. Escribe agendar si necesitas ayuda.')

    if texto_normalizado in {'1', 'confirmar', 'confirmo', 'si', 'sí', 'voy', 'ok'}:
        turno.estado = Turno.Estado.CONFIRMADO
        turno.save(update_fields=['estado'])
        conversacion.estado = ConversacionWhatsApp.Estado.FINALIZADO
        conversacion.datos = {'turno_id': turno.id}
        conversacion.save(update_fields=['estado', 'datos', 'actualizado'])
        _notificar_dueno(negocio, f'Cliente confirmó asistencia.\n\nCliente: {cliente.nombre or cliente.telefono}\nServicio: {turno.servicio.nombre}\nFecha: {formatear_fecha(turno.fecha_hora_inicio)}\nHora: {formatear_hora(turno.fecha_hora_inicio)}')
        return _enviar(negocio, cliente.telefono, 'Gracias, tu turno queda confirmado. Te esperamos.')

    if texto_normalizado in {'2', 'reagendar', 'cambiar', 'cambiar hora', 'cambiar fecha'}:
        conversacion.estado = ConversacionWhatsApp.Estado.ESPERANDO_REAGENDAR_FECHA
        conversacion.datos = {'turno_id': turno.id, 'servicio_id': turno.servicio_id}
        conversacion.save(update_fields=['estado', 'datos', 'actualizado'])
        return _enviar(negocio, cliente.telefono, 'Sin problema. ¿Para qué nueva fecha deseas mover tu turno?')

    if texto_normalizado in {'3', 'cancelar', 'no voy', 'no puedo'}:
        conversacion.estado = ConversacionWhatsApp.Estado.ESPERANDO_CONFIRMACION_CANCELACION
        conversacion.datos = {'turno_id': turno.id}
        conversacion.save(update_fields=['estado', 'datos', 'actualizado'])
        return _enviar(negocio, cliente.telefono, '¿Seguro que deseas cancelar tu turno? Responde SI para cancelar o NO para mantenerlo.')

    return _enviar(negocio, cliente.telefono, 'Responde 1 para confirmar, 2 para reagendar o 3 para cancelar.')


def _confirmar_proximo_turno(negocio, cliente):
    turno = proximo_turno_activo_cliente(negocio, cliente)
    if not turno:
        return _enviar(negocio, cliente.telefono, 'No encontré un turno activo para confirmar.')
    turno.estado = Turno.Estado.CONFIRMADO
    turno.save(update_fields=['estado'])
    _notificar_dueno(negocio, f'Turno confirmado por WhatsApp.\n\nCliente: {cliente.nombre or cliente.telefono}\nServicio: {turno.servicio.nombre}\nFecha: {formatear_fecha(turno.fecha_hora_inicio)}\nHora: {formatear_hora(turno.fecha_hora_inicio)}')
    return _enviar(negocio, cliente.telefono, 'Gracias. Tu turno queda confirmado.')


def _mostrar_proximo_turno(negocio, cliente):
    turno = proximo_turno_activo_cliente(negocio, cliente)
    if not turno:
        return _enviar(negocio, cliente.telefono, 'No encontré un turno activo a tu nombre. Si deseas reservar, escribe agendar.')
    return _enviar(
        negocio,
        cliente.telefono,
        'Tu próximo turno es:\n\n'
        + _resumen_turno(turno)
        + f'\nEstado: {turno.get_estado_display()}\n\n'
        'Puedes responder confirmar, reagendar o cancelar.',
    )


def _pasar_a_humano(negocio, cliente, conversacion):
    conversacion.estado = ConversacionWhatsApp.Estado.ESPERANDO_HUMANO
    conversacion.save(update_fields=['estado', 'actualizado'])
    _notificar_dueno(negocio, f'Cliente solicita atención humana.\n\nCliente: {cliente.nombre or cliente.telefono}\nTeléfono: {cliente.telefono}')
    return _enviar(negocio, cliente.telefono, 'Claro. Ya avisé al negocio para que una persona te ayude por este chat.')


def _mensaje_ubicacion(negocio):
    if negocio.direccion:
        return f'Estamos ubicados en:\n\n{negocio.direccion}'
    sucursal = negocio.sucursales.filter(activo=True).first()
    if sucursal and sucursal.direccion:
        return f'Estamos ubicados en:\n\n{sucursal.direccion}'
    return 'Aún no hay una dirección configurada para este negocio.'


def _resumen_turno(turno):
    direccion = turno.sucursal.direccion if turno.sucursal and turno.sucursal.direccion else turno.negocio.direccion
    return (
        f'Servicio: {turno.servicio.nombre}\n'
        f'Fecha: {formatear_fecha(turno.fecha_hora_inicio)}\n'
        f'Hora: {formatear_hora(turno.fecha_hora_inicio)}\n'
        f'Dirección: {direccion or "Por confirmar"}'
    )


def _mensaje_confirmacion_turno(turno):
    return 'Listo, tu turno quedó agendado.\n\n' + _resumen_turno(turno) + '\n\nTe enviaremos un recordatorio antes de tu cita. Si necesitas cambiarlo, escribe "reagendar".'


def _mensaje_nuevo_turno_dueno(turno):
    return (
        'Nuevo turno agendado.\n\n'
        f'Cliente: {turno.cliente.nombre or turno.cliente.telefono}\n'
        f'Teléfono: {turno.cliente.telefono}\n'
        f'Servicio: {turno.servicio.nombre}\n'
        f'Fecha: {formatear_fecha(turno.fecha_hora_inicio)}\n'
        f'Hora: {formatear_hora(turno.fecha_hora_inicio)}'
    )


def _mensaje_reagendado_dueno(turno):
    return (
        'Turno reagendado.\n\n'
        f'Cliente: {turno.cliente.nombre or turno.cliente.telefono}\n'
        f'Servicio: {turno.servicio.nombre}\n'
        f'Nueva fecha: {formatear_fecha(turno.fecha_hora_inicio)}\n'
        f'Nueva hora: {formatear_hora(turno.fecha_hora_inicio)}'
    )


def _mensaje_cancelado_dueno(turno):
    return (
        'Turno cancelado.\n\n'
        f'Cliente: {turno.cliente.nombre or turno.cliente.telefono}\n'
        f'Teléfono: {turno.cliente.telefono}\n'
        f'Servicio: {turno.servicio.nombre}\n'
        f'Fecha original: {formatear_fecha(turno.fecha_hora_inicio)}\n'
        f'Hora original: {formatear_hora(turno.fecha_hora_inicio)}'
    )

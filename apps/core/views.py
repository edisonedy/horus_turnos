import csv
from datetime import datetime
from urllib.parse import quote

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone

from apps.core.selectors import reporte_negocio, resumen_dashboard, uso_whatsapp
from apps.negocios.selectors import horarios_activos, negocio_principal, obtener_negocio_usuario


DIAS_SEMANA = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
# Nombres que pide schema.org para los horarios (rich snippet de Google).
DIAS_SCHEMA = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

# Redes de Daya Facial Care (las mismas del sitio oficial).
REDES = [
    {'nombre': 'Instagram', 'icono': 'bi-instagram', 'url': 'https://www.instagram.com/dayafacialcare'},
    {'nombre': 'TikTok', 'icono': 'bi-tiktok', 'url': 'https://www.tiktok.com/@erika_dayana1'},
    {'nombre': 'Facebook', 'icono': 'bi-facebook', 'url': 'https://www.facebook.com/profile.php?id=61579203707901'},
]

# Fotos reales de Daya Facial Care (descargadas del sitio oficial), en static/img/daya/.
# Orden alineado con el comando crear_daya.
IMG_SERVICIOS = [
    'img/daya/srv-daya-facial-care-1.jpg',   # Limpieza facial profesional (mascarilla de carbón)
    'img/daya/srv-hollywood-peel-2.jpg',     # Tratamiento para acné (Hollywood peel)
    'img/daya/srv-microdermoabrasion-2.jpg', # Hiperpigmentación / microdermoabrasión
    'img/daya/srv-dermapen.jpg',             # Rejuvenecimiento facial (dermapen)
    'img/daya/srv-laser-hair-removal.jpg',   # Depilación láser
    'img/daya/srv-lifting-pestanas.jpg',     # Lifting de pestañas
    'img/daya/srv-disenio-cejas.jpg',        # Cejas 3D + pigmento
    'img/daya/srv-daya-facial-care-7.jpg',   # Depilación con cera / facial
]
IMG_PRODUCTOS = [
    'img/daya/prod-crema-anti-pigment.jpeg',  # Crema Anti-Pigment
    'img/daya/prod-vitamina-c.jpeg',          # Vitamina C
    'img/daya/prod-tea-tree-oil.jpeg',        # Tea Tree Oil
    'img/daya/prod-kit-green-tea.jpeg',       # Kit Green Tea
    'img/daya/prod-kit-acneica.jpg',          # Kit piel Acneica
    'img/daya/prod-colageno.jpeg',            # Colágeno
]
# 8 fotos: la primera ocupa doble alto, así el mosaico de 3 columnas queda lleno.
IMG_GALERIA = [
    'img/daya/estudio.jpeg', 'img/daya/srv-daya-facial-care-1.jpg', 'img/daya/srv-hollywood-peel-2.jpg',
    'img/daya/srv-microdermoabrasion-2.jpg', 'img/daya/srv-lifting-pestanas.jpg', 'img/daya/srv-dermapen.jpg',
    'img/daya/srv-disenio-cejas.jpg', 'img/daya/srv-daya-facial-care-7.jpg',
]


def _link_whatsapp(numero, texto):
    """Enlace de WhatsApp con el mensaje ya escrito."""
    if not numero:
        return ''
    return 'https://wa.me/%s?text=%s' % (numero, quote(texto))


def _estado_horario(horarios_hoy, ahora):
    """(abierto_ahora, franja_de_hoy) según los horarios del negocio."""
    if not horarios_hoy:
        return False, None
    for horario in horarios_hoy:
        if horario.hora_inicio <= ahora.time() <= horario.hora_fin:
            return True, horario
    return False, horarios_hoy[0]


def landing(request):
    negocio = negocio_principal()
    numero_wa = ''
    servicios = []
    productos = []
    horarios = []
    faqs = []
    promo = None
    abierto_ahora = False
    horario_hoy = None
    wa_general = ''
    wa_promo = ''

    if negocio:
        numero_wa = negocio.telefono_whatsapp or ''
        wa_general = _link_whatsapp(numero_wa, 'Hola Daya, quiero agendar una cita 💆')

        servicios = [
            {
                'obj': s,
                'imagen': IMG_SERVICIOS[i % len(IMG_SERVICIOS)],
                # Cada tarjeta abre WhatsApp con el tratamiento ya escrito:
                # menos fricción para la clienta y el bot entiende de una.
                'wa': _link_whatsapp(numero_wa, 'Hola Daya, quiero agendar %s 💆' % s.nombre),
            }
            for i, s in enumerate(negocio.servicios.filter(activo=True).order_by('id'))
        ]
        productos = [
            {
                'obj': p,
                'imagen': IMG_PRODUCTOS[i % len(IMG_PRODUCTOS)],
                'wa': _link_whatsapp(numero_wa, 'Hola Daya, me interesa %s ($%s) ✨' % (p.nombre, p.precio)),
            }
            for i, p in enumerate(negocio.productos.filter(activo=True).order_by('id'))
        ]

        ahora = timezone.localtime()
        activos = list(horarios_activos(negocio))
        horarios = [
            {
                'dia': DIAS_SEMANA[h.dia_semana],
                'dia_schema': DIAS_SCHEMA[h.dia_semana],
                'inicio': h.hora_inicio,
                'fin': h.hora_fin,
                'es_hoy': h.dia_semana == ahora.weekday(),
            }
            for h in activos
        ]
        abierto_ahora, horario_hoy = _estado_horario(
            [h for h in activos if h.dia_semana == ahora.weekday()], ahora)

        faqs = list(negocio.preguntas_frecuentes.filter(activo=True).order_by('orden', 'id')[:8])

        hoy = ahora.date()
        promo = (negocio.promociones_whatsapp
                 .filter(activo=True)
                 .exclude(fecha_fin__lt=hoy)
                 .exclude(fecha_inicio__gt=hoy)
                 .order_by('orden', 'id')
                 .first())
        if promo:
            wa_promo = _link_whatsapp(
                numero_wa, 'Hola Daya, quiero la promo "%s" 🎁' % promo.titulo)
        else:
            wa_promo = wa_general

    return render(request, 'core/landing.html', {
        'public_page': True,
        'negocio': negocio,
        'numero_wa': numero_wa,
        'wa_general': wa_general,
        'wa_promo': wa_promo,
        'servicios': servicios,
        'productos': productos,
        'horarios': horarios,
        'abierto_ahora': abierto_ahora,
        'horario_hoy': horario_hoy,
        'faqs': faqs,
        'promo': promo,
        'redes': REDES,
        'hero_img': 'img/daya/estudio.jpeg',
        'logo_img': 'img/daya/logo.png',
        'about_img': 'img/daya/srv-daya-facial-care-7.jpg',
        'about_img2': 'img/daya/srv-hollywood-peel-2.jpg',
        'promo_img': 'img/daya/srv-daya-facial-care-1.jpg',
        'galeria': IMG_GALERIA,
    })


@login_required
def dashboard(request):
    negocio = obtener_negocio_usuario(request.user)
    contexto = {'negocio': negocio, **resumen_dashboard(negocio)}
    return render(request, 'core/dashboard.html', contexto)


def _parse_fecha(valor):
    try:
        return datetime.strptime(valor, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return None


@login_required
def reportes(request):
    negocio = obtener_negocio_usuario(request.user)
    desde = _parse_fecha(request.GET.get('desde'))
    hasta = _parse_fecha(request.GET.get('hasta'))
    datos = reporte_negocio(negocio, desde=desde, hasta=hasta)

    if request.GET.get('export') == 'csv':
        return _exportar_csv(datos)

    contexto = {'negocio': negocio, **datos}
    if negocio:
        contexto.update(uso_whatsapp(negocio))
    return render(request, 'core/reportes.html', contexto)


def _exportar_csv(datos):
    response = HttpResponse(content_type='text/csv')
    nombre = f"reporte_{datos['desde']}_{datos['hasta']}.csv"
    response['Content-Disposition'] = f'attachment; filename="{nombre}"'
    writer = csv.writer(response)
    writer.writerow(['Fecha', 'Hora', 'Cliente', 'Servicio', 'Estado', 'Precio'])
    for turno in datos['turnos']:
        inicio = timezone.localtime(turno.fecha_hora_inicio)
        writer.writerow([
            inicio.strftime('%Y-%m-%d'),
            inicio.strftime('%H:%M'),
            turno.cliente.nombre or turno.cliente.telefono,
            turno.servicio.nombre,
            turno.get_estado_display(),
            turno.servicio.precio,
        ])
    return response

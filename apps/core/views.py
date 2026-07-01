import csv
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone

from apps.core.selectors import reporte_negocio, resumen_dashboard, uso_whatsapp
from apps.negocios.selectors import horarios_activos, negocio_principal, obtener_negocio_usuario


DIAS_SEMANA = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']

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
IMG_GALERIA = [
    'img/daya/estudio.jpeg', 'img/daya/srv-daya-facial-care-1.jpg', 'img/daya/srv-hollywood-peel-2.jpg',
    'img/daya/srv-microdermoabrasion-2.jpg', 'img/daya/srv-lifting-pestanas.jpg', 'img/daya/srv-dermapen.jpg',
]


def landing(request):
    negocio = negocio_principal()
    numero_wa = ''
    servicios = []
    productos = []
    horarios = []
    if negocio:
        numero_wa = negocio.telefono_whatsapp or ''
        servicios = [
            {'obj': s, 'imagen': IMG_SERVICIOS[i % len(IMG_SERVICIOS)]}
            for i, s in enumerate(negocio.servicios.filter(activo=True).order_by('id'))
        ]
        productos = [
            {'obj': p, 'imagen': IMG_PRODUCTOS[i % len(IMG_PRODUCTOS)]}
            for i, p in enumerate(negocio.productos.filter(activo=True).order_by('id'))
        ]
        horarios = [
            {'dia': DIAS_SEMANA[h.dia_semana], 'inicio': h.hora_inicio, 'fin': h.hora_fin}
            for h in horarios_activos(negocio)
        ]
    return render(request, 'core/landing.html', {
        'public_page': True,
        'negocio': negocio,
        'numero_wa': numero_wa,
        'servicios': servicios,
        'productos': productos,
        'horarios': horarios,
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

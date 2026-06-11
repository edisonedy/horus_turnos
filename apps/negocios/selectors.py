from .models import ConfiguracionNegocioBot, HorarioAtencion, Negocio, Sucursal


def obtener_negocio_usuario(usuario):
    if not usuario.is_authenticated:
        return None
    return Negocio.objects.filter(propietario=usuario, activo=True).order_by('fecha_creacion').first()


def negocios_del_usuario(usuario):
    if not usuario.is_authenticated:
        return Negocio.objects.none()
    return Negocio.objects.filter(propietario=usuario).order_by('nombre')


def obtener_configuracion_bot(negocio):
    config, _ = ConfiguracionNegocioBot.objects.get_or_create(negocio=negocio)
    return config


def sucursales_activas(negocio):
    return Sucursal.objects.filter(negocio=negocio, activo=True).order_by('nombre')


def horarios_activos(negocio):
    return HorarioAtencion.objects.filter(negocio=negocio, activo=True).select_related('sucursal').order_by('dia_semana', 'hora_inicio')

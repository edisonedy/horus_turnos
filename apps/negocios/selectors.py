from .models import ConfiguracionNegocioBot, HorarioAtencion, Negocio, Sucursal


def obtener_negocio_usuario(usuario):
    if not usuario.is_authenticated:
        return None
    propio = Negocio.objects.filter(propietario=usuario, activo=True).order_by('fecha_creacion').first()
    if propio:
        return propio
    # Instalación single-tenant: cualquier administrador gestiona el negocio principal,
    # aunque no sea su propietario directo (p. ej. el superusuario edison gestiona Daya).
    return negocio_principal()


def negocio_principal():
    """Negocio único del sistema (instalación single-tenant). Devuelve el primer
    negocio activo, que es el que se muestra en la landing pública y el branding."""
    return Negocio.objects.filter(activo=True).order_by('fecha_creacion').first()


def obtener_configuracion_bot(negocio):
    config, _ = ConfiguracionNegocioBot.objects.get_or_create(negocio=negocio)
    return config


def sucursales_activas(negocio):
    return Sucursal.objects.filter(negocio=negocio, activo=True).order_by('nombre')


def horarios_activos(negocio):
    return HorarioAtencion.objects.filter(negocio=negocio, activo=True).select_related('sucursal').order_by('dia_semana', 'hora_inicio')

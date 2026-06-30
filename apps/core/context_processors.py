from apps.negocios.selectors import negocio_principal


def branding(request):
    """Expone el negocio principal en todas las plantillas para el branding
    (navbar, footer, títulos). En esta instalación single-tenant es Daya Facial Care."""
    return {'negocio_actual': negocio_principal()}

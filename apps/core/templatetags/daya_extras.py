"""Filtros de plantilla para la landing pública."""
import os

from django import template

register = template.Library()


@register.filter
def webp(ruta):
    """'img/daya/estudio.jpeg' -> 'img/daya/webp/estudio.webp'.

    Las versiones WebP se generan con `manage.py optimizar_imagenes`. Se usan
    dentro de <picture>; si alguna no existiera, el navegador cae al <img>
    original sin romper nada.
    """
    if not ruta:
        return ruta
    carpeta, archivo = os.path.split(str(ruta))
    base = os.path.splitext(archivo)[0]
    return '/'.join(filter(None, [carpeta, 'webp', base + '.webp']))

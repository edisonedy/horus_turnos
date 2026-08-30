"""Genera las versiones WebP que usa la landing.

Uso:  py manage.py optimizar_imagenes
Corre esto cada vez que agregues fotos nuevas a static/img/daya/.
"""
import os

from django.conf import settings
from django.core.management.base import BaseCommand

ORIGEN = 'img/daya'
SUBCARPETA = 'webp'
# El hero se ve mucho más grande que las tarjetas, por eso lleva más pixeles.
ANCHO_GRANDE = {'estudio.jpeg'}
TOPE_GRANDE = 1400
TOPE_NORMAL = 900
CALIDAD = 80
EXTENSIONES = {'.jpg', '.jpeg', '.png'}


class Command(BaseCommand):
    help = 'Crea/actualiza las copias WebP de static/img/daya/ (las usa la landing).'

    def add_arguments(self, parser):
        parser.add_argument('--forzar', action='store_true',
                            help='Regenera aunque el WebP ya esté al día.')

    def handle(self, *args, **opciones):
        try:
            from PIL import Image
        except ImportError:
            self.stderr.write('Falta Pillow: pip install Pillow')
            return

        base = os.path.join(settings.BASE_DIR, 'static', *ORIGEN.split('/'))
        destino = os.path.join(base, SUBCARPETA)
        if not os.path.isdir(base):
            self.stderr.write('No existe %s' % base)
            return
        os.makedirs(destino, exist_ok=True)

        antes = despues = 0
        hechas = omitidas = 0
        for archivo in sorted(os.listdir(base)):
            ruta = os.path.join(base, archivo)
            nombre, extension = os.path.splitext(archivo)
            if not os.path.isfile(ruta) or extension.lower() not in EXTENSIONES:
                continue
            if archivo.startswith('favicon'):
                continue

            salida = os.path.join(destino, nombre + '.webp')
            if not opciones['forzar'] and os.path.exists(salida) \
                    and os.path.getmtime(salida) >= os.path.getmtime(ruta):
                omitidas += 1
                continue

            imagen = Image.open(ruta)
            imagen = imagen.convert('RGBA' if imagen.mode in ('P', 'RGBA') else 'RGB')
            tope = TOPE_GRANDE if archivo in ANCHO_GRANDE else TOPE_NORMAL
            if max(imagen.size) > tope:
                imagen.thumbnail((tope, tope), Image.LANCZOS)
            imagen.save(salida, 'WEBP', quality=CALIDAD, method=6)

            antes += os.path.getsize(ruta)
            despues += os.path.getsize(salida)
            hechas += 1
            self.stdout.write('  %-34s %5d KB -> %4d KB' % (
                archivo, os.path.getsize(ruta) // 1024, os.path.getsize(salida) // 1024))

        if hechas:
            ahorro = 100 - (despues * 100 // antes) if antes else 0
            self.stdout.write(self.style.SUCCESS(
                '%d imagenes optimizadas (%d KB -> %d KB, -%d%%). %d ya estaban al dia.'
                % (hechas, antes // 1024, despues // 1024, ahorro, omitidas)))
        else:
            self.stdout.write('Todo al dia (%d imagenes).' % omitidas)

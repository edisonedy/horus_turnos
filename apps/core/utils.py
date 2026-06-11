import re
import unicodedata
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.utils import timezone

DIAS_SEMANA = {
    'lunes': 0,
    'martes': 1,
    'miercoles': 2,
    'miércoles': 2,
    'jueves': 3,
    'viernes': 4,
    'sabado': 5,
    'sábado': 5,
    'domingo': 6,
}


def normalizar_texto(texto):
    texto = (texto or '').strip().lower()
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(char for char in texto if unicodedata.category(char) != 'Mn')
    texto = re.sub(r'\s+', ' ', texto)
    return texto


def solo_digitos(valor):
    return re.sub(r'\D+', '', valor or '')


def normalizar_telefono(telefono, codigo_pais_default='593'):
    digitos = solo_digitos(telefono)
    if not digitos:
        return ''
    if digitos.startswith('00'):
        digitos = digitos[2:]
    if digitos.startswith('0') and len(digitos) == 10:
        digitos = f'{codigo_pais_default}{digitos[1:]}'
    return digitos


def timezone_actual():
    return ZoneInfo(settings.TIME_ZONE)


def parsear_fecha_natural(texto, referencia=None):
    referencia = referencia or timezone.localdate()
    valor_original = (texto or '').strip()
    valor = normalizar_texto(valor_original)

    if valor in {'hoy', 'today'}:
        return referencia
    if valor in {'manana', 'mañana', 'tomorrow'}:
        return referencia + timedelta(days=1)
    if valor in {'pasado manana', 'pasado mañana'}:
        return referencia + timedelta(days=2)

    if valor in DIAS_SEMANA:
        objetivo = DIAS_SEMANA[valor]
        dias = (objetivo - referencia.weekday()) % 7
        if dias == 0:
            dias = 7
        return referencia + timedelta(days=dias)

    formatos = ['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d', '%d/%m/%y']
    for formato in formatos:
        try:
            return datetime.strptime(valor_original, formato).date()
        except ValueError:
            continue
    return None


def parsear_hora(texto):
    valor = normalizar_texto(texto)
    match = re.search(r'(\d{1,2})(?::|h)?(\d{2})?', valor)
    if not match:
        return None
    hora = int(match.group(1))
    minuto = int(match.group(2) or 0)
    if hora < 0 or hora > 23 or minuto < 0 or minuto > 59:
        return None
    return hora, minuto


def combinar_fecha_hora(fecha, hora):
    naive = datetime.combine(fecha, hora)
    return timezone.make_aware(naive, timezone_actual())


def formatear_fecha(fecha):
    if isinstance(fecha, datetime):
        fecha = timezone.localtime(fecha).date()
    return fecha.strftime('%d/%m/%Y')


def formatear_hora(fecha_hora):
    return timezone.localtime(fecha_hora).strftime('%H:%M')


def respuesta_afirmativa(texto):
    valor = normalizar_texto(texto)
    return valor in {'si', 'sí', 's', 'ok', 'confirmar', 'confirmo', 'voy', '1', 'dale'}


def respuesta_negativa(texto):
    valor = normalizar_texto(texto)
    return valor in {'no', 'n', 'cancelar', 'mantener', '2'}

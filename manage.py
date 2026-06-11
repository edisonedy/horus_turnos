#!/usr/bin/env python
"""Django command-line utility for HORUS TURNOS."""
import os
import sys


def main():
    # PyCharm puede heredar un DJANGO_SETTINGS_MODULE inválido desde la
    # configuración de ejecución. Para este proyecto local usamos siempre este.
    os.environ['DJANGO_SETTINGS_MODULE'] = 'horus_turnos.settings'
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            'Django no está instalado o el entorno virtual no está activo.'
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()

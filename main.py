#!/usr/bin/env python
"""Launcher local para HORUS TURNOS.

Permite ejecutar el proyecto desde PyCharm usando main.py. Si no se pasan
argumentos, levanta el servidor de desarrollo igual que manage.py runserver.
"""
import os
import sys


def main():
    os.environ['DJANGO_SETTINGS_MODULE'] = 'horus_turnos.settings'

    if len(sys.argv) == 1:
        sys.argv.extend(['runserver', '127.0.0.1:8000'])

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            'Django no está instalado o el entorno virtual no está activo.'
        ) from exc

    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()

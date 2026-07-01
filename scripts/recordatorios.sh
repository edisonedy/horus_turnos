#!/bin/bash
# Genera y envía los recordatorios de WhatsApp pendientes.
# Pensado para ejecutarse por cron cada pocos minutos en el servidor Linux.
#
#   crontab -e   ->   */5 * * * * /home/django/horus_turnos/scripts/recordatorios.sh >> /home/django/horus_turnos/logs/cron.log 2>&1
#
# Detecta la carpeta del proyecto a partir de la ubicación del script.
DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$DIR" || exit 1

PY="$DIR/.venv/bin/python"
[ -x "$PY" ] || PY="python3"

echo "----- $(date '+%Y-%m-%d %H:%M:%S') -----"
"$PY" manage.py generar_recordatorios
"$PY" manage.py enviar_recordatorios

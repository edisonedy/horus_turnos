# Genera y envía los recordatorios WhatsApp pendientes.
# Pensado para ejecutarse desde el Programador de tareas de Windows
# cada 5-10 minutos, en lugar del loop manual procesar_recordatorios_loop.

$ErrorActionPreference = 'Stop'
$Raiz = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Raiz '.venv\Scripts\python.exe'

Set-Location $Raiz
& $Python manage.py generar_recordatorios
& $Python manage.py enviar_recordatorios

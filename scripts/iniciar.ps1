# Arranca Daya Facial Care: servidor Django + túnel cloudflared + reconecta el webhook.
# Uso: click derecho > "Ejecutar con PowerShell"  (o)  powershell -ExecutionPolicy Bypass -File scripts\iniciar.ps1
$ErrorActionPreference = 'SilentlyContinue'
$proj = Split-Path -Parent $PSScriptRoot
$py = Join-Path $proj '.venv\Scripts\python.exe'
New-Item -ItemType Directory -Force (Join-Path $proj 'logs') | Out-Null

Write-Host "Deteniendo instancias anteriores..." -ForegroundColor Yellow
Get-NetTCPConnection -LocalPort 8060 -State Listen | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
Get-CimInstance Win32_Process -Filter "Name='cloudflared.exe'" | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
Start-Sleep -Seconds 2

Write-Host "Iniciando servidor Django (puerto 8060)..." -ForegroundColor Cyan
Start-Process -FilePath $py -ArgumentList 'manage.py','runserver','127.0.0.1:8060','--noreload' `
  -WorkingDirectory $proj -WindowStyle Hidden `
  -RedirectStandardOutput (Join-Path $proj 'logs\runserver.out') -RedirectStandardError (Join-Path $proj 'logs\runserver.err')

Write-Host "Iniciando túnel cloudflared..." -ForegroundColor Cyan
$cf = (Get-Command cloudflared).Source
if (-not $cf) { $cf = 'C:\Program Files (x86)\cloudflared\cloudflared.exe' }
Start-Process -FilePath $cf -ArgumentList 'tunnel','--url','http://127.0.0.1:8060' -WindowStyle Hidden `
  -RedirectStandardOutput (Join-Path $proj 'logs\cf.out') -RedirectStandardError (Join-Path $proj 'logs\cf.err')

Write-Host "Esperando la URL del túnel..." -ForegroundColor Cyan
Start-Sleep -Seconds 12
$url = Select-String -Path (Join-Path $proj 'logs\cf.err'),(Join-Path $proj 'logs\cf.out') `
  -Pattern 'https://[a-z0-9-]+\.trycloudflare\.com' | ForEach-Object { $_.Matches.Value } | Select-Object -First 1

if ($url) {
  $webhook = "$url/whatsapp/webhook/"
  Write-Host "Reconectando WhatsApp en Meta..." -ForegroundColor Cyan
  & $py (Join-Path $proj 'manage.py') registrar_webhook $webhook
  Write-Host ""
  Write-Host "==================================================" -ForegroundColor Green
  Write-Host " LISTO - Daya Facial Care esta en linea" -ForegroundColor Green
  Write-Host "==================================================" -ForegroundColor Green
  Write-Host " Panel:   http://127.0.0.1:8060/panel/   (daya / daya)"
  Write-Host " Webhook: $webhook"
  Write-Host " Escribe al numero de prueba de WhatsApp para probar el bot."
} else {
  Write-Host "No se obtuvo la URL del tunel. Revisa logs\cf.err" -ForegroundColor Red
}

# HORUS TURNOS

Sistema SaaS multi-negocio WhatsApp-first para gestión de turnos, consultas básicas, productos y cotizaciones. El cliente final opera por WhatsApp; el panel web es solo administrativo.

## Estado local actual

Base de datos configurada en `.env`:

```env
DB_NAME=horus_turnos
DB_USER=postgres
DB_PASSWORD=edison
DB_HOST=localhost
DB_PORT=5432
```

Usuario demo creado:

```text
usuario: edison
contraseña: edison
```

Negocio (único, instalación single-tenant):

```text
Daya Facial Care — estética facial, Queens NY
Servicios: Limpieza Facial, Acné, Hiperpigmentación, Rejuvenecimiento,
           Depilación Láser, Lifting de Pestañas, Cejas 3D, Depilación con Cera
Productos: Crema Anti-Pigment, Vitamina C, Tea Tree Oil, Kit Green Tea,
           Kit piel Acneica, Colágeno
Horario: Lun–Vie 10:00–20:00, Sáb y Dom 11:00–18:00
Admin: daya / daya  (también edison / edison)
```

## Ejecutar proyecto

**Solo el sitio (sin WhatsApp):**

```powershell
.\.venv\Scripts\python.exe manage.py runserver
```

**Todo en línea (sitio + bot de WhatsApp por túnel), un comando:**

```powershell
powershell -ExecutionPolicy Bypass -File scripts\iniciar.ps1
```

Ese script levanta el servidor en el puerto 8060, abre el túnel `cloudflared` y
**reconecta el webhook de WhatsApp en Meta automáticamente** (con el token guardado),
así que no hay que entrar a Meta cuando el túnel cambia de URL. Requiere tener
`cloudflared` instalado.

Si solo cambió la URL del túnel y quieres reconectar el webhook a mano:

```powershell
.\.venv\Scripts\python.exe manage.py registrar_webhook https://TU-TUNEL/whatsapp/webhook/
```

### Entrar a configurar
- Panel admin: **http://127.0.0.1:8060/panel/** — usuario `daya` / `daya` (o `edison` / `edison`).
- Configura el negocio, servicios, horarios, productos y el **WhatsApp API** desde el menú lateral.

Entrar al panel:

```text
http://127.0.0.1:8000/accounts/login/
```

Landing comercial:

```text
http://127.0.0.1:8000/
```

Panel administrativo:

```text
http://127.0.0.1:8000/panel/
```

Configuración del negocio:

```text
http://127.0.0.1:8000/panel/negocio/
```

Modelo de negocio y estrategia comercial:

```text
docs/modelo_negocio.md
```

## Cliente en producción: Daya Facial Care

Esta instalación está personalizada para un único negocio: **Daya Facial Care**
(Queens, NY). Para cargar/actualizar sus datos reales (servicios, productos,
horarios, promociones) y dejarlo como negocio único activo:

```powershell
.\.venv\Scripts\python.exe manage.py crear_daya
```

Esto crea el administrador y desactiva cualquier otro negocio (single-tenant):

```text
usuario: daya
contraseña: daya
```

La landing pública (`/`) toma su marca, servicios, productos, horarios, dirección
y botón de WhatsApp directamente del negocio activo. Tras iniciar sesión, el panel
incluye **Reportes** (`/panel/reportes/`) con filtro por rango de fechas, métricas
de turnos, ventas y clientes, y exportación a CSV.

## Si necesitas recargar los datos del negocio

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py crear_daya
```

## WhatsApp Cloud API

Endpoint del webhook en el sistema:

```text
/whatsapp/webhook/
```

En local necesitas exponer Django con ngrok:

```powershell
ngrok http 8000
```

En Meta configura:

```text
Callback URL: https://TU_SUBDOMINIO.ngrok-free.app/whatsapp/webhook/
Verify token: el mismo verify_token guardado en Panel > WhatsApp API
```

En el panel `WhatsApp API` debes guardar:

```text
phone_number_id
business_account_id
access_token
verify_token
app_secret
numero_whatsapp
activo=True
```

`app_secret` es el App Secret de la app de Meta. Si lo defines (en el panel o en
`WHATSAPP_APP_SECRET` del `.env`), el webhook valida la firma `X-Hub-Signature-256`
de cada POST y rechaza peticiones falsas. Si lo dejas vacío, el webhook funciona
igual pero sin verificar la firma (se registra una advertencia en los logs).

El sistema envía mensajes usando:

```text
https://graph.facebook.com/v20.0/{phone_number_id}/messages
```

## Probar envío WhatsApp

```powershell
.\.venv\Scripts\python.exe manage.py shell
```

```python
from apps.negocios.models import Negocio
from apps.whatsapp_api.services import WhatsAppService
negocio = Negocio.objects.get(slug='daya-facial-care')
WhatsAppService(negocio=negocio).enviar_texto('593XXXXXXXXX', 'Prueba HORUS TURNOS')
```

## Flujo cliente por WhatsApp

Ejemplos:

```text
hola
que puedes hacer
ayuda
quiero un corte
mañana
1
```

También puede escribir de forma natural si `BOT_USA_OPENAI=True`:

```text
quiero corte mañana a las 10
```

Si el servicio, fecha y hora existen y hay disponibilidad, el turno se agenda directo. Si falta algún dato, el bot pide solo lo pendiente.

```text
reagendar
viernes
2
```

```text
cancelar
SI
```

```text
servicios
precio limpieza facial
productos
tienen vitamina c
formas de pago
promociones
mi turno
ubicación
humano
```

Ejemplos de lenguaje natural como recepcionista:

```text
Quiero una limpieza facial el sábado en la mañana
¿Hay espacio hoy para lifting de pestañas?
No puedo ir, quiero cambiar mi cita
¿Cuánto cuesta el diseño de cejas?
¿Dónde están ubicados?
Quiero comprar la Vitamina C
Quiero hablar con una persona
```

Flujo de pedido/cotización:

```text
productos
1
2
SI
```

El sistema registra el pedido en `Panel > Pedidos` y avisa al dueño por WhatsApp.

Promociones y autoservicio:

```text
promociones
mi turno
confirmar
reagendar
cancelar
```

## Comandos del dueño por WhatsApp

Desde el número configurado como dueño:

```text
agenda hoy
agenda mañana
turnos pendientes
turnos confirmados
clientes nuevos
resumen día
servicios
bloquear horario hoy 15:00 60
liberar horario
liberar horario ID
```

## Recordatorios

Generar recordatorios pendientes:

```powershell
.\.venv\Scripts\python.exe manage.py generar_recordatorios
```

Enviar recordatorios vencidos:

```powershell
.\.venv\Scripts\python.exe manage.py enviar_recordatorios
```

Worker local para generar y enviar recordatorios automáticamente mientras esté abierto (solo para desarrollo):

```powershell
.\.venv\Scripts\python.exe manage.py procesar_recordatorios_loop --intervalo 60
```

En producción no uses el loop manual (depende de una ventana abierta). Usa el
script `scripts/procesar_recordatorios.ps1` registrado en el Programador de
tareas de Windows para que corra cada 5 minutos aunque nadie tenga sesión:

```powershell
schtasks /Create /TN "HorusRecordatorios" /SC MINUTE /MO 5 ^
  /TR "powershell -NoProfile -ExecutionPolicy Bypass -File C:\proyectos\horus_turnos\scripts\procesar_recordatorios.ps1" ^
  /RL HIGHEST /F
```

Enviar reporte diario al dueño:

```powershell
.\.venv\Scripts\python.exe manage.py enviar_reporte_diario
```

Enviar reporte de un negocio específico:

```powershell
.\.venv\Scripts\python.exe manage.py enviar_reporte_diario --negocio daya-facial-care
```

Programación recomendada:

```text
Cada 10 o 15 minutos: generar_recordatorios
Cada 5 minutos: enviar_recordatorios
```

Cuando se agenda o reagenda un turno por WhatsApp, el sistema crea automáticamente recordatorios 24h y 2h antes si aplican. Al enviar un recordatorio, la conversación queda esperando:

```text
1. Confirmar
2. Reagendar
3. Cancelar
```

## OpenAI / ChatGPT para inteligencia del bot

Configura en `.env`:

```env
OPENAI_API_KEY=tu_api_key_real
OPENAI_MODEL=gpt-5.2
BOT_USA_OPENAI=True
```

El archivo `apps/bot_turnos/ai.py` usa OpenAI solo para interpretar intención, servicio, fecha y hora. La creación, cancelación y reagendamiento siguen protegidos por la lógica del sistema.

Sin `OPENAI_API_KEY`, el bot sigue funcionando con reglas locales.

## Logs

El sistema escribe logs en `logs/horus.log` (rotación automática, 5 MB x 5
archivos) y también a consola. Loggers principales: `horus.whatsapp` (webhook y
envíos) y `horus.recordatorios`. Ajusta el nivel con `LOG_LEVEL` en `.env`.

## Validación

```powershell
.\.venv\Scripts\python.exe manage.py check
```

Resultado actual: sin errores.

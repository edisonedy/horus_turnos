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

Negocio demo:

```text
Barbería Demo HORUS
Servicios: Corte de cabello, Barba, Limpieza facial
Productos: Shampoo profesional, Cera para peinar, Kit barba
Promociones: Combo corte + barba, Producto recomendado
Horario: lunes a sábado, 09:00 a 18:00
```

## Ejecutar proyecto

```powershell
.\.venv\Scripts\python.exe manage.py runserver
```

También puedes ejecutar desde PyCharm usando `main.py`; sin argumentos levanta:

```text
http://127.0.0.1:8000/
```

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

## Si necesitas recrear demo

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py crear_demo_horus
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
numero_whatsapp
activo=True
```

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
negocio = Negocio.objects.get(slug='barberia-demo-horus')
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
precio corte
productos
tienen cera para peinar
formas de pago
promociones
mi turno
ubicación
humano
```

Ejemplos de lenguaje natural como recepcionista:

```text
Quiero corte mañana a las 10
¿Hay espacio hoy para barba?
No puedo ir, quiero cambiar mi cita
¿Cuánto cuesta limpieza facial?
¿Dónde están ubicados?
Quiero comprar cera para peinar
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

Worker local para generar y enviar recordatorios automáticamente mientras esté abierto:

```powershell
.\.venv\Scripts\python.exe manage.py procesar_recordatorios_loop --intervalo 60
```

Enviar reporte diario al dueño:

```powershell
.\.venv\Scripts\python.exe manage.py enviar_reporte_diario
```

Enviar reporte de un negocio específico:

```powershell
.\.venv\Scripts\python.exe manage.py enviar_reporte_diario --negocio barberia-demo-horus
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

## Validación

```powershell
.\.venv\Scripts\python.exe manage.py check
```

Resultado actual: sin errores.

from pathlib import Path
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY', default='dev-insecure-change-me')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='http://localhost:8000,http://127.0.0.1:8000', cast=Csv())

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'apps.core',
    'apps.usuarios',
    'apps.negocios',
    'apps.agenda',
    'apps.whatsapp_api',
    'apps.bot_turnos',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'horus_turnos.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.core.context_processors.branding',
            ],
        },
    },
]

WSGI_APPLICATION = 'horus_turnos.wsgi.application'
ASGI_APPLICATION = 'horus_turnos.asgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='horus_turnos'),
        'USER': config('DB_USER', default='horus_turnos_user'),
        'PASSWORD': config('DB_PASSWORD', default=''),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = config('LANGUAGE_CODE', default='es-ec')
TIME_ZONE = config('TIME_ZONE', default='America/Guayaquil')
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'

WHATSAPP_ACCESS_TOKEN = config('WHATSAPP_ACCESS_TOKEN', default='')
WHATSAPP_PHONE_NUMBER_ID = config('WHATSAPP_PHONE_NUMBER_ID', default='')
WHATSAPP_BUSINESS_ACCOUNT_ID = config('WHATSAPP_BUSINESS_ACCOUNT_ID', default='')
WHATSAPP_TEST_PHONE_NUMBER = config('WHATSAPP_TEST_PHONE_NUMBER', default='')
WHATSAPP_VERIFY_TOKEN = config('WHATSAPP_VERIFY_TOKEN', default='horus_turnos_verify_123')
WHATSAPP_APP_SECRET = config('WHATSAPP_APP_SECRET', default='')
WHATSAPP_GRAPH_API_VERSION = config('WHATSAPP_GRAPH_API_VERSION', default='v20.0')
WHATSAPP_REQUEST_TIMEOUT = config('WHATSAPP_REQUEST_TIMEOUT', default=15, cast=int)
# Plantilla aprobada por Meta para recordatorios (llega fuera de la ventana de 24h).
WHATSAPP_TEMPLATE_RECORDATORIO = config('WHATSAPP_TEMPLATE_RECORDATORIO', default='recordatorio_cita')
WHATSAPP_TEMPLATE_REACTIVACION = config('WHATSAPP_TEMPLATE_REACTIVACION', default='reactivacion_clienta')
WHATSAPP_TEMPLATE_IDIOMA = config('WHATSAPP_TEMPLATE_IDIOMA', default='es')

# Nombres propios (BOT_AI_*) para no colisionar con un OPENAI_API_KEY global del
# sistema. Vacío en BASE_URL = OpenAI; para DeepSeek usar https://api.deepseek.com.
OPENAI_API_KEY = config('BOT_AI_API_KEY', default='')
OPENAI_BASE_URL = config('BOT_AI_BASE_URL', default='')
OPENAI_MODEL = config('BOT_AI_MODEL', default='deepseek-chat')
BOT_USA_OPENAI = config('BOT_USA_IA', default=False, cast=bool)
# Si True, WhatsApp usa el AGENTE con memoria (Opción B). Si el agente falla,
# cae automáticamente al bot híbrido. Requiere BOT_USA_IA=True.
BOT_MODO_AGENTE = config('BOT_MODO_AGENTE', default=False, cast=bool)

LOG_DIR = BASE_DIR / 'logs'
LOG_DIR.mkdir(exist_ok=True)
LOG_LEVEL = config('LOG_LEVEL', default='INFO')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{asctime} {levelname} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'archivo': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / 'horus.log',
            'maxBytes': 5 * 1024 * 1024,
            'backupCount': 5,
            'encoding': 'utf-8',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'archivo'],
        'level': 'WARNING',
    },
    'loggers': {
        'horus': {
            'handlers': ['console', 'archivo'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console', 'archivo'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}

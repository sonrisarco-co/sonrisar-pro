from pathlib import Path
import os
import dj_database_url

# --- BASE DIR ---
BASE_DIR = Path(__file__).resolve().parent.parent

# --- SECURITY ---
SECRET_KEY = 'django-insecure-reemplazar-esto-luego'
DEBUG = True
ALLOWED_HOSTS = ["*"]

# --- APPS INSTALADAS ---
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_crontab',
    'rest_framework',
    'corsheaders',



    # App principal
    'core',
]

# --- MIDDLEWARE ---
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# --- URLS PRINCIPALES ---
ROOT_URLCONF = 'backend.urls'

# --- TEMPLATES ---
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],   # No usas directorios externos
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# --- WSGI ---
WSGI_APPLICATION = 'backend.wsgi.application'

# --- BASE DE DATOS ---
DATABASES = {
    'default': dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600
    )
}

# --- IDIOMA / HORARIO ---
LANGUAGE_CODE = 'es-es'
TIME_ZONE = 'America/Montevideo'
USE_I18N = True
USE_TZ = True

# --- ARCHIVOS ESTÁTICOS ---
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'core' / 'static',
]


# --- MEDIA (archivos subidos) ---
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# --- CONFIG GENERAL ---
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

DATE_FORMAT = "d/m/Y"
DATETIME_FORMAT = "d/m/Y H:i"
SHORT_DATE_FORMAT = "d/m/Y"

# ==========================
# WATI - WhatsApp API Sonrisar
# ==========================
WATI_API_URL = "https://app-server.wati.io/api/v1/sendSessionMessage"
WATI_API_TOKEN = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiI1OWFjMjAyZi0zZjIwLTQ5MDMtYWVjYi0xYTY4Y2U5OGIyYWYiLCJ1bmlxdWVfbmFtZSI6InNvbnJpc2FyY29AZ21haWwuY29tIiwibmFtZWlkIjoic29ucmlzYXJjb0BnbWFpbC5jb20iLCJlbWFpbCI6InNvbnJpc2FyY29AZ21haWwuY29tIiwiYXV0aF90aW1lIjoiMDIvMDUvMjAyNiAwNTo0NDoyNSIsImRiX25hbWUiOiJ3YXRpX2FwcF90cmlhbCIsImh0dHA6Ly9zY2hlbWFzLm1pY3Jvc29mdC5jb20vd3MvMjAwOC8wNi9pZGVudGl0eS9jbGFpbXMvcm9sZSI6IlRSSUFMIiwiZXhwIjoxNzcwOTQwODAwLCJpc3MiOiJDbGFyZV9BSSIsImF1ZCI6IkNsYXJlX0FJIn0.hflkTas7Uqx5iAhFJc3Uh-htjnWYPk4OV_CvGxL4lno"
WATI_NUMBER = "59892706293"


CRONJOBS = [
    ('0 12 * * *', 'core.tasks.enviar_recordatorios_automaticos'),
]


SONRISAR_COBROS_PORT = "8001"
SONRISAR_COBROS_NUEVO_PATH = "/pagos/nuevo/"
SONRISAR_COBROS_API_PACIENTE_PATH = "/pagos/api/por-paciente/"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    )
}

CORS_ALLOW_ALL_ORIGINS = True

CSRF_TRUSTED_ORIGINS = [
    'https://*.tail7ab5ac.ts.net',
]








# campuscare/campuscare/settings.py — Step 11
"""Django settings for the CampusCare project."""

from pathlib import Path
from urllib.parse import unquote, urlparse

from decouple import Csv, config

BASE_DIR = Path(__file__).resolve().parent.parent


def read_debug_flag() -> bool:
    """Read DEBUG from the environment and coerce unknown values to False."""
    debug_value = str(config('DEBUG', default='False')).strip().lower()
    return debug_value in {'1', 'true', 'yes', 'on'}


def build_database_config() -> dict[str, object]:
    """Build the Django database configuration from DATABASE_URL."""
    default_database_url = 'sqlite:///db.sqlite3'
    database_url = config('DATABASE_URL', default=default_database_url)
    parsed_url = urlparse(database_url)

    if parsed_url.scheme == 'sqlite':
        if database_url.startswith('sqlite:////'):
            database_path = Path(unquote(database_url.removeprefix('sqlite:///')))
        else:
            relative_path = database_url.removeprefix('sqlite:///') or 'db.sqlite3'
            database_path = BASE_DIR / unquote(relative_path)

        return {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': str(database_path),
        }

    if parsed_url.scheme in {'postgres', 'postgresql'}:
        return {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': parsed_url.path.lstrip('/'),
            'USER': unquote(parsed_url.username or ''),
            'PASSWORD': unquote(parsed_url.password or ''),
            'HOST': parsed_url.hostname or 'localhost',
            'PORT': str(parsed_url.port or 5432),
        }

    raise ValueError('Unsupported DATABASE_URL scheme. Use sqlite:/// or postgresql://.')


SECRET_KEY = config('SECRET_KEY')
DEBUG = read_debug_flag()
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'crispy_forms',
    'crispy_bootstrap5',
    'accounts.apps.AccountsConfig',
    'core.apps.CoreConfig',
    'appointments.apps.AppointmentsConfig',
    'consultation.apps.ConsultationConfig',
    'pharmacy.apps.PharmacyConfig',
    'inventory.apps.InventoryConfig',
    'calendar_app.apps.CalendarAppConfig',
    'analytics.apps.AnalyticsConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'appointments.middleware.TokenExpiryMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'campuscare.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.dispensary_status',
            ],
        },
    },
]

WSGI_APPLICATION = 'campuscare.wsgi.application'

DATABASES = {
    'default': build_database_config(),
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

if not DEBUG:
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 3600
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = False
    SECURE_REFERRER_POLICY = 'same-origin'

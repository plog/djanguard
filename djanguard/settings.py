from pathlib import Path
from decouple import config
import logging
import graypy
from datetime import datetime, timedelta
import os

BASE_DIR                                  = Path(__file__).resolve().parent.parent
ADMIN_URL                                 = config('ADMIN_URL')
APP_NAME                                  = config('APP_NAME')
BOT_TOKEN                                 = config('BOT_TOKEN')
DEBUG                                     = config('DEBUG', default=False, cast=bool)
LOGIN_REDIRECT_URL                        = '/config/'
LOGOUT_REDIRECT_URL                       = LOGIN_REDIRECT_URL
LOGIN_URL                                 = f'/accounts/login/?next={LOGIN_REDIRECT_URL}'
GOOGLE_OAUTH_CLIENT_ID                    = config('GOOGLE_OAUTH_CLIENT_ID')
AUTHENTICATION_BACKENDS                   = ['django.contrib.auth.backends.ModelBackend']
SECURE_REFERRER_POLICY                    = 'no-referrer-when-downgrade'
SECURE_CROSS_ORIGIN_OPENER_POLICY         = "same-origin-allow-popups"
SECRET_KEY                                = config('SECRET_KEY')
CELERY_BROKER_URL                         = config('CELERY_BROKER_URL')
CELERY_RESULT_BACKEND                     = config('CELERY_BROKER_URL')
CELERY_ACCEPT_CONTENT                     = ['json']
CELERY_TASK_SERIALIZER                    = 'json'
CELERY_RESULT_SERIALIZER                  = 'json'
CELERY_TIMEZONE                           = 'UTC'
CELERY_RESULT_BACKEND                     = 'django-db'
CELERY_RESULT_EXTENDED                    = True
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_TASK_SOFT_TIME_LIMIT               = 1600  # 10 minutes soft time limit
CELERY_TASK_TIME_LIMIT                    = 1200  # 20 minutes hard time limit
CELERY_TASK_RESULT_EXPIRES                = timedelta(minutes=15)
CELERY_BEAT_SCHEDULE = {
    'check-sensors-periodically': {
        'task': 'monitor.tasks.schedule_sensor_actions',
        'schedule': timedelta(seconds=30),  # Run every 10 seconds
    },
    'delete-old-task-results-every-hour': {
        'task': 'monitor.tasks.delete_old_task_results',
        'schedule': timedelta(seconds=60),  # This runs every hour at the start of the hour
    },    
}

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'django_celery_results',
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',    
    'monitor',
    'website',
    'drf_yasg',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ALLOWED_HOSTS = [
    'djanguard.bali.plog.net',
    '172.18.0.11',
    '141.95.99.27',
    '10.11.12.100',
    'djanguard.com',
    'localhost'
]
CORS_ALLOWED_ORIGINS = [
    "http://localhost:8014",
    "https://djanguard.com",
]
CSRF_TRUSTED_ORIGINS = [
    'chrome-extension://hlgbhaldaijnheibapmhlpladgacnadb',
    'http://127.0.0.1:8010',
    'http://10.11.12.100:8014',
    'https://guardexam.com'
]
ROOT_URLCONF = 'djanguard.urls'
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'templates'),
            os.path.join(BASE_DIR, 'monitor','templates'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'common.admin_url.admin_url', 
            ],
        },
    },
]
WSGI_APPLICATION = 'djanguard.wsgi.application'
DATABASES = {
    'default': {
        'ENGINE'  : 'django.db.backends.postgresql',
        'NAME'    : config('DB_NAME'),
        'USER'    : config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST'    : config('DB_HOST'),
        'PORT'    : 5432,
        'CONN_MAX_AGE': 300, 
    }
}
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True
STATIC_URL         = '/static/'
STATIC_ROOT        = os.path.join(BASE_DIR, '..','django_djanguard_static')
DATA_DIR           = os.path.join(BASE_DIR, '..','django_djanguard_data')
STATICFILES_DIRS   = [os.path.join(BASE_DIR,'static'),]
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
REST_FRAMEWORK = { 
    'DEFAULT_SCHEMA_CLASS': 'rest_framework.schemas.coreapi.AutoSchema',
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'common.authentication.APIKeyAuthentication', 
        'rest_framework.authentication.SessionAuthentication',  # Keep your current session-based authentication
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.UserRateThrottle',  # Rate-limiting based on user authentication
        'rest_framework.throttling.AnonRateThrottle',  # For unauthenticated users (if applicable)
    ],
    'DEFAULT_THROTTLE_RATES': {
        'user': '200/second',  # Allow 1 request per second per user
        'anon': '500/minute',  # Allow 10 requests per minute for anonymous users (adjust as needed)
    }    
}
SWAGGER_SETTINGS = {
    'USE_SESSION_AUTH': True,
    'SECURITY_DEFINITIONS': {
        'Basic': {'type': 'basic'},
        'APIKey': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header',
            'description': 'Provide the API key as a Bearer token in the Authorization header.'
        },
    },
}
log_level = 'INFO'
log_size = 2
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        }
    },
    'handlers': {
        'gelf': {
            'level': log_level,  # Set your desired level
            'class': 'graypy.GELFUDPHandler',
            'host': 'graylog',  # Replace with Graylog server IP or hostname
            'port': 12201,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['gelf'],
            'level': log_level,
            'propagate': False,
        },
        'django.country_restriction': {
            'handlers': ['gelf'],
            'level': log_level,
            'propagate': False,
        },
        'celery_process': {
            'handlers': ['gelf'],
            'level': log_level,
            'propagate': False,
        },
    },
}

# Override logging to add custom fields automatically
class DjangoGELFHandler(logging.Handler):
    def emit(self, record):
        if not hasattr(record, '_app_name'):
            record._app_name = 'my_django_app'  # Replace with a unique name for each application
        super().emit(record)

# Add this custom handler to your logger
handler = DjangoGELFHandler()
logger = logging.getLogger('django')
logger.addHandler(handler)
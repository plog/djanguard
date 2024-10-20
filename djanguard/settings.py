from pathlib import Path
from decouple import config
from celery.schedules import crontab
from datetime import datetime, timedelta
import os

BASE_DIR              = Path(__file__).resolve().parent.parent
ADMIN_URL             = config('ADMIN_URL')
LOGIN_REDIRECT_URL    = '/config/'
LOGOUT_REDIRECT_URL   = LOGIN_REDIRECT_URL
LOGIN_URL             = f'/accounts/login/?next={LOGIN_REDIRECT_URL}'
GOOGLE_OAUTH_CLIENT_ID = config('GOOGLE_OAUTH_CLIENT_ID')
if not GOOGLE_OAUTH_CLIENT_ID:
    raise ValueError(
        'GOOGLE_OAUTH_CLIENT_ID is missing.' 
        'Have you put it in a file at core/.env ?'
    )

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

SECURE_REFERRER_POLICY = 'no-referrer-when-downgrade'
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin-allow-popups"
SECRET_KEY = 'django-insecure-z*ypnwid#cw-(*u7w4b684p$!&f9h83=j1&8v2tidz6-9+7q59'
DEBUG      = config('DEBUG', default=False, cast=bool)

CELERY_BROKER_URL        = config('CELERY_BROKER_URL')
CELERY_RESULT_BACKEND    = config('CELERY_BROKER_URL')
CELERY_ACCEPT_CONTENT    = ['json']
CELERY_TASK_SERIALIZER   = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE          = 'UTC'
CELERY_RESULT_BACKEND    = 'django-db'
CELERY_RESULT_EXTENDED   = True
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_TASK_SOFT_TIME_LIMIT = 1600  # 10 minutes soft time limit
CELERY_TASK_TIME_LIMIT = 1200  # 20 minutes hard time limit
CELERY_TASK_RESULT_EXPIRES = timedelta(minutes=15)

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
REST_FRAMEWORK = { 'DEFAULT_SCHEMA_CLASS': 'rest_framework.schemas.coreapi.AutoSchema' }
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
        'file_general': {
            'level'      : log_level,
            'class'      : 'logging.handlers.RotatingFileHandler',
            'filename'   : os.path.join(BASE_DIR, 'logs','django_general.log'),
            'maxBytes'   : 1024*1024*log_size,
            'backupCount': 5,
            'formatter'  : 'verbose',
        },
        'file_country_restriction': {
            'level'      : log_level,
            'class'      : 'logging.handlers.RotatingFileHandler',
            'filename'   : os.path.join(BASE_DIR,'logs','country_restriction.log'),
            'maxBytes'   : 1024*1024*log_size,
            'backupCount': 5,
            'formatter'  : 'verbose',
        },      
        'file_errors': {
            'level'      : log_level,
            'class'      : 'logging.handlers.RotatingFileHandler',
            'filename'   : os.path.join(BASE_DIR,'logs','django_errors.log'),
            'maxBytes'   : 1024*1024*log_size,
            'backupCount': 5,
            'formatter'  : 'verbose',
        }, 
        'celery': {
            'level'      : log_level,
            'class'      : 'logging.handlers.RotatingFileHandler',
            'filename'   : os.path.join(BASE_DIR,'logs','celery_process.log'),
            'maxBytes'   : 1024*1024*log_size, 
            'backupCount': 5,
            'formatter'  : 'verbose',
        },         
    },
    'loggers': {
        'django': {
            'handlers': ['file_general'],
            'level': log_level,
            'propagate': False,
        },
        'country_restriction': {
            'handlers': ['file_country_restriction'],
            'level': log_level,
            'propagate': False,
        },
        'celery_process': {
            'handlers': ['celery'],
            'level': log_level,
            'propagate': False,
        },
    },
}

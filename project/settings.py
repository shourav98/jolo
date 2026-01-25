
import os
from pathlib import Path
from datetime import timedelta
import os
from dotenv import load_dotenv
load_dotenv()
# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

###################################
#   SECURITY CONFIGURATION
###################################
SECRET_KEY = 'kcponinneq@v3g95g^#@r0-i6zz^sdu&2=p2glm@1u(^hv7ky5'

DEBUG = True   # ⚠️ Production e False korte hobe

ALLOWED_HOSTS = ['*']

###################################
#   APPLICATIONS
###################################
INSTALLED_APPS = [
    "daphne",
    "unfold",  # before django.contrib.admin
    "unfold.contrib.filters",  
    "unfold.contrib.forms",  
    "unfold.contrib.inlines",  
    "unfold.contrib.import_export",  
    "unfold.contrib.guardian",  
    "unfold.contrib.simple_history",  
    "unfold.contrib.location_field",  
    "unfold.contrib.constance",
    # Django default apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # 3rd party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'channels',
    'django_ckeditor_5',
     "drf_spectacular",
    # 'django.contrib.contenttypes'
    # 'corsheaders',

    # Local apps
    'apps.account.apps.AccountConfig',
    'apps.feed.apps.FeedConfig',
    'apps.messaging.apps.MessagingConfig',
    'apps.monetization.apps.MonetizationConfig',
    'apps.notification.apps.NotificationConfig',
    'apps.cms.apps.CmsConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    # 'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Custom middleware for online status tracking
    'apps.messaging.middleware.OnlineStatusMiddleware',
    'apps.messaging.middleware.RealTimeOnlineMiddleware',
]

ROOT_URLCONF = 'project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR/'templates'],
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

#WSGI_APPLICATION = 'project.wsgi.application'
ASGI_APPLICATION = 'project.asgi.application'


# Redis backend for channel layers
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("127.0.0.1", 6379)],  # or your Redis host
        },
    },
}

###################################
#   DATABASE
###################################
# from .conf import database
# DATABASES = database.SQLITE

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

###################################
#   PASSWORD VALIDATION
###################################
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

###################################
#   INTERNATIONALIZATION
###################################
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Dhaka'
USE_I18N = True
USE_TZ = True

###################################
#   STATIC & MEDIA FILES
###################################
STATIC_URL = '/static/'
STATICFILES_DIRS = [str(BASE_DIR / 'static')]  # cast Path to string
STATIC_ROOT = str(BASE_DIR / 'staticfiles')

MEDIA_URL = '/media/'
MEDIA_ROOT = str(BASE_DIR / 'media')

DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


###################################
#   EMAIL CONFIG
###################################
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
# In production: use SMTP instead of console

###################################
#   DJANGO REST FRAMEWORK
###################################
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
	'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication'
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'EXCEPTION_HANDLER': 'project.custom_exception.custom_exception_handler',
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    
}

# api documentation settings
SPECTACULAR_SETTINGS = {
    'AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'SWAGGER_UI_SETTINGS': {
        'persistAuthorization': True,
    },
}

###################################
#   SIMPLE JWT CONFIG
###################################
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=1500),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=2),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

###################################
#   CUSTOM USER MODEL
###################################
AUTH_USER_MODEL = 'account.CustomUser'


###################################
#   CORS
###################################
# CORS_ALLOW_ALL_ORIGINS = True
CSRF_TRUSTED_ORIGINS = [
	'https://jolo.softvencealpha.com'
]

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'debug.log',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'apps.messaging': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}






CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-reset-token-cache',
    }
}



#stripe

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
STRIPE_SUCCESS_URL = os.getenv("STRIPE_SUCCESS_URL", "http://localhost:3000/payment/success")
# Cloudinary settings
import cloudinary
import cloudinary.uploader
import cloudinary.api



CLOUDINARY_CLOUD_NAME = 'drgex74p8'
CLOUDINARY_API_KEY = '299944692925619'
CLOUDINARY_API_SECRET = 'jE2dwOn2xNtvkvPczMqZg5SEuvM'


# CLOUDINARY_CLOUD_NAME = 'di0lvpobz'
# CLOUDINARY_API_KEY = '683753412926143'
# CLOUDINARY_API_SECRET = 'U7x96FUna9_8hYZ3807YNqj_cGI'

cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET
)
STRIPE_CANCEL_URL = os.getenv("STRIPE_CANCEL_URL", "http://localhost:3000/payment/cancel")


CKEDITOR_5_CONFIGS = {
    'extends': {
        'toolbar': [
            'heading', '|',
            'bold', 'italic', 'underline', 'strikethrough', '|',
            'bulletedList', 'numberedList', '|',
            'link', 'blockQuote', '|',
            'undo', 'redo',
        ],
    },
}


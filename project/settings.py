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
    "unfold",  # before django.contrib.admin
    "unfold.contrib.filters",  # optional, if special filters are needed
    "unfold.contrib.forms",  # optional, if special form elements are needed
    "unfold.contrib.inlines",  # optional, if special inlines are needed
    "unfold.contrib.import_export",  # optional, if django-import-export package is used
    "unfold.contrib.guardian",  # optional, if django-guardian package is used
    "unfold.contrib.simple_history",  # optional, if django-simple-history package is used
    "unfold.contrib.location_field",  # optional, if django-location-field package is used
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
    # 'django.contrib.contenttypes'
    # 'corsheaders',

    # Local apps
    'apps.account',
    'apps.feed.apps.FeedConfig',
    'apps.monetization'

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

WSGI_APPLICATION = 'project.wsgi.application'
# ASGI_APPLICATION = 'project.asgi.application'

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
TIME_ZONE = 'UTC'
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
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'EXCEPTION_HANDLER': 'project.custom_exception.custom_exception_handler',
}

###################################
#   SIMPLE JWT CONFIG
###################################
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
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
STRIPE_CANCEL_URL = os.getenv("STRIPE_CANCEL_URL", "http://localhost:3000/payment/cancel")

"""
Django settings for core project.

Lee variables de entorno desde el `.env` en el root del proyecto
(un nivel arriba de `backend/`), centralizado para backend y frontend.
"""

from datetime import timedelta
from pathlib import Path

from decouple import Config, Csv, RepositoryEnv

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent

_root_env = PROJECT_ROOT / ".env"
if _root_env.exists():
    config = Config(RepositoryEnv(str(_root_env)))
else:
    from decouple import config  # fallback a variables del entorno del proceso

ENVIRONMENT = config("ENVIRONMENT", default="development")
IS_PRODUCTION = ENVIRONMENT == "production"

SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost", cast=Csv())


INSTALLED_APPS = [
    "jobs",
    "users",
    "dashboard",
    "notifications",
    "tips",
    "corsheaders",
    "rest_framework",
    # Necesario para invalidar refresh tokens al rotar (SEGURIDAD).
    "rest_framework_simplejwt.token_blacklist",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"


# ----- Base de datos -----
DATABASE_ENGINE = config("DATABASE_ENGINE", default="django.db.backends.sqlite3")

if DATABASE_ENGINE == "django.db.backends.sqlite3":
    DATABASES = {
        "default": {
            "ENGINE": DATABASE_ENGINE,
            "NAME": PROJECT_ROOT / config("DATABASE_NAME", default="database/db.sqlite3"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": DATABASE_ENGINE,
            "NAME": config("DATABASE_NAME"),
            "USER": config("DATABASE_USER"),
            "PASSWORD": config("DATABASE_PASSWORD"),
            "HOST": config("DATABASE_HOST", default="localhost"),
            "PORT": config("DATABASE_PORT", default="5432"),
        }
    }


AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
AUTH_USER_MODEL = "users.User"


# ----- CORS -----
CORS_ALLOWED_ORIGINS = config("CORS_ALLOWED_ORIGINS", default="http://localhost:4200", cast=Csv())
CORS_ALLOW_CREDENTIALS = True

# SEGURIDAD: prevenir misconfiguración de CORS en prod. La combinación
# wildcard + credentials viola la spec del navegador y, si se logra
# servir, expone los tokens del usuario a cualquier origen.
if IS_PRODUCTION:
    for _origin in CORS_ALLOWED_ORIGINS:
        if "*" in _origin or _origin.strip() in ("", "null"):
            from django.core.exceptions import ImproperlyConfigured

            raise ImproperlyConfigured(
                f"CORS_ALLOWED_ORIGINS contiene un valor inseguro en producción: {_origin!r}"
            )


# ----- DRF + JWT -----
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

# SEGURIDAD: si el cache backend (Redis) está down, django-ratelimit
# por defecto tira ConnectionError → 500 en cada endpoint decorado. Eso
# es un DoS auto-infligido: si Redis se cae, no podés ni loguearte.
# FAIL_OPEN=True deja pasar la request cuando no se puede consultar el
# rate limit. Trade: perdemos el limit temporal, pero el sitio sigue
# vivo y se loguea el problema. En prod monitor en Grafana el up/down.
RATELIMIT_FAIL_OPEN = True


# OBSERVABILIDAD: el default de Django manda `django.request` a
# `mail_admins`, y como no tenemos ADMINS configurado los 500 se pierden
# sin dejar rastro. Mandamos todo a stderr — gunicorn (--error-logfile -)
# lo captura → journalctl → diagnóstico real cuando algo revienta.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{asctime} [{levelname}] {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        # Stack traces de 500s — el motivo de este bloque.
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        # DB queries solo si DEBUG, demasiado ruidoso en prod.
        "django.db.backends": {
            "level": "WARNING",
            "propagate": False,
        },
    },
}

SIMPLE_JWT = {
    # SEGURIDAD:
    # - Access token corto (15 min) limita ventana de explotación si
    #   un atacante exfiltra el token via XSS o sniffing.
    # - Refresh token rota en cada uso (`ROTATE_REFRESH_TOKENS=True`)
    #   y el viejo se blacklistea (`BLACKLIST_AFTER_ROTATION=True`).
    #   Si un refresh es robado, en cuanto el legítimo lo use el del
    #   atacante queda invalidado.
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}


# ----- Celery -----
CELERY_BROKER_URL = config("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", default="redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutos

# Beat schedule — tareas recurrentes. Requiere `skiltak-celerybeat.service`
# corriendo en el VPS además del worker. En dev se levanta a mano con
# `celery -A core beat`.
from celery.schedules import crontab  # noqa: E402

CELERY_BEAT_SCHEDULE = {
    # Lunes 06:00 UTC (03:00 ART, 01:00 COT): horario de baja carga.
    "generate-weekly-tips": {
        "task": "tips.generate_weekly_tips",
        "schedule": crontab(hour=6, minute=0, day_of_week=1),
    },
    # 04:00 UTC todos los días (01:00 ART, 23:00 COT del día anterior).
    # Antes del horario en que los usuarios chequean ofertas. La tarea
    # serializa los users — con ~100 usuarios y ~30s por scrape, cabe en
    # la ventana sin saturar.
    "daily-scrape-for-active-users": {
        "task": "jobs.daily_scrape_for_active_users",
        "schedule": crontab(hour=4, minute=0),
    },
    # Limpieza de ofertas de más de 30 días — los portales descontinúan
    # constantemente y el feed con cosas viejas pierde relevancia.
    # 05:00 UTC, después del scrape diario.
    "clean-old-offers": {
        "task": "jobs.clean_old_offers",
        "schedule": crontab(hour=5, minute=0),
    },
}


# ----- Redis cache + sesiones -----
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": config("REDIS_CACHE_URL", default="redis://127.0.0.1:6379/1"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
        "KEY_PREFIX": "skillbridge",
        "TIMEOUT": 300,
    }
}

SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

# SEGURIDAD: sesiones más cortas + cierre por browser close. La sesión
# vive 8h (jornada laboral) y se invalida si el usuario cierra el
# browser. Reduce ventana de explotación si una máquina compartida
# queda sin lock.
SESSION_COOKIE_AGE = 60 * 60 * 8  # 8 horas
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# SEGURIDAD: límite duro de body request para mitigar DoS por upload
# masivo. Coincide con `_MAX_IMAGE_BYTES` del validator + margen para
# multipart overhead. Para uploads de CV (10MB) usar un endpoint
# dedicado con override local si es necesario.
DATA_UPLOAD_MAX_MEMORY_SIZE = 12 * 1024 * 1024  # 12 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 12 * 1024 * 1024


# ----- Archivos estáticos y media -----
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ----- Email -----
EMAIL_BACKEND = config("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = config("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="noreply@skiltak.com")

PASSWORD_RESET_TIMEOUT = 600  # 10 min


# ----- Hardening de producción -----
if IS_PRODUCTION:
    # Cuando nginx habla con gunicorn por unix socket, REMOTE_ADDR queda
    # vacío y django-ratelimit con key='ip' explota con ImproperlyConfigured.
    # Nginx reenvía la IP del cliente real en X-Real-IP — le decimos a
    # ratelimit que mire ese header. Scoped a prod porque en dev/test
    # REMOTE_ADDR sí está poblado y queremos el comportamiento default.
    #
    # SEGURIDAD: spoofear este header requiere bypass de nginx (que
    # rebinda el valor a $remote_addr, descartando lo que mande el
    # cliente). Gunicorn solo escucha en el socket unix local — no hay
    # vector externo para inyectar X-Real-IP falso.
    RATELIMIT_IP_META_KEY = "HTTP_X_REAL_IP"

    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
    SECURE_BROWSER_XSS_FILTER = True  # legacy header, no daña (defense-in-depth)
    X_FRAME_OPTIONS = "DENY"
    CSRF_TRUSTED_ORIGINS = config(
        "CSRF_TRUSTED_ORIGINS",
        default="https://skiltak.com,https://www.skiltak.com,https://api.skiltak.com",
        cast=Csv(),
    )

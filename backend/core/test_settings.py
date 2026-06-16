"""Configuración de Django para tests.

Importa todo de `core.settings` y reemplaza solo lo que no debe
depender de servicios externos durante los tests:

  - Base de datos: SQLite en memoria (rápida y aislada).
  - Cache: locmem (no requiere Redis corriendo).
  - Celery: modo eager (las tasks se ejecutan sincrónicamente en el mismo proceso).
  - Email: backend in-memory.
  - Password hashers: el más rápido (acelera ~3x los tests con usuarios).
"""

from core.settings import *  # noqa: F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

SESSION_ENGINE = "django.contrib.sessions.backends.db"

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# El hardening de producción no aplica en tests
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0

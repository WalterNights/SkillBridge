from django.apps import AppConfig


class JobsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "jobs"

    def ready(self) -> None:
        # Side effects de import: registra los @receiver de signals.py.
        # Hay que hacerlo acá (no a nivel de módulo) para que Django ya
        # tenga todas las apps cargadas cuando el handler resuelve
        # `UserProfile`.
        from jobs import signals  # noqa: F401

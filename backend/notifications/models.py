from django.conf import settings
from django.db import models


class Notification(models.Model):
    """Notificación in-app para un usuario.

    Diseño minimalista a propósito:
      - `kind` decide el ícono y el copy del frontend (match/reminder/system)
      - `metadata` JSON para data libre (ej: lista de offer ids del match)
        sin tener que migrar la tabla por cada nuevo tipo de notif
      - `is_read` y `is_saved` son flags independientes — una notif puede
        estar guardada y leída a la vez
    """

    KIND_CHOICES = [
        ("match", "Match"),
        ("reminder", "Reminder"),
        ("system", "System"),
        # Una empresa marcó interés en este profesional. El metadata
        # lleva company_id, legal_name, responsible_name y responsible_role
        # para que el frontend renderice la noti sin un roundtrip extra.
        ("company_interest", "Company Interest"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    kind = models.CharField(max_length=16, choices=KIND_CHOICES)
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    is_read = models.BooleanField(default=False)
    is_saved = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            # El listado del drawer filtra por user + (is_read|is_saved) y
            # ordena por created_at desc. Este índice cubre los 3 tabs.
            models.Index(fields=["user", "-created_at"]),
        ]

    def __str__(self):
        return f"[{self.kind}] {self.title} → {self.user.username}"

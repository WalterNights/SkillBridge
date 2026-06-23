from django.conf import settings
from django.db import models


class JobApplication(models.Model):
    """Postulación de un usuario a una oferta.

    Flujo de status:
      - `pending`: el user clickeó "Aplicar en {portal}" — se abrió el
        portal pero todavía no confirmó que efectivamente aplicó.
      - `applied`: el user confirmó "Sí, aplicé" desde la card de
        confirmación del job-detail.

    Si dice "No, todavía no", la fila se borra (no se queda como
    pending huérfano).

    `unique_together` evita doble registro si el user clickea Apply
    dos veces; el flujo siempre usa `get_or_create` o `update_or_create`.
    """

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("applied", "Applied"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="applications",
    )
    offer = models.ForeignKey(
        "jobs.JobOffer",
        on_delete=models.CASCADE,
        related_name="applications",
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    clicked_at = models.DateTimeField(auto_now_add=True)
    applied_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("user", "offer")
        ordering = ["-applied_at", "-clicked_at"]
        indexes = [
            # El feed pide "¿esta oferta ya está aplicada?" para muchas
            # ofertas a la vez — query típico: user + offer__in=[...].
            models.Index(fields=["user", "status"]),
        ]

    def __str__(self):
        return f"{self.user.username} → {self.offer.title} ({self.status})"

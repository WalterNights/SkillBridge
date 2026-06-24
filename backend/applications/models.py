from django.conf import settings
from django.db import models


class JobApplication(models.Model):
    """Postulación de un usuario a una oferta.

    Flujo de status (estados desde click hasta resolución del proceso):
      - `pending`:    el user clickeó "Aplicar en {portal}" pero no
                      confirmó. Si dice "No, todavía no", la fila se borra.
      - `applied`:    el user confirmó "Sí, aplicé". Default después de
                      la card de confirmación del job-detail.
      - `in_review`:  el user marca manualmente que el HR confirmó
                      recepción / pidió info / dio next step de pantalla.
      - `interview`:  agendaron entrevista. Cualquier formato.
      - `offer`:      hicieron una oferta concreta.
      - `rejected`:   rechazaron la postulación.
      - `withdrawn`:  el user retiró su postulación (cambió de opinión).

    Las transiciones son libres — un user puede mover una postulación
    entre estados como necesite (ej. de `interview` de vuelta a
    `in_review` si pospusieron una entrevista). No enforcemos un
    state machine estricto porque los procesos de HR son caóticos
    en la realidad y la lógica de "qué es válido" no nos corresponde.

    `unique_together` evita doble registro si el user clickea Apply
    dos veces; el flujo siempre usa `get_or_create` o `update_or_create`.
    """

    STATUS_CHOICES = [
        ("pending", "Pendiente de confirmar"),
        ("applied", "Aplicada"),
        ("in_review", "En revisión"),
        ("interview", "Entrevista"),
        ("offer", "Oferta recibida"),
        ("rejected", "Rechazada"),
        ("withdrawn", "Retirada"),
    ]

    # Estados que cuentan como "activo" — el user todavía espera respuesta
    # o tiene proceso vivo. Usado por el frontend para filtrar el feed
    # de "Mis postulaciones" sin las cerradas.
    ACTIVE_STATUSES = frozenset({"applied", "in_review", "interview", "offer"})

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
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="pending")
    clicked_at = models.DateTimeField(auto_now_add=True)
    applied_at = models.DateTimeField(null=True, blank=True)
    # Snapshot del último cambio de status — útil para sorting "última
    # actividad" y para mostrar "actualizado hace N días" en la UI.
    status_changed_at = models.DateTimeField(null=True, blank=True)
    # Notas libres del user sobre su proceso (recordatorio, contactos).
    # Opcional, no se renderiza si está vacío.
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ("user", "offer")
        # Ordering: las recién aplicadas primero, después por último cambio.
        # Postulaciones cerradas (rejected/withdrawn) caen al fondo
        # naturalmente porque applied_at no se actualiza al cerrarlas.
        ordering = ["-status_changed_at", "-applied_at", "-clicked_at"]
        indexes = [
            # El feed pide "¿esta oferta ya está aplicada?" para muchas
            # ofertas a la vez — query típico: user + offer__in=[...].
            models.Index(fields=["user", "status"]),
        ]

    def __str__(self):
        return f"{self.user.username} → {self.offer.title} ({self.status})"

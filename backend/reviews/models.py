"""Reseñas de la plataforma escritas por usuarios reales.

Diseño:
  - Una reseña por usuario (`OneToOne`). Editarla la devuelve a
    `pending` — el admin vuelve a aprobar el texto nuevo.
  - Solo pueden opinar usuarios con al menos
    `settings.REVIEWS_MIN_APPLICATIONS` postulaciones reales (ver
    `reviews.services.eligibility`). Así no entra cualquiera a dejar
    una reseña sin haber usado el producto.
  - El landing muestra solo reseñas que cumplen TRES condiciones, sin
    análisis de texto ni AI:
      1. `status='published'` (aprobada por un admin),
      2. `rating >= LANDING_MIN_RATING` (la señal la da el propio user),
      3. `allow_public=True` (consentimiento explícito para mostrar
         nombre, cargo, ciudad y foto — Ley 1581 de datos personales).
    Las reseñas bajas NO se borran: quedan como feedback para el admin.
"""

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

# Rating mínimo para aparecer en el landing.
LANDING_MIN_RATING = 4
COMMENT_MIN_LENGTH = 20
COMMENT_MAX_LENGTH = 500


class Review(models.Model):
    STATUS_PENDING = "pending"
    STATUS_PUBLISHED = "published"
    STATUS_REJECTED = "rejected"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pendiente"),
        (STATUS_PUBLISHED, "Publicada"),
        (STATUS_REJECTED, "Rechazada"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="review",
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    comment = models.CharField(max_length=COMMENT_MAX_LENGTH)
    allow_public = models.BooleanField(
        default=False,
        help_text="El usuario autorizó mostrar su reseña, nombre y foto en el landing.",
    )

    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True
    )
    moderated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="moderated_reviews",
    )
    moderated_at = models.DateTimeField(null=True, blank=True)
    moderation_note = models.CharField(max_length=200, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            # El endpoint del landing filtra status + rating + allow_public.
            models.Index(fields=["status", "rating"]),
        ]

    def __str__(self) -> str:
        return f"[{self.status}] {self.user} ★{self.rating}"

"""Modelos del sistema FAQ.

Diseño:
  - `FaqCategory` es CRUD-eable por admin (no enum), así pueden añadir
    "Pricing" o "API" sin migración.
  - `FaqQuestion` arranca con `status='pending'` para preguntas de
    usuarios. El admin decide publicarlas (visibles en `/faq`) o
    rechazarlas (soft-delete: queda para analytics).
  - Las preguntas curadas a mano se cargan con `source='seed'` y
    `status='published'` directo desde data migration.

Tracking: NO borramos preguntas rechazadas. Sirven para detectar
patrones (qué confunde a la gente, qué features faltan, etc.).
"""

from django.conf import settings
from django.db import models
from django.utils.text import slugify


class FaqCategory(models.Model):
    """Agrupador visual del FAQ público (Cuenta, CV, Matches, etc.)."""

    name = models.CharField(max_length=60, unique=True)
    # Slug para URLs limpias en el futuro (`/faq/cv`) y como clave estable
    # entre frontend y backend.
    slug = models.SlugField(max_length=80, unique=True, blank=True)
    description = models.CharField(max_length=200, blank=True)
    display_order = models.PositiveIntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["display_order", "name"]
        verbose_name_plural = "Faq categories"

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:80]
        super().save(*args, **kwargs)


class FaqQuestion(models.Model):
    """Una entrada del FAQ. Vive en distintos estados según moderación."""

    STATUS_PENDING = "pending"
    STATUS_PUBLISHED = "published"
    STATUS_REJECTED = "rejected"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pendiente"),
        (STATUS_PUBLISHED, "Publicado"),
        (STATUS_REJECTED, "Rechazado"),
    ]

    SOURCE_SEED = "seed"
    SOURCE_USER = "user"
    SOURCE_CHOICES = [
        (SOURCE_SEED, "Curado por admin"),
        (SOURCE_USER, "Pregunta de usuario"),
    ]

    question = models.CharField(max_length=300)
    # `answer` es la respuesta canónica mostrada al público. Para `seed`
    # se llena a mano; para `user` arranca como copia del `ai_draft` y
    # el admin puede editarla antes de publicar.
    answer = models.TextField(blank=True)
    # Preservamos el draft AI sin modificar — sirve como referencia para
    # ver cuánto editó el admin y para análisis de calidad del modelo.
    ai_draft = models.TextField(blank=True)

    category = models.ForeignKey(
        FaqCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="questions",
    )

    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default=SOURCE_USER)
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True
    )

    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="asked_faqs",
    )
    moderated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="moderated_faqs",
    )
    moderated_at = models.DateTimeField(null=True, blank=True)
    # Razón opcional cuando se rechaza (para tener trazabilidad de por
    # qué se rechazó — ofensivo, irrelevante, duplicado, etc.).
    moderation_note = models.CharField(max_length=200, blank=True)

    # Tracking / analytics
    view_count = models.PositiveIntegerField(default=0)
    display_order = models.PositiveIntegerField(default=0, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            # `/api/faq/` filtra `status='published'` y ordena por
            # category + display_order — este índice cubre ese query.
            models.Index(fields=["status", "category", "display_order"]),
        ]

    def __str__(self) -> str:
        return f"[{self.status}] {self.question[:60]}"

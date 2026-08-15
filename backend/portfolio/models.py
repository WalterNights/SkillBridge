"""Modelo del portafolio público editable por admins.

Diseño intencional:

- Un `Portfolio` = un slug (ej. "walternightsdev") = una URL pública
  (`/portafolio/walternightsdev`). `owner` FK a User existe para poder
  extender a multi-tenant sin refactor: hoy solo se crea uno via data
  migration, mañana los admins podrán crear los suyos con `slug` único.
- `content` y `content_en` son JSONField porque el contenido de un
  portafolio se edita como un todo (hero + about + experience + projects
  + contact + sidebar) y no hacemos queries sobre campos internos. La
  forma del JSON es un contrato con el frontend — se documenta en
  `frontend/src/app/portfolio/i18n/es.json`.
- `PortfolioImage` NO va dentro del JSON: los ImageFields necesitan
  storage real (multipart upload, MEDIA_URL, validación por magic
  bytes). Cada imagen se referencia desde el JSON por `project_id`
  (matchea `Project.id` en el frontend). Diseño simétrico al del CV
  (photo/banner de UserProfile).
"""

from __future__ import annotations

from django.conf import settings
from django.db import models

from users.models import validate_uploaded_image


class Portfolio(models.Model):
    """Portafolio público de un admin. Uno por slug."""

    slug = models.SlugField(
        max_length=64,
        unique=True,
        help_text="Segmento de URL público — /portafolio/<slug>.",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="portfolios",
        help_text="Dueño del contenido. Solo el owner (o cualquier admin) puede editar.",
    )
    # JSON blob con el árbol completo de contenido en el idioma default (ES).
    # Estructura: {"hero": {...}, "about": {...}, "experience": {...},
    #              "projects": {...}, "contact": {...}, "sidebar": {...}}
    # El schema exacto lo define el frontend (portfolio/i18n/es.json).
    content = models.JSONField(default=dict, blank=True)
    # Mismo schema, versión EN. Se guardan por separado para simplificar
    # el editor (un PUT sobrescribe ambos idiomas atómicamente).
    content_en = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["slug"]

    def __str__(self) -> str:
        return f"Portfolio<{self.slug}>"


def _portfolio_cover_upload_path(instance: "PortfolioImage", filename: str) -> str:
    """Namespace por slug para evitar colisiones y facilitar limpieza."""
    return f"portfolio_covers/{instance.portfolio.slug}/{filename}"


class PortfolioImage(models.Model):
    """Cover de un proyecto del portafolio.

    Un mismo `project_id` puede tener varias imágenes (por si en el
    futuro queremos galería), pero el frontend hoy usa solo la más
    reciente. `unique_together` NO se aplica adrede para permitir esa
    evolución sin migration.
    """

    portfolio = models.ForeignKey(
        Portfolio,
        on_delete=models.CASCADE,
        related_name="images",
    )
    project_id = models.SlugField(
        max_length=64,
        help_text="Matchea `Project.id` del JSON de content (ej. 'ranktitan').",
    )
    image = models.ImageField(
        upload_to=_portfolio_cover_upload_path,
        validators=[validate_uploaded_image],
    )
    alt_text = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Descripción para accesibilidad. Se muestra en <img alt>.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["portfolio", "project_id"]),
        ]

    def __str__(self) -> str:
        return f"PortfolioImage<{self.portfolio.slug}/{self.project_id}>"

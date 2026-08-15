"""Serializers del portafolio.

Dos audiencias:

- **Público** (`PortfolioPublicSerializer`): lo consume el shell en
  `/portafolio/<slug>` sin auth. Devuelve el árbol completo listo para
  renderizar. Sin PII sensible, ni FK a User expuesto.
- **Admin** (`PortfolioAdminSerializer`): expone lo mismo + campos de
  gestión (updated_at) para el editor. El PUT del editor manda el JSON
  completo — no hacemos merge parcial para evitar bugs sutiles cuando
  el editor borra items de un array.
"""

from __future__ import annotations

from rest_framework import serializers

from portfolio.models import Portfolio, PortfolioImage


class PortfolioImageSerializer(serializers.ModelSerializer):
    """Salida standard de una cover. `url` es absoluta si el request lo
    permite (drf inyecta el host); en su defecto queda relativa a
    MEDIA_URL, y el frontend la resuelve contra el base URL de la API."""

    url = serializers.SerializerMethodField()

    class Meta:
        model = PortfolioImage
        fields = ["id", "project_id", "url", "alt_text", "created_at"]
        read_only_fields = ["id", "url", "created_at"]

    def get_url(self, obj: PortfolioImage) -> str:
        request = self.context.get("request")
        url = obj.image.url
        return request.build_absolute_uri(url) if request else url


class PortfolioImageUploadSerializer(serializers.ModelSerializer):
    """Input del POST — el frontend manda multipart con `image`,
    `project_id` y `alt_text`. La validación de la imagen la hace el
    validator del modelo (magic bytes, tamaño, extensión)."""

    class Meta:
        model = PortfolioImage
        fields = ["id", "project_id", "image", "alt_text"]
        read_only_fields = ["id"]


class PortfolioPublicSerializer(serializers.ModelSerializer):
    """Salida pública — sin owner, sin updated_at, sin metadata interna.
    El shell consume este payload y lo mergea sobre los defaults de
    i18n del bundle."""

    images = PortfolioImageSerializer(many=True, read_only=True)

    class Meta:
        model = Portfolio
        fields = ["slug", "content", "content_en", "images"]
        read_only_fields = fields


class PortfolioAdminSerializer(serializers.ModelSerializer):
    """Serializer admin — mismo payload que el público + metadata.
    `slug` y `owner` son read-only: la creación de portafolios no va por
    la API pública (data migration o admin de Django solamente)."""

    images = PortfolioImageSerializer(many=True, read_only=True)

    class Meta:
        model = Portfolio
        fields = [
            "slug",
            "content",
            "content_en",
            "images",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["slug", "images", "created_at", "updated_at"]

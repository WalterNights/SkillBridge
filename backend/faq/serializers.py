"""Serializers del FAQ.

Tres formas distintas:
  - Public: lo que ve el visitante de `/faq` (categorías + Q&A
    publicadas, sin metadata interna).
  - Submit: input del POST /api/faq/ask/ (solo `question`).
  - Admin: vista completa con todos los campos de moderación + AI draft.
"""

from rest_framework import serializers

from faq.models import FaqCategory, FaqQuestion


class FaqCategorySerializer(serializers.ModelSerializer):
    """Vista pública de categorías. Solo `is_active=True` desde la view."""

    class Meta:
        model = FaqCategory
        fields = ["id", "name", "slug", "description", "display_order"]


class FaqPublicSerializer(serializers.ModelSerializer):
    """Vista del FAQ público — solo lo que el visitante necesita ver.

    No expone: ai_draft, submitted_by, moderation_note, status, source.
    Esos viven detrás del endpoint admin.
    """

    category = FaqCategorySerializer(read_only=True)

    class Meta:
        model = FaqQuestion
        fields = [
            "id",
            "question",
            "answer",
            "category",
            "display_order",
            "view_count",
            "created_at",
            "updated_at",
        ]


class FaqSubmitSerializer(serializers.Serializer):
    """Input del POST /api/faq/ask/.

    SEGURIDAD: no aceptamos `answer` ni `status` del cliente — esos
    los pone el servidor (AI genera el draft, status arranca pending).
    """

    question = serializers.CharField(
        min_length=10,
        max_length=300,
        trim_whitespace=True,
        help_text="La pregunta del usuario (10-300 chars).",
    )


class FaqAdminSerializer(serializers.ModelSerializer):
    """Vista admin — todos los campos relevantes para moderar.

    Read-only los que NO debe poder cambiar el admin desde el panel:
      - source (no se puede convertir un user-q en seed)
      - submitted_by (autor original)
      - ai_draft (referencia inmutable de qué generó el modelo)
      - created_at / view_count / moderated_at (timestamps gestionados)
    """

    category = FaqCategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=FaqCategory.objects.all(),
        source="category",
        write_only=True,
        required=False,
        allow_null=True,
    )
    submitted_by_username = serializers.CharField(
        source="submitted_by.username", read_only=True, default=""
    )
    moderated_by_username = serializers.CharField(
        source="moderated_by.username", read_only=True, default=""
    )

    class Meta:
        model = FaqQuestion
        fields = [
            "id",
            "question",
            "answer",
            "ai_draft",
            "category",
            "category_id",
            "source",
            "status",
            "submitted_by",
            "submitted_by_username",
            "moderated_by",
            "moderated_by_username",
            "moderated_at",
            "moderation_note",
            "view_count",
            "display_order",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "source",
            "submitted_by",
            "submitted_by_username",
            "moderated_by",
            "moderated_by_username",
            "moderated_at",
            "ai_draft",
            "view_count",
            "created_at",
            "updated_at",
        ]

"""Serializers de reseñas.

Tres audiencias:
  - Own (`ReviewOwnSerializer`): el usuario crea/edita su reseña. Solo
    puede tocar rating, comment y allow_public — status y moderación
    son read-only.
  - Landing (`ReviewLandingSerializer`): lo que ve cualquier visitante.
    Nombre abreviado ("Martina G."), cargo, ciudad y foto del perfil.
    Sin email, username ni ids de usuario.
  - Admin (`ReviewAdminSerializer`): todo, para la cola de moderación.
"""

from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers

from reviews.models import COMMENT_MIN_LENGTH, LANDING_MIN_RATING, Review


def _profile_of(user):
    """`user.profile` levanta si el user nunca completó el perfil."""
    try:
        return user.profile
    except ObjectDoesNotExist:
        return None


def _short_name(user) -> str:
    profile = _profile_of(user)
    if profile and profile.first_name.strip():
        last = profile.last_name.strip()
        initial = f" {last[0]}." if last else ""
        return f"{profile.first_name.strip()}{initial}"
    return user.username


class ReviewOwnSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = [
            "rating",
            "comment",
            "allow_public",
            "status",
            "moderation_note",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["status", "moderation_note", "created_at", "updated_at"]

    def validate_comment(self, value: str) -> str:
        value = value.strip()
        if len(value) < COMMENT_MIN_LENGTH:
            raise serializers.ValidationError(
                f"Cuéntanos un poco más (mínimo {COMMENT_MIN_LENGTH} caracteres)."
            )
        return value


class ReviewLandingSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    city = serializers.SerializerMethodField()
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ["id", "rating", "comment", "name", "role", "city", "photo_url"]

    def get_name(self, obj: Review) -> str:
        return _short_name(obj.user)

    def get_role(self, obj: Review) -> str:
        profile = _profile_of(obj.user)
        return profile.professional_title if profile else ""

    def get_city(self, obj: Review) -> str:
        profile = _profile_of(obj.user)
        return profile.city if profile else ""

    def get_photo_url(self, obj: Review) -> str | None:
        profile = _profile_of(obj.user)
        if not profile or not profile.photo:
            return None
        request = self.context.get("request")
        url = profile.photo.url
        return request.build_absolute_uri(url) if request else url


class ReviewAdminSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    display_name = serializers.SerializerMethodField()
    moderated_by_username = serializers.CharField(
        source="moderated_by.username", read_only=True, default=""
    )
    landing_eligible = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = [
            "id",
            "username",
            "display_name",
            "rating",
            "comment",
            "allow_public",
            "landing_eligible",
            "status",
            "moderation_note",
            "moderated_by_username",
            "moderated_at",
            "created_at",
            "updated_at",
        ]
        # El admin modera, no reescribe la opinión del usuario.
        read_only_fields = [
            "id",
            "username",
            "display_name",
            "rating",
            "comment",
            "allow_public",
            "moderated_by_username",
            "moderated_at",
            "created_at",
            "updated_at",
        ]

    def get_display_name(self, obj: Review) -> str:
        return _short_name(obj.user)

    def get_landing_eligible(self, obj: Review) -> bool:
        """Si se publica, ¿llega al landing? (misma regla que ReviewLandingView)."""
        return obj.rating >= LANDING_MIN_RATING and obj.allow_public

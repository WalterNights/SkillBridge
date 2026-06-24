from rest_framework import serializers

from applications.models import CoverLetter, JobApplication
from jobs.models import JobOffer
from jobs.serializers import JobOfferSerializer


class JobApplicationSerializer(serializers.ModelSerializer):
    """Serializer del modelo JobApplication.

    `offer` anidado para que el view de "Mis postulaciones" renderee
    título/empresa/portal sin un round-trip extra. `offer_id` solo en
    el create (write-only) para no duplicar payload en el response.
    """

    offer = JobOfferSerializer(read_only=True)
    offer_id = serializers.PrimaryKeyRelatedField(
        source="offer",
        queryset=JobOffer.objects.all(),
        write_only=True,
    )

    class Meta:
        model = JobApplication
        fields = [
            "id",
            "offer",
            "offer_id",
            "status",
            "clicked_at",
            "applied_at",
            "status_changed_at",
            "notes",
        ]
        # `notes` editable via PATCH /applications/{id}/.
        # `status` se cambia via /update-status/ o /confirm/ — no via PATCH
        # directo para preservar las side-effects (status_changed_at).
        read_only_fields = ["id", "status", "clicked_at", "applied_at", "status_changed_at"]


class CoverLetterSerializer(serializers.ModelSerializer):
    """Serializer del modelo CoverLetter.

    `content` editable via PATCH — al editarlo seteamos user_edited=True
    en la view para distinguir cartas "as generated" de las modificadas
    (afecta la advertencia "vas a perder tus cambios" al regenerar).
    Los snapshots de la oferta son read-only — se setean al crear y no
    se tocan después (la oferta puede borrarse, la carta sobrevive).
    """

    class Meta:
        model = CoverLetter
        fields = [
            "id",
            "offer",
            "offer_title_snapshot",
            "offer_company_snapshot",
            "offer_url_snapshot",
            "content",
            "tone",
            "language",
            "user_edited",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "offer",
            "offer_title_snapshot",
            "offer_company_snapshot",
            "offer_url_snapshot",
            "user_edited",
            "created_at",
            "updated_at",
        ]

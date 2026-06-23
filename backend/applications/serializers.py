from rest_framework import serializers

from applications.models import JobApplication
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
        fields = ["id", "offer", "offer_id", "status", "clicked_at", "applied_at"]
        read_only_fields = ["id", "status", "clicked_at", "applied_at"]

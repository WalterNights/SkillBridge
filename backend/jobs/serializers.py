from rest_framework import serializers

from .models import JobOffer


class JobOfferSerializer(serializers.ModelSerializer):
    matched_skills = serializers.SerializerMethodField()
    missing_skills = serializers.SerializerMethodField()
    match_percentage = serializers.SerializerMethodField()

    class Meta:
        model = JobOffer
        # SEGURIDAD: fields explícitos, no `__all__`. Blinda mass-assignment
        # si mañana el viewset pasa de ReadOnly a ModelViewSet — sin esto,
        # un POST podría setear `is_active`, `keywords`, `country`, `url`
        # y contaminar el feed. Todos los campos derivados (category,
        # modality, country, is_active) los calcula el pipeline de scrape,
        # jamás el cliente.
        fields = [
            "id",
            "title",
            "company",
            "location",
            "summary",
            "url",
            "keywords",
            "portal",
            "country",
            "modality",
            "salary_text",
            "category",
            "is_active",
            "last_checked_at",
            "created_at",
            "matched_skills",
            "missing_skills",
            "match_percentage",
        ]

    def get_match_percentage(self, job):
        return getattr(job, "match_percentage", None)

    def get_matched_skills(self, job):
        return getattr(job, "matched_skills", [])

    def get_missing_skills(self, job):
        return getattr(job, "missing_skills", [])

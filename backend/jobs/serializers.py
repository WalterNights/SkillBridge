from rest_framework import serializers

from .models import JobOffer
from .services.description_enricher import is_stub_summary
from .services.feed_preferences import MAX_COUNTRIES, PREFERABLE_MODALITIES


class JobOfferSerializer(serializers.ModelSerializer):
    matched_skills = serializers.SerializerMethodField()
    missing_skills = serializers.SerializerMethodField()
    match_percentage = serializers.SerializerMethodField()
    # Solo lo rellena el endpoint /ignored/ via `offer._ignore_reason`.
    # En el feed regular es "" — la UI lo ignora si esta vacio.
    ignore_reason = serializers.SerializerMethodField()
    summary_is_partial = serializers.SerializerMethodField()

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
            "ignore_reason",
            "summary_is_partial",
        ]

    def get_summary_is_partial(self, job) -> bool:
        """True si `summary` es un relleno y no la descripción real — el
        frontend muestra un link al portal para leerla completa."""
        return is_stub_summary(job)

    def get_match_percentage(self, job):
        return getattr(job, "match_percentage", None)

    def get_matched_skills(self, job):
        return getattr(job, "matched_skills", [])

    def get_missing_skills(self, job):
        return getattr(job, "missing_skills", [])

    def get_ignore_reason(self, job):
        return getattr(job, "_ignore_reason", "")


class FeedPreferencesSerializer(serializers.Serializer):
    """Valida las preferencias del feed antes de guardarlas en el perfil."""

    modalities_first = serializers.ListField(
        child=serializers.ChoiceField(choices=PREFERABLE_MODALITIES),
        required=False,
        default=list,
    )
    countries_first = serializers.ListField(
        child=serializers.RegexField(r"^[A-Za-z]{2}$"),
        required=False,
        default=list,
        max_length=MAX_COUNTRIES,
    )
    countries_last = serializers.ListField(
        child=serializers.RegexField(r"^[A-Za-z]{2}$"),
        required=False,
        default=list,
        max_length=MAX_COUNTRIES,
    )

    def validate(self, attrs):
        # ISO en mayúsculas y sin duplicados, preservando el orden elegido.
        for key in ("modalities_first", "countries_first", "countries_last"):
            values = [v.upper() if key.startswith("countries") else v for v in attrs[key]]
            attrs[key] = list(dict.fromkeys(values))
        overlap = set(attrs["countries_first"]) & set(attrs["countries_last"])
        if overlap:
            raise serializers.ValidationError(
                {"countries_last": f"Un país no puede ir primero y al final: {', '.join(sorted(overlap))}."}
            )
        return attrs


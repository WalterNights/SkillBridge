"""Serializer del POST /track/. Acepta el shape que manda el frontend
y aplica saneo defensivo (trim, truncate) — los campos largos no
levantan 400, se cortan al máximo.
"""

from rest_framework import serializers

from analytics.models import AnalyticsEvent


class TrackEventSerializer(serializers.Serializer):
    event_type = serializers.ChoiceField(
        choices=[c[0] for c in AnalyticsEvent.EVENT_CHOICES]
    )
    # `path` siempre es ruta del frontend. Forzamos `/` inicial para
    # normalizar y truncamos a 200 sin levantar error.
    path = serializers.CharField(max_length=300, trim_whitespace=True)
    label = serializers.CharField(
        max_length=80, required=False, allow_blank=True, default=""
    )
    anon_id = serializers.CharField(min_length=8, max_length=64, trim_whitespace=True)
    referrer = serializers.CharField(
        max_length=400, required=False, allow_blank=True, default=""
    )

    def validate_path(self, value: str) -> str:
        value = value.strip()
        if not value.startswith("/"):
            value = "/" + value
        return value[:200]

    def validate_referrer(self, value: str) -> str:
        return (value or "").strip()[:200]

from rest_framework import serializers

from tips.models import Tip


class TipSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tip
        fields = ["id", "text", "category", "source"]
        read_only_fields = fields

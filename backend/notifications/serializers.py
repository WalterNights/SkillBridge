from rest_framework import serializers

from notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id",
            "kind",
            "title",
            "body",
            "is_read",
            "is_saved",
            "metadata",
            "created_at",
        ]
        read_only_fields = fields

"""Admin Django de analytics — útil para debugging y limpieza retroactiva
(ej. borrar tráfico de un bot que el filter dejó pasar)."""

from django.contrib import admin

from analytics.models import AnalyticsEvent


@admin.register(AnalyticsEvent)
class AnalyticsEventAdmin(admin.ModelAdmin):
    list_display = ("created_at", "event_type", "path", "label", "user", "anon_id")
    list_filter = ("event_type", "created_at")
    search_fields = ("path", "label", "anon_id", "user_agent", "referrer")
    readonly_fields = (
        "event_type",
        "path",
        "label",
        "anon_id",
        "user",
        "referrer",
        "user_agent",
        "created_at",
    )

    def has_add_permission(self, request) -> bool:
        # Eventos solo se crean via API — no a mano desde el admin.
        return False

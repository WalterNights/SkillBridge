"""Django admin de reseñas — respaldo del UI custom en `/admin/reviews`."""

from django.contrib import admin

from reviews.models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("user", "rating", "status", "allow_public", "created_at")
    list_filter = ("status", "rating", "allow_public")
    search_fields = ("comment", "user__username", "user__email")
    readonly_fields = ("created_at", "updated_at", "moderated_by", "moderated_at")

"""Django admin para FAQ — útil cuando el UI custom no está disponible
(carga manual de batch, debugging en prod, etc.). El UI principal vive
en `/admin/faqs/` del frontend."""

from django.contrib import admin

from faq.models import FaqCategory, FaqQuestion


@admin.register(FaqCategory)
class FaqCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "display_order", "is_active", "created_at")
    list_editable = ("display_order", "is_active")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(FaqQuestion)
class FaqQuestionAdmin(admin.ModelAdmin):
    list_display = (
        "question_preview",
        "status",
        "source",
        "category",
        "submitted_by",
        "view_count",
        "created_at",
    )
    list_filter = ("status", "source", "category")
    search_fields = ("question", "answer", "ai_draft")
    readonly_fields = (
        "submitted_by",
        "ai_draft",
        "view_count",
        "created_at",
        "updated_at",
    )

    @admin.display(description="Pregunta")
    def question_preview(self, obj: FaqQuestion) -> str:
        return obj.question[:80] + ("…" if len(obj.question) > 80 else "")

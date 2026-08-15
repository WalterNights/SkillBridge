"""Django admin del portafolio — para inspeccionar / editar el JSON
crudo cuando el editor Angular no está disponible o hay un bug."""

from __future__ import annotations

from django.contrib import admin

from portfolio.models import Portfolio, PortfolioImage


class PortfolioImageInline(admin.TabularInline):
    model = PortfolioImage
    extra = 0
    readonly_fields = ["created_at"]


@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ["slug", "owner", "updated_at"]
    search_fields = ["slug", "owner__username"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [PortfolioImageInline]


@admin.register(PortfolioImage)
class PortfolioImageAdmin(admin.ModelAdmin):
    list_display = ["portfolio", "project_id", "created_at"]
    list_filter = ["portfolio"]
    search_fields = ["project_id", "portfolio__slug"]
    readonly_fields = ["created_at"]

"""Migra `sidebar.socials` de dict a lista de {id, url} y agrega
`sidebar.tech` como lista de icon IDs.

El schema pasó de:
    "socials": {"github": "GitHub", "linkedin": "LinkedIn", "email": "Email"}

a:
    "socials": [
        {"id": "github", "url": "https://…"},
        {"id": "linkedin", "url": "https://…"},
        {"id": "email", "url": "mailto:…"}
    ],
    "tech": ["python", "django", ...]

La migración es idempotente: si detecta que socials ya es una lista,
no toca nada. Si es un dict (formato viejo), lo convierte usando URLs
por default sensatos. `tech` se agrega vacío si no existe.

Se aplica sobre ambos JSONs (`content` y `content_en`) del portfolio.
"""

from __future__ import annotations

from django.db import migrations


_DEFAULT_URLS = {
    "github": "https://github.com/",
    "linkedin": "https://linkedin.com/in/",
    "email": "mailto:",
    "twitter": "https://x.com/",
    "x": "https://x.com/",
    "website": "https://",
}


def _upgrade_sidebar(content: dict) -> dict:
    """Muta `content['sidebar']` in-place al nuevo schema. Devuelve el
    dict raíz para chainar con `.save()`."""
    sidebar = content.get("sidebar")
    if not isinstance(sidebar, dict):
        return content

    # Migrar socials si sigue siendo un dict.
    socials = sidebar.get("socials")
    if isinstance(socials, dict):
        sidebar["socials"] = [
            {"id": key, "url": _DEFAULT_URLS.get(key, "https://")}
            for key in socials.keys()
        ]
    elif not isinstance(socials, list):
        sidebar["socials"] = []

    # Agregar tech si no existe.
    if "tech" not in sidebar or not isinstance(sidebar["tech"], list):
        sidebar["tech"] = []

    # Agregar techLabel si no existe (fallback para el sidebar del portafolio).
    if "techLabel" not in sidebar:
        sidebar["techLabel"] = "Stack"

    return content


def upgrade_sidebar_schema(apps, schema_editor):
    Portfolio = apps.get_model("portfolio", "Portfolio")
    for p in Portfolio.objects.all():
        p.content = _upgrade_sidebar(p.content or {})
        p.content_en = _upgrade_sidebar(p.content_en or {})
        p.save(update_fields=["content", "content_en"])


def downgrade_sidebar_schema(apps, schema_editor):
    """Reversa best-effort: convierte list de socials a dict, borra tech.
    Se pierden URLs personalizadas (el schema viejo no las tenía)."""
    Portfolio = apps.get_model("portfolio", "Portfolio")
    for p in Portfolio.objects.all():
        for field in ("content", "content_en"):
            data = getattr(p, field) or {}
            sidebar = data.get("sidebar")
            if not isinstance(sidebar, dict):
                continue
            socials = sidebar.get("socials")
            if isinstance(socials, list):
                sidebar["socials"] = {
                    item.get("id", "unknown"): item.get("id", "").title()
                    for item in socials
                    if isinstance(item, dict)
                }
            sidebar.pop("tech", None)
            sidebar.pop("techLabel", None)
        p.save(update_fields=["content", "content_en"])


class Migration(migrations.Migration):
    dependencies = [
        ("portfolio", "0002_seed_walternightsdev"),
    ]

    operations = [
        migrations.RunPython(upgrade_sidebar_schema, reverse_code=downgrade_sidebar_schema),
    ]

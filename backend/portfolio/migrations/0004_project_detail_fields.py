"""Backfill defensivo de los campos de detalle en cada `projects.items`.

Agrega si no existen:
    longDescription: ""
    process: ""
    challenges: []
    features: []

Necesario para que el editor Angular pueda hacer `patchValue` sobre los
FormArrays/FormControls sin choquar contra items viejos que no tienen
las keys. El frontend es defensivo también (los oculta si están vacíos),
pero es más limpio garantizar el shape acá.

Idempotente: si un campo ya existe, no lo toca. Reversible: eliminación
best-effort de los campos agregados.
"""

from __future__ import annotations

from django.db import migrations


_STRING_FIELDS = ("longDescription", "process")
_LIST_FIELDS = ("challenges", "features")


def _upgrade_projects_items(content: dict) -> None:
    """Muta `content['projects']['items']` in-place para asegurar el
    shape completo en cada item."""
    projects = content.get("projects") if isinstance(content, dict) else None
    if not isinstance(projects, dict):
        return
    items = projects.get("items")
    if not isinstance(items, list):
        return
    for item in items:
        if not isinstance(item, dict):
            continue
        for key in _STRING_FIELDS:
            if key not in item or not isinstance(item.get(key), str):
                item[key] = ""
        for key in _LIST_FIELDS:
            if key not in item or not isinstance(item.get(key), list):
                item[key] = []


def _downgrade_projects_items(content: dict) -> None:
    projects = content.get("projects") if isinstance(content, dict) else None
    if not isinstance(projects, dict):
        return
    items = projects.get("items")
    if not isinstance(items, list):
        return
    for item in items:
        if not isinstance(item, dict):
            continue
        for key in _STRING_FIELDS + _LIST_FIELDS:
            item.pop(key, None)


def upgrade(apps, schema_editor):
    Portfolio = apps.get_model("portfolio", "Portfolio")
    for p in Portfolio.objects.all():
        content = p.content or {}
        content_en = p.content_en or {}
        _upgrade_projects_items(content)
        _upgrade_projects_items(content_en)
        p.content = content
        p.content_en = content_en
        p.save(update_fields=["content", "content_en"])


def downgrade(apps, schema_editor):
    Portfolio = apps.get_model("portfolio", "Portfolio")
    for p in Portfolio.objects.all():
        content = p.content or {}
        content_en = p.content_en or {}
        _downgrade_projects_items(content)
        _downgrade_projects_items(content_en)
        p.content = content
        p.content_en = content_en
        p.save(update_fields=["content", "content_en"])


class Migration(migrations.Migration):
    dependencies = [
        ("portfolio", "0003_sidebar_socials_array_and_tech"),
    ]

    operations = [
        migrations.RunPython(upgrade, reverse_code=downgrade),
    ]

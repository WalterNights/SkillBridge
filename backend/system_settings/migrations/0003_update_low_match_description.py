"""Actualiza la descripcion del flag show_low_match_filter.

El threshold del checkbox subio de 30% a 50% (commits 2026-06-27)
para quedar consistente con el chip "Regular 50-69%" que ya estaba
visible en los filtros del feed. La descripcion del flag que ve el
admin en /admin/feature-flags todavia decia "30" — confundia.
"""

from django.db import migrations


_NEW_DESCRIPTION = (
    "Si está activo, en el feed aparece un checkbox 'Ver matches bajos' "
    "junto al filtro 'Regular 50-69%'. Cuando el usuario lo activa, el "
    "feed baja el threshold de match% a 50 — consistente con el chip "
    "'Regular' que ya esta en los filtros. Apagarlo cuando el scraping "
    "este trayendo volumen suficiente arriba del 60%."
)


def update_description(apps, schema_editor):
    SystemSetting = apps.get_model("system_settings", "SystemSetting")
    SystemSetting.objects.filter(key="show_low_match_filter").update(
        description=_NEW_DESCRIPTION
    )


def reverse_noop(apps, schema_editor):
    """No revertimos — la descripcion vieja no aporta nada."""
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("system_settings", "0002_seed_default_flags"),
    ]

    operations = [
        migrations.RunPython(update_description, reverse_code=reverse_noop),
    ]

"""Siembra los flags conocidos al crear la tabla.

Cuando se agrega un flag nuevo al código, agregar acá una entrada con
default sensato. Garantiza que en cualquier ambiente (dev/prod) el flag
exista en DB con su descripción y default — sin esto, el endpoint
público devuelve un dict vacío y el código que lee el flag tendría que
asumir defaults (que se desincronizan con el del modelo).
"""

from django.db import migrations


_DEFAULT_FLAGS = [
    {
        "key": "show_low_match_filter",
        "value_bool": False,
        "description": (
            "Si está activo, en el feed aparece un checkbox 'Ver matches bajos' "
            "junto al filtro 'Regular 50-69%'. Cuando el usuario lo activa, el "
            "feed baja el threshold de match% a 30 — útil cuando el scraping "
            "trae poca cosa por encima del 60% default y queremos darle "
            "visibilidad temporal a matches mediocres. Apagarlo cuando el "
            "scraping esté trayendo volumen suficiente."
        ),
    },
]


def seed_flags(apps, schema_editor):
    SystemSetting = apps.get_model("system_settings", "SystemSetting")
    for flag in _DEFAULT_FLAGS:
        SystemSetting.objects.update_or_create(
            key=flag["key"],
            defaults={
                "value_bool": flag["value_bool"],
                "description": flag["description"],
            },
        )


def unseed_flags(apps, schema_editor):
    SystemSetting = apps.get_model("system_settings", "SystemSetting")
    keys = [f["key"] for f in _DEFAULT_FLAGS]
    SystemSetting.objects.filter(key__in=keys).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("system_settings", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_flags, reverse_code=unseed_flags),
    ]

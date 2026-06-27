"""Actualiza descripcion del flag show_low_match_filter — segunda iteracion.

Cambio del modelo del checkbox 2026-06-27:
- Default del feed bajo de 60% a 50%.
- El checkbox 'Ver matches debiles' ahora extiende el feed al rango
  30-49% (antes era 50%+ que coincidia con el default ya).

La descripcion vieja decia "baja el threshold de match% a 50" — con
el nuevo modelo el threshold baja a 30 y los matches del 30-49%
aparecen ADEMAS de los 50%+ que ya se muestran por default.
"""

from django.db import migrations


_NEW_DESCRIPTION = (
    "Si esta activo, en el feed aparece un checkbox 'Ver matches "
    "debiles' junto al filtro 'Regular 50-69%'. Cuando el usuario lo "
    "activa, el feed extiende su rango al 30-49% (ademas del 50%+ "
    "que muestra por default). Util para perfiles con poca oferta "
    "arriba del 50%. Apagarlo cuando el scraping este trayendo "
    "volumen suficiente arriba del 50%."
)


def update_description(apps, schema_editor):
    SystemSetting = apps.get_model("system_settings", "SystemSetting")
    SystemSetting.objects.filter(key="show_low_match_filter").update(
        description=_NEW_DESCRIPTION
    )


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("system_settings", "0003_update_low_match_description"),
    ]

    operations = [
        migrations.RunPython(update_description, reverse_code=reverse_noop),
    ]

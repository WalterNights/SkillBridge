"""Actualiza descripcion del flag show_low_match_filter — tercera iteracion.

2026-06-27 cambio del checkbox a modo DIAGNOSTICO:
- Antes: extendia el feed al rango 30-49%.
- Ahora: muestra TODO lo que el scraper trajo (incluyendo 0% match).

Motivo: clientes reportaron casos donde el scraper traia ofertas
(Trabajando: 30 ofertas) pero ninguna pasaba el threshold del feed.
Sin poder ver QUE ofertas trajo el scraper, no se podia diagnosticar
si el matcher estaba siendo correcto (ofertas realmente off-topic) o
demasiado estricto (descartando ofertas validas).

Activar el checkbox ahora permite ver todo el universo del scrape y
sacar conclusiones para mejorar el matcher o el query.
"""

from django.db import migrations


_NEW_DESCRIPTION = (
    "Si esta activo, en el feed aparece un checkbox 'Ver matches "
    "debiles' junto al filtro 'Regular 50-69%'. Cuando el usuario lo "
    "activa, el feed entra en MODO DIAGNOSTICO: muestra todas las "
    "ofertas que el scraper trajo, incluyendo las que matchearon 0%. "
    "Util para diagnosticar si el matcher esta filtrando bien o "
    "demasiado estricto. NO recomendado para usuarios finales en "
    "produccion estable — apagar cuando el matcher este afinado."
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
        ("system_settings", "0004_low_match_range_30_49"),
    ]

    operations = [
        migrations.RunPython(update_description, reverse_code=reverse_noop),
    ]

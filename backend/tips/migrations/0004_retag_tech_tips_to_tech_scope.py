"""Re-tagueo los 6 tips manuales del seed cuyo category='tech' a
`profession_scope='tech'` — antes todos quedaban en 'all' por default.

El resto del seed inicial (CV, búsqueda, entrevistas, networking, soft,
product, wellness — 45 tips) sigue en 'all' porque aplica a cualquier
profesión.

Identifico por `category='tech'` AND `source='manual'` para no pisar
tips AI futuros que vayan llegando con su scope propio.
"""

from django.db import migrations


def retag(apps, schema_editor):
    Tip = apps.get_model("tips", "Tip")
    Tip.objects.filter(category="tech", source="manual").update(profession_scope="tech")


def revert(apps, schema_editor):
    Tip = apps.get_model("tips", "Tip")
    Tip.objects.filter(category="tech", source="manual").update(profession_scope="all")


class Migration(migrations.Migration):

    dependencies = [
        ("tips", "0003_tip_profession_scope"),
    ]

    operations = [
        migrations.RunPython(retag, reverse_code=revert),
    ]

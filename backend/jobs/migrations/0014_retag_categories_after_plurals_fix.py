"""Re-clasifica TODAS las ofertas con el classifier corregido.

Bug encontrado 2026-06-27 vía browser test del cliente zootecnista:
el classifier no detectaba plurales — "Empresas agrícolas",
"Zootecnistas", "Veterinarios", "Diseñadores" caían a 'general'
porque el patrón `\bagrícola\b` no matchea "agrícolas" (la `s` rompe
el word boundary).

Resultado en prod: el feed del zootecnista mostraba 0 ofertas
'agro' a pesar de haber 162 ofertas tageadas en DB. Casi todas
eran 'general' porque casi todas usaban plurales en el título.

El classifier post-fix usa `_word_with_plurals` que acepta plurales
opcionales automáticamente. Esta migration corre el classifier nuevo
sobre `title + summary` de cada oferta y actualiza su `category`.

Trabaja en chunks de 500 para no cargar miles de filas en memoria.
"""

from django.db import migrations


def retag_categories(apps, schema_editor):
    """Re-aplica `infer_profession_category(title + summary)` con el
    classifier nuevo (que entiende plurales)."""
    from users.services.profession_classifier import infer_profession_category

    JobOffer = apps.get_model("jobs", "JobOffer")
    total = JobOffer.objects.count()
    if total == 0:
        return

    CHUNK = 500
    qs = JobOffer.objects.only("id", "title", "summary", "category").iterator(
        chunk_size=CHUNK
    )
    to_update = []
    changed = 0
    for offer in qs:
        text = f"{offer.title or ''} {offer.summary or ''}"
        new_category = infer_profession_category(text)
        if new_category != offer.category:
            offer.category = new_category
            to_update.append(offer)
            changed += 1
            if len(to_update) >= CHUNK:
                JobOffer.objects.bulk_update(to_update, ["category"])
                to_update = []
    if to_update:
        JobOffer.objects.bulk_update(to_update, ["category"])


def reverse_noop(apps, schema_editor):
    """No reversible — las categorías viejas eran wrong."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("jobs", "0013_joboffer_category"),
    ]

    operations = [
        migrations.RunPython(retag_categories, reverse_code=reverse_noop),
    ]

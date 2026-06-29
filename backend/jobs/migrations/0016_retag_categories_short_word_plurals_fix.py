"""Re-clasifica ofertas tras fix del bug "Hrs" en classifier.

Bug detectado 2026-06-29 durante test plan local de 10 perfiles:
el classifier tageaba ofertas retail/operario como 'hr' porque el
patron de plurales aceptaba "hrs" (abreviatura de horas) como plural
de "hr" (human resources).

  "FT 42 Hrs, Falabella Rancagua" -> hr  (FALSO POSITIVO)
  "CADETE PART TIME 30 HRS"       -> hr  (FALSO POSITIVO)

Fix: en `_word_with_plurals`, no agregar plural a palabras de ≤2
caracteres. Esto cubre 'hr', 'ui', 'qa' — siglas que casi siempre
matcheean falsos positivos cuando aceptan plural automatico.

Esta migracion re-corre el classifier title-only sobre todas las
ofertas y actualiza categoria.
"""

from django.db import migrations


def retag_categories(apps, schema_editor):
    """Re-aplica `infer_profession_category(title)` con el fix de plurales."""
    from users.services.profession_classifier import infer_profession_category

    JobOffer = apps.get_model("jobs", "JobOffer")
    total = JobOffer.objects.count()
    if total == 0:
        return

    CHUNK = 500
    qs = JobOffer.objects.only("id", "title", "category").iterator(chunk_size=CHUNK)
    to_update = []
    for offer in qs:
        new_category = infer_profession_category(offer.title or "")
        if new_category != offer.category:
            offer.category = new_category
            to_update.append(offer)
            if len(to_update) >= CHUNK:
                JobOffer.objects.bulk_update(to_update, ["category"])
                to_update = []
    if to_update:
        JobOffer.objects.bulk_update(to_update, ["category"])


def reverse_noop(apps, schema_editor):
    """No reversible — las categorias previas tenian falsos positivos."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("jobs", "0015_retag_categories_title_only"),
    ]

    operations = [
        migrations.RunPython(retag_categories, reverse_code=reverse_noop),
    ]

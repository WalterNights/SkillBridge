"""Re-clasifica TODAS las ofertas usando SOLO el title (no title+summary).

Bug encontrado 2026-06-29 via browser test del cliente Fabio (zootecnista):
la oferta "Tecnico auxiliar de cocina" aparecia como agro en su feed
porque su summary mencionaba "zootecnia" y "animales" — el centro era
un veterinario pero el ROL del candidato es trades, no agro.

El problema general: clasificar sobre title+summary captura SECTOR del
empleador (mencionado en summary) en lugar de ROL del candidato
(declarado en title). Para users con vertical claro, este patron
genera falsos positivos que contradicen la promesa "cero ruido".

Trade-off: ofertas con title vago ("Oferta urgente · Empresa X") que
antes se clasificaban via summary ahora quedan en 'general'. Eso
significa que NO aparecen en el feed de users con vertical claro —
preferible a mostrar ruido. Users 'general' siguen viendolas.

Trabaja en chunks de 500 para no cargar miles de filas en memoria.
"""

from django.db import migrations


def retag_categories(apps, schema_editor):
    """Re-aplica `infer_profession_category(title)` — solo title, sin summary."""
    from users.services.profession_classifier import infer_profession_category

    JobOffer = apps.get_model("jobs", "JobOffer")
    total = JobOffer.objects.count()
    if total == 0:
        return

    CHUNK = 500
    qs = JobOffer.objects.only("id", "title", "category").iterator(
        chunk_size=CHUNK
    )
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
    """No reversible — las categorias viejas tenian falsos positivos."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("jobs", "0014_retag_categories_after_plurals_fix"),
    ]

    operations = [
        migrations.RunPython(retag_categories, reverse_code=reverse_noop),
    ]

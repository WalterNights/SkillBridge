"""Agrega campo `category` a JobOffer + pobla las ofertas existentes.

Critico para escalabilidad y privacidad del feed: sin esta categoria,
todas las ofertas que cualquier user scrapea aparecen en el feed de
todos los users con su match% calculado individualmente. Resultado:
un zootecnista veia 'Senior React Native Developer · 0%' en su feed
porque otro user las scrapeo.

Con `category` indexado, el viewset filtra por la categoria del user
ANTES de calcular match%. Cada user ve solo su universo relevante.
"""

from django.db import migrations, models


def populate_categories(apps, schema_editor):
    """Aplica `infer_profession_category(title + summary)` a cada oferta
    existente y guarda el resultado en `category`. Trabaja en bulk por
    eficiencia — usar .update() por chunks de 500 evita instanciar
    miles de objetos en memoria.
    """
    # Import diferido para no atar la migration al import-time de la app
    # (que podría cambiar en futuras refactorizaciones).
    from users.services.profession_classifier import infer_profession_category

    JobOffer = apps.get_model("jobs", "JobOffer")
    total = JobOffer.objects.count()
    if total == 0:
        return

    # Iteración por chunks para no cargar miles de filas en memoria.
    # 500 es un buen balance entre número de queries y RAM.
    CHUNK = 500
    updated = 0
    qs = JobOffer.objects.only("id", "title", "summary").iterator(chunk_size=CHUNK)
    to_update = []
    for offer in qs:
        text = f"{offer.title or ''} {offer.summary or ''}"
        category = infer_profession_category(text)
        offer.category = category
        to_update.append(offer)
        if len(to_update) >= CHUNK:
            JobOffer.objects.bulk_update(to_update, ["category"])
            updated += len(to_update)
            to_update = []
    if to_update:
        JobOffer.objects.bulk_update(to_update, ["category"])
        updated += len(to_update)


def reverse_noop(apps, schema_editor):
    """No reversible — al borrar el campo se pierden las categorias."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0012_purge_old_torre_offers'),
    ]

    operations = [
        migrations.AddField(
            model_name='joboffer',
            name='category',
            field=models.CharField(
                db_index=True,
                default='general',
                help_text='Categoría profesional macro inferida del título+summary',
                max_length=20,
            ),
        ),
        migrations.RunPython(populate_categories, reverse_code=reverse_noop),
    ]

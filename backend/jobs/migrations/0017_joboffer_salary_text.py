"""Agrega campo `salary_text` a JobOffer + pobla las ofertas existentes.

Para nuevas ofertas el scraper llenará el campo al persistir. Para las
que ya están en DB, este data migration corre el mismo extractor sobre
el summary — así el feed muestra salarios inmediatamente después del
deploy sin esperar a que las ofertas se re-scrapeen.

Reversible: al remover el campo se pierde el texto, pero la fuente
(summary) sigue intacta.
"""

from django.db import migrations, models


def populate_salary(apps, schema_editor):
    """Corre `extract_salary(summary)` sobre cada oferta existente."""
    # Import diferido para no atar la migración al import-time del módulo.
    from jobs.utils.offer_attributes import extract_salary

    JobOffer = apps.get_model("jobs", "JobOffer")
    if JobOffer.objects.count() == 0:
        return

    CHUNK = 500
    qs = JobOffer.objects.only("id", "summary", "salary_text").iterator(chunk_size=CHUNK)
    to_update = []
    for offer in qs:
        detected = extract_salary(offer.summary or "")
        if detected and detected != offer.salary_text:
            offer.salary_text = detected
            to_update.append(offer)
        if len(to_update) >= CHUNK:
            JobOffer.objects.bulk_update(to_update, ["salary_text"])
            to_update = []
    if to_update:
        JobOffer.objects.bulk_update(to_update, ["salary_text"])


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("jobs", "0016_retag_categories_short_word_plurals_fix"),
    ]

    operations = [
        migrations.AddField(
            model_name="joboffer",
            name="salary_text",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Salario tal como aparece en la oferta. Vacío si no se detectó",
                max_length=120,
            ),
            preserve_default=False,
        ),
        migrations.RunPython(populate_salary, reverse_code=reverse_noop),
    ]

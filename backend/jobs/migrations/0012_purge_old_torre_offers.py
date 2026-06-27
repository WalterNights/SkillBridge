"""Purga las ofertas de Torre actualmente en DB.

Contexto: la primera version del TorreScraper (commits 663e35c9 y
ec92c645) NO filtraba por status ni por edad — Torre devuelve ofertas
viejas marcadas `status=open` indefinidamente, y nuestro scraper las
guardaba como nuevas. Un cliente reporto haber visto una oferta de
4 años atras con 87% match, y al clickear caia a 'Este trabajo se
encuentra cerrado'.

El commit que mete esta migration agrega filtros al scraper para que
las proximas ofertas solo entren si status='open' y created <= 30d.
Pero las que YA estan en DB son sospechosas — no las podemos verificar
sin re-pegar a Torre por cada una (caro y rate-limit).

Decision: borrar todas las ofertas portal='torre' (un puñado, low
impact). La proxima vez que cualquier user dispare 'Obtener ofertas',
Torre re-trae las frescas filtradas correctamente.

Justificacion de la agresividad: las ofertas borradas pudieron ser
buenas, pero el riesgo de dejar pasar una cerrada/vieja al feed
golpea mucho mas la confianza del usuario que tener que re-scrapear.
"""

from django.db import migrations


def purge_torre_offers(apps, schema_editor):
    JobOffer = apps.get_model("jobs", "JobOffer")
    JobOffer.objects.filter(portal="torre").delete()


def reverse_noop(apps, schema_editor):
    """No reversible — las ofertas borradas eran sospechosas."""
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("jobs", "0011_fix_torre_urls"),
    ]

    operations = [
        migrations.RunPython(purge_torre_offers, reverse_code=reverse_noop),
    ]

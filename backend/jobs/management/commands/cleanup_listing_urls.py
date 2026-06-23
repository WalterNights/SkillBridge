"""Borra ofertas existentes cuyo URL apunta a una página de listado
(no a una oferta individual). One-shot, sirve para limpiar la basura
acumulada antes de que el nuevo filtro de URL del scraper entrara en
producción.

Uso:
    python manage.py cleanup_listing_urls           # dry-run, solo cuenta
    python manage.py cleanup_listing_urls --apply   # borra de verdad

Estrategia: aplica los mismos predicados que el scraper ahora usa al
parse time (`_is_individual_offer_url`, `_is_linkedin_listing`). Si la
URL no pasa esos filtros → es un listing y se borra.
"""

from django.core.management.base import BaseCommand

from jobs.adapters.scrapers.web_search import _is_individual_offer_url, _is_linkedin_listing
from jobs.models import JobOffer


class Command(BaseCommand):
    help = "Borra ofertas con URL de listado en vez de oferta individual."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Borra de verdad. Sin esto es dry-run.",
        )

    def handle(self, *args, **options):
        apply = options["apply"]
        to_delete = []
        kept = 0

        for offer in JobOffer.objects.all().only("id", "url", "title"):
            is_listing = _is_linkedin_listing(offer.url)
            is_individual = _is_individual_offer_url(offer.url)
            if is_listing or not is_individual:
                to_delete.append((offer.id, offer.url, offer.title))
            else:
                kept += 1

        self.stdout.write(self.style.WARNING(f"A borrar: {len(to_delete)}"))
        for offer_id, url, title in to_delete[:20]:
            self.stdout.write(f"  - [{offer_id}] {title[:70]} -> {url[:100]}")
        if len(to_delete) > 20:
            self.stdout.write(f"  … y {len(to_delete) - 20} más")
        self.stdout.write(self.style.SUCCESS(f"Se mantienen: {kept}"))

        if not apply:
            self.stdout.write(
                self.style.NOTICE("\nDry-run. Para borrar, agregá --apply")
            )
            return

        ids = [oid for oid, _, _ in to_delete]
        deleted, _ = JobOffer.objects.filter(id__in=ids).delete()
        self.stdout.write(self.style.SUCCESS(f"Borradas: {deleted} ofertas"))

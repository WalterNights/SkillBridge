"""Reclasifica ofertas 'general' usando también su descripción.

Las ofertas nuevas ya se clasifican así al guardarse (`infer_offer_category`).
Este comando aplica la misma regla a las que ya estaban en la base:

    python manage.py retag_general_offers --dry-run   # solo muestra
    python manage.py retag_general_offers             # aplica
"""

from collections import Counter

from django.core.management.base import BaseCommand

from jobs.models import JobOffer
from users.services.profession_classifier import infer_offer_category

_SAMPLE_SIZE = 15


class Command(BaseCommand):
    help = "Reclasifica ofertas 'general' con título + descripción (regla estricta)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Solo muestra cuántas cambiarían y una muestra, sin guardar.",
        )

    def handle(self, *args, dry_run: bool = False, **options):
        changes: list[tuple[JobOffer, str]] = []
        for offer in JobOffer.objects.filter(category="general").only("id", "title", "summary"):
            category = infer_offer_category(offer.title, offer.summary)
            if category != "general":
                changes.append((offer, category))

        by_category = Counter(category for _, category in changes)
        verb = "Cambiarían" if dry_run else "Reclasificadas"
        self.stdout.write(f"{verb} {len(changes)} ofertas: {dict(by_category)}")
        for offer, category in changes[:_SAMPLE_SIZE]:
            self.stdout.write(f"  - #{offer.id} [{category}] {offer.title[:70]}")

        if dry_run:
            return
        for offer, category in changes:
            JobOffer.objects.filter(pk=offer.pk).update(category=category)

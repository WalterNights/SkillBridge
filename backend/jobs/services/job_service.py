"""
Servicio para gestión de ofertas de trabajo.
"""
from __future__ import annotations

import logging
from typing import Iterable, List, Optional

from django.db.models import Q, QuerySet

from jobs.adapters.scrapers.base import JobOfferData
from jobs.adapters.scrapers.registry import get_scraper
from jobs.models import JobOffer

logger = logging.getLogger(__name__)


class JobService:
    """Servicio para operaciones con ofertas de trabajo"""

    @staticmethod
    def get_all_jobs() -> QuerySet[JobOffer]:
        """Todas las ofertas, ordenadas de más nueva a más vieja."""
        return JobOffer.objects.all().order_by('-created_at')

    @staticmethod
    def get_job_by_id(job_id: int) -> Optional[JobOffer]:
        try:
            return JobOffer.objects.get(pk=job_id)
        except JobOffer.DoesNotExist:
            logger.warning("Job with id %s not found", job_id)
            return None

    @staticmethod
    def scrape_new_jobs(
        query: str,
        location: str,
        portal: str = 'computrabajo',
    ) -> List[JobOffer]:
        """Scrapea `portal` y persiste solo las ofertas nuevas.

        Args:
            query: Término de búsqueda (título profesional).
            location: Ubicación.
            portal: Identificador del scraper (default 'computrabajo').
                Cuando agreguemos más, basta con cambiar este parámetro.

        Returns:
            JobOffers recién creados (no las que ya existían).
        """
        logger.info(
            "Scraping job offers portal=%s query=%r location=%r",
            portal, query, location,
        )
        scraper = get_scraper(portal)
        offers_data = scraper.search(query, location)
        return JobService.save_new_offers(offers_data)

    @staticmethod
    def save_new_offers(offers_data: Iterable[JobOfferData]) -> List[JobOffer]:
        """Persiste DTOs en DB devolviendo solo las que se crearon ahora.

        Usa `get_or_create` por `url` (campo unique). Si una oferta ya
        existe no se actualiza ni se devuelve — el scraping es idempotente.

        Si una oferta puntual falla al guardar (ej: campo demasiado largo,
        URL malformada), se loguea y se sigue con el resto — no aborta
        la batch entera. Aprendido tras un `DataError` por una sola URL
        de Computrabajo > 200 chars que rompía todas las demás.
        """
        created: List[JobOffer] = []
        skipped = 0
        for data in offers_data:
            try:
                obj, was_created = JobOffer.objects.get_or_create(
                    url=data.url,
                    defaults={
                        'title': data.title,
                        'company': data.company,
                        'location': data.location,
                        'summary': data.summary,
                        'keywords': data.keywords,
                    },
                )
                if was_created:
                    created.append(obj)
            except Exception:
                skipped += 1
                logger.exception("Skipping offer (url=%r)", data.url)
        logger.info(
            "save_new_offers: %d nuevas guardadas, %d saltadas",
            len(created), skipped,
        )
        return created

    @staticmethod
    def get_recent_jobs(limit: int = 20) -> QuerySet[JobOffer]:
        return JobOffer.objects.all().order_by('-created_at')[:limit]

    @staticmethod
    def search_jobs(keyword: str) -> QuerySet[JobOffer]:
        """Busca ofertas por palabra clave en título, summary o keywords."""
        return JobOffer.objects.filter(
            Q(title__icontains=keyword) |
            Q(summary__icontains=keyword) |
            Q(keywords__icontains=keyword)
        ).order_by('-created_at')

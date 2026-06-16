"""
Servicio para gestión de ofertas de trabajo.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Iterable, List, Optional

from django.db.models import Q, QuerySet

from jobs.adapters.scrapers.base import JobOfferData
from jobs.adapters.scrapers.registry import available_portals, get_scraper
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
        """Scrapea un único portal y persiste solo las ofertas nuevas."""
        logger.info(
            "Scraping job offers portal=%s query=%r location=%r",
            portal, query, location,
        )
        scraper = get_scraper(portal)
        offers_data = scraper.search(query, location)
        return JobService.save_new_offers(offers_data)

    @staticmethod
    def scrape_all_portals(
        query: str,
        location: str,
        portals: Optional[List[str]] = None,
        max_workers: int = 4,
    ) -> List[JobOffer]:
        """Scrapea todos los portales registrados en paralelo.

        Usa un ThreadPoolExecutor — el trabajo es I/O bound (HTTP), así que
        threads son apropiados; evita la complejidad de Celery sin perder
        paralelismo. Cada portal corre en su propio thread; si uno explota,
        los otros siguen y devolvemos lo que se pudo obtener.

        Args:
            query: Término de búsqueda.
            location: Ubicación.
            portals: Lista de portales a scrapear. Si es None, usa todos
                los registrados.
            max_workers: Threads concurrentes. Default 4 (suficiente para
                hasta ~6-8 portales sin saturar I/O del VPS).

        Returns:
            Lista de JobOffers recién creados (cross-portal, deduplicado por url).
        """
        target_portals = portals or available_portals()
        logger.info(
            "Scraping all portals=%s query=%r location=%r",
            target_portals, query, location,
        )

        all_offers_data: List[JobOfferData] = []
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            future_to_portal = {
                pool.submit(_scrape_one_portal, p, query, location): p
                for p in target_portals
            }
            for future in as_completed(future_to_portal):
                portal_name = future_to_portal[future]
                try:
                    offers = future.result()
                    logger.info("%s: %d ofertas raw", portal_name, len(offers))
                    all_offers_data.extend(offers)
                except Exception:
                    logger.exception("Portal %s failed completely", portal_name)

        return JobService.save_new_offers(all_offers_data)

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
                        'portal': data.portal,
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


def _scrape_one_portal(portal: str, query: str, location: str) -> List[JobOfferData]:
    """Helper top-level para ThreadPoolExecutor — debe ser pickleable."""
    return get_scraper(portal).search(query, location)

"""
Servicio para gestión de ofertas de trabajo.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed

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
        return JobOffer.objects.all().order_by("-created_at")

    @staticmethod
    def get_job_by_id(job_id: int) -> JobOffer | None:
        try:
            return JobOffer.objects.get(pk=job_id)
        except JobOffer.DoesNotExist:
            logger.warning("Job with id %s not found", job_id)
            return None

    @staticmethod
    def scrape_new_jobs(
        query: str,
        location: str,
        portal: str = "computrabajo",
    ) -> list[JobOffer]:
        """Scrapea un único portal y persiste solo las ofertas nuevas."""
        logger.info(
            "Scraping job offers portal=%s query=%r location=%r",
            portal,
            query,
            location,
        )
        scraper = get_scraper(portal)
        offers_data = scraper.search(query, location)
        return JobService.save_new_offers(offers_data)

    @staticmethod
    def scrape_all_portals(
        query: str,
        location: str,
        portals: list[str] | None = None,
        max_workers: int = 4,
    ) -> list[JobOffer]:
        """Wrapper backward-compatible: devuelve sólo las ofertas creadas."""
        created, _stats = JobService.scrape_all_portals_with_stats(
            query, location, portals, max_workers
        )
        return created

    @staticmethod
    def scrape_all_portals_with_stats(
        query: str,
        location: str,
        portals: list[str] | None = None,
        max_workers: int = 4,
    ) -> tuple[list[JobOffer], dict[str, dict]]:
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
            (offers, stats) — `offers` es la lista de JobOffers recién creados
            (cross-portal, deduplicado por url). `stats` mapea portal → dict
            `{"found": N, "error": str|None}` con lo que devolvió crudo el
            scraper. Útil para diagnosticar qué portal falló silenciosamente.
        """
        target_portals = portals or available_portals()
        logger.info(
            "Scraping all portals=%s query=%r location=%r",
            target_portals,
            query,
            location,
        )

        stats: dict[str, dict] = {p: {"found": 0, "error": None} for p in target_portals}
        all_offers_data: list[JobOfferData] = []
        portal_offers: dict[str, list[JobOfferData]] = {p: [] for p in target_portals}

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            future_to_portal = {
                pool.submit(_scrape_one_portal, p, query, location): p for p in target_portals
            }
            for future in as_completed(future_to_portal):
                portal_name = future_to_portal[future]
                try:
                    offers = future.result()
                    logger.info("%s: %d ofertas raw", portal_name, len(offers))
                    stats[portal_name]["found"] = len(offers)
                    portal_offers[portal_name] = offers
                    all_offers_data.extend(offers)
                except Exception as exc:
                    logger.exception("Portal %s failed completely", portal_name)
                    stats[portal_name]["error"] = f"{type(exc).__name__}: {exc}"

        created = JobService.save_new_offers(all_offers_data)
        # Cuántas de las nuevas vienen de cada portal — útil para ver si el
        # portal scrapea pero las URLs ya estaban todas en DB.
        for portal_name in target_portals:
            stats[portal_name]["saved_new"] = sum(
                1 for o in created if o.portal == portal_name
            )
        return created, stats

    @staticmethod
    def scrape_for_profile(
        profile,
        max_workers: int = 4,
    ) -> tuple[list[JobOffer], dict[str, dict]]:
        """Scrapea solo los portales que el `PortalRouterService` sugiere
        para este perfil, cada uno con su query refinado.

        Diferencia con `scrape_all_portals_with_stats`:
          - No scrapea todo el registry — descarta los portales que no
            tienen sentido para el perfil (un diseñador no necesita
            Hireline; un developer no necesita WeWorkRemotely si el
            router decide que el rol es local).
          - El query NO es necesariamente `profile.professional_title` —
            el router refina por portal (ej. "diseñador UX" en LinkedIn
            vs "UI/UX Designer" en WeWorkRemotely vs el título completo
            en Computrabajo).

        Returns el mismo formato `(offers, stats)` que el método legacy
        para que el view layer no se entere de la diferencia.
        """
        # Import local para evitar import circular (portal_router importa
        # de jobs.adapters; jobs.services se importa desde tests).
        from jobs.services.portal_router import PortalRouterService

        plans = PortalRouterService.suggest_portals(profile)
        if not plans:
            logger.warning(
                "PortalRouter devolvió 0 planes para user=%s — scrape no-op",
                profile.user_id,
            )
            return [], {}

        logger.info(
            "scrape_for_profile user=%s plans=%s",
            profile.user_id,
            [(p.portal, p.query) for p in plans],
        )

        stats: dict[str, dict] = {
            p.portal: {"found": 0, "error": None} for p in plans
        }
        portal_offers: dict[str, list[JobOfferData]] = {p.portal: [] for p in plans}
        all_offers_data: list[JobOfferData] = []

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            future_to_plan = {
                pool.submit(_scrape_one_portal, p.portal, p.query, p.location): p
                for p in plans
            }
            for future in as_completed(future_to_plan):
                plan = future_to_plan[future]
                try:
                    offers = future.result()
                    logger.info("%s: %d ofertas raw (query=%r)", plan.portal, len(offers), plan.query)
                    stats[plan.portal]["found"] = len(offers)
                    portal_offers[plan.portal] = offers
                    all_offers_data.extend(offers)
                except Exception as exc:
                    logger.exception("Portal %s falló", plan.portal)
                    stats[plan.portal]["error"] = f"{type(exc).__name__}: {exc}"

        created = JobService.save_new_offers(all_offers_data)
        for plan in plans:
            stats[plan.portal]["saved_new"] = sum(
                1 for o in created if o.portal == plan.portal
            )
        return created, stats

    @staticmethod
    def save_new_offers(offers_data: Iterable[JobOfferData]) -> list[JobOffer]:
        """Persiste DTOs en DB devolviendo solo las que se crearon ahora.

        Usa `get_or_create` por `url` (campo unique). Si una oferta ya
        existe no se actualiza ni se devuelve — el scraping es idempotente.

        Si una oferta puntual falla al guardar (ej: campo demasiado largo,
        URL malformada), se loguea y se sigue con el resto — no aborta
        la batch entera. Aprendido tras un `DataError` por una sola URL
        de Computrabajo > 200 chars que rompía todas las demás.
        """
        from jobs.utils.offer_attributes import extract_country, extract_modality
        from users.services.profession_classifier import infer_profession_category

        created: list[JobOffer] = []
        skipped = 0
        for data in offers_data:
            try:
                # Atributos derivados (country + modality + category)
                # calculados acá —no en cada scraper— para tener un único
                # punto de verdad. Los scrapers solo devuelven los campos
                # crudos.
                country = extract_country(data.location)
                modality = extract_modality(data.location, data.summary)
                # Category: clasificamos sobre title + summary porque hay
                # ofertas donde el rol está claro en summary pero el
                # title es genérico (ej. "Oferta urgente · Empresa X").
                category = infer_profession_category(f"{data.title} {data.summary}")
                obj, was_created = JobOffer.objects.get_or_create(
                    url=data.url,
                    defaults={
                        "title": data.title,
                        "company": data.company,
                        "location": data.location,
                        "summary": data.summary,
                        "keywords": data.keywords,
                        "portal": data.portal,
                        "country": country,
                        "modality": modality,
                        "category": category,
                    },
                )
                if was_created:
                    created.append(obj)
            except Exception:
                skipped += 1
                logger.exception("Skipping offer (url=%r)", data.url)
        logger.info(
            "save_new_offers: %d nuevas guardadas, %d saltadas",
            len(created),
            skipped,
        )
        return created

    @staticmethod
    def get_recent_jobs(limit: int = 20) -> QuerySet[JobOffer]:
        return JobOffer.objects.all().order_by("-created_at")[:limit]

    @staticmethod
    def search_jobs(keyword: str) -> QuerySet[JobOffer]:
        """Busca ofertas por palabra clave en título, summary o keywords."""
        return JobOffer.objects.filter(
            Q(title__icontains=keyword)
            | Q(summary__icontains=keyword)
            | Q(keywords__icontains=keyword)
        ).order_by("-created_at")


def _scrape_one_portal(portal: str, query: str, location: str) -> list[JobOfferData]:
    """Helper top-level para ThreadPoolExecutor — debe ser pickleable."""
    return get_scraper(portal).search(query, location)

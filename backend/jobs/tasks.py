"""
Tareas asíncronas para el módulo de jobs.
"""

import logging

from celery import shared_task

from jobs.models import JobOffer
from jobs.services.job_service import JobService

logger = logging.getLogger(__name__)


@shared_task(name="jobs.scrape_job_offers")
def scrape_job_offers(query: str, location: str, portal: str = "computrabajo"):
    """Tarea asíncrona para scraping de ofertas de trabajo."""
    logger.info(
        "Starting async scraping task: portal=%s query=%r location=%r",
        portal,
        query,
        location,
    )
    try:
        new_offers = JobService.scrape_new_jobs(query, location, portal=portal)
        return {
            "status": "success",
            "offers_created": len(new_offers),
            "query": query,
            "location": location,
            "portal": portal,
        }
    except Exception as e:
        logger.error("Scraping task failed: %s", e, exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "query": query,
            "location": location,
            "portal": portal,
        }


@shared_task(name="jobs.clean_old_offers")
def clean_old_offers(days_old: int = 30):
    """
    Tarea asíncrona para limpiar ofertas antiguas.

    Args:
        days_old: Número de días para considerar una oferta como antigua

    Returns:
        Dict con número de ofertas eliminadas
    """
    from datetime import timedelta

    from django.utils import timezone

    logger.info(f"Starting cleanup task for offers older than {days_old} days")

    try:
        cutoff_date = timezone.now() - timedelta(days=days_old)
        deleted_count, _ = JobOffer.objects.filter(created_at__lt=cutoff_date).delete()

        logger.info(f"Cleanup completed. Deleted {deleted_count} old offers")

        return {"status": "success", "offers_deleted": deleted_count, "days_old": days_old}
    except Exception as e:
        logger.error(f"Cleanup task failed: {e!s}", exc_info=True)
        return {"status": "error", "error": str(e)}

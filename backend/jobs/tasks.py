"""
Tareas asíncronas para el módulo de jobs.
"""

import logging

from celery import shared_task

from jobs.models import JobOffer
from jobs.services.job_service import JobService
from jobs.services.matching_service import JobMatchingService

logger = logging.getLogger(__name__)


# Umbral para crear notif desde el cron diario — mismo que el path
# síncrono en JobOfferViewSet.scrape para que el UX sea consistente.
_NOTIF_MATCH_THRESHOLD = 70


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


@shared_task(name="jobs.daily_scrape_for_active_users")
def daily_scrape_for_active_users():
    """Cron diario: scrape para cada usuario con perfil completo.

    "Activo" = perfil con `professional_title` y `city` poblados (los
    dos campos mínimos que el scrape necesita). Sin esto el scraper no
    sabe qué buscar.

    Por cada usuario:
      1. Scrape de los portales con su query/location.
      2. Filter por match score (mínimo 25%, mismo umbral que la view).
      3. Si ≥1 oferta supera 70%, crear notif kind=match.

    Anti-thundering-herd: serializamos a propósito (no fan-out con
    chord) — los portales rate-limitean por IP, así que paralelizar
    explota su 429. ~30s por user es aceptable: 100 usuarios = 50min,
    bien dentro de la ventana nocturna.

    Falla individual de un user no detiene el resto — atrapamos
    Exception por iteración y logueamos.
    """
    from notifications.models import Notification
    from users.models import UserProfile

    # `exclude` con strings vacíos también para cubrir el caso default
    # del CharField (que es '' en Django, no NULL).
    profiles = UserProfile.objects.exclude(
        professional_title=""
    ).exclude(city="").select_related("user")

    summary = {"users_processed": 0, "users_skipped": 0, "notifications_created": 0}

    for profile in profiles:
        try:
            new_offers, _stats = JobService.scrape_all_portals_with_stats(
                profile.professional_title, profile.city
            )
            filtered = JobMatchingService.filter_jobs_by_skills(
                new_offers, profile, min_match_percentage=25
            )
            high_match = [
                o for o in filtered if getattr(o, "match_percentage", 0) >= _NOTIF_MATCH_THRESHOLD
            ]
            if high_match:
                sample_titles = [(o.title or "")[:60] for o in high_match[:3]]
                if len(high_match) > 3:
                    body = (
                        f"{', '.join(sample_titles)} y {len(high_match) - 3} más — "
                        f"todas con +{_NOTIF_MATCH_THRESHOLD}% match."
                    )
                else:
                    body = (
                        f"{', '.join(sample_titles)} — "
                        f"todas con +{_NOTIF_MATCH_THRESHOLD}% match."
                    )
                Notification.objects.create(
                    user=profile.user,
                    kind="match",
                    title=(
                        f"{len(high_match)} "
                        f"{'nueva oferta calza' if len(high_match) == 1 else 'nuevas ofertas calzan'} "
                        "con tu perfil"
                    ),
                    body=body,
                    metadata={"offer_ids": [o.id for o in high_match], "source": "daily_cron"},
                )
                summary["notifications_created"] += 1
            summary["users_processed"] += 1
        except Exception as exc:
            logger.error(
                "Daily scrape failed for user=%s: %s", profile.user.username, exc, exc_info=True
            )
            summary["users_skipped"] += 1

    logger.info("Daily scrape complete: %s", summary)
    return summary


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

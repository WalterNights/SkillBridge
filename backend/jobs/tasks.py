"""
Tareas asíncronas para el módulo de jobs.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from django.utils import timezone

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
                new_offers, profile, min_match_percentage=40
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


# --- Validador de disponibilidad ---------------------------------------
# Detecta ofertas que el portal de origen bajó y las marca `is_active=False`.
# El feed ya filtra por is_active — así desaparecen del UX sin borrar el
# registro (permite auditoría, reversar si fue false positive, mantener
# ForeignKeys de JobApplication y CoverLetter).

# User-agent real — algunos portales devuelven 403 al ver "python-requests".
_PROBE_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

# Marcadores de "oferta ya no disponible" en el HTML del portal. Solo
# aplicamos cuando el status es 200 — sino el 404/410 ya nos alcanza.
# Case-insensitive; el detector chequea `text.lower()` para evitar
# depender del casing exacto que el portal use.
_PORTAL_DEAD_MARKERS: dict[str, tuple[str, ...]] = {
    "computrabajo": (
        "esta oferta ya no está disponible",
        "esta oferta ya no esta disponible",  # sin tilde, defensive
        "esta oferta ha caducado",
    ),
    "linkedin": (
        "this job is no longer available",
        "no longer accepting applications",
    ),
    "indeed": (
        "this job posting is no longer available",
    ),
    "elempleo": (
        "esta oferta no se encuentra disponible",
    ),
    # Otros portales: agregar marcadores cuando aparezcan casos reales.
    # Sin marcador, solo el 404/410 los descarta — más conservador pero
    # mejor que false positives.
}

# HTTP timeout corto — el probe no debe colgar el worker si un portal está
# lento. La respuesta es binaria (viva / muerta), no necesitamos el body
# completo; con 8s alcanza en la práctica.
_PROBE_TIMEOUT_SECONDS = 8

# Paralelismo — HEAD requests son baratas, pero no queremos martillar al
# mismo portal con 20 conexiones simultáneas. 5 es un buen compromiso:
# 5k ofertas × 500ms / 5 workers ≈ 8 min por run, dentro de la ventana
# nocturna. Un ThreadPoolExecutor global mezcla portales naturalmente
# porque la query no está agrupada por portal.
_PROBE_WORKERS = 5


def _probe_offer(offer_id: int, url: str, portal: str) -> tuple[int, bool, str]:
    """Chequea si `url` sigue viva. Devuelve (offer_id, is_dead, reason).

    Decisiones:
      - 404 / 410 → muerta ("http_404", "http_410").
      - 200 + marcador de "no disponible" en el HTML del portal → muerta
        ("dead_marker:<match>").
      - 200 sin marcador → viva.
      - Otros 2xx/3xx (redirect, 429, 5xx) → viva por precaución. Falsos
        positivos son peores que falsos negativos: si marcamos muerta
        una oferta viva, el user pierde la oportunidad; si dejamos viva
        una muerta, hasta 24h para que el próximo probe la detecte.
      - Timeout / conn error → viva (portal caído no significa oferta muerta).
    """
    try:
        # Sesión efímera por probe: los portales tratan a los HEAD con
        # cookies persistentes como sospechosos. Sin sesión reusable no
        # tenemos rate de conexión compartido — la sobrecarga es minimal
        # comparada con los 500ms del round trip.
        response = requests.get(
            url,
            headers={
                "User-Agent": _PROBE_USER_AGENT,
                "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
                "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
            },
            allow_redirects=True,
            timeout=_PROBE_TIMEOUT_SECONDS,
            # Stream=True + iter_content: leemos hasta 32 KB solo para
            # buscar marcadores. Descargar el HTML completo (que puede
            # ser MB en LinkedIn) sería malgastar ancho de banda.
            stream=True,
        )
    except requests.RequestException as exc:
        return offer_id, False, f"network_error:{type(exc).__name__}"

    status = response.status_code

    if status in (404, 410):
        response.close()
        return offer_id, True, f"http_{status}"

    if status == 200:
        markers = _PORTAL_DEAD_MARKERS.get(portal, ())
        if markers:
            try:
                # Leer solo los primeros 64KB — suficiente para el
                # marcador que suele estar arriba de la página. Portal
                # que pone el "no disponible" al final del HTML nos
                # escapa (edge case aceptable).
                sample = response.raw.read(64 * 1024, decode_content=True)
                if isinstance(sample, bytes):
                    sample = sample.decode("utf-8", errors="ignore")
                sample_lower = sample.lower()
                for marker in markers:
                    if marker in sample_lower:
                        return offer_id, True, f"dead_marker:{marker[:30]}"
            except Exception as exc:  # noqa: BLE001 — best-effort
                logger.debug("probe %s: failed to read body: %s", url, exc)
            finally:
                response.close()
        return offer_id, False, "http_200"

    response.close()
    return offer_id, False, f"http_{status}"


@shared_task(name="jobs.verify_active_offers")
def verify_active_offers():
    """Cron diario: chequea la URL de cada oferta activa y marca
    `is_active=False` cuando el portal de origen la dio de baja.

    Corre 03:00 UTC (antes del scrape de 04:00) para dejar el feed
    limpio cuando llega el batch nuevo. No borra registros — solo
    apaga el flag; la limpieza por edad la hace `clean_old_offers`.

    Return: `{"status", "checked", "marked_dead", "reasons"}` con un
    contador por razón (http_404, dead_marker:*, etc) para diagnóstico.
    """
    qs = (
        JobOffer.objects.filter(is_active=True)
        .only("id", "url", "portal")
        .order_by("last_checked_at")  # nulls first en Postgres — priorizamos las nunca chequeadas
    )
    total = qs.count()
    if total == 0:
        return {"status": "success", "checked": 0, "marked_dead": 0, "reasons": {}}

    logger.info("verify_active_offers: probing %d active offers", total)

    now = timezone.now()
    dead_ids: list[int] = []
    alive_ids: list[int] = []
    reasons: dict[str, int] = {}

    with ThreadPoolExecutor(max_workers=_PROBE_WORKERS) as pool:
        # Materializamos el queryset antes de submit para cerrar la
        # conexión de DB durante los probes (los threads no comparten
        # conexión y el default connection pool de Django es chico).
        futures = {
            pool.submit(_probe_offer, offer.id, offer.url, offer.portal): offer.id
            for offer in qs.iterator(chunk_size=500)
        }
        for future in as_completed(futures):
            try:
                offer_id, is_dead, reason = future.result()
            except Exception as exc:  # noqa: BLE001
                # Un probe individual que revienta no debe tumbar la
                # tarea entera — los otros N-1 igual pueden completarse.
                logger.warning("probe crashed: %s", exc)
                continue
            reasons[reason] = reasons.get(reason, 0) + 1
            if is_dead:
                dead_ids.append(offer_id)
            else:
                alive_ids.append(offer_id)

    # Update masivos — evitamos N updates individuales.
    if dead_ids:
        JobOffer.objects.filter(id__in=dead_ids).update(
            is_active=False, last_checked_at=now
        )
    if alive_ids:
        # Marcar last_checked_at solo en las que EFECTIVAMENTE se probaron
        # y quedaron vivas. Sirve al próximo run para priorizar las más
        # viejas primero via el order_by de arriba.
        JobOffer.objects.filter(id__in=alive_ids).update(last_checked_at=now)

    summary = {
        "status": "success",
        "checked": total,
        "marked_dead": len(dead_ids),
        "reasons": reasons,
    }
    logger.info("verify_active_offers complete: %s", summary)
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

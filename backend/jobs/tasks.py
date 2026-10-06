"""
Tareas asíncronas para el módulo de jobs.
"""

import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

import requests
from celery import shared_task
from django.utils import timezone

from jobs.adapters.scrapers.base import parse_iso_datetime
from jobs.models import JobOffer
from jobs.services.description_enricher import (
    STUB_MAX_LENGTH,
    UNFETCHABLE_PORTALS,
    enrich_offer,
)
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
}

# Marcadores aplicados a TODOS los portales. Son frases completas que solo
# aparecen cuando la propia oferta está cerrada ("esta oferta…", "this
# job…"), no palabras sueltas como "no disponible" que podrían salir en un
# bloque de "ofertas similares" de una oferta viva.
_GENERIC_DEAD_MARKERS: tuple[str, ...] = (
    "esta oferta ya no está disponible",
    "esta oferta ya no esta disponible",
    "esta oferta ha finalizado",
    "esta oferta ha expirado",
    "esta vacante ya no está disponible",
    "esta vacante ya no esta disponible",
    "esta vacante ha sido cerrada",
    "this job is no longer available",
    "this job has expired",
)

# `validThrough` del JSON-LD JobPosting (schema.org). Si la página dice que
# la oferta venció, le creemos al portal.
_VALID_THROUGH_RE = re.compile(r'"validThrough"\s*:\s*"([^"]+)"')

# Cuánto HTML leemos buscando marcadores / JSON-LD. El JSON-LD suele ir en
# el <head>, pero en portales con mucho inline CSS/JS queda más abajo.
_PROBE_SAMPLE_BYTES = 256 * 1024

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


def _redirected_to_listing(original_url: str, final_url: str) -> bool:
    """True si el portal redirigió la oferta a la home o a un listado padre.

    Ej: `/ofertas/123-dev` → `/ofertas` o `/`. Es como varios portales
    "dan de baja" una oferta sin devolver 404. Solo contamos rutas
    estrictamente más cortas y ancestras de la original — un redirect a
    una URL canónica más larga (`/jobs/view/123` → `/jobs/view/dev-123`)
    o a un login wall NO cuenta como muerte.
    """
    original_path = urlparse(original_url).path.rstrip("/")
    final_path = urlparse(final_url).path.rstrip("/")
    if not original_path or final_path == original_path:
        return False
    return final_path == "" or original_path.startswith(final_path + "/")


def _dead_reason_from_body(body: str, portal: str) -> str | None:
    """Busca en el HTML señales de que la oferta está cerrada."""
    body_lower = body.lower()
    for marker in _PORTAL_DEAD_MARKERS.get(portal, ()) + _GENERIC_DEAD_MARKERS:
        if marker in body_lower:
            return f"dead_marker:{marker[:30]}"

    match = _VALID_THROUGH_RE.search(body)
    if match:
        valid_through = parse_iso_datetime(match.group(1))
        if valid_through and valid_through < timezone.now():
            return "expired_valid_through"
    return None


def _probe_offer(
    offer_id: int, url: str, portal: str, timeout: float = _PROBE_TIMEOUT_SECONDS
) -> tuple[int, bool, str]:
    """Chequea si `url` sigue viva. Devuelve (offer_id, is_dead, reason).

    Decisiones:
      - 404 / 410 → muerta ("http_404", "http_410").
      - Redirect a la home o a un listado padre → muerta ("redirect_to_listing").
      - 200 + marcador de "no disponible" (del portal o genérico) → muerta
        ("dead_marker:<match>").
      - 200 + JSON-LD con `validThrough` vencido → muerta ("expired_valid_through").
      - 200 sin señales → viva.
      - Otros status (403 anti-bot, 429, 5xx) → viva por precaución. Falsos
        positivos son peores que falsos negativos: si marcamos muerta
        una oferta viva, el user pierde la oportunidad; si dejamos viva
        una muerta, la limpia la fecha de cierre o la limpieza por edad.
      - Timeout / conn error → viva (portal caído no significa oferta muerta).
    """
    try:
        # Sesión efímera por probe: los portales tratan a los requests con
        # cookies persistentes como sospechosos.
        response = requests.get(
            url,
            headers={
                "User-Agent": _PROBE_USER_AGENT,
                "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
                "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
            },
            allow_redirects=True,
            timeout=timeout,
            # stream=True: leemos solo una muestra del HTML, no la página
            # entera (que puede ser MB en LinkedIn).
            stream=True,
        )
    except requests.RequestException as exc:
        return offer_id, False, f"network_error:{type(exc).__name__}"

    status = response.status_code

    if status in (404, 410):
        response.close()
        return offer_id, True, f"http_{status}"

    if status != 200:
        response.close()
        return offer_id, False, f"http_{status}"

    try:
        final_url = getattr(response, "url", None) or url
        if getattr(response, "history", None) and _redirected_to_listing(url, final_url):
            return offer_id, True, "redirect_to_listing"

        sample = response.raw.read(_PROBE_SAMPLE_BYTES, decode_content=True)
        if isinstance(sample, bytes):
            sample = sample.decode("utf-8", errors="ignore")
        dead_reason = _dead_reason_from_body(sample, portal)
        if dead_reason:
            return offer_id, True, dead_reason
    except Exception as exc:  # noqa: BLE001 — best-effort
        logger.debug("probe %s: failed to read body: %s", url, exc)
    finally:
        response.close()
    return offer_id, False, "http_200"


def _deactivate_expired_offers(now) -> int:
    """Apaga las ofertas cuya fecha de cierre publicada ya pasó."""
    return JobOffer.objects.filter(is_active=True, expires_at__lte=now).update(
        is_active=False, last_checked_at=now
    )


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
    now = timezone.now()
    # Primero las que vencieron por fecha: no hace falta pegarle al portal.
    expired = _deactivate_expired_offers(now)

    qs = (
        JobOffer.objects.filter(is_active=True)
        .only("id", "url", "portal")
        .order_by("last_checked_at")  # nulls first en Postgres — priorizamos las nunca chequeadas
    )
    total = qs.count()
    if total == 0:
        return {
            "status": "success",
            "checked": 0,
            "marked_dead": 0,
            "expired": expired,
            "reasons": {},
        }

    logger.info("verify_active_offers: probing %d active offers", total)

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
        "expired": expired,
        "reasons": reasons,
    }
    logger.info("verify_active_offers complete: %s", summary)
    return summary


def check_offer_availability(
    offer: JobOffer, timeout: float = _PROBE_TIMEOUT_SECONDS
) -> bool:
    """Verifica UNA oferta ya mismo y persiste el resultado.

    Usado al abrir el detalle (si no se verificó hace rato) y cuando un
    usuario la reporta como "no disponible". Devuelve True si sigue viva.
    """
    now = timezone.now()
    if offer.expires_at and offer.expires_at <= now:
        is_dead, reason = True, "expired_at"
    else:
        _, is_dead, reason = _probe_offer(offer.id, offer.url, offer.portal, timeout)

    offer.last_checked_at = now
    update_fields = ["last_checked_at"]
    if is_dead:
        offer.is_active = False
        update_fields.append("is_active")
        logger.info("offer %s marked dead on demand (%s)", offer.id, reason)
    offer.save(update_fields=update_fields)
    return not is_dead


@shared_task(name="jobs.verify_single_offer")
def verify_single_offer(offer_id: int) -> dict:
    """Versión async de `check_offer_availability` (reportes de usuarios)."""
    offer = JobOffer.objects.filter(pk=offer_id, is_active=True).first()
    if offer is None:
        return {"offer_id": offer_id, "alive": False, "skipped": True}
    return {"offer_id": offer_id, "alive": check_offer_availability(offer)}


# Lote nocturno de descripciones: tope por corrida y pausa entre requests
# para no gatillar el rate-limit de LinkedIn (bloquea con 429/999).
_ENRICH_BATCH_LIMIT = 60
_ENRICH_PAUSE_SECONDS = 1.5
_ENRICH_TIMEOUT_SECONDS = 10


@shared_task(name="jobs.enrich_stub_descriptions")
def enrich_stub_descriptions(limit: int = _ENRICH_BATCH_LIMIT) -> dict:
    """Cron diario: completa la descripción de ofertas activas guardadas con
    un relleno, empezando por las más nuevas (las que más se van a ver)."""
    import time

    from django.db.models.functions import Length

    candidates = (
        JobOffer.objects.filter(is_active=True, description_fetched_at__isnull=True)
        .exclude(portal__in=UNFETCHABLE_PORTALS)
        .annotate(summary_len=Length("summary"))
        .filter(summary_len__lt=STUB_MAX_LENGTH)
        .order_by("-created_at")[:limit]
    )
    attempted = improved = 0
    for offer in candidates:
        if attempted:
            time.sleep(_ENRICH_PAUSE_SECONDS)
        attempted += 1
        if enrich_offer(offer, timeout=_ENRICH_TIMEOUT_SECONDS):
            improved += 1

    summary = {"status": "success", "attempted": attempted, "improved": improved}
    logger.info("enrich_stub_descriptions complete: %s", summary)
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
        # Las ofertas con postulaciones NO se borran: `JobApplication.offer`
        # es CASCADE y el usuario perdería su historial de postulaciones.
        # Esas quedan (inactivas si murieron) mientras exista la postulación.
        deleted_count, _ = JobOffer.objects.filter(
            created_at__lt=cutoff_date, applications__isnull=True
        ).delete()

        logger.info(f"Cleanup completed. Deleted {deleted_count} old offers")

        return {"status": "success", "offers_deleted": deleted_count, "days_old": days_old}
    except Exception as e:
        logger.error(f"Cleanup task failed: {e!s}", exc_info=True)
        return {"status": "error", "error": str(e)}

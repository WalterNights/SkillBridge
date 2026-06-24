"""Celery tasks del módulo notifications.

`send_daily_match_alerts` itera todos los usuarios con
`email_alerts_enabled=True` y perfil completo. Para cada uno:
  1. Trae las JobOffer creadas en las últimas 24h.
  2. Aplica el matching contra el perfil del user (min match 85%).
  3. Si hay matches, manda un email con el digest.
  4. Marca `last_alert_sent_at = now` para anti-dedup.

Diseño:
  - Anti-dedup defensivo: si el último envío fue hace menos de 20h,
    skip. Cubre el caso de que la tarea corra dos veces por timing
    drift del beat scheduler.
  - El email se envía sync dentro de la task — si Gmail/SMTP tarda
    o falla, el siguiente user no espera. Aceptable porque la tarea
    corre en celery worker, no en request path.
  - Sin tracking pixel ni links rastreables — privacidad sobre
    analytics. Si en el futuro queremos open rate, agregamos un
    pixel + unsubscribe link nativo (más allá del `email_alerts_enabled`
    flag local).
"""

from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

from jobs.models import JobOffer
from jobs.services.matching_service import JobMatchingService
from users.models import UserProfile

logger = logging.getLogger(__name__)


# Mínimo match % para que una oferta entre en el digest. Más alto que
# el del feed (25%) porque la barra del email es "vale la pena que
# interrumpa tu inbox" — más restrictivo.
_MIN_MATCH_PERCENTAGE = 85

# Ventana de tiempo para considerar ofertas "nuevas" del digest.
_OFFER_FRESHNESS_HOURS = 24

# Anti-dedup: no mandamos dos emails si el último envío fue hace menos
# de esto. Margen sobre las 24h de la cadencia natural para tolerar
# drift del scheduler de Celery beat.
_MIN_HOURS_BETWEEN_SENDS = 20

# Capeamos cantidad de ofertas en el email para no saturar — top 10
# por match score. Si el user quiere más, abre el feed.
_MAX_OFFERS_PER_EMAIL = 10


@shared_task(name="notifications.send_daily_match_alerts")
def send_daily_match_alerts() -> dict:
    """Tarea diaria — itera perfiles activos y manda digest si aplica.

    Returns:
        dict con métricas: users_processed, emails_sent, errors.
        Útil para Flower / monitoring del beat.
    """
    now = timezone.now()
    freshness_cutoff = now - timedelta(hours=_OFFER_FRESHNESS_HOURS)
    dedup_cutoff = now - timedelta(hours=_MIN_HOURS_BETWEEN_SENDS)

    profiles = (
        UserProfile.objects.filter(email_alerts_enabled=True)
        .exclude(professional_title="")
        .exclude(city="")
        .select_related("user")
    )

    metrics = {"users_processed": 0, "emails_sent": 0, "skipped_recent": 0, "errors": 0}

    # Pre-fetch de ofertas frescas — la misma query para todos los users.
    # ~24h de offers no es mucho (~50-200 filas típico) — ok cargar en memoria.
    fresh_offers = list(JobOffer.objects.filter(created_at__gte=freshness_cutoff))
    if not fresh_offers:
        logger.info("send_daily_match_alerts: 0 fresh offers, nothing to send")
        return metrics

    for profile in profiles:
        metrics["users_processed"] += 1
        try:
            # Anti-dedup
            if profile.last_alert_sent_at and profile.last_alert_sent_at >= dedup_cutoff:
                metrics["skipped_recent"] += 1
                continue

            email_to = profile.user.email
            if not email_to:
                # User sin email — raro pero no debería tirar la task.
                continue

            matches = JobMatchingService.filter_jobs_by_skills(
                fresh_offers, profile, min_match_percentage=_MIN_MATCH_PERCENTAGE
            )
            if not matches:
                continue

            # Tomamos top N por match score. `filter_jobs_by_skills` ya
            # ordena DESC por match_percentage.
            top_matches = matches[:_MAX_OFFERS_PER_EMAIL]

            _send_digest_email(profile, top_matches)
            profile.last_alert_sent_at = now
            profile.save(update_fields=["last_alert_sent_at"])
            metrics["emails_sent"] += 1

        except Exception as exc:
            metrics["errors"] += 1
            logger.exception(
                "send_daily_match_alerts: failed for user=%s: %s",
                profile.user.username,
                exc,
            )

    logger.info("send_daily_match_alerts complete: %s", metrics)
    return metrics


def _send_digest_email(profile, matches: list[JobOffer]) -> None:
    """Renderiza y envía el email a un usuario.

    Plantillas:
      - notifications/emails/daily_alerts.html  (rich, branded)
      - notifications/emails/daily_alerts.txt   (fallback texto plano
        para clientes que no rendereen HTML — buena práctica deliverability)
    """
    first_name = profile.first_name or profile.user.username
    context = {
        "first_name": first_name,
        "matches": matches,
        "match_count": len(matches),
        "platform_url": "https://skiltak.com",
        "settings_url": "https://skiltak.com/settings",
    }
    subject = (
        f"{len(matches)} oferta{'s' if len(matches) != 1 else ''} nueva"
        f"{'s' if len(matches) != 1 else ''} con +{_MIN_MATCH_PERCENTAGE}% match para ti"
    )
    text_body = render_to_string("notifications/emails/daily_alerts.txt", context)
    html_body = render_to_string("notifications/emails/daily_alerts.html", context)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[profile.user.email],
    )
    msg.attach_alternative(html_body, "text/html")
    msg.send(fail_silently=False)

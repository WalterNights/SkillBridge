"""Signals del módulo jobs.

Por ahora solo uno: invalidar el cache del `PortalRouterService` cuando
el `UserProfile` cambia (típicamente título, skills o ciudad). Sin esto,
un usuario que actualiza su perfil sigue viendo planes de scrape viejos
durante 24h (el TTL del cache).

Conectado vía `JobsConfig.ready()` para que Django lo registre al
arrancar — sin import a nivel de módulo, sino cuando el AppConfig dice
que las apps están listas.
"""

from __future__ import annotations

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from jobs.services.portal_router import PortalRouterService
from users.models import UserProfile

logger = logging.getLogger(__name__)


@receiver(post_save, sender=UserProfile)
def invalidate_portal_router_cache(sender, instance: UserProfile, **kwargs) -> None:
    """Invalida el plan cacheado cuando el perfil cambia.

    No discriminamos qué campo cambió — la mayoría de updates (title,
    skills, city, country) afectan al plan. Un signal por campo sería
    over-engineering; el costo de invalidar de más es 1 llamada extra
    a Gemini en el próximo scrape.
    """
    try:
        PortalRouterService.invalidate(instance.user_id)
    except Exception:
        # No tirar — los signals deben fail-silent o rompen el save().
        logger.exception("Falló invalidación del cache del PortalRouter")

"""Preferencias persistentes del feed: qué ofertas mostrar primero.

A diferencia de los filtros del dashboard (por sesión, esconden ofertas),
las preferencias se guardan en `UserProfile.feed_preferences` y solo
REORDENAN: nada se oculta. Ej. un usuario en Colombia que no quiere ver
primero las ofertas de España las manda al final, pero siguen ahí.

Forma guardada:
    {"modalities_first": ["remote", "hybrid"],
     "countries_first": ["CO", "MX"],
     "countries_last": ["ES"]}
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import TypedDict

from jobs.models import JobOffer
from jobs.utils.offer_attributes import MODALITY_HYBRID, MODALITY_ONSITE, MODALITY_REMOTE

PREFERABLE_MODALITIES = (MODALITY_REMOTE, MODALITY_HYBRID, MODALITY_ONSITE)
MAX_COUNTRIES = 30


class FeedPreferences(TypedDict):
    modalities_first: list[str]
    countries_first: list[str]
    countries_last: list[str]


def empty_preferences() -> FeedPreferences:
    return {"modalities_first": [], "countries_first": [], "countries_last": []}


def read_preferences(raw: Mapping | None) -> FeedPreferences:
    """Lee lo guardado tolerando datos viejos o parciales."""
    prefs = empty_preferences()
    if not isinstance(raw, Mapping):
        return prefs
    for key in prefs:
        value = raw.get(key)
        if isinstance(value, list):
            prefs[key] = [v for v in value if isinstance(v, str)]
    return prefs


def _preference_rank(offer: JobOffer, prefs: FeedPreferences) -> tuple[int, int]:
    """Clave de orden (menor = antes): primero sale de "al final", después
    si la oferta coincide con alguna preferencia de "primero"."""
    country = (offer.country or "").upper()
    demoted = country in prefs["countries_last"]
    preferred = offer.modality in prefs["modalities_first"] or country in prefs["countries_first"]
    return (1 if demoted else 0, 0 if preferred else 1)


def apply_feed_preferences(offers: Iterable[JobOffer], raw_prefs: Mapping | None) -> list[JobOffer]:
    """Reordena `offers` según las preferencias, sin esconder ninguna.

    El sort es estable: dentro de cada grupo se mantiene el orden que ya
    traía la lista (por % de match o por recencia).
    """
    offers = list(offers)
    prefs = read_preferences(raw_prefs)
    if not any(prefs.values()):
        return offers
    return sorted(offers, key=lambda offer: _preference_rank(offer, prefs))

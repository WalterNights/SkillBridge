"""Completa la descripción de ofertas que se guardaron con un texto de relleno.

Varios scrapers no bajan la página de detalle y guardan un `summary` armado
con el listado ("{cargo} en {empresa} — {ciudad}" en LinkedIn, el tagline en
Torre, el snippet del buscador en websearch). Este servicio baja la
descripción real después, una sola vez por oferta:

  - Al abrir el detalle (on-demand, desde `JobOfferViewSet.retrieve`).
  - En lote, con la tarea nocturna `jobs.enrich_stub_descriptions`.

Fuentes por URL (verificadas en vivo, 2026-10):
  - LinkedIn: endpoint público `jobs-guest/jobs/api/jobPosting/{id}`.
  - Torre: `torre.ai/api/suite/opportunities/{id}` (`details[].content`).
  - Resto: JSON-LD `JobPosting.description` de la página de la oferta.
  - Mercado Libre, InfoJobs, Indeed, Magneto: no se pueden leer sin
    navegador (SPA / anti-bot) → el frontend linkea al portal.
"""

from __future__ import annotations

import json
import logging
import re
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from django.utils import timezone

from jobs.adapters.scrapers.base import safe_get
from jobs.models import JobOffer

logger = logging.getLogger(__name__)

# Debajo de este largo el summary es un relleno, no una descripción. Los
# rellenos miden ~60-250 caracteres; las descripciones reales, miles.
STUB_MAX_LENGTH = 280

# Portales cuya página de detalle no se puede leer con requests.
UNFETCHABLE_PORTALS = frozenset({"meli", "infojobs", "indeed", "magneto"})

# Tope de lo que guardamos — las descripciones largas de verdad rondan 5-6k.
MAX_DESCRIPTION_LENGTH = 8000

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
_HEADERS = {
    "User-Agent": _USER_AGENT,
    "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
}

_LINKEDIN_JOB_ID_RE = re.compile(r"(\d{8,})")
_LINKEDIN_POSTING_URL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
_TORRE_OPPORTUNITY_URL = "https://torre.ai/api/suite/opportunities/{opp_id}"


def is_stub_summary(offer: JobOffer) -> bool:
    return len((offer.summary or "").strip()) < STUB_MAX_LENGTH


def can_enrich(offer: JobOffer) -> bool:
    """True si vale la pena intentar bajar la descripción real."""
    return (
        offer.description_fetched_at is None
        and offer.portal not in UNFETCHABLE_PORTALS
        and is_stub_summary(offer)
    )


def _html_to_text(html: str) -> str:
    return BeautifulSoup(html, "html.parser").get_text("\n", strip=True)


def _fetch_linkedin(url: str, timeout: float) -> str | None:
    match = _LINKEDIN_JOB_ID_RE.search(urlparse(url).path)
    if not match:
        return None
    response = safe_get(
        _LINKEDIN_POSTING_URL.format(job_id=match.group(1)), headers=_HEADERS, timeout=timeout
    )
    if response.status_code != 200:
        return None
    soup = BeautifulSoup(response.text, "html.parser")
    node = soup.select_one(".show-more-less-html__markup") or soup.select_one(".description__text")
    return node.get_text("\n", strip=True) if node else None


def _fetch_torre(url: str, timeout: float) -> str | None:
    # https://torre.ai/jobs/OdvYo3bw-titulo-slug → "OdvYo3bw"
    segments = [s for s in urlparse(url).path.split("/") if s]
    if len(segments) < 2:
        return None
    opp_id = segments[-1].split("-", 1)[0]
    response = safe_get(
        _TORRE_OPPORTUNITY_URL.format(opp_id=opp_id), headers=_HEADERS, timeout=timeout
    )
    if response.status_code != 200:
        return None
    details = response.json().get("details") or []
    # `content` viene con HTML (<p>, <ul>…): lo pasamos a texto plano.
    parts = [_html_to_text(d.get("content") or "") for d in details if isinstance(d, dict)]
    return "\n\n".join(p for p in parts if p) or None


def _find_job_posting(data: object) -> dict | None:
    """Busca el nodo JobPosting en un JSON-LD (dict, lista o @graph)."""
    if isinstance(data, list):
        return next((n for n in map(_find_job_posting, data) if n), None)
    if not isinstance(data, dict):
        return None
    if data.get("@type") == "JobPosting":
        return data
    return _find_job_posting(data.get("@graph", []))


def _fetch_json_ld(url: str, timeout: float) -> str | None:
    response = safe_get(url, headers=_HEADERS, timeout=timeout)
    if response.status_code != 200:
        return None
    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            posting = _find_job_posting(json.loads(tag.string or ""))
        except json.JSONDecodeError:
            continue
        if posting and posting.get("description"):
            return _html_to_text(posting["description"])
    return None


def fetch_full_description(url: str, timeout: float) -> str | None:
    """Baja la descripción real de la oferta en `url`, o None si no se pudo."""
    host = urlparse(url).netloc.lower()
    if host.endswith("linkedin.com"):
        fetcher = _fetch_linkedin
    elif host.endswith("torre.ai"):
        fetcher = _fetch_torre
    else:
        fetcher = _fetch_json_ld
    try:
        text = fetcher(url, timeout)
    except (requests.RequestException, ValueError) as exc:
        logger.info("enrich %s: %s", url, exc)
        return None
    return text[:MAX_DESCRIPTION_LENGTH] if text else None


def enrich_offer(offer: JobOffer, timeout: float) -> bool:
    """Intenta reemplazar el relleno por la descripción real.

    Marca `description_fetched_at` siempre (haya salido o no) para no
    reintentar en cada visita. Devuelve True si se actualizó el summary.
    """
    description = fetch_full_description(offer.url, timeout)
    offer.description_fetched_at = timezone.now()
    update_fields = ["description_fetched_at"]
    improved = bool(description) and len(description) > len(offer.summary or "")
    if improved:
        offer.summary = description
        update_fields.append("summary")
    offer.save(update_fields=update_fields)
    return improved

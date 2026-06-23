"""Parser de cards individuales del HTML guest de LinkedIn.

Compartido entre `web_search.py` (cuando expande un listing extraído de
DDG) y `linkedin.py` (que pega directo al endpoint guest de LinkedIn).
Mismo HTML, mismo parser — duplicarlo en cada scraper era pedido para
desincronizar selectors.

Los selectors están basados en la version actual del guest HTML
(2026). LinkedIn cambia clases sin avisar — el módulo prueba varios
fallbacks. Si todos fallan, devuelve None y el caller skipea.
"""

from __future__ import annotations

import logging

from jobs.adapters.scrapers.base import (
    MAX_OFFER_AGE_DAYS,
    JobOfferData,
    extract_age_days,
    extract_keywords,
)

logger = logging.getLogger(__name__)


def parse_linkedin_card(card, portal: str) -> JobOfferData | None:
    """Extrae un JobOfferData de un single card del HTML guest de LinkedIn.

    Args:
        card: BeautifulSoup tag de la card (li.base-card o similar).
        portal: valor a guardar en `JobOfferData.portal`. El caller
            decide — desde el listing-via-DDG es "websearch", desde el
            scraper directo es "linkedin".

    Returns:
        JobOfferData listo para persistir, o None si la card está rota
        o la oferta tiene más días de los permitidos.
    """
    link_tag = card.select_one("a.base-card__full-link") or card.select_one(
        "a[href*='/jobs/view/']"
    )
    if not link_tag:
        return None
    href = link_tag.get("href", "").split("?")[0]  # strip tracking params
    if "/jobs/view/" not in href:
        return None

    title_tag = card.select_one("h3.base-search-card__title")
    company_tag = card.select_one("h4.base-search-card__subtitle a") or card.select_one(
        "h4.base-search-card__subtitle"
    )
    location_tag = card.select_one("span.job-search-card__location")
    time_tag = card.select_one("time")

    title = title_tag.get_text(strip=True) if title_tag else ""
    if not title:
        return None
    company = company_tag.get_text(strip=True) if company_tag else ""
    location = location_tag.get_text(strip=True) if location_tag else ""

    # Filtro de edad sobre el texto del <time> ("hace 4 semanas").
    posted_text = time_tag.get_text(strip=True) if time_tag else ""
    age_days = extract_age_days(posted_text)
    if age_days is not None and age_days > MAX_OFFER_AGE_DAYS:
        logger.info("Skipping old LinkedIn card (%d days): %s", age_days, title[:60])
        return None

    # Summary armado del título + empresa + location. NO fetcheamos el
    # detalle de la oferta para no multiplicar requests a LinkedIn (que
    # rate-limitea agresivo). El user ve el detalle real cuando clickea
    # Aplicar y cae directo en la página de la oferta.
    summary_parts = [title]
    if company:
        summary_parts.append(f"en {company}")
    if location:
        summary_parts.append(f"— {location}")
    summary = " ".join(summary_parts)

    return JobOfferData(
        title=title[:500],
        company=company[:255],
        location=location[:255],
        summary=summary[:2000],
        keywords=extract_keywords(f"{title} {company}"),
        url=href,
        portal=portal,
    )

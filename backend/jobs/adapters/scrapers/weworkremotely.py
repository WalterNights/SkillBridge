"""Scraper de weworkremotely.com (jobs remotos internacionales).

WeWorkRemotely renderiza el listado server-side: cada `li.feature` /
`li.new-listing-container` dentro de `section.jobs` es una oferta, con
título en `span.title` (o `h3`) y empresa en `span.company` (o `h4`).
El href que va al detalle de la oferta empieza con `/remote-jobs/` —
hay otros `<a>` dentro de la card que apuntan a `/company/...` y los
descartamos.

El search del sitio sí filtra por keyword:
    https://weworkremotely.com/remote-jobs/search?term=<query>

Es la fuente perfecta para perfiles dev — ~90% de las ofertas son tech
y todas son remoto, así que matchean bien sin importar el `location`
del perfil.
"""

from __future__ import annotations

import logging
import re

import requests
from bs4 import BeautifulSoup

from jobs.adapters.scrapers.base import (
    JobOfferData,
    JobScraper,
    ScraperError,
    extract_keywords,
)

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/114.0.0.0 Safari/537.36"
)

BASE_URL = "https://weworkremotely.com"


class WeWorkRemotelyScraper(JobScraper):
    """Scraper para weworkremotely.com."""

    portal_name = "weworkremotely"

    def search(self, query: str, location: str, pages: int = 1) -> list[JobOfferData]:
        if not query:
            raise ScraperError("query es obligatorio")

        # WWR no pagina el endpoint de search (devuelve ~50-80 ofertas en una sola
        # página). El parámetro `pages` queda en la firma para conformar el
        # contrato de JobScraper, pero se ignora.
        search_url = (
            f"{BASE_URL}/remote-jobs/search?term="
            + requests.utils.quote(query, safe="")
        )
        logger.info("Iniciando scrape WWR: query=%r url=%s", query, search_url)

        try:
            response = requests.get(
                search_url,
                headers={"User-Agent": USER_AGENT},
                timeout=self.request_timeout_seconds,
            )
        except requests.RequestException as e:
            logger.error("Error fetching WWR search: %s", e)
            return []

        soup = BeautifulSoup(response.content, "html.parser")
        cards = soup.select(
            "section.jobs li.feature, section.jobs li.new-listing-container"
        )
        logger.info("WWR ofertas en página: %d", len(cards))

        offers: list[JobOfferData] = []
        for card in cards:
            try:
                offer = self._parse_card(card)
                if offer is not None:
                    offers.append(offer)
            except Exception:
                logger.exception("WWR card parsing failed, skipping")
        return offers

    # ---- Helpers internos ----------------------------------------------

    def _parse_card(self, card) -> JobOfferData | None:
        # Buscar el link al job concreto — descartar los de Company Profile
        job_link = None
        for a in card.find_all("a", href=True):
            href = a["href"]
            if href.startswith("/remote-jobs/") and "/click" not in href:
                job_link = a
                break
        if not job_link:
            return None

        href = job_link["href"]
        job_url = BASE_URL + href if href.startswith("/") else href

        title_tag = card.select_one(
            "span.title, .new-listing__header__title, h3"
        )
        company_tag = card.select_one(
            "span.company, .new-listing__company-name, h4"
        )

        title = title_tag.get_text(strip=True) if title_tag else ""
        company = company_tag.get_text(strip=True) if company_tag else ""

        # Si el title quedó vacío caemos al texto completo de la card (raro)
        if not title:
            return None

        location_text = self._extract_location_hint(card)

        # WWR no muestra description en la card — fetch del detail
        summary = self._fetch_detail(job_url)
        if not summary:
            summary = card.get_text(" ", strip=True)[:2000]

        keywords = extract_keywords(summary)

        return JobOfferData(
            title=title[:500],
            company=company[:255],
            location=location_text[:255],
            summary=summary,
            keywords=keywords,
            url=job_url,
            portal=self.portal_name,
        )

    @staticmethod
    def _extract_location_hint(card) -> str:
        """Devuelve un string corto representando dónde se puede trabajar.

        WWR siempre muestra "Anywhere in the World" o una lista de
        regiones — extraemos lo que aparezca después del tipo de contrato
        (Full-Time / Contract / Part-Time).
        """
        text = card.get_text(" ", strip=True)
        match = re.search(
            r"(?:Full-Time|Part-Time|Contract|Freelance)\s+([^•|]+?)(?:\s{2,}|$)",
            text,
        )
        if match:
            return match.group(1).strip()[:255]
        return "Remote"

    def _fetch_detail(self, offer_url: str) -> str:
        """Baja el detail page y devuelve el cuerpo de la descripción."""
        try:
            response = requests.get(
                offer_url,
                headers={"User-Agent": USER_AGENT},
                timeout=self.request_timeout_seconds,
            )
        except requests.RequestException as e:
            logger.warning("WWR detail %s falló: %s", offer_url, e)
            return ""

        soup = BeautifulSoup(response.content, "html.parser")
        # El cuerpo de la descripción suele estar en .listing-container .lis-container__job__content__description
        # o en .listing-container, o como fallback en <article>.
        block = (
            soup.select_one(".lis-container__job__content__description")
            or soup.select_one(".listing-container")
            or soup.select_one("article")
        )
        if not block:
            return ""

        text = block.get_text(" ", strip=True)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:5000]

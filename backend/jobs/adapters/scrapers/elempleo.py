"""Scraper de elempleo.com (Colombia).

Elempleo renderiza el listado server-side con clases `result-item` para
cada card. El título y URL salen de `h2.item-title` (con su anchor
padre/cercano); company de `h3.company-name-text`; el resto del texto
estructurado (ubicación, modalidad, contrato) está en spans con icon
prefix dentro de la card.

Para el detail page, los selectores cambiaron varias veces — para no
pelearnos con eso, este scraper extrae todo lo posible desde el listado
y deja el detalle para una futura iteración si hace falta más texto.
"""

from __future__ import annotations

import logging
import re

import requests
from bs4 import BeautifulSoup
from unidecode import unidecode

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

BASE_URL = "https://www.elempleo.com"

# Prefijos de icon-text que vienen pegados al texto real (p.ej.
# "industryEmpresa confidencial" o "countryUbicaciónBogotá"). Los limpiamos.
_ICON_PREFIXES = ("industry", "country", "COP", "currency", "briefcase")


class ElempleoScraper(JobScraper):
    """Scraper para www.elempleo.com (Colombia)."""

    portal_name = "elempleo"

    def search(self, query: str, location: str, pages: int = 2) -> list[JobOfferData]:
        if not query:
            raise ScraperError("query es obligatorio")

        clean_query = unidecode(query).replace(" ", "%20")
        # location no va en URL — elempleo filtra por keyword principal; lo
        # podemos refinar después con un filtro UI sobre los resultados.
        base = f"{BASE_URL}/co/ofertas-empleo/?Search={clean_query}&pubdate=hoy"

        logger.info(
            "Iniciando scrape Elempleo: query=%r location=%r pages=%d",
            query,
            location,
            pages,
        )

        offers: list[JobOfferData] = []
        for page in range(1, pages + 1):
            url = f"{base}&PageIndex={page}"
            offers.extend(self._parse_listing_page(url))
        return offers

    # ---- Helpers internos ----------------------------------------------

    def _parse_listing_page(self, url: str) -> list[JobOfferData]:
        try:
            response = requests.get(
                url,
                headers={"User-Agent": USER_AGENT},
                timeout=self.request_timeout_seconds,
            )
        except requests.RequestException as e:
            logger.error("Error fetching Elempleo listing %s: %s", url, e)
            return []

        soup = BeautifulSoup(response.content, "html.parser")
        cards = soup.select(".result-item")
        logger.info("Elempleo ofertas en %s: %d", url, len(cards))

        offers: list[JobOfferData] = []
        for card in cards:
            try:
                offer = self._parse_card(card)
                if offer is not None:
                    offers.append(offer)
            except Exception:
                logger.exception("Elempleo card parsing failed, skipping")
        return offers

    def _parse_card(self, card) -> JobOfferData | None:
        title_tag = card.select_one("h2.item-title")
        if not title_tag:
            return None

        title = self._clean_text(title_tag.get_text(strip=True))

        # El href está en el <a> ancestro o nearby
        link = title_tag.find_parent("a") or card.find("a", href=True)
        if not link or not link.get("href"):
            return None
        href = link["href"]
        job_url = BASE_URL + href if href.startswith("/") else href

        company_tag = card.select_one("h3.company-name-text")
        company = self._clean_text(company_tag.get_text(strip=True)) if company_tag else ""

        location = self._extract_location(card)

        # Resumen tomado de la card (Elempleo no muestra description en el listado)
        summary = self._build_summary_from_card(card)

        keywords = extract_keywords(summary)

        return JobOfferData(
            title=title,
            company=company,
            location=location,
            summary=summary,
            keywords=keywords,
            url=job_url,
            portal=self.portal_name,
        )

    @staticmethod
    def _clean_text(text: str) -> str:
        """Quita prefijos de icon-text concatenados (industry, country, etc.)."""
        for prefix in _ICON_PREFIXES:
            if text.startswith(prefix):
                text = text[len(prefix) :].strip()
        return text.strip()

    def _extract_location(self, card) -> str:
        """Heurística: buscar 'Ubicación' en el texto de la card."""
        text = card.get_text(" ", strip=True)
        match = re.search(
            r"(?:country)?Ubicaci[oó]n\s*([A-ZÁ-Úa-zá-ú., ]+?)(?:Modalidad|$|Hoy)",
            text,
        )
        if match:
            return self._clean_text(match.group(1).strip())[:255]
        return ""

    @staticmethod
    def _build_summary_from_card(card) -> str:
        """Texto bruto de la card limpiado, sin prefijos de icon-text."""
        raw = card.get_text(" ", strip=True)
        cleaned = re.sub(r"(Enlace copiado|Copiar enlace|industry|country|COP)", "", raw)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned[:2000]

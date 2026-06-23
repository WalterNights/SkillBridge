"""Scraper directo a LinkedIn vía el endpoint guest público.

Diferente del path antiguo (DDG → URL LinkedIn → fan-out de listing):
acá hablamos directamente con la API guest de LinkedIn, que devuelve
HTML de cards sin requerir login. Pega de cobertura: pasamos de las
~10-25 ofertas que DDG indexa a las 100+ que LinkedIn realmente tiene.

Endpoint: `seeMoreJobPostings/search`. Recibe `keywords`, `location`,
`start` (offset, escala de 25). LinkedIn lo usa internamente cuando un
guest hace scroll infinito — es estable porque cambiar romperia su
propio funnel.

Tradeoffs:
  - LinkedIn rate-limitea agresivo (status 429 o 999). Mitigamos con
    delay de 1.5s entre páginas + máximo 4 páginas por scrape (~100
    jobs es suficiente para un user en un día).
  - El HTML puede mutar — defensive selectors via `parse_linkedin_card`.
    Si todos fallan, devuelve [] y los logs lo dicen.
  - No fetcheamos el detalle de cada oferta (sería 100× requests más).
    El user ve el cuerpo completo cuando clickea "Aplicar en LinkedIn".
"""

from __future__ import annotations

import logging
import time

import requests
from bs4 import BeautifulSoup

from jobs.adapters.scrapers._linkedin_card import parse_linkedin_card
from jobs.adapters.scrapers.base import (
    JobOfferData,
    JobScraper,
    ScraperError,
)

logger = logging.getLogger(__name__)


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)


class LinkedInGuestScraper(JobScraper):
    """Scraper directo de LinkedIn que pagina el endpoint guest."""

    portal_name = "linkedin"

    _BASE_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    _PAGE_SIZE = 25
    _DEFAULT_MAX_PAGES = 4
    _PAGE_DELAY_SECONDS = 1.5

    def search(self, query: str, location: str, pages: int = 1) -> list[JobOfferData]:
        """Pagina hasta `_DEFAULT_MAX_PAGES` páginas del endpoint guest.

        El parámetro `pages` del interface se ignora a propósito —
        siempre paginamos hasta el máximo o hasta una página vacía /
        rate-limit / sin ofertas nuevas. Cada página son 25 jobs.
        """
        if not query:
            raise ScraperError("query es obligatorio")

        logger.info(
            "LinkedIn guest scrape: query=%r location=%r", query, location
        )

        offers: list[JobOfferData] = []
        seen_urls: set[str] = set()

        for page in range(self._DEFAULT_MAX_PAGES):
            start = page * self._PAGE_SIZE
            html = self._fetch_page(query, location, start)
            if html is None:
                # Falla de red o rate-limit — paramos acá, no
                # insistimos. Los siguientes scrapes pueden recuperar.
                break

            page_offers = self._parse_cards(html)
            if not page_offers:
                # Página vacía → ya no hay más resultados.
                logger.info("LinkedIn page %d: 0 offers, stopping", page)
                break

            new_count = 0
            for offer in page_offers:
                if offer.url in seen_urls:
                    continue
                seen_urls.add(offer.url)
                offers.append(offer)
                new_count += 1

            logger.info(
                "LinkedIn page %d: %d cards, %d new", page, len(page_offers), new_count
            )

            # Si no hubo NADA nuevo en esta página, no insistimos —
            # LinkedIn está sirviendo cards repetidas (suele pasar
            # cerca del final del set de resultados).
            if new_count == 0:
                break

            # Delay entre páginas — respeta rate-limit. Lo skipeamos
            # en la última iteración para no perder tiempo.
            if page < self._DEFAULT_MAX_PAGES - 1:
                time.sleep(self._PAGE_DELAY_SECONDS)

        logger.info("LinkedIn guest scrape complete: %d offers", len(offers))
        return offers

    # ---- HTTP ----------------------------------------------------------

    def _fetch_page(self, query: str, location: str, start: int) -> str | None:
        """Pega al endpoint guest y devuelve el HTML, o None ante fallo."""
        try:
            response = requests.get(
                self._BASE_URL,
                params={
                    "keywords": query,
                    "location": location,
                    "start": str(start),
                },
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
                    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
                },
                timeout=self.request_timeout_seconds,
            )
        except requests.RequestException as e:
            logger.warning("LinkedIn fetch failed (start=%d): %s", start, e)
            return None

        # 429 = rate limit explícito, 999 = anti-bot de LinkedIn.
        # En ambos casos paramos y dejamos para el próximo scrape.
        if response.status_code in (429, 999):
            logger.warning(
                "LinkedIn rate-limited (start=%d, status=%d)", start, response.status_code
            )
            return None
        if response.status_code >= 400:
            logger.warning(
                "LinkedIn returned %d (start=%d)", response.status_code, start
            )
            return None

        return response.text

    # ---- Parsing -------------------------------------------------------

    def _parse_cards(self, html: str) -> list[JobOfferData]:
        soup = BeautifulSoup(html, "html.parser")
        # Selectors con fallbacks — LinkedIn cambia clases sin avisar.
        cards = (
            soup.select("li div.base-card")
            or soup.select("div.base-card")
            or soup.select("li.result-card")
        )
        offers: list[JobOfferData] = []
        for card in cards:
            try:
                offer = parse_linkedin_card(card, portal=self.portal_name)
                if offer is not None:
                    offers.append(offer)
            except Exception:
                logger.exception("LinkedIn card parse failed, skipping")
        return offers

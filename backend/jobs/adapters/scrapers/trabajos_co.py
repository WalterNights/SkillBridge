"""Scraper de colombia.trabajos.com.

Portal estático server-rendered — sin SPA, sin Cloudflare. Misma forma
que Computrabajo: requests + BeautifulSoup.

Parámetros de la URL (descubiertos via DevTools / pagination links):
  - CADENA: query de búsqueda free-text (espacios → +)
  - IDPAIS=40: Colombia
  - ORD=F: orden por fecha descendente
  - DESDE=N: offset para paginación (40 por página → DESDE=41 = pág 2)

Estructura del card:
  <div class="listado2014 card oferta">
    <a class="oferta j4m_link" href="..."> Título </a>
    <a class="empresa"><span>Empresa</span></a>
    <span class="loc"> Ubicación </span>
    <span class="fecha"> DD/MM/YYYY </span>
    <div class="doextended"> Snippet de la descripción </div>
    <p class="oi"><span>Contrato</span><span>Jornada</span></p>
  </div>

Para descripción completa hace falta GET adicional al detail URL, pero
para el match downstream el snippet del listado + extract_keywords sobre
título + snippet alcanza para que el algoritmo de matching funcione sin
disparar 40 requests extra por scrape.
"""

from __future__ import annotations

import logging
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup

from jobs.adapters.scrapers.base import (
    MAX_OFFER_AGE_DAYS,
    JobOfferData,
    JobScraper,
    ScraperError,
    extract_age_days,
    extract_keywords,
)

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/114.0.0.0 Safari/537.36"
)

BASE_URL = "https://colombia.trabajos.com"
SEARCH_PATH = "/bolsa-empleo/"

# Page size del portal — no es configurable.
PAGE_SIZE = 40


class TrabajosColombiaScraper(JobScraper):
    """Scraper para colombia.trabajos.com."""

    portal_name = "trabajos_co"
    description = (
        "Bolsa generalista de Colombia (colombia.trabajos.com). Fuerte en "
        "ventas, call center, atención al cliente, mantenimiento, "
        "operativos y servicios generales. Tech presente pero menor."
    )
    categories = ("all",)

    def search(self, query: str, location: str, pages: int = 2) -> list[JobOfferData]:
        if not query:
            raise ScraperError("query es obligatorio")

        # location no se usa como filtro en el portal — los listings vienen
        # con la ubicación dentro de cada card y el match downstream
        # filtra por ciudad. Loggeamos para diagnóstico.
        logger.info(
            "Iniciando scrape trabajos.com Colombia: query=%r location=%r pages=%d",
            query,
            location,
            pages,
        )

        offers: list[JobOfferData] = []
        for page_index in range(pages):
            # DESDE=1, 41, 81, … (1-indexed inclusive)
            desde = page_index * PAGE_SIZE + 1
            url = f"{BASE_URL}{SEARCH_PATH}?" + urlencode({
                "CADENA": query,
                "IDPAIS": "40",  # Colombia
                "ORD": "F",       # por fecha desc
                "DESDE": desde,
            })
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
            logger.error("Error fetching listing %s: %s", url, e)
            return []

        soup = BeautifulSoup(response.content, "html.parser")
        cards = soup.select("div.listado2014.card.oferta")
        logger.info("Ofertas en %s: %d", url, len(cards))

        offers: list[JobOfferData] = []
        for card in cards:
            try:
                offer = self._parse_listing_card(card)
                if offer is not None:
                    offers.append(offer)
            except Exception:
                logger.exception("Card parsing failed, skipping")
        return offers

    def _parse_listing_card(self, card) -> JobOfferData | None:
        title_link = card.select_one("a.oferta.j4m_link")
        if not title_link or not title_link.get("href"):
            return None

        title = title_link.get_text(strip=True)
        job_url = title_link["href"]
        # Los hrefs ya son absolutos en este portal — defensa contra cambios.
        if not job_url.startswith("http"):
            job_url = BASE_URL + (job_url if job_url.startswith("/") else "/" + job_url)

        company_tag = card.select_one("a.empresa span")
        company = company_tag.get_text(strip=True) if company_tag else ""

        # span.loc puede tener anidamientos varios — agarramos el texto
        # plano y limpiamos espacios duplicados.
        location_tag = card.select_one("span.loc")
        location_text = (
            " ".join(location_tag.get_text(" ", strip=True).split())
            if location_tag
            else ""
        )

        summary_tag = card.select_one("div.doextended")
        summary = summary_tag.get_text(" ", strip=True) if summary_tag else ""

        # Filtro de edad — la fecha viene como DD/MM/YYYY en span.fecha,
        # pero también puede haber "Hoy" o "Hace N días" en el texto del
        # card (en algunos layouts premium). Probamos primero con
        # extract_age_days sobre todo el card; si nada matchea, dejamos
        # pasar (caller asume reciente).
        age_days = extract_age_days(card.get_text(" ", strip=True))
        if age_days is not None and age_days > MAX_OFFER_AGE_DAYS:
            logger.info(
                "Skipping old trabajos_co offer (%d days): %s",
                age_days,
                title[:60],
            )
            return None

        # Para el contrato/jornada (p.oi span), agregamos al summary para
        # que el matcher tenga más contexto.
        oi_tag = card.select_one("p.oi")
        if oi_tag:
            extras = " · ".join(s.get_text(strip=True) for s in oi_tag.select("span") if s.get_text(strip=True))
            if extras:
                summary = (summary + "\n\n" + extras).strip()

        keywords = extract_keywords(f"{title} {summary}")

        return JobOfferData(
            title=title,
            company=company,
            location=location_text,
            summary=summary,
            keywords=keywords,
            url=job_url,
            portal=self.portal_name,
        )

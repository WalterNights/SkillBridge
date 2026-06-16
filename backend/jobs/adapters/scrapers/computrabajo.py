"""Scraper de computrabajo.com (Colombia).

Reemplazo del módulo `jobs/utils/scraper.py`. Cambios respecto al original:
  - Estructura de clase para encajar en el patrón Strategy
  - Sin `print`, todo va por `logger`
  - Sin `open("output.html", ...)` — el dump de debug fue eliminado
  - Timeout configurable en `requests.get`
  - Devuelve `JobOfferData` (DTO), no persiste en DB
  - Errores tipados con `ScraperError`
"""
from __future__ import annotations

import logging
import re
from typing import List, Tuple

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

BASE_URL = "https://co.computrabajo.com"

_DETAIL_SECTION_SPLITS = (
    'requisitos', 'habilidades', 'condiciones', 'te ofrecemos',
    'perfil', 'ofrecemos', 'conocimientos', 'skills',
    'qué harás', 'responsabilidades',
)


class ComputrabajoScraper(JobScraper):
    """Scraper para co.computrabajo.com."""

    portal_name = 'computrabajo'

    def search(self, query: str, location: str, pages: int = 2) -> List[JobOfferData]:
        if not query or not location:
            raise ScraperError("query y location son obligatorios")

        slug_query = query.replace(" ", "-").lower()
        slug_location = unidecode(location.lower())
        base = f"{BASE_URL}/trabajo-de-{slug_query}-en-{slug_location}?p="

        logger.info(
            "Iniciando scrape Computrabajo: query=%r location=%r pages=%d",
            query, location, pages,
        )

        offers: List[JobOfferData] = []
        for page in range(1, pages + 1):
            url = f"{base}{page}"
            offers.extend(self._parse_listing_page(url))
        return offers

    # ---- Helpers internos ----------------------------------------------

    def _parse_listing_page(self, url: str) -> List[JobOfferData]:
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
        articles = soup.find_all("article", class_="box_offer")
        logger.info("Ofertas en %s: %d", url, len(articles))

        offers: List[JobOfferData] = []
        for article in articles:
            try:
                offer = self._parse_listing_card(article)
                if offer is not None:
                    offers.append(offer)
            except Exception:
                # Una tarjeta rota no debe abortar la página entera.
                logger.exception("Card parsing failed, skipping")
        return offers

    def _parse_listing_card(self, article) -> JobOfferData | None:
        title_tag = article.select_one("a.js-o-link")
        company_tag = article.select_one("a.fc_base.t_ellipsis")
        paragraphs = article.find_all("p")
        location_tag = paragraphs[1] if len(paragraphs) > 1 else None

        if not title_tag:
            return None

        job_url = BASE_URL + title_tag["href"]
        title = title_tag.get_text(strip=True)
        company = company_tag.get_text(strip=True) if company_tag else ''
        location_text = location_tag.get_text(strip=True) if location_tag else ''

        summary, keywords = self._fetch_detail(job_url)

        return JobOfferData(
            title=title,
            company=company,
            location=location_text,
            summary=summary,
            keywords=keywords,
            url=job_url,
        )

    def _fetch_detail(self, offer_url: str) -> Tuple[str, str]:
        """Devuelve (summary, keywords) para una oferta individual."""
        try:
            response = requests.get(
                offer_url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=self.request_timeout_seconds,
            )
        except requests.RequestException as e:
            logger.warning("Error fetching detail %s: %s", offer_url, e)
            return '', ''

        soup = BeautifulSoup(response.content, "html.parser")
        description_title = soup.find(
            "h3",
            string=lambda text: text and "descripción" in text.lower(),
        )
        if not description_title:
            return '', ''

        chunks: List[str] = []
        for sibling in description_title.find_next_siblings():
            if sibling.name == "h3":
                break
            if sibling.name in ("p", "li"):
                for child in sibling:
                    if getattr(child, 'name', None) == "br":
                        chunks.append("\n")
                        continue
                    text = child.get_text() if hasattr(child, 'get_text') else str(child)
                    if "Requerimientos" in text:
                        chunks.append("\n\nRequerimientos:\n\n")
                    elif "Aptitudes asociadas a esta oferta" in text or "Palabras clave:" in text:
                        break
                    else:
                        chunks.append(text)
            elif sibling.name == "ul":
                for li in sibling.find_all("li"):
                    chunks.append(f"- {li.get_text(strip=True)}\n\n")

        full_text = "".join(chunks)
        keywords = extract_keywords(full_text)
        return full_text, keywords

"""Scraper de infojobs.net (España).

InfoJobs es el bolsa generalista líder en España. Cubre todos los
sectores — tech, salud, educación, oficios, retail. Útil para users
LATAM que buscan trabajo remoto internacional o mudanza a España.

Notas de implementación:
  - HTML plano (sin Cloudflare challenge), scraping directo con
    requests + BeautifulSoup.
  - URLs de detalle son protocol-less (`//www.infojobs.net/...`) — se
    reponen con `https:` al persistir.
  - Cards en `<li class="ij-OfferList-offerCardItem">`.
  - Location es una ciudad de España (Madrid, Barcelona, etc.) — sin
    concepto de país porque InfoJobs solo cubre España. Se anota
    "España" como país explícito al construir el `location` del DTO
    para que `extract_country` lo detecte.
"""

from __future__ import annotations

import logging

import requests
from bs4 import BeautifulSoup, Tag

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
    "Chrome/126.0.0.0 Safari/537.36"
)

_BASE_URL = "https://www.infojobs.net"
# InfoJobs pagina con `?page=N` — página 1 es la default sin param.
_SEARCH_PATH = "/ofertas-trabajo"


class InfoJobsScraper(JobScraper):
    """Scraper de infojobs.net (España)."""

    portal_name = "infojobs"
    description = (
        "Bolsa generalista líder en España. Cobertura amplia en tech, "
        "salud, educación, oficios, retail y perfiles ejecutivos. Útil "
        "para users LATAM interesados en trabajo remoto internacional o "
        "mudanza a España. No cubre otros países."
    )
    # Generalista — cualquier categoría puede tener ofertas en InfoJobs.
    categories = ("all",)

    def search(self, query: str, location: str, pages: int = 2) -> list[JobOfferData]:
        if not query:
            raise ScraperError("query es obligatorio")

        # `location` del user LATAM (Bogotá, Buenos Aires) no aplica a
        # InfoJobs — el portal es solo España. Ignoramos y traemos
        # ofertas de toda España; el matcher decide si le calzan al user
        # por título+skills.
        logger.info(
            "InfoJobs scrape: query=%r (location %r ignorada, portal solo España)",
            query,
            location,
        )

        offers: list[JobOfferData] = []
        seen_urls: set[str] = set()

        for page in range(1, pages + 1):
            html = self._fetch_page(query, page)
            if html is None:
                break

            page_offers = self._parse_cards(html)
            if not page_offers:
                # Página vacía → fin de resultados.
                logger.info("InfoJobs page %d: 0 offers, stopping", page)
                break

            new_count = 0
            for offer in page_offers:
                if offer.url in seen_urls:
                    continue
                seen_urls.add(offer.url)
                offers.append(offer)
                new_count += 1

            logger.info(
                "InfoJobs page %d: %d cards, %d new", page, len(page_offers), new_count
            )
            if new_count == 0:
                break

        logger.info("InfoJobs scrape complete: %d offers", len(offers))
        return offers

    # ---- HTTP ---------------------------------------------------------

    def _fetch_page(self, query: str, page: int) -> str | None:
        """Página de búsqueda por keyword. Devuelve HTML crudo o None."""
        params: dict[str, str] = {"keyword": query}
        if page > 1:
            params["page"] = str(page)
        url = _BASE_URL + _SEARCH_PATH
        try:
            response = requests.get(
                url,
                params=params,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
                    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
                },
                timeout=self.request_timeout_seconds,
            )
        except requests.RequestException as exc:
            logger.warning("InfoJobs fetch failed (page=%d): %s", page, exc)
            return None
        if response.status_code != 200:
            logger.warning(
                "InfoJobs returned %d (page=%d)", response.status_code, page
            )
            return None
        return response.text

    # ---- Parsing ------------------------------------------------------

    def _parse_cards(self, html: str) -> list[JobOfferData]:
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.find_all("li", class_="ij-OfferList-offerCardItem")
        offers: list[JobOfferData] = []
        for card in cards:
            try:
                offer = self._parse_card(card)
                if offer is not None:
                    offers.append(offer)
            except Exception:
                logger.exception("InfoJobs card parse failed, skipping")
        return offers

    def _parse_card(self, card: Tag) -> JobOfferData | None:
        """Extrae los campos de una card de oferta. Selectores estables
        verificados el 2026-07-13:

          - `.ij-OfferCardContent-description-title-link` → título
          - `.ij-OfferCardContent-description-link[href]` → URL detalle
            (protocol-less, se prepend `https:`)
          - `.ij-OfferCardContent-description-subtitle-link` → empresa
          - `.ij-OfferCardContent-description-list-item` → meta (varios:
            ciudad, modalidad, fecha, contrato, jornada, salario)
        """
        title_el = card.find(class_="ij-OfferCardContent-description-title-link")
        title = title_el.get_text(strip=True) if title_el else ""
        if not title:
            return None

        # Link a la oferta — el `.description-link` es el que apunta al
        # detalle. Es protocol-less (`//www.infojobs.net/...`), prepend
        # https para tener una URL válida.
        link_el = card.find("a", class_="ij-OfferCardContent-description-link", href=True)
        raw_href = link_el.get("href") if link_el else ""
        if not raw_href:
            return None
        if raw_href.startswith("//"):
            url = "https:" + raw_href
        elif raw_href.startswith("/"):
            url = _BASE_URL + raw_href
        else:
            url = raw_href

        company_el = card.find(
            class_="ij-OfferCardContent-description-subtitle-link"
        )
        company = company_el.get_text(strip=True) if company_el else ""

        # Meta list — orden empírico observado en producción:
        #   [0] ciudad, [1] modalidad, [2] fecha publicación, [3]
        #   contrato, [4] jornada, [5] salario.
        # Los índices pueden variar si InfoJobs cambia el layout —
        # extraemos por semantics best-effort.
        meta_els = card.find_all(class_="ij-OfferCardContent-description-list-item")
        meta_texts = [m.get_text(strip=True) for m in meta_els]

        city = meta_texts[0] if meta_texts else ""
        # `location` del DTO — agregamos "España" como país para que
        # `extract_country` lo detecte como ES sin ambigüedad.
        location = f"{city}, España" if city else "España"

        # Summary con la meta relevante — útil como fallback cuando el
        # detalle no se fetchea (mismo trade-off que Computrabajo).
        summary_parts = [title]
        if company:
            summary_parts.append(f"Empresa: {company}")
        if meta_texts:
            summary_parts.append(" · ".join(meta_texts[:6]))
        summary = " — ".join(summary_parts)

        keywords = extract_keywords(f"{title} {' '.join(meta_texts)}")

        return JobOfferData(
            title=title,
            company=company,
            location=location,
            summary=summary,
            url=url,
            keywords=keywords,
            portal="infojobs",
        )

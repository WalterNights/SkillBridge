"""Scraper de co.indeed.com — best-effort via Playwright.

Indeed protege con Cloudflare (status 403 al request HTTP plano,
"Security Check" como response). Un browser headless puede pasar el
challenge en la primera carga si el TLS fingerprint + JS engine son
de Chrome real — Playwright + Chromium cumple eso.

Riesgo conocido: Cloudflare puede subir el nivel de challenge (captcha
visual) en cualquier momento. Si lo hace, el scraper devuelve []
silenciosamente y el scrape general sigue con los otros portales.

Estrategia idéntica al MagnetoScraper: navegar, esperar cards, parsear.
Indeed sí renderiza el primer batch de jobs en el HTML inicial (SSR
parcial), pero Playwright es necesario para pasar Cloudflare.
"""

from __future__ import annotations

import logging
from urllib.parse import quote_plus

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


_BASE_URL = "https://co.indeed.com/jobs"
_LOAD_TIMEOUT_MS = 30000
_CARDS_WAIT_TIMEOUT_MS = 15000


class IndeedScraper(JobScraper):
    """Scraper de Indeed Colombia via Playwright headless."""

    portal_name = "indeed"
    description = (
        "Agregador global con presencia fuerte en Colombia, México y "
        "España. Generalista — sirve para casi cualquier vertical "
        "(tech, ventas, salud, agro/veterinaria, agroindustria, "
        "nutrición animal, producción avícola/porcícola, multinacionales "
        "del sector). Depende de Playwright (puede fallar silencioso) y "
        "a veces lo bloquea Cloudflare."
    )
    categories = ("all",)

    def search(self, query: str, location: str, pages: int = 1) -> list[JobOfferData]:
        if not query:
            raise ScraperError("query es obligatorio")

        try:
            from jobs.adapters.scrapers._playwright_session import playwright_page
        except ImportError as exc:
            logger.warning("Playwright not available, skipping Indeed: %s", exc)
            return []

        url = self._build_url(query, location)
        logger.info("Indeed scrape: %s", url)

        html: str | None = None
        try:
            with playwright_page(timeout_ms=_LOAD_TIMEOUT_MS) as page:
                page.goto(url, wait_until="domcontentloaded")
                # Esperar a que aparezcan los job cards. El selector
                # estable de Indeed es `[data-jk]` (data attribute con
                # el job key — el id único).
                try:
                    page.wait_for_selector(
                        "[data-jk], a[href*='/viewjob']",
                        timeout=_CARDS_WAIT_TIMEOUT_MS,
                    )
                except Exception:
                    logger.warning(
                        "Indeed: no cards within timeout — likely Cloudflare challenge"
                    )
                    return []
                # Pequeño settle time para JS post-paint
                page.wait_for_timeout(1500)
                html = page.content()
        except Exception as exc:
            logger.warning("Indeed Playwright session failed: %s", exc)
            return []

        if not html:
            return []
        return self._parse_listing(html)

    @staticmethod
    def _build_url(query: str, location: str) -> str:
        # q = keyword, l = location. Funciona también con location vacío.
        params = [f"q={quote_plus(query)}"]
        if location:
            params.append(f"l={quote_plus(location)}")
        return f"{_BASE_URL}?{'&'.join(params)}"

    def _parse_listing(self, html: str) -> list[JobOfferData]:
        soup = BeautifulSoup(html, "html.parser")

        # `[data-jk]` son los containers de cada card. Cada uno tiene
        # un `<a>` con `/viewjob?jk=...`, el título, empresa, location.
        cards = soup.select("[data-jk]") or soup.select("a[href*='/viewjob']")
        # Si los cards no son los containers sino solo los anchors,
        # convertimos al parent que tiene todo el contenido.
        if cards and cards[0].name == "a":
            cards = [c.find_parent("li") or c.find_parent("div") or c for c in cards]
        logger.info("Indeed raw cards: %d", len(cards))

        offers: list[JobOfferData] = []
        seen_urls: set[str] = set()
        for card in cards:
            try:
                offer = self._parse_card(card)
                if offer is None or offer.url in seen_urls:
                    continue
                seen_urls.add(offer.url)
                offers.append(offer)
            except Exception:
                logger.exception("Indeed card parse failed, skipping")
        logger.info("Indeed valid offers: %d", len(offers))
        return offers

    def _parse_card(self, card) -> JobOfferData | None:
        link_tag = card.select_one("a[href*='/viewjob']") or card.select_one(
            "h2.jobTitle a"
        )
        if not link_tag:
            return None
        href = link_tag.get("href", "")
        if not href:
            return None
        url = (
            href if href.startswith("http") else f"https://co.indeed.com{href}"
        ).split("&")[0]  # strip los & extras dejamos solo jk=

        title_tag = (
            card.select_one("h2.jobTitle span[title]")
            or card.select_one("h2.jobTitle")
            or card.select_one("[class*='jobTitle']")
        )
        title = title_tag.get_text(strip=True) if title_tag else link_tag.get_text(strip=True)
        if not title or len(title) < 4:
            return None

        company_tag = card.select_one(
            "[data-testid='company-name'], [class*='companyName'], [class*='company-name']"
        )
        location_tag = card.select_one(
            "[data-testid='text-location'], [class*='companyLocation'], [class*='locationsContainer']"
        )
        company = company_tag.get_text(strip=True) if company_tag else ""
        location = location_tag.get_text(strip=True) if location_tag else ""

        # Indeed muestra "hace X días" en un span tipo `[class*='date']`
        # o como texto plano cerca del bottom del card.
        date_tag = card.select_one(
            "[data-testid='myJobsStateDate'], [class*='date'], span.date"
        )
        date_text = date_tag.get_text(strip=True) if date_tag else card.get_text(" ", strip=True)
        age_days = extract_age_days(date_text)
        if age_days is not None and age_days > MAX_OFFER_AGE_DAYS:
            logger.info("Skipping old Indeed card (%d days): %s", age_days, title[:60])
            return None

        snippet_tag = card.select_one(
            "[data-testid='snippetWrapper'], [class*='snippet'], [class*='job-snippet']"
        )
        snippet = snippet_tag.get_text(" ", strip=True) if snippet_tag else ""
        summary = " ".join([s for s in (title, company, snippet) if s])[:2000]

        return JobOfferData(
            title=title[:500],
            company=company[:255],
            location=location[:255],
            summary=summary,
            keywords=extract_keywords(summary),
            url=url,
            portal=self.portal_name,
        )

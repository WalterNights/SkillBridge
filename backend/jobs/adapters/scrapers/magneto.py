"""Scraper de magneto365.com — portal de empleos colombiano.

Magneto es un SPA Next.js sin SSR. La HTML inicial que sirve es un shell
vacío; los jobs los carga JS pegando a su API interna. Por eso plain
`requests` no funciona — necesitamos un browser real que ejecute el JS.

Estrategia:
  1. Navegar a su URL de búsqueda con keyword + location.
  2. Esperar a que el JS cargue los job cards.
  3. Extraer el HTML rendered y parsearlo con BS4.
  4. Cerrar el browser (cleanup garantizado por el context manager).

Costo: ~10-20s por scrape vs ~2s con HTTP plano. Vale la pena por la
cobertura adicional — Magneto agrega ~30-80 ofertas por búsqueda en
Colombia que no aparecían via DDG.

Defensa contra cambios en su HTML: selectors con fallbacks. Si todos
fallan, devuelve [] sin tumbar el scrape general.
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


_BASE_URL = "https://www.magneto365.com/co/trabajos/buscar"
_LOAD_TIMEOUT_MS = 45000
# Después del page.goto() esperamos a que aparezcan los cards en el DOM.
# Si no aparecen en este tiempo, asumimos que no hay resultados o
# Magneto cambió el layout — devolvemos vacío sin romper.
_CARDS_WAIT_TIMEOUT_MS = 20000
# Settle time post-render: aunque el primer card aparece rápido, el SPA
# sigue hidratando más cards después. 3s nos da el 90% de los visibles.
_POST_CARDS_SETTLE_MS = 3000


class MagnetoScraper(JobScraper):
    """Scraper de Magneto365 via Playwright headless."""

    portal_name = "magneto"

    def search(self, query: str, location: str, pages: int = 1) -> list[JobOfferData]:
        if not query:
            raise ScraperError("query es obligatorio")

        # Import perezoso del helper (que a su vez importa playwright).
        # Si playwright no está instalado en este entorno, ImportError
        # se propaga y el JobService skipea este scraper individual.
        try:
            from jobs.adapters.scrapers._playwright_session import playwright_page
        except ImportError as exc:
            logger.warning("Playwright not available, skipping Magneto: %s", exc)
            return []

        url = self._build_url(query, location)
        logger.info("Magneto scrape: %s", url)

        html: str | None = None
        try:
            with playwright_page(timeout_ms=_LOAD_TIMEOUT_MS) as page:
                # `domcontentloaded` en vez de `networkidle` porque
                # Magneto deja conexiones long-lived (analytics, ws) y
                # networkidle nunca llega → timeout duro.
                page.goto(url, wait_until="domcontentloaded")
                # Esperar a que aparezca AL MENOS un anchor a oferta.
                # El SPA puede tardar ~5-15s en hidratar el listado.
                try:
                    page.wait_for_selector(
                        "a[href*='/co/trabajos/']",
                        timeout=_CARDS_WAIT_TIMEOUT_MS,
                    )
                except Exception:
                    logger.warning("Magneto: no cards detected within timeout")
                    return []
                # Settle time — el primer card aparece rápido pero el
                # SPA sigue agregando más después. 3s captura el 90%
                # de los visibles.
                page.wait_for_timeout(_POST_CARDS_SETTLE_MS)
                html = page.content()
        except Exception as exc:
            # Playwright puede fallar por Chromium no instalado, RAM
            # llena, timeout duro, etc. Loguear y devolver vacío — el
            # scrape general sigue con los otros portales.
            logger.warning("Magneto Playwright session failed: %s", exc)
            return []

        if not html:
            return []
        return self._parse_listing(html)

    @staticmethod
    def _build_url(query: str, location: str) -> str:
        # URL pattern observado: /co/trabajos/buscar?title=X&city=Y
        # Si Magneto cambia los param names el scraper igual carga la
        # página de búsqueda y muestra "popular jobs" — peor caso
        # devuelve menos pero relevantes.
        params = [f"title={quote_plus(query)}"]
        if location:
            params.append(f"city={quote_plus(location)}")
        return f"{_BASE_URL}?{'&'.join(params)}"

    def _parse_listing(self, html: str) -> list[JobOfferData]:
        soup = BeautifulSoup(html, "html.parser")

        # Buscamos los enlaces a ofertas individuales. Magneto las URLs
        # tienen `/co/trabajos/<slug>-<id>`. Filtramos las que no son
        # detail (buscar, inicio, etc).
        cards = soup.select("a[href*='/co/trabajos/']")
        cards = [
            c for c in cards
            if c.get("href")
            and "/buscar" not in c["href"]
            and "/inicio" not in c["href"]
            and c["href"] != "/co/trabajos/"
        ]
        logger.info("Magneto raw cards: %d", len(cards))

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
                logger.exception("Magneto card parse failed, skipping")
        logger.info("Magneto valid offers: %d", len(offers))
        return offers

    def _parse_card(self, card) -> JobOfferData | None:
        href = card.get("href", "")
        if not href:
            return None
        # URL absoluta
        url = (
            href if href.startswith("http") else f"https://www.magneto365.com{href}"
        ).split("?")[0]

        # El título suele ser el primer <h3> o <h2> dentro del card,
        # o el texto del propio anchor si no hay heading.
        title_tag = (
            card.select_one("h3, h2, [class*='title'], [data-testid*='title']")
        )
        title = title_tag.get_text(strip=True) if title_tag else card.get_text(" ", strip=True)
        title = " ".join(title.split())  # collapse whitespace
        if not title or len(title) < 4:
            return None

        # Empresa y location pueden estar en spans hermanos del título.
        # Fallback: substring del texto completo del card.
        full_text = card.get_text(" ", strip=True)
        company = ""
        location = ""
        for selector in [
            "[class*='company']", "[data-testid*='company']",
            "span:nth-of-type(2)",
        ]:
            tag = card.select_one(selector)
            if tag and tag.get_text(strip=True):
                company = tag.get_text(strip=True)
                break
        for selector in [
            "[class*='location']", "[data-testid*='location']",
            "[class*='city']",
        ]:
            tag = card.select_one(selector)
            if tag and tag.get_text(strip=True):
                location = tag.get_text(strip=True)
                break

        # Filtro de edad — Magneto suele mostrar "Hace 3 días" en algún
        # span del card. Lo escaneamos sobre el texto completo.
        age_days = extract_age_days(full_text)
        if age_days is not None and age_days > MAX_OFFER_AGE_DAYS:
            logger.info("Skipping old Magneto card (%d days): %s", age_days, title[:60])
            return None

        summary = full_text[:2000]

        return JobOfferData(
            title=title[:500],
            company=company[:255],
            location=location[:255],
            summary=summary,
            keywords=extract_keywords(f"{title} {summary}"),
            url=url,
            portal=self.portal_name,
        )

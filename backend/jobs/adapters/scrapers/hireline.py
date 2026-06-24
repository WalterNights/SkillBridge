"""Scraper de hireline.io (México + Colombia, tech-focused).

Hireline es un SPA Vue (sin __NUXT__/__NEXT_DATA__), pero los detail
pages de cada oferta están server-rendered para SEO. Estrategia:

  1. Leer sitemap_ofertas.xml del país (MX, CO) — listas todas las
     URLs de ofertas con <lastmod>.
  2. Filtrar las que tienen lastmod >7 días (regla compartida en base).
  3. Cap a MAX_OFFERS_PER_RUN para no spamear el portal.
  4. Para cada URL, fetch del detail y parsear el bloque JSON-LD
     `JobPosting` — schema.org estable, mucho más robusto que parsear
     CSS classes que cambian con cada deploy del frontend.

`query` y `location` no se usan como filtro de búsqueda (Hireline no
tiene endpoint público de search por keyword). El matching downstream
se encarga: cualquier oferta recibida pasa por el algoritmo que decide
si encaja con el perfil del user.

Si JSON-LD falta en una página (improbable, Google lo exige), la
ignoramos en silencio — el resto del scrape no se rompe.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from xml.etree import ElementTree as ET

import requests
from bs4 import BeautifulSoup

from jobs.adapters.scrapers.base import (
    MAX_OFFER_AGE_DAYS,
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

BASE_URL = "https://hireline.io"

# Países activos en Hireline. MX y CO son los grandes; US tiene pocas
# ofertas y son en inglés (las dejamos fuera por ahora).
_COUNTRY_SITEMAPS = [
    f"{BASE_URL}/mx/sitemap_ofertas.xml",
    f"{BASE_URL}/co/sitemap_ofertas.xml",
]

# Cap por scrape para no martillar al portal. ~30 detail pages × 2
# países = 60 requests por run, manejable y bajo el radar de rate-limit.
MAX_OFFERS_PER_RUN_PER_COUNTRY = 30

# XML namespace del sitemaps.org schema — ElementTree no parsea tags
# sin namespace si el XML lo declara.
_SM_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


class HirelineScraper(JobScraper):
    """Scraper de hireline.io vía sitemap + JSON-LD."""

    portal_name = "hireline"

    def search(self, query: str, location: str, pages: int = 2) -> list[JobOfferData]:
        logger.info(
            "Iniciando scrape Hireline: query=%r location=%r (sitemap-based, query ignorado)",
            query,
            location,
        )

        # `pages` no aplica directamente (no hay paginación de sitemap).
        # Lo respetamos como hint de "cuánto cap": pages=1 → 15 per país;
        # pages=2 → 30 per país (default).
        cap_per_country = max(15, MAX_OFFERS_PER_RUN_PER_COUNTRY * pages // 2)

        offers: list[JobOfferData] = []
        for sitemap_url in _COUNTRY_SITEMAPS:
            urls = self._recent_urls_from_sitemap(sitemap_url, cap=cap_per_country)
            for url in urls:
                offer = self._parse_detail_page(url)
                if offer is not None:
                    offers.append(offer)
        return offers

    # ---- Helpers internos ----------------------------------------------

    def _recent_urls_from_sitemap(self, sitemap_url: str, cap: int) -> list[str]:
        """Lee el sitemap, filtra por lastmod reciente, cap al N más
        nuevo. Devuelve URLs ya ordenadas por recencia descendente."""
        try:
            response = requests.get(
                sitemap_url,
                headers={"User-Agent": USER_AGENT},
                timeout=self.request_timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException as e:
            logger.warning("Error fetching Hireline sitemap %s: %s", sitemap_url, e)
            return []

        try:
            root = ET.fromstring(response.content)
        except ET.ParseError as e:
            logger.warning("Sitemap malformado %s: %s", sitemap_url, e)
            return []

        now = datetime.now(timezone.utc).date()
        entries: list[tuple[str, datetime]] = []
        for url_el in root.findall("sm:url", _SM_NS):
            loc_el = url_el.find("sm:loc", _SM_NS)
            mod_el = url_el.find("sm:lastmod", _SM_NS)
            if loc_el is None or loc_el.text is None:
                continue
            loc = loc_el.text.strip()
            lastmod_str = (mod_el.text or "").strip() if mod_el is not None else ""

            # Filtro de edad por lastmod del sitemap. Formato típico:
            # "2026-06-23" o "2026-06-23T12:00:00+00:00".
            try:
                lastmod = datetime.fromisoformat(lastmod_str.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                # Sin lastmod confiable → no podemos filtrar por edad,
                # mejor descartarla que asumir reciente y desperdiciar
                # un fetch del detail.
                continue
            if (now - lastmod.date()).days > MAX_OFFER_AGE_DAYS:
                continue
            entries.append((loc, lastmod))

        # Ordenar por lastmod descendente y cap.
        entries.sort(key=lambda t: t[1], reverse=True)
        urls = [loc for loc, _ in entries[:cap]]
        logger.info("Hireline sitemap %s: %d URLs recientes (cap %d)", sitemap_url, len(urls), cap)
        return urls

    def _parse_detail_page(self, url: str) -> JobOfferData | None:
        try:
            response = requests.get(
                url,
                headers={"User-Agent": USER_AGENT},
                timeout=self.request_timeout_seconds,
            )
        except requests.RequestException as e:
            logger.warning("Error fetching Hireline detail %s: %s", url, e)
            return None

        if response.status_code != 200:
            logger.info("Hireline detail %s devolvió %d, skip", url, response.status_code)
            return None

        soup = BeautifulSoup(response.content, "html.parser")
        # Buscamos el JSON-LD que es @type JobPosting (la página tiene
        # varios JSON-LD: WebSite, EmploymentAgency, JobPosting).
        for script in soup.find_all("script", type="application/ld+json"):
            raw = (script.string or "").strip()
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict) and data.get("@type") == "JobPosting":
                return self._job_posting_to_offer(data, url)
        logger.info("Hireline detail %s sin JSON-LD JobPosting, skip", url)
        return None

    @staticmethod
    def _job_posting_to_offer(data: dict, url: str) -> JobOfferData:
        """Convierte el dict del JobPosting (schema.org) a JobOfferData.

        Campos esperados (no todos pueden estar):
          - title, description (HTML o texto)
          - hiringOrganization.name
          - jobLocation.address.{addressLocality, addressRegion, addressCountry}
            (puede ser dict o list)
        """
        title = (data.get("title") or "").strip()

        # description suele venir con HTML — limpiamos a texto plano para
        # el matcher y para el preview que mostramos al user.
        description_html = data.get("description") or ""
        description = BeautifulSoup(description_html, "html.parser").get_text(" ", strip=True)

        organization = data.get("hiringOrganization") or {}
        company = organization.get("name", "") if isinstance(organization, dict) else ""

        # jobLocation puede ser dict o list — normalizamos al primero.
        loc_node = data.get("jobLocation")
        if isinstance(loc_node, list):
            loc_node = loc_node[0] if loc_node else None
        location = ""
        if isinstance(loc_node, dict):
            addr = loc_node.get("address") or {}
            if isinstance(addr, dict):
                parts = [
                    addr.get("addressLocality") or "",
                    addr.get("addressRegion") or "",
                    addr.get("addressCountry") or "",
                ]
                location = ", ".join(p.strip() for p in parts if p and p.strip())

        keywords = extract_keywords(f"{title} {description}")

        return JobOfferData(
            title=title,
            company=company.strip(),
            location=location,
            summary=description,
            keywords=keywords,
            url=url,
            portal="hireline",
        )

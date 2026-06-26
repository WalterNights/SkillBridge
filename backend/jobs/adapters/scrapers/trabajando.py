"""Scraper de Trabajando.com (Chile + Colombia).

Misma estrategia que Hireline: el portal es SPA pero los detail pages
están server-rendered con JSON-LD JobPosting para SEO.

Flujo:
  1. Lee sitemap-ofertas.xml de cada país (CL, CO).
  2. Filtra URLs con lastmod >7 días.
  3. Cap a MAX_OFFERS_PER_RUN_PER_COUNTRY para no martillar.
  4. Por cada URL, fetch del detail page y parsea el JSON-LD JobPosting.

`query` y `location` se ignoran como filtro server-side — el sitemap no
los soporta. El matching downstream hace el trabajo de seleccionar las
relevantes al perfil del user.
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
    extract_keywords,
)

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/114.0.0.0 Safari/537.36"
)

# Países activos. Trabajando.com tiene presencia en muchos países más
# (.com.ar, .com.mx, etc) — agregamos solo CL y CO para empezar; el
# sitemap de los grandes ya trae miles de ofertas, suficiente para que
# el matcher tenga material.
_COUNTRY_SITEMAPS = [
    "https://www.trabajando.cl/sitemap-ofertas.xml",
    "https://www.trabajando.com.co/sitemap-ofertas.xml",
]

# Sitemaps suelen traer >2000 URLs por país. Cap agresivo para no
# disparar 2k requests por scrape — el matcher prefiere variedad sobre
# volumen, las 30 más recientes alcanzan.
MAX_OFFERS_PER_RUN_PER_COUNTRY = 30

_SM_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


class TrabajandoScraper(JobScraper):
    """Scraper de trabajando.cl + trabajando.com.co vía sitemap + JSON-LD."""

    portal_name = "trabajando"
    description = (
        "Bolsa generalista LATAM (trabajando.cl, trabajando.com.co, etc). "
        "Fuerte en Chile y Colombia. Cobertura horizontal: ventas, "
        "administrativos, ingeniería, salud, hostelería, retail."
    )
    categories = ("all",)

    def search(self, query: str, location: str, pages: int = 2) -> list[JobOfferData]:
        logger.info(
            "Iniciando scrape Trabajando.com: query=%r location=%r (sitemap-based)",
            query,
            location,
        )

        # `pages` actúa como multiplicador del cap — pages=1 = 15 per país,
        # pages=2 = 30 (default).
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
        try:
            response = requests.get(
                sitemap_url,
                headers={"User-Agent": USER_AGENT},
                timeout=self.request_timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException as e:
            logger.warning("Error fetching Trabajando sitemap %s: %s", sitemap_url, e)
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
            try:
                lastmod = datetime.fromisoformat(lastmod_str.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                continue
            if (now - lastmod.date()).days > MAX_OFFER_AGE_DAYS:
                continue
            entries.append((loc, lastmod))

        entries.sort(key=lambda t: t[1], reverse=True)
        urls = [loc for loc, _ in entries[:cap]]
        logger.info("Trabajando sitemap %s: %d URLs recientes (cap %d)", sitemap_url, len(urls), cap)
        return urls

    def _parse_detail_page(self, url: str) -> JobOfferData | None:
        try:
            response = requests.get(
                url,
                headers={"User-Agent": USER_AGENT},
                timeout=self.request_timeout_seconds,
            )
        except requests.RequestException as e:
            logger.warning("Error fetching Trabajando detail %s: %s", url, e)
            return None

        if response.status_code != 200:
            logger.info("Trabajando detail %s devolvió %d, skip", url, response.status_code)
            return None

        soup = BeautifulSoup(response.content, "html.parser")
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
        logger.info("Trabajando detail %s sin JSON-LD JobPosting, skip", url)
        return None

    @staticmethod
    def _job_posting_to_offer(data: dict, url: str) -> JobOfferData:
        title = (data.get("title") or "").strip()

        description_html = data.get("description") or ""
        description = BeautifulSoup(description_html, "html.parser").get_text(" ", strip=True)

        organization = data.get("hiringOrganization") or {}
        company = organization.get("name", "") if isinstance(organization, dict) else ""

        loc_node = data.get("jobLocation")
        if isinstance(loc_node, list):
            loc_node = loc_node[0] if loc_node else None
        location = ""
        if isinstance(loc_node, dict):
            addr = loc_node.get("address") or {}
            if isinstance(addr, dict):
                # Trabajando suele poner la dirección en `streetAddress`
                # con formato "comuna, ciudad, país". Tomamos eso si está,
                # sino caemos a addressLocality + region + country.
                street = (addr.get("streetAddress") or "").strip()
                if street:
                    location = street
                else:
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
            portal="trabajando",
        )

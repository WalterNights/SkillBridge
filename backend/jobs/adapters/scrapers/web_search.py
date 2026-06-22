"""Meta-scraper que usa un buscador web como agregador de jobs.

Backend: DuckDuckGo HTML version (https://html.duckduckgo.com/html/).

¿Por qué no Google directo? Probamos Google primero pero su SERP
requiere JS para renderizar — el HTML que devuelve a clientes sin JS
es solo un meta-refresh a `?enablejs=...`. Resultado: 0 selectores
matchean nada. Para hacerlo andar habría que cargar Chrome headless
(Playwright), agregar mucha infra. DDG sirve la misma idea (`site:`
operators, restringir a portales conocidos) y responde HTML completo
sin JS — exactamente lo que necesitamos.

Limitaciones aceptadas (decisiones explícitas, no bugs):
- SIN detail-fetch: usamos el snippet del SERP como `summary`. Es el
  fragmento que aparece bajo el título — suele incluir empresa y un
  pedazo de la descripción. Suficiente para que `extract_keywords`
  levante el stack si está mencionado.
- Anuncios: DDG mezcla ads de Bing al inicio. Los detectamos por URL
  (van a `duckduckgo.com/y.js?ad_domain=...`) y los descartamos.
- Portal tag: todas las ofertas salen como `portal="websearch"`. La URL
  real apunta al portal original (LinkedIn/Elempleo/etc), así que el
  usuario no pierde nada al clickear. Tagear todo igual mantiene las
  stats consistentes en `scrape_all_portals_with_stats`.
- Volumen: DDG no tiene rate-limit publicado pero es educado quedarse
  bajo ~100 req/día. Si escalamos, migrar a Google Custom Search API.
"""

from __future__ import annotations

import ipaddress
import logging
import re
import socket
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

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
    "Chrome/126.0.0.0 Safari/537.36"
)

# Portales a los que restringimos la búsqueda. Cualquier resultado fuera
# de esta lista se descarta (no es una oferta). Mantener corta —
# agregar uno nuevo dispara más OR site: en el query.
_JOB_SITES = (
    "linkedin.com/jobs",
    "elempleo.com",
    "bumeran.com.co",
    "computrabajo.com.co",
    "indeed.com.co",
    "getonbrd.com",
    "magneto365.com",
)

# Marcadores que indican que el buscador nos sirvió rate-limit o
# captcha en vez de SERP. Si vemos cualquiera, abortamos sin reintentar.
_RATE_LIMIT_MARKERS = (
    "unusual traffic",
    "tráfico inusual",
    "rate limit",
)

# Marcadores que sugieren que la oferta ya está cerrada y aparecen en el
# snippet/título del SERP. Filtro zero-cost — los que están claramente
# muertos los descartamos antes de tocar la DB. NO captura los casos
# donde DDG indexó la oferta cuando estaba viva pero hoy está cerrada
# (ahí necesitamos el probe activo).
_CLOSED_SNIPPET_MARKERS = (
    "ya no se aceptan",
    "no longer accepting",
    "no longer available",
    "this position is no longer",
    "vacante cerrada",
    "convocatoria cerrada",
    "oferta cerrada",
    "esta oferta no está disponible",
    "esta oferta ya no",
    "expirada",
    "expired",
)

# Marcadores que LinkedIn pone en el body de la página cuando una oferta
# está cerrada. Lo busca solo el probe activo para URLs de LinkedIn,
# que es el principal source de "ofertas indexadas pero ya muertas".
_LINKEDIN_CLOSED_MARKERS = (
    "no longer accepting applications",
    "ya no se aceptan solicitudes",
    "esta oferta de empleo no está disponible",
    "this job is no longer available",
)

# Concurrencia y timeout del probe activo. Bajos a propósito: cada GET
# expone a antibot de LinkedIn, así que mejor pocos en paralelo y rápido.
_PROBE_MAX_WORKERS = 3
_PROBE_TIMEOUT_SECONDS = 6

# SEGURIDAD (SSRF): hosts cuyo subdominio aceptamos resolver y probar.
# DDG nos da URLs que pasan el filtro `_JOB_SITES`, pero ese filtro es
# substring — `https://attacker.com/linkedin.com/jobs/foo` lo pasaría.
# Acá enforce-amos un match estricto sobre el host del URL. Sumado a
# la denylist de IPs privadas en `_resolves_to_public_ip`, cierra el
# vector de pedirle al backend que hablé con 127.0.0.1 o el endpoint
# de metadata de cloud (169.254.169.254).
_PROBE_ALLOWED_HOSTS = (
    "linkedin.com",
    "www.linkedin.com",
    "co.linkedin.com",
    "es.linkedin.com",
)


def _is_safe_probe_url(url: str) -> bool:
    """Devuelve True si el URL apunta a un host de LinkedIn legítimo Y
    resuelve a una IP pública. False ante cualquier duda."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    host = (parsed.hostname or "").lower()
    if host not in _PROBE_ALLOWED_HOSTS:
        return False
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        return False
    for info in infos:
        ip_str = info[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            return False
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            return False
    return True


class WebSearchJobsScraper(JobScraper):
    """Scraper meta que usa DDG HTML restringida a sitios de empleo."""

    portal_name = "websearch"

    def search(self, query: str, location: str, pages: int = 1) -> list[JobOfferData]:
        if not query:
            raise ScraperError("query es obligatorio")

        ddg_query = self._build_query(query, location)
        url = "https://html.duckduckgo.com/html/"
        logger.info("WebSearch scrape: query=%r", ddg_query)

        try:
            # DDG HTML acepta POST y GET — usamos POST porque GET con el
            # query largo a veces dispara su detector de scrapers.
            response = requests.post(
                url,
                data={"q": ddg_query, "kl": "co-es"},  # kl = region:lang
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
                    "Accept": (
                        "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
                    ),
                },
                timeout=self.request_timeout_seconds,
            )
        except requests.RequestException as e:
            logger.error("WebSearch fetch failed: %s", e)
            return []

        if response.status_code >= 400:
            logger.warning("WebSearch responded %d", response.status_code)
            return []

        if self._is_rate_limited(response.text):
            logger.warning("WebSearch returned rate-limit page — aborting")
            return []

        offers = self._parse_serp(response.text)
        # Probe activo solo para LinkedIn: el snippet pre-filter ya pasó,
        # pero LinkedIn suele tener ofertas indexadas que indexaron vivas
        # y hoy están cerradas. Costo: 1 GET por oferta de LinkedIn.
        offers = self._filter_closed_linkedin(offers)
        return offers

    # ---- Query / detection ---------------------------------------------

    @staticmethod
    def _build_query(query: str, location: str) -> str:
        """Arma el query con quotes en el rol + ubicación + clause de sites."""
        sites_clause = " OR ".join(f"site:{s}" for s in _JOB_SITES)
        loc = f'"{location}"' if location else ""
        return f'"{query}" {loc} ({sites_clause})'.strip()

    @staticmethod
    def _is_rate_limited(html: str) -> bool:
        lowered = html.lower()
        return any(m in lowered for m in _RATE_LIMIT_MARKERS)

    @staticmethod
    def _is_closed_by_snippet(title: str, snippet: str) -> bool:
        """Marca obvia de cerrado en el texto del SERP. Zero cost —
        captura los casos donde DDG ya indexó la oferta con el mensaje
        de cierre. NO sirve cuando DDG indexó la oferta cuando estaba
        viva (ahí entra el probe activo)."""
        combined = f"{title} {snippet}".lower()
        return any(m in combined for m in _CLOSED_SNIPPET_MARKERS)

    # ---- Active probe: only for LinkedIn ------------------------------

    def _filter_closed_linkedin(
        self, offers: list[JobOfferData]
    ) -> list[JobOfferData]:
        """Recorre los URLs de LinkedIn en paralelo y descarta los que
        sirven el banner de cerrado. NO toca otros portales.

        Para todo lo que no sea LinkedIn, la oferta pasa intacta. Para
        LinkedIn, si el probe responde claro que está cerrada, la
        descarta; ante cualquier ambigüedad (red caída, status >= 400,
        rate-limit) la mantenemos — no penalizar por errores de red.
        """
        linkedin_offers = [o for o in offers if "linkedin.com" in o.url]
        if not linkedin_offers:
            return offers

        linkedin_urls = [o.url for o in linkedin_offers]
        logger.info(
            "Probing %d LinkedIn URLs for closed status", len(linkedin_urls)
        )

        with ThreadPoolExecutor(max_workers=_PROBE_MAX_WORKERS) as pool:
            results = list(pool.map(self._is_linkedin_offer_closed, linkedin_urls))

        closed_urls = {url for url, closed in zip(linkedin_urls, results, strict=False) if closed}
        if not closed_urls:
            return offers
        logger.info("Dropping %d closed LinkedIn offers", len(closed_urls))
        return [o for o in offers if o.url not in closed_urls]

    @staticmethod
    def _is_linkedin_offer_closed(url: str) -> bool:
        """Hace GET al URL de LinkedIn y busca markers de cerrado en el
        body. Devuelve False (mantener oferta) ante red caída, status
        4xx/5xx o cualquier otra duda.

        SEGURIDAD (SSRF): el URL viene de DDG SERP, no es 100% confiable.
        Antes del GET validamos host + resolución a IP pública via
        `_is_safe_probe_url`. Si el chequeo falla, asumimos oferta viva
        (devuelve False) y no tocamos el endpoint sospechoso.
        """
        if not _is_safe_probe_url(url):
            logger.warning("Skipping unsafe probe URL: %s", url)
            return False
        try:
            response = requests.get(
                url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
                },
                timeout=_PROBE_TIMEOUT_SECONDS,
                allow_redirects=True,
            )
        except requests.RequestException:
            return False
        if response.status_code >= 400:
            return False
        body = response.text.lower()
        return any(m in body for m in _LINKEDIN_CLOSED_MARKERS)

    # ---- SERP parsing --------------------------------------------------

    def _parse_serp(self, html: str) -> list[JobOfferData]:
        soup = BeautifulSoup(html, "html.parser")
        result_blocks = soup.select(".result")
        logger.info("WebSearch raw blocks: %d", len(result_blocks))

        offers: list[JobOfferData] = []
        seen_urls: set[str] = set()
        for block in result_blocks:
            try:
                offer = self._parse_block(block)
                if offer is None or offer.url in seen_urls:
                    continue
                seen_urls.add(offer.url)
                offers.append(offer)
            except Exception:
                logger.exception("WebSearch block parse failed, skipping")
        logger.info("WebSearch valid offers: %d", len(offers))
        return offers

    def _parse_block(self, block) -> JobOfferData | None:
        link = block.select_one("a.result__a")
        if not link:
            return None

        href = link.get("href", "")
        # DDG envuelve algunas URLs en un redirect propio (/l/?uddg=...);
        # extraemos la URL real. Para ads (`y.js?ad_domain=...`) descartamos.
        href = self._unwrap_url(href)
        if not href:
            return None

        # Whitelist por dominio: DDG mezcla resultados orgánicos con ads
        # de Bing al principio. Si la URL no es a un portal de empleo
        # conocido, no nos interesa.
        if not any(site in href for site in _JOB_SITES):
            return None

        title = link.get_text(strip=True)
        if not title:
            return None

        snippet_tag = block.select_one(".result__snippet")
        snippet = snippet_tag.get_text(" ", strip=True) if snippet_tag else ""

        # Pre-filter por snippet/título: si DDG indexó la oferta con un
        # marker claro de cerrado, la descartamos antes de meterla a la DB.
        if self._is_closed_by_snippet(title, snippet):
            logger.info("Skipping closed offer (snippet marker): %s", href)
            return None

        domain = urlparse(href).netloc.lower()
        company = self._infer_company(snippet, fallback=self._domain_label(domain))
        location_hint = self._infer_location(snippet)
        keywords = extract_keywords(f"{title} {snippet}")

        return JobOfferData(
            title=title[:500],
            company=company[:255],
            location=location_hint[:255],
            summary=snippet[:2000],
            keywords=keywords,
            url=href,
            portal=self.portal_name,
        )

    @staticmethod
    def _unwrap_url(href: str) -> str:
        """DDG ads van a /y.js?ad_domain=... (descartar). Los orgánicos
        a veces van envueltos en /l/?uddg=<url-encoded> — extraemos el
        target real desde el query param. Los directos `http(s)://` se
        devuelven tal cual."""
        if not href:
            return ""
        if "y.js" in href:
            # Ad redirect — descartar
            return ""
        if href.startswith("//"):
            href = f"https:{href}"
        # Wrapper /l/?uddg=...
        if "uddg=" in href:
            from urllib.parse import parse_qs, unquote, urlparse as _u

            parsed = _u(href)
            qs = parse_qs(parsed.query)
            uddg = qs.get("uddg", [None])[0]
            if uddg:
                return unquote(uddg)
        return href if href.startswith("http") else ""

    # ---- Heuristics (company / location / portal label) ---------------

    @staticmethod
    def _domain_label(domain: str) -> str:
        """Etiqueta legible derivada del dominio. Fallback cuando no
        encontramos la empresa real en el snippet."""
        if "linkedin" in domain:
            return "LinkedIn"
        if "elempleo" in domain:
            return "Elempleo"
        if "bumeran" in domain:
            return "Bumeran"
        if "computrabajo" in domain:
            return "Computrabajo"
        if "indeed" in domain:
            return "Indeed"
        if "getonbrd" in domain:
            return "Get on Board"
        if "magneto" in domain:
            return "Magneto365"
        return domain

    @staticmethod
    def _infer_company(snippet: str, fallback: str) -> str:
        """Heurística suave: primer chunk antes de `·`/`-` en el snippet
        suele ser el nombre de la empresa. Si arranca con fecha o es
        muy largo, fallback a label del dominio."""
        if not snippet:
            return fallback
        first_chunk = re.split(r"[·\-—]", snippet, maxsplit=1)[0].strip()
        if not first_chunk:
            return fallback
        date_pattern = (
            r"^(hace\s|\d+\s+(d[íi]a|hora|hour|day|week|semana|month|mes))"
        )
        if re.match(date_pattern, first_chunk, re.IGNORECASE):
            return fallback
        if len(first_chunk) > 80:
            return fallback
        return first_chunk

    @staticmethod
    def _infer_location(snippet: str) -> str:
        """Mismo patrón: tomamos el segundo o tercer chunk del snippet
        buscando una ubicación. Descarta chunks que parecen fecha."""
        if not snippet:
            return ""
        parts = [p.strip() for p in re.split(r"[·\-—]", snippet)]
        date_pattern = (
            r"\b(hace\s|d[íi]as?|horas?|days?|ago|semanas?|weeks?|months?|meses?)\b"
        )
        for part in parts[1:]:
            if not part:
                continue
            if re.search(date_pattern, part, re.IGNORECASE):
                continue
            if "," in part or re.search(r"\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+", part):
                return part
        return ""

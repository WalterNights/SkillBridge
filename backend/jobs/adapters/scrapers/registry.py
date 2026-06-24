"""Factory para resolver scrapers por nombre.

Para agregar un portal nuevo: importar la clase y registrarla en _REGISTRY.
El resto del código (services, tasks) sigue hablando con el registry, no
con clases concretas.

Elempleo está fuera del registry porque su buscador corre 100% en cliente
vía JS — la URL pública devuelve siempre la misma lista de "ofertas
populares de hoy" sin importar el query, así que guardábamos ~40 ofertas
irrelevantes con match 0% cada vez que se llamaba. Para volver a
activarlo hace falta uno de:
  - un headless browser (Playwright) en el VPS que ejecute el JS
  - acceder a /api/joboffers/findbyfilter con cookies de sesión
La clase ElempleoScraper se queda en el código para retomarla cuando
tengamos esa infra.
"""

from __future__ import annotations

from jobs.adapters.scrapers.base import JobScraper, ScraperError
from jobs.adapters.scrapers.computrabajo import ComputrabajoScraper
from jobs.adapters.scrapers.hireline import HirelineScraper
from jobs.adapters.scrapers.indeed import IndeedScraper
from jobs.adapters.scrapers.linkedin import LinkedInGuestScraper
from jobs.adapters.scrapers.magneto import MagnetoScraper
from jobs.adapters.scrapers.trabajos_co import TrabajosColombiaScraper
from jobs.adapters.scrapers.web_search import WebSearchJobsScraper
from jobs.adapters.scrapers.weworkremotely import WeWorkRemotelyScraper

# WeWorkRemotelyScraper queda implementado pero FUERA del registro por
# defecto porque es 100% remoto/tech — para un contador, diseñador o
# vendedor era ruido garantizado en el feed. Cuando agreguemos perfiles
# "remote-first" o un toggle en el wizard de profile, lo activamos opt-in.
#
# LinkedInGuestScraper pega directo a la API guest de LinkedIn (HTTP plano).
# MagnetoScraper / IndeedScraper requieren Playwright (Chromium headless)
# porque son SPAs / tienen Cloudflare. Si Playwright no está instalado en
# el entorno (ej. CI sin chromium), esos scrapers devuelven [] sin tirar.
# WebSearchJobsScraper cubre los portales sin scraper dedicado
# (elempleo, bumeran, getonbrd) via DDG.
_REGISTRY: dict[str, type[JobScraper]] = {
    ComputrabajoScraper.portal_name: ComputrabajoScraper,
    HirelineScraper.portal_name: HirelineScraper,
    LinkedInGuestScraper.portal_name: LinkedInGuestScraper,
    MagnetoScraper.portal_name: MagnetoScraper,
    IndeedScraper.portal_name: IndeedScraper,
    TrabajosColombiaScraper.portal_name: TrabajosColombiaScraper,
    WebSearchJobsScraper.portal_name: WebSearchJobsScraper,
}


def get_scraper(portal: str) -> JobScraper:
    """Devuelve una instancia del scraper para `portal`.

    Raises:
        ScraperError: si el portal no está registrado.
    """
    scraper_cls = _REGISTRY.get(portal.lower())
    if scraper_cls is None:
        available = ", ".join(sorted(_REGISTRY)) or "(ninguno)"
        raise ScraperError(f"Portal '{portal}' no soportado. Disponibles: {available}")
    return scraper_cls()


def available_portals() -> list[str]:
    """Lista los portales que tenemos implementados."""
    return sorted(_REGISTRY)

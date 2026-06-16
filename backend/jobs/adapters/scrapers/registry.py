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
from jobs.adapters.scrapers.weworkremotely import WeWorkRemotelyScraper

_REGISTRY: dict[str, type[JobScraper]] = {
    ComputrabajoScraper.portal_name: ComputrabajoScraper,
    WeWorkRemotelyScraper.portal_name: WeWorkRemotelyScraper,
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

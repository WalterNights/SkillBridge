"""Factory para resolver scrapers por nombre.

Hoy solo existe Computrabajo. Cuando agreguemos InfoJobs, Indeed, etc.,
basta con registrarlos acá — el resto del código (services, tasks)
sigue hablando con el `ScraperRegistry`, no con clases concretas.
"""

from __future__ import annotations

from jobs.adapters.scrapers.base import JobScraper, ScraperError
from jobs.adapters.scrapers.computrabajo import ComputrabajoScraper
from jobs.adapters.scrapers.elempleo import ElempleoScraper

_REGISTRY: dict[str, type[JobScraper]] = {
    ComputrabajoScraper.portal_name: ComputrabajoScraper,
    ElempleoScraper.portal_name: ElempleoScraper,
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

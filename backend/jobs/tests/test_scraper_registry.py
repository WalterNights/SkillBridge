"""Tests del registry de scrapers."""

import pytest

from jobs.adapters.scrapers.base import JobScraper, ScraperError
from jobs.adapters.scrapers.computrabajo import ComputrabajoScraper
from jobs.adapters.scrapers.registry import available_portals, get_scraper


@pytest.mark.unit
class TestRegistry:
    def test_get_scraper_returns_computrabajo_instance(self):
        scraper = get_scraper("computrabajo")
        assert isinstance(scraper, ComputrabajoScraper)
        assert isinstance(scraper, JobScraper)

    def test_get_scraper_is_case_insensitive(self):
        assert isinstance(get_scraper("COMPUTRABAJO"), ComputrabajoScraper)
        assert isinstance(get_scraper("Computrabajo"), ComputrabajoScraper)

    def test_unknown_portal_raises_scraper_error(self):
        # Elempleo está fuera del registry hasta que tengamos Playwright
        with pytest.raises(ScraperError, match="no soportado"):
            get_scraper("elempleo")
        with pytest.raises(ScraperError, match="no soportado"):
            get_scraper("linkedin")

    def test_available_portals_lists_all_registered(self):
        assert available_portals() == ["computrabajo"]

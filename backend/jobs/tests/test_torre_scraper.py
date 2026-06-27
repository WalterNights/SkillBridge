"""Tests para `TorreScraper`.

Cubre:
- search() exitoso con response JSON estructurado.
- search() degrada limpio cuando la API responde 500 / non-JSON / shape
  raro (no rompe el resto del scrape, devuelve []).
- _to_offer() normaliza correctamente los campos cuando vienen como
  dicts, listas, strings o ausentes (el shape de Torre varía).
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from jobs.adapters.scrapers.base import ScraperError
from jobs.adapters.scrapers.torre import TorreScraper, _OPPORTUNITY_URL_TEMPLATE


def _fake_response(json_body=None, status_code: int = 200, text: str = ""):
    """Mock liviano del response de `requests.post`. Solo expone los
    campos que el scraper toca."""

    class _R:
        def __init__(self):
            self.status_code = status_code
            self.text = text or ""
            self._json = json_body

        def json(self):
            if self._json is None:
                raise ValueError("no json body")
            return self._json

    return _R()


_VALID_RESPONSE = {
    "results": [
        {
            "id": "OPP-12345",
            "objective": "Senior Product Designer",
            "organizations": [{"name": "Acme Inc"}],
            "locations": ["Bogotá, Colombia"],
            "remote": False,
            "skills": [{"name": "Figma"}, {"name": "User Research"}],
            "details": "Diseña la próxima generación de productos digitales.",
        },
        {
            "id": "OPP-67890",
            "objective": "Motion Designer",
            "organizations": [{"name": "Creative Studio"}],
            "locations": [],
            "remote": True,
            "skills": [{"name": "After Effects"}, {"name": "Cinema 4D"}],
        },
    ]
}


@pytest.mark.unit
class TestTorreScraperSearch:
    def test_parses_valid_response_into_offers(self):
        scraper = TorreScraper()
        with patch("jobs.adapters.scrapers.torre.requests.post") as mock_post:
            mock_post.return_value = _fake_response(json_body=_VALID_RESPONSE)
            offers = scraper.search("diseñador UX", "Bogotá")

        assert len(offers) == 2
        first = offers[0]
        assert first.title == "Senior Product Designer"
        assert first.company == "Acme Inc"
        assert first.location == "Bogotá, Colombia"
        assert first.portal == "torre"
        assert first.url == _OPPORTUNITY_URL_TEMPLATE.format(id="OPP-12345")

    def test_remote_opportunity_without_location_uses_Remote_marker(self):
        """Para que extract_modality detecte la modalidad remote, ponemos
        'Remote' como location cuando la opp es remota y no tiene
        location estructurado."""
        scraper = TorreScraper()
        with patch("jobs.adapters.scrapers.torre.requests.post") as mock_post:
            mock_post.return_value = _fake_response(json_body=_VALID_RESPONSE)
            offers = scraper.search("motion", "Bogotá")
        motion_offer = next(o for o in offers if "Motion" in o.title)
        assert motion_offer.location == "Remote"

    def test_empty_query_raises(self):
        scraper = TorreScraper()
        with pytest.raises(ScraperError):
            scraper.search("", "Bogotá")

    def test_500_response_returns_empty(self):
        scraper = TorreScraper()
        with patch("jobs.adapters.scrapers.torre.requests.post") as mock_post:
            mock_post.return_value = _fake_response(status_code=500, text="boom")
            offers = scraper.search("diseñador", "Bogotá")
        assert offers == []

    def test_non_json_response_returns_empty(self):
        scraper = TorreScraper()
        with patch("jobs.adapters.scrapers.torre.requests.post") as mock_post:
            # json_body=None hace que .json() tire ValueError
            mock_post.return_value = _fake_response(json_body=None, text="<html>oops</html>")
            offers = scraper.search("diseñador", "Bogotá")
        assert offers == []

    def test_missing_results_key_returns_empty(self):
        """Si la API cambia el shape, fail-silent — el resto del scrape
        no se rompe."""
        scraper = TorreScraper()
        with patch("jobs.adapters.scrapers.torre.requests.post") as mock_post:
            mock_post.return_value = _fake_response(json_body={"data": "unexpected"})
            offers = scraper.search("diseñador", "Bogotá")
        assert offers == []

    def test_request_exception_returns_empty(self):
        """Network failure no debe propagar — degrada limpio."""
        import requests as req

        scraper = TorreScraper()
        with patch("jobs.adapters.scrapers.torre.requests.post") as mock_post:
            mock_post.side_effect = req.ConnectionError("dns fail")
            offers = scraper.search("diseñador", "Bogotá")
        assert offers == []


@pytest.mark.unit
class TestTorreScraperToOffer:
    """Tests directos sobre `_to_offer` — robustez frente a shapes raros."""

    def test_missing_id_returns_none(self):
        offer = TorreScraper._to_offer({"objective": "Designer"}, location_hint="")
        assert offer is None

    def test_missing_title_returns_none(self):
        offer = TorreScraper._to_offer({"id": "X"}, location_hint="")
        assert offer is None

    def test_skills_as_strings_also_supported(self):
        """A veces la API devuelve `skills` como lista de strings simples
        en vez de dicts. Tiene que soportar ambos."""
        offer = TorreScraper._to_offer(
            {
                "id": "OPP-1",
                "objective": "Designer",
                "skills": ["Figma", "Sketch"],
            },
            location_hint="Bogotá",
        )
        assert offer is not None
        # Skills tageadas con el taxonomy llegan al summary fallback.
        assert "figma" in (offer.summary or "").lower() or "figma" in (
            offer.keywords or ""
        ).lower()

    def test_location_hint_fallback(self):
        """Sin location estructurado y sin remote, usamos el location
        pedido por el caller — no quedar con location vacío."""
        offer = TorreScraper._to_offer(
            {"id": "OPP-1", "objective": "Designer"},
            location_hint="Lima, Perú",
        )
        assert offer is not None
        assert offer.location == "Lima, Perú"

    def test_organization_as_dict_extracts_name(self):
        offer = TorreScraper._to_offer(
            {
                "id": "OPP-1",
                "objective": "Designer",
                "organizations": [{"name": "Big Co"}, {"name": "Other"}],
            },
            location_hint="",
        )
        assert offer is not None
        assert offer.company == "Big Co"

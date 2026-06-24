"""Tests del scraper trabajos.com Colombia con HTML fixtures (sin red).

Cubre:
  - Parser del listado (cards)
  - Skip de tarjetas viejas (>7 días)
  - Tarjetas sin link → ignoradas, no abortan la página
  - Errores de red → lista vacía
  - URL de búsqueda incluye CADENA + IDPAIS=40 + DESDE para paginación
"""

from unittest.mock import Mock

import pytest

from jobs.adapters.scrapers.base import JobOfferData, ScraperError
from jobs.adapters.scrapers.trabajos_co import TrabajosColombiaScraper


# HTML real (recortado) del portal — replica la estructura observada en
# colombia.trabajos.com/bolsa-empleo/ al 2026-06-23.
LISTING_HTML = """
<html><body>
  <div class="listado2014 card oferta">
    <div class="card-body">
      <div class="title-block">
        <a class="oferta j4m_link" href="https://colombia.trabajos.com/bolsa-empleo/111/backend-dev/" title="Oferta">Backend Developer Python</a>
      </div>
      <a class="empresa"><span>Acme Corp</span></a>
      <div class="info-oferta">
        <span class="loc"><span class="location"><span><strong>Bogotá</strong> Cundinamarca</span></span></span>
        <span class="fecha">22/06/2026</span>
      </div>
      <div class="doextended">Buscamos un desarrollador backend con experiencia en Python, Django y PostgreSQL para liderar un equipo de microservicios.</div>
      <p class="oi"><span>Indefinido</span><span class="oilast">Jornada Completa</span></p>
    </div>
  </div>
  <div class="listado2014 card oferta">
    <div class="card-body">
      <div class="title-block">
        <a class="oferta j4m_link" href="https://colombia.trabajos.com/bolsa-empleo/222/frontend-dev/" title="Oferta">Frontend Dev React</a>
      </div>
      <a class="empresa"><span>Initech</span></a>
      <div class="info-oferta">
        <span class="loc"><span class="location"><span>Medellín</span></span></span>
        <span class="fecha">23/06/2026</span>
      </div>
      <div class="doextended">Frontend Engineer con React y TypeScript.</div>
    </div>
  </div>
</body></html>
"""

LISTING_HTML_OLD_OFFER = """
<html><body>
  <div class="listado2014 card oferta">
    <div class="card-body">
      <div class="title-block">
        <a class="oferta j4m_link" href="https://colombia.trabajos.com/bolsa-empleo/999/old/" title="Oferta">Oferta Vieja</a>
      </div>
      <a class="empresa"><span>OldCo</span></a>
      <div class="info-oferta">
        <span class="loc"><span>Cali</span></span>
        <span class="fecha">01/05/2026</span>
      </div>
      <div class="doextended">Hace 30 días. Backend Engineer.</div>
    </div>
  </div>
</body></html>
"""

LISTING_HTML_BAD_CARD = """
<html><body>
  <div class="listado2014 card oferta">
    <div class="card-body">
      <!-- Sin a.oferta.j4m_link → ignorada -->
      <a class="empresa"><span>Sin link</span></a>
    </div>
  </div>
  <div class="listado2014 card oferta">
    <div class="card-body">
      <div class="title-block">
        <a class="oferta j4m_link" href="https://colombia.trabajos.com/bolsa-empleo/333/ok/" title="Oferta">Oferta Buena</a>
      </div>
      <a class="empresa"><span>Good Co</span></a>
      <div class="info-oferta">
        <span class="loc"><span>Bogotá</span></span>
        <span class="fecha">22/06/2026</span>
      </div>
      <div class="doextended">Algo concreto. Python developer.</div>
    </div>
  </div>
</body></html>
"""


def _mock_response(html: str) -> Mock:
    response = Mock()
    response.content = html.encode("utf-8")
    return response


@pytest.mark.unit
class TestTrabajosColombiaSearch:
    def test_search_requires_query(self):
        scraper = TrabajosColombiaScraper()
        with pytest.raises(ScraperError):
            scraper.search("", "Bogotá")

    def test_parses_offers_from_listing(self, mocker):
        mocker.patch(
            "jobs.adapters.scrapers.trabajos_co.requests.get",
            return_value=_mock_response(LISTING_HTML),
        )

        offers = TrabajosColombiaScraper().search("backend", "Bogotá", pages=1)

        assert len(offers) == 2
        assert all(isinstance(o, JobOfferData) for o in offers)
        titles = [o.title for o in offers]
        assert "Backend Developer Python" in titles
        assert "Frontend Dev React" in titles
        for o in offers:
            assert o.portal == "trabajos_co"
            assert o.url.startswith("https://colombia.trabajos.com/")

    def test_extracts_keywords_from_listing(self, mocker):
        """No hacemos GET al detail (caro). Las keywords salen del title +
        snippet del card via extract_keywords."""
        mocker.patch(
            "jobs.adapters.scrapers.trabajos_co.requests.get",
            return_value=_mock_response(LISTING_HTML),
        )

        offers = TrabajosColombiaScraper().search("backend", "Bogotá", pages=1)
        first = next(o for o in offers if "Backend" in o.title)
        kw_set = set(first.keywords.split(", "))
        assert {"python", "django", "postgresql"}.issubset(kw_set)

    def test_company_and_location_extracted(self, mocker):
        mocker.patch(
            "jobs.adapters.scrapers.trabajos_co.requests.get",
            return_value=_mock_response(LISTING_HTML),
        )
        offers = TrabajosColombiaScraper().search("backend", "Bogotá", pages=1)
        backend = next(o for o in offers if "Backend" in o.title)
        assert backend.company == "Acme Corp"
        assert "Bogotá" in backend.location

    def test_old_offer_is_filtered(self, mocker):
        """`Hace 30 días` en el texto del card → se filtra por
        MAX_OFFER_AGE_DAYS (7 días)."""
        mocker.patch(
            "jobs.adapters.scrapers.trabajos_co.requests.get",
            return_value=_mock_response(LISTING_HTML_OLD_OFFER),
        )
        offers = TrabajosColombiaScraper().search("anything", "Cali", pages=1)
        assert offers == []

    def test_broken_cards_do_not_abort_page(self, mocker):
        mocker.patch(
            "jobs.adapters.scrapers.trabajos_co.requests.get",
            return_value=_mock_response(LISTING_HTML_BAD_CARD),
        )
        offers = TrabajosColombiaScraper().search("anything", "Bogotá", pages=1)
        assert len(offers) == 1
        assert offers[0].title == "Oferta Buena"

    def test_network_error_returns_empty(self, mocker):
        import requests

        mocker.patch(
            "jobs.adapters.scrapers.trabajos_co.requests.get",
            side_effect=requests.ConnectionError("timeout"),
        )
        offers = TrabajosColombiaScraper().search("anything", "Bogotá", pages=1)
        assert offers == []

    def test_pagination_uses_DESDE_offset(self, mocker):
        """pages=2 → 2 requests, segundo con DESDE=41 (offset 1-indexed)."""
        calls: list[str] = []

        def fake_get(url, **kwargs):
            calls.append(url)
            return _mock_response("<html><body></body></html>")

        mocker.patch(
            "jobs.adapters.scrapers.trabajos_co.requests.get", side_effect=fake_get
        )
        TrabajosColombiaScraper().search("python", "Bogotá", pages=2)
        assert len(calls) == 2
        assert "DESDE=1" in calls[0]
        assert "DESDE=41" in calls[1]
        assert "CADENA=python" in calls[0]
        assert "IDPAIS=40" in calls[0]

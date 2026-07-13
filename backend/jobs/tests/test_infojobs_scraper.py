"""Tests del scraper InfoJobs con HTML fixtures (sin red).

Estructura del HTML capturada de producción el 2026-07-13 vía curl:
  * Cards en `<li class="ij-OfferList-offerCardItem">`.
  * Título en `.ij-OfferCardContent-description-title-link` (span/a).
  * Link a detalle en `a.ij-OfferCardContent-description-link[href]`
    con href protocol-less (`//www.infojobs.net/...`).
  * Empresa en `.ij-OfferCardContent-description-subtitle-link`.
  * Meta items en `.ij-OfferCardContent-description-list-item` — orden
    empírico: [ciudad, modalidad, fecha, contrato, jornada, salario].
"""

from unittest.mock import Mock

import pytest

from jobs.adapters.scrapers.base import ScraperError
from jobs.adapters.scrapers.infojobs import InfoJobsScraper


_LISTING_HTML = """
<html><body>
  <ul>
    <li class="ij-OfferList-offerCardItem">
      <div class="ij-OfferCardContent">
        <span class="ij-OfferCardContent-description-title-link">
          BECA IT - Desarrollo ERP
        </span>
        <a class="ij-OfferCardContent-description-link"
           href="//www.infojobs.net/zaragoza/beca-it/of-i706?ori=1">Ver oferta</a>
        <a class="ij-OfferCardContent-description-subtitle-link"
           href="https://fersa.ofertas-trabajo.infojobs.net">FERSA BEARINGS SA</a>
        <ul>
          <li class="ij-OfferCardContent-description-list-item">Zaragoza</li>
          <li class="ij-OfferCardContent-description-list-item">Presencial</li>
          <li class="ij-OfferCardContent-description-list-item">08 jun</li>
          <li class="ij-OfferCardContent-description-list-item">Contrato formativo</li>
          <li class="ij-OfferCardContent-description-list-item">Jornada completa</li>
          <li class="ij-OfferCardContent-description-list-item">1050€-1100€ Bruto/mes</li>
        </ul>
      </div>
    </li>
    <li class="ij-OfferList-offerCardItem">
      <div class="ij-OfferCardContent">
        <span class="ij-OfferCardContent-description-title-link">
          Full Stack Developer Remote
        </span>
        <a class="ij-OfferCardContent-description-link"
           href="//www.infojobs.net/madrid/full-stack/of-i999">Ver oferta</a>
        <a class="ij-OfferCardContent-description-subtitle-link">Acme España</a>
        <ul>
          <li class="ij-OfferCardContent-description-list-item">Madrid</li>
          <li class="ij-OfferCardContent-description-list-item">Remoto</li>
          <li class="ij-OfferCardContent-description-list-item">10 jul</li>
        </ul>
      </div>
    </li>
  </ul>
</body></html>
"""


_LISTING_EMPTY_HTML = """
<html><body>
  <div>No hay ofertas para tu búsqueda.</div>
</body></html>
"""


_LISTING_HTML_WITH_BAD_CARD = """
<html><body>
  <ul>
    <li class="ij-OfferList-offerCardItem">
      <!-- Sin título — la card se descarta silenciosamente -->
      <a class="ij-OfferCardContent-description-link" href="//www.infojobs.net/bad"></a>
    </li>
    <li class="ij-OfferList-offerCardItem">
      <span class="ij-OfferCardContent-description-title-link">Backend Developer</span>
      <a class="ij-OfferCardContent-description-link"
         href="//www.infojobs.net/barcelona/backend/of-i123">Ver</a>
      <a class="ij-OfferCardContent-description-subtitle-link">Good Co</a>
      <ul>
        <li class="ij-OfferCardContent-description-list-item">Barcelona</li>
      </ul>
    </li>
  </ul>
</body></html>
"""


def _mock_response(html: str, status: int = 200) -> Mock:
    r = Mock()
    r.status_code = status
    r.text = html
    return r


@pytest.mark.unit
class TestInfoJobsScraperSearch:
    def test_empty_query_raises(self):
        scraper = InfoJobsScraper()
        with pytest.raises(ScraperError):
            scraper.search("", "")

    def test_parses_two_offers_from_listing(self, monkeypatch):
        scraper = InfoJobsScraper()
        monkeypatch.setattr(
            "jobs.adapters.scrapers.infojobs.requests.get",
            lambda *a, **kw: _mock_response(_LISTING_HTML),
        )
        # `pages=1` — con solo 1 página, la 2da búsqueda no dispara.
        offers = scraper.search("desarrollador", "Madrid", pages=1)
        assert len(offers) == 2
        assert offers[0].title == "BECA IT - Desarrollo ERP"
        assert offers[0].company == "FERSA BEARINGS SA"
        assert offers[0].portal == "infojobs"
        # URL protocol-less debe volverse https://.
        assert offers[0].url.startswith("https://www.infojobs.net/")

    def test_location_includes_espana_suffix(self, monkeypatch):
        """La ciudad de la meta se anota con `, España` para que
        `extract_country` la clasifique como ES sin ambigüedad."""
        scraper = InfoJobsScraper()
        monkeypatch.setattr(
            "jobs.adapters.scrapers.infojobs.requests.get",
            lambda *a, **kw: _mock_response(_LISTING_HTML),
        )
        offers = scraper.search("desarrollador", "Madrid", pages=1)
        assert offers[0].location == "Zaragoza, España"
        assert offers[1].location == "Madrid, España"

    def test_summary_includes_company_and_meta(self, monkeypatch):
        scraper = InfoJobsScraper()
        monkeypatch.setattr(
            "jobs.adapters.scrapers.infojobs.requests.get",
            lambda *a, **kw: _mock_response(_LISTING_HTML),
        )
        offers = scraper.search("desarrollador", "Madrid", pages=1)
        summary = offers[0].summary
        assert "FERSA BEARINGS SA" in summary
        assert "Presencial" in summary
        assert "Contrato formativo" in summary

    def test_bad_card_does_not_break_page(self, monkeypatch):
        scraper = InfoJobsScraper()
        monkeypatch.setattr(
            "jobs.adapters.scrapers.infojobs.requests.get",
            lambda *a, **kw: _mock_response(_LISTING_HTML_WITH_BAD_CARD),
        )
        offers = scraper.search("dev", "Barcelona", pages=1)
        # Solo la card buena queda; la sin título se descarta.
        assert len(offers) == 1
        assert offers[0].title == "Backend Developer"

    def test_dedupes_urls_across_pages(self, monkeypatch):
        """Si las páginas 1 y 2 devuelven la misma URL, la 2da se
        descarta y el scraper termina temprano (new_count == 0)."""
        scraper = InfoJobsScraper()
        monkeypatch.setattr(
            "jobs.adapters.scrapers.infojobs.requests.get",
            lambda *a, **kw: _mock_response(_LISTING_HTML),
        )
        offers = scraper.search("dev", "Madrid", pages=3)
        # 2 URLs únicas independientemente de cuántas páginas pedimos.
        assert len(offers) == 2

    def test_empty_listing_returns_empty(self, monkeypatch):
        scraper = InfoJobsScraper()
        monkeypatch.setattr(
            "jobs.adapters.scrapers.infojobs.requests.get",
            lambda *a, **kw: _mock_response(_LISTING_EMPTY_HTML),
        )
        assert scraper.search("dev", "Madrid", pages=1) == []

    def test_http_error_returns_empty(self, monkeypatch):
        scraper = InfoJobsScraper()
        monkeypatch.setattr(
            "jobs.adapters.scrapers.infojobs.requests.get",
            lambda *a, **kw: _mock_response("", status=503),
        )
        # 5xx no debe explotar — degradamos silenciosamente para que el
        # scrape multi-portal no se aborte.
        assert scraper.search("dev", "Madrid", pages=1) == []

    def test_network_error_returns_empty(self, monkeypatch):
        import requests as req

        scraper = InfoJobsScraper()

        def raise_conn(*a, **kw):
            raise req.ConnectionError("dns fail")

        monkeypatch.setattr(
            "jobs.adapters.scrapers.infojobs.requests.get", raise_conn
        )
        assert scraper.search("dev", "Madrid", pages=1) == []

"""Tests del scraper Computrabajo con HTML fixtures (sin red).

Mockeamos `requests.get` para controlar el HTML que el parser recibe.
Los tests cubren:
  - El parser de la lista (cards)
  - El parser del detalle (descripción + keywords)
  - Tarjetas rotas no abortan la página
  - Errores de red devuelven lista vacía (no excepciones)
"""
from unittest.mock import Mock

import pytest

from jobs.adapters.scrapers.base import JobOfferData, ScraperError
from jobs.adapters.scrapers.computrabajo import ComputrabajoScraper


LISTING_HTML = """
<html><body>
  <article class="box_offer">
    <a class="js-o-link" href="/oferta-de-trabajo-test-1">Backend Developer</a>
    <a class="fc_base t_ellipsis">Acme Corp</a>
    <p>No usado</p>
    <p>Bogotá, Cundinamarca</p>
  </article>
  <article class="box_offer">
    <a class="js-o-link" href="/oferta-de-trabajo-test-2">Frontend Dev</a>
    <a class="fc_base t_ellipsis">Initech</a>
    <p>No usado</p>
    <p>Medellín, Antioquia</p>
  </article>
</body></html>
"""

LISTING_HTML_WITH_BAD_CARD = """
<html><body>
  <article class="box_offer">
    <!-- Sin link → la card es ignorada, no rompe la página -->
    <a class="fc_base t_ellipsis">Sin nombre</a>
  </article>
  <article class="box_offer">
    <a class="js-o-link" href="/oferta-buena">Senior Dev</a>
    <a class="fc_base t_ellipsis">Good Co</a>
    <p>x</p>
    <p>Cali</p>
  </article>
</body></html>
"""

DETAIL_HTML = """
<html><body>
  <h3>Descripción del puesto</h3>
  <p>Buscamos un desarrollador con experiencia en Python, Django y PostgreSQL.</p>
  <p>Requisitos: experiencia con React.js y Node.js.</p>
  <h3>Beneficios</h3>
  <p>Trabajo remoto</p>
</body></html>
"""

DETAIL_HTML_NO_DESCRIPTION = """
<html><body><p>Página sin la sección descripción</p></body></html>
"""


def _mock_response(html: str) -> Mock:
    response = Mock()
    response.content = html.encode('utf-8')
    return response


@pytest.mark.unit
class TestComputrabajoSearch:
    def test_search_requires_query_and_location(self):
        scraper = ComputrabajoScraper()
        with pytest.raises(ScraperError):
            scraper.search('', 'Bogotá')
        with pytest.raises(ScraperError):
            scraper.search('Backend', '')

    def test_parses_two_offers_from_listing(self, mocker):
        # Listing devuelve LISTING_HTML, detail devuelve DETAIL_HTML para todas
        def fake_get(url, **kwargs):
            if 'trabajo-de-' in url:
                return _mock_response(LISTING_HTML)
            return _mock_response(DETAIL_HTML)

        mocker.patch('jobs.adapters.scrapers.computrabajo.requests.get', side_effect=fake_get)

        offers = ComputrabajoScraper().search('Backend Developer', 'Bogotá', pages=1)

        assert len(offers) == 2
        assert all(isinstance(o, JobOfferData) for o in offers)
        titles = [o.title for o in offers]
        assert 'Backend Developer' in titles
        assert 'Frontend Dev' in titles
        # URL absoluta basada en BASE_URL de Computrabajo
        for o in offers:
            assert o.url.startswith('https://co.computrabajo.com/')

    def test_extracts_keywords_from_detail(self, mocker):
        def fake_get(url, **kwargs):
            if 'trabajo-de-' in url:
                return _mock_response(LISTING_HTML)
            return _mock_response(DETAIL_HTML)

        mocker.patch('jobs.adapters.scrapers.computrabajo.requests.get', side_effect=fake_get)

        offers = ComputrabajoScraper().search('Backend Developer', 'Bogotá', pages=1)
        # Cada oferta hace fetch del detail → debe tener keywords extraídas
        kw_set = set(offers[0].keywords.split(', '))
        # `react.js` se normaliza a `react`, `node.js` a `node`
        assert {'python', 'django', 'postgresql', 'react', 'node'}.issubset(kw_set)

    def test_broken_cards_do_not_abort_page(self, mocker):
        def fake_get(url, **kwargs):
            if 'trabajo-de-' in url:
                return _mock_response(LISTING_HTML_WITH_BAD_CARD)
            return _mock_response(DETAIL_HTML)

        mocker.patch('jobs.adapters.scrapers.computrabajo.requests.get', side_effect=fake_get)

        offers = ComputrabajoScraper().search('Dev', 'Cali', pages=1)
        # La card sin link se ignora; la buena se parsea
        assert len(offers) == 1
        assert offers[0].title == 'Senior Dev'

    def test_network_error_returns_empty_list(self, mocker):
        import requests
        mocker.patch(
            'jobs.adapters.scrapers.computrabajo.requests.get',
            side_effect=requests.ConnectionError('timeout'),
        )

        offers = ComputrabajoScraper().search('Anything', 'Anywhere', pages=1)
        assert offers == []

    def test_detail_without_description_returns_empty_summary(self, mocker):
        def fake_get(url, **kwargs):
            if 'trabajo-de-' in url:
                return _mock_response(LISTING_HTML)
            return _mock_response(DETAIL_HTML_NO_DESCRIPTION)

        mocker.patch('jobs.adapters.scrapers.computrabajo.requests.get', side_effect=fake_get)

        offers = ComputrabajoScraper().search('Backend', 'Bogotá', pages=1)
        assert all(o.summary == '' for o in offers)
        assert all(o.keywords == '' for o in offers)

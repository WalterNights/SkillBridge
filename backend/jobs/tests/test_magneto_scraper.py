"""Tests del parser de Magneto con HTML fijo (sin Playwright ni red)."""

import pytest

from jobs.adapters.scrapers.magneto import MagnetoScraper

LISTING_HTML = """
<html><body>
  <nav>
    <a href="/co/trabajos/empleos-por-ciudades">Empleos por ciudades</a>
    <a href="/co/trabajos/buscar?title=dev">Buscar</a>
    <a href="/co/trabajos/">Trabajos</a>
  </nav>
  <a href="/co/trabajos/desarrollador-backend-python-12345">
    <h3>Desarrollador Backend Python</h3>
    <span>Acme SAS</span><span>Bogotá</span>
  </a>
  <a href="https://www.magneto365.com/co/trabajos/analista-de-datos-998?ref=x">
    <h3>Analista de Datos</h3>
  </a>
</body></html>
"""


@pytest.mark.unit
def test_parser_keeps_only_offer_links():
    offers = MagnetoScraper()._parse_listing(LISTING_HTML)
    urls = [o.url for o in offers]
    assert urls == [
        "https://www.magneto365.com/co/trabajos/desarrollador-backend-python-12345",
        "https://www.magneto365.com/co/trabajos/analista-de-datos-998",
    ]
    assert offers[0].title == "Desarrollador Backend Python"

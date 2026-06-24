"""Tests del scraper Trabajando.com (sitemap-based + JSON-LD).

Mismo patrón que test_hireline_scraper. Cubre:
  - Sitemap malformado → []
  - Filtro lastmod >7 días
  - Parsing del JSON-LD con jobLocation con streetAddress (caso típico
    de Trabajando.com — no usa addressLocality directamente).
  - Error de red → no aborta el resto
"""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest

from jobs.adapters.scrapers.trabajando import TrabajandoScraper


def _today_iso() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _days_ago_iso(days: int) -> str:
    return (datetime.now(timezone.utc).date() - timedelta(days=days)).isoformat()


def _sitemap_xml(entries: list[tuple[str, str]]) -> bytes:
    items = "".join(
        f"<url><loc>{loc}</loc><lastmod>{mod}</lastmod></url>"
        for loc, mod in entries
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"{items}"
        "</urlset>"
    ).encode("utf-8")


def _detail_html(job_posting: dict | None) -> bytes:
    if job_posting is None:
        return b"<html><body><h1>No JSON-LD</h1></body></html>"
    return (
        "<html><body>"
        '<script type="application/ld+json">'
        + json.dumps(job_posting)
        + "</script>"
        "</body></html>"
    ).encode("utf-8")


def _mock_response(content: bytes, status: int = 200) -> Mock:
    response = Mock()
    response.content = content
    response.status_code = status
    response.raise_for_status = Mock()
    return response


@pytest.mark.unit
class TestTrabajandoScraper:
    def test_malformed_sitemap_returns_empty(self, mocker):
        mocker.patch(
            "jobs.adapters.scrapers.trabajando.requests.get",
            return_value=_mock_response(b"not xml"),
        )
        offers = TrabajandoScraper().search("any", "Chile", pages=1)
        assert offers == []

    def test_parses_job_posting_with_street_address(self, mocker):
        """Trabajando.com pone la ubicación en `streetAddress` ('comuna,
        ciudad, país'), no en addressLocality. Verificamos que el
        parser lo agarra."""
        jp = {
            "@context": "https://schema.org/",
            "@type": "JobPosting",
            "title": "Backend Engineer",
            "description": "<p>Backend con Python y Django</p>",
            "hiringOrganization": {"name": "Acme CL"},
            "jobLocation": {
                "@type": "Place",
                "address": {
                    "@type": "PostalAddress",
                    "streetAddress": "Providencia, santiago, Chile",
                    "addressLocality": "Santiago",
                    "addressCountry": "CL",
                },
            },
        }
        sm = _sitemap_xml([("https://www.trabajando.cl/trabajo/1-be", _today_iso())])

        def fake_get(url, **kwargs):
            if "sitemap-ofertas.xml" in url:
                return _mock_response(sm)
            return _mock_response(_detail_html(jp))

        mocker.patch("jobs.adapters.scrapers.trabajando.requests.get", side_effect=fake_get)

        offers = TrabajandoScraper().search("any", "Chile", pages=1)
        assert len(offers) >= 1
        first = offers[0]
        assert first.title == "Backend Engineer"
        assert first.company == "Acme CL"
        assert "santiago" in first.location.lower()
        assert "<p>" not in first.summary
        assert first.portal == "trabajando"
        assert "python" in first.keywords
        assert "django" in first.keywords

    def test_old_entries_filtered(self, mocker):
        sm = _sitemap_xml(
            [
                ("https://www.trabajando.cl/trabajo/old", _days_ago_iso(30)),
                ("https://www.trabajando.cl/trabajo/fresh", _today_iso()),
            ]
        )
        fresh_jp = {
            "@context": "https://schema.org/",
            "@type": "JobPosting",
            "title": "Fresh",
            "description": "Python",
            "hiringOrganization": {"name": "Co"},
        }

        def fake_get(url, **kwargs):
            if "sitemap-ofertas.xml" in url:
                return _mock_response(sm)
            return _mock_response(_detail_html(fresh_jp))

        mocker.patch("jobs.adapters.scrapers.trabajando.requests.get", side_effect=fake_get)
        offers = TrabajandoScraper().search("any", "Chile", pages=1)
        assert all(o.title == "Fresh" for o in offers)

    def test_network_error_returns_empty(self, mocker):
        import requests

        mocker.patch(
            "jobs.adapters.scrapers.trabajando.requests.get",
            side_effect=requests.ConnectionError("timeout"),
        )
        offers = TrabajandoScraper().search("any", "Chile", pages=1)
        assert offers == []

    def test_detail_without_json_ld_is_skipped(self, mocker):
        sm = _sitemap_xml([("https://www.trabajando.cl/trabajo/x", _today_iso())])

        def fake_get(url, **kwargs):
            if "sitemap-ofertas.xml" in url:
                return _mock_response(sm)
            return _mock_response(_detail_html(None))

        mocker.patch("jobs.adapters.scrapers.trabajando.requests.get", side_effect=fake_get)
        offers = TrabajandoScraper().search("any", "Chile", pages=1)
        assert offers == []

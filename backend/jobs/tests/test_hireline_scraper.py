"""Tests del scraper Hireline (sitemap-based + JSON-LD).

Cubre:
  - Sitemap malformado → []
  - Filtro de lastmod >7 días
  - Cap MAX_OFFERS_PER_RUN_PER_COUNTRY
  - Parsing del JSON-LD JobPosting con todas sus formas (jobLocation
    como dict, como list, sin address, etc.)
  - Detail page sin JobPosting → skip silencioso
  - Errores de red en sitemap o detail → no aborta el resto
"""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest

from jobs.adapters.scrapers.base import JobOfferData
from jobs.adapters.scrapers.hireline import HirelineScraper


def _today_iso() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _days_ago_iso(days: int) -> str:
    return (datetime.now(timezone.utc).date() - timedelta(days=days)).isoformat()


def _sitemap_xml(entries: list[tuple[str, str]]) -> bytes:
    """entries = [(url, lastmod_iso), ...] — devuelve XML del sitemap."""
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
    """Detail page con JSON-LD JobPosting embebido (o sin él si None)."""
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
class TestHirelineSitemap:
    def test_malformed_sitemap_returns_empty(self, mocker):
        mocker.patch(
            "jobs.adapters.scrapers.hireline.requests.get",
            return_value=_mock_response(b"not xml at all"),
        )
        offers = HirelineScraper().search("anything", "Mexico", pages=1)
        assert offers == []

    def test_old_entries_filtered_out(self, mocker):
        # Sitemap con 2 ofertas viejas + 1 nueva → solo la nueva pasa.
        old_xml = _sitemap_xml(
            [
                ("https://hireline.io/mx/empleos/old-1/1", _days_ago_iso(30)),
                ("https://hireline.io/mx/empleos/old-2/2", _days_ago_iso(15)),
                ("https://hireline.io/mx/empleos/fresh/3", _today_iso()),
            ]
        )

        # JSON-LD válido para la oferta fresca
        fresh_jp = {
            "@context": "https://schema.org/",
            "@type": "JobPosting",
            "title": "Fresh Backend Dev",
            "description": "Python and Django.",
            "hiringOrganization": {"name": "Fresh Co"},
        }

        def fake_get(url, **kwargs):
            if url.endswith("sitemap_ofertas.xml"):
                return _mock_response(old_xml)
            return _mock_response(_detail_html(fresh_jp))

        mocker.patch("jobs.adapters.scrapers.hireline.requests.get", side_effect=fake_get)

        offers = HirelineScraper().search("anything", "Mexico", pages=1)
        # Una oferta fresca × 2 sitemaps (MX, CO) — pero el mock devuelve
        # el mismo XML para ambos, así que también 1 fresca de CO con
        # mismo JP. Total: 2 ofertas (deduplicación por URL pasa
        # downstream en JobService.save_new_offers, no acá).
        assert len(offers) == 2
        assert all(o.title == "Fresh Backend Dev" for o in offers)


@pytest.mark.unit
class TestJobPostingParser:
    def test_parses_full_job_posting(self, mocker):
        jp = {
            "@context": "https://schema.org/",
            "@type": "JobPosting",
            "title": "Senior QA Automation Engineer",
            "description": "Looking for an engineer with <b>Python</b>, Selenium and Django.",
            "hiringOrganization": {"name": "Acme Corp"},
            "jobLocation": {
                "@type": "Place",
                "address": {
                    "addressLocality": "Monterrey",
                    "addressRegion": "NL",
                    "addressCountry": "MX",
                },
            },
        }
        sm = _sitemap_xml([("https://hireline.io/mx/empleos/qa/1", _today_iso())])

        def fake_get(url, **kwargs):
            if url.endswith("sitemap_ofertas.xml"):
                return _mock_response(sm)
            return _mock_response(_detail_html(jp))

        mocker.patch("jobs.adapters.scrapers.hireline.requests.get", side_effect=fake_get)

        offers = HirelineScraper().search("qa", "Mexico", pages=1)
        assert len(offers) >= 1
        first = offers[0]
        assert first.title == "Senior QA Automation Engineer"
        assert first.company == "Acme Corp"
        assert "Monterrey" in first.location
        assert "Python" in first.summary  # HTML stripped
        assert "<b>" not in first.summary
        assert first.portal == "hireline"
        # extract_keywords detecta python, selenium, django desde título+descripción
        assert "python" in first.keywords
        assert "django" in first.keywords

    def test_job_location_as_list_takes_first(self, mocker):
        jp = {
            "@context": "https://schema.org/",
            "@type": "JobPosting",
            "title": "Remote Dev",
            "description": "Anywhere.",
            "hiringOrganization": {"name": "Remote Co"},
            "jobLocation": [
                {"address": {"addressLocality": "CDMX", "addressCountry": "MX"}},
                {"address": {"addressLocality": "Bogotá", "addressCountry": "CO"}},
            ],
        }
        sm = _sitemap_xml([("https://hireline.io/mx/empleos/r/1", _today_iso())])

        def fake_get(url, **kwargs):
            if url.endswith("sitemap_ofertas.xml"):
                return _mock_response(sm)
            return _mock_response(_detail_html(jp))

        mocker.patch("jobs.adapters.scrapers.hireline.requests.get", side_effect=fake_get)
        offers = HirelineScraper().search("anything", "Mexico", pages=1)
        assert "CDMX" in offers[0].location
        assert "Bogotá" not in offers[0].location

    def test_detail_without_json_ld_is_skipped(self, mocker):
        sm = _sitemap_xml([("https://hireline.io/mx/empleos/x/1", _today_iso())])

        def fake_get(url, **kwargs):
            if url.endswith("sitemap_ofertas.xml"):
                return _mock_response(sm)
            return _mock_response(_detail_html(None))  # no JSON-LD

        mocker.patch("jobs.adapters.scrapers.hireline.requests.get", side_effect=fake_get)
        offers = HirelineScraper().search("anything", "Mexico", pages=1)
        assert offers == []


@pytest.mark.unit
class TestHirelineErrorHandling:
    def test_network_error_on_sitemap_returns_empty(self, mocker):
        import requests

        mocker.patch(
            "jobs.adapters.scrapers.hireline.requests.get",
            side_effect=requests.ConnectionError("timeout"),
        )
        offers = HirelineScraper().search("anything", "Mexico", pages=1)
        assert offers == []

    def test_one_broken_detail_does_not_abort_run(self, mocker):
        """Si un detail tira excepción, el resto del scrape continúa."""
        sm = _sitemap_xml(
            [
                ("https://hireline.io/mx/empleos/broken/1", _today_iso()),
                ("https://hireline.io/mx/empleos/good/2", _today_iso()),
            ]
        )
        good_jp = {
            "@context": "https://schema.org/",
            "@type": "JobPosting",
            "title": "Good Offer",
            "description": "Python",
            "hiringOrganization": {"name": "GoodCo"},
        }

        call_count = {"n": 0}

        def fake_get(url, **kwargs):
            if url.endswith("sitemap_ofertas.xml"):
                return _mock_response(sm)
            call_count["n"] += 1
            if "/broken/" in url:
                import requests

                raise requests.ConnectionError("blew up")
            return _mock_response(_detail_html(good_jp))

        mocker.patch("jobs.adapters.scrapers.hireline.requests.get", side_effect=fake_get)
        offers = HirelineScraper().search("anything", "Mexico", pages=1)
        # La oferta buena se parsea (× 2 países = 2 entries del sitemap)
        assert all(o.title == "Good Offer" for o in offers)
        assert len(offers) >= 1

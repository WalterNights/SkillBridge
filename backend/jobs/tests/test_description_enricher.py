"""Tests del enriquecimiento de descripciones con relleno.

Cubre:
- Fuentes: LinkedIn (guest API), Torre (API), JSON-LD genérico.
- Qué se intenta: solo rellenos, no portales sin acceso, una sola vez.
- `enrich_offer` nunca empeora el summary.
- On-demand al abrir el detalle y lote nocturno.
- `save_new_offers` reemplaza un relleno por una descripción más larga.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
import requests

from jobs.adapters.scrapers.base import JobOfferData
from jobs.models import JobOffer
from jobs.services.description_enricher import (
    can_enrich,
    enrich_offer,
    fetch_full_description,
)
from jobs.services.job_service import JobService
from jobs.tasks import enrich_stub_descriptions

LONG_TEXT = "Responsabilidades del cargo. " * 30  # ~870 caracteres


@pytest.fixture(autouse=True)
def _public_dns():
    """Los tests usan hosts ficticios: simulamos que resuelven a IPs públicas
    para que el chequeo SSRF de `safe_get` no los descarte."""
    with patch("jobs.adapters.scrapers.base._host_is_public", return_value=True):
        yield


class _Resp:
    def __init__(self, status_code=200, text="", payload=None):
        self.status_code = status_code
        self.text = text
        self._payload = payload

    def json(self):
        return self._payload


def _offer(**overrides) -> JobOffer:
    base = {
        "title": "Backend Developer",
        "company": "Acme",
        "location": "Bogotá",
        "summary": "Backend Developer en Acme — Bogotá",
        "keywords": "python",
        "portal": "linkedin",
        "url": "https://co.linkedin.com/jobs/view/backend-developer-at-acme-4430753798",
    }
    base.update(overrides)
    return JobOffer.objects.create(**base)


@pytest.mark.unit
class TestFetchFullDescription:
    def test_linkedin_uses_guest_posting_api(self):
        html = f'<div class="show-more-less-html__markup"><p>{LONG_TEXT}</p></div>'
        with patch(
            "jobs.services.description_enricher.requests.get", return_value=_Resp(200, html)
        ) as get:
            text = fetch_full_description(
                "https://co.linkedin.com/jobs/view/dev-at-acme-4430753798", timeout=5
            )
        assert text.startswith("Responsabilidades")
        assert get.call_args.args[0].endswith("/jobPosting/4430753798")

    def test_torre_joins_details(self):
        payload = {"details": [{"content": "Responsabilidades: X"}, {"content": "Requisitos: Y"}]}
        with patch(
            "jobs.services.description_enricher.requests.get",
            return_value=_Resp(200, payload=payload),
        ) as get:
            text = fetch_full_description("https://torre.ai/jobs/OdvYo3bw-ux-designer", timeout=5)
        assert text == "Responsabilidades: X\n\nRequisitos: Y"
        assert get.call_args.args[0].endswith("/opportunities/OdvYo3bw")

    def test_generic_reads_json_ld_job_posting_in_graph(self):
        html = (
            '<script type="application/ld+json">{"@graph": [{"@type": "WebSite"},'
            ' {"@type": "JobPosting", "description": "<p>Funciones del cargo</p>"}]}</script>'
        )
        with patch(
            "jobs.services.description_enricher.requests.get", return_value=_Resp(200, html)
        ):
            assert (
                fetch_full_description("https://example.com/oferta/1", timeout=5)
                == "Funciones del cargo"
            )

    def test_network_error_returns_none(self):
        with patch(
            "jobs.services.description_enricher.requests.get", side_effect=requests.Timeout("slow")
        ):
            assert fetch_full_description("https://example.com/oferta/1", timeout=5) is None


@pytest.mark.integration
@pytest.mark.django_db
class TestEnrichOffer:
    def test_can_enrich_rules(self):
        assert can_enrich(_offer()) is True
        assert can_enrich(_offer(url="https://x.com/1", summary=LONG_TEXT)) is False
        assert can_enrich(_offer(url="https://x.com/2", portal="meli")) is False

    def test_replaces_stub_and_marks_fetched(self):
        offer = _offer()
        with patch(
            "jobs.services.description_enricher.fetch_full_description", return_value=LONG_TEXT
        ):
            assert enrich_offer(offer, timeout=5) is True
        offer.refresh_from_db()
        assert offer.summary == LONG_TEXT
        assert offer.description_fetched_at is not None
        assert can_enrich(offer) is False

    def test_failed_fetch_keeps_stub_but_does_not_retry(self):
        offer = _offer()
        with patch("jobs.services.description_enricher.fetch_full_description", return_value=None):
            assert enrich_offer(offer, timeout=5) is False
        offer.refresh_from_db()
        assert offer.summary == "Backend Developer en Acme — Bogotá"
        assert offer.description_fetched_at is not None

    def test_detail_enriches_on_demand(self, authed_client, settings):
        settings.JOBS_ONDEMAND_FETCH = True
        offer = _offer(last_checked_at="2099-01-01T00:00:00Z")  # sin probe de disponibilidad
        with patch("jobs.views.enrich_offer", wraps=lambda o, timeout: _set_summary(o)) as enrich:
            body = authed_client.get(f"/api/jobs/jobs/{offer.id}/").json()
        enrich.assert_called_once()
        assert body["summary"] == LONG_TEXT
        assert body["summary_is_partial"] is False

    def test_detail_flags_partial_summary_for_unfetchable_portal(self, authed_client):
        offer = _offer(url="https://mercadolibre.eightfold.ai/careers/job/1", portal="meli")
        body = authed_client.get(f"/api/jobs/jobs/{offer.id}/").json()
        assert body["summary_is_partial"] is True

    def test_nightly_batch_skips_unfetchable_and_long(self):
        stub = _offer()
        _offer(url="https://x.com/meli", portal="meli")
        _offer(url="https://x.com/long", summary=LONG_TEXT)
        with (
            patch(
                "jobs.services.description_enricher.fetch_full_description", return_value=LONG_TEXT
            ),
            patch("time.sleep"),
        ):
            result = enrich_stub_descriptions()
        assert result == {"status": "success", "attempted": 1, "improved": 1}
        stub.refresh_from_db()
        assert stub.summary == LONG_TEXT


def _set_summary(offer: JobOffer) -> bool:
    offer.summary = LONG_TEXT
    offer.save(update_fields=["summary"])
    return True


@pytest.mark.integration
@pytest.mark.django_db
def test_rescrape_with_longer_summary_replaces_stub():
    data = JobOfferData(
        title="Backend Developer",
        company="Acme",
        location="Bogotá",
        summary="Backend Developer en Acme — Bogotá",
        url="https://example.com/ofertas/777",
        keywords="python",
        portal="computrabajo",
    )
    JobService.save_new_offers([data])
    JobService.save_new_offers([JobOfferData(**{**data.__dict__, "summary": LONG_TEXT})])
    JobService.save_new_offers([JobOfferData(**{**data.__dict__, "summary": "corto"})])

    offer = JobOffer.objects.get(url__contains="/ofertas/777")
    assert offer.summary == LONG_TEXT

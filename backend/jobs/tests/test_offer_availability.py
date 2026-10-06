"""Tests de disponibilidad de ofertas (fecha de cierre + verificación).

Cubre:
- `parse_iso_datetime`: formatos de fecha de los portales.
- Probe: marcadores genéricos, `validThrough` vencido, redirect a listado.
- Cron: desactiva por `expires_at` sin pegarle al portal.
- Feed y detalle: ocultan vencidas; verificación on-demand al abrir.
- Reporte "no disponible" dispara la verificación.
- `clean_old_offers` no borra ofertas con postulaciones.
- `save_new_offers` guarda / actualiza `expires_at`.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from applications.models import JobApplication
from jobs.adapters.scrapers.base import JobOfferData, parse_iso_datetime
from jobs.models import JobOffer
from jobs.services.job_service import JobService
from jobs.tasks import _probe_offer, clean_old_offers, verify_active_offers


class _FakeRaw:
    def __init__(self, body: bytes):
        self._body = body

    def read(self, size: int = -1, decode_content: bool = False):
        return self._body if size == -1 else self._body[:size]


class _FakeResponse:
    def __init__(self, status_code=200, body="", url="", history=()):
        self.status_code = status_code
        self.raw = _FakeRaw(body.encode("utf-8"))
        self.url = url
        self.history = list(history)

    def close(self):
        pass


def _make_offer(**overrides) -> JobOffer:
    base = {
        "title": "Backend Developer",
        "company": "Acme",
        "location": "Remote",
        "summary": "Test",
        "keywords": "python",
        "portal": "trabajando",
        "url": "https://example.com/ofertas/123-backend",
        # Descripción ya intentada: estos tests prueban solo disponibilidad,
        # sin que el detalle dispare también el enriquecimiento.
        "description_fetched_at": timezone.now(),
    }
    base.update(overrides)
    return JobOffer.objects.create(**base)


@pytest.mark.unit
class TestParseIsoDatetime:
    def test_date_only_assumes_utc(self):
        assert parse_iso_datetime("2026-10-30") == datetime(2026, 10, 30, tzinfo=UTC)

    def test_z_suffix(self):
        assert parse_iso_datetime("2026-10-30T23:59:59Z").tzinfo is not None

    @pytest.mark.parametrize("raw", [None, "", "   ", "not-a-date", 123])
    def test_invalid_returns_none(self, raw):
        assert parse_iso_datetime(raw) is None


@pytest.mark.unit
class TestProbeSignals:
    def _probe(self, response, url="https://example.com/ofertas/123-backend", portal="meli"):
        with patch("jobs.tasks.requests.get", return_value=response):
            _, is_dead, reason = _probe_offer(1, url, portal)
        return is_dead, reason

    def test_generic_marker_applies_to_any_portal(self):
        html = "<h2>Esta vacante ya no está disponible</h2>"
        assert self._probe(_FakeResponse(200, html)) == (
            True,
            "dead_marker:esta vacante ya no está dispon",
        )

    def test_expired_valid_through_marks_dead(self):
        html = '<script type="application/ld+json">{"validThrough": "2020-01-01"}</script>'
        assert self._probe(_FakeResponse(200, html)) == (True, "expired_valid_through")

    def test_future_valid_through_stays_alive(self):
        future = (timezone.now() + timedelta(days=10)).date().isoformat()
        html = f'{{"validThrough": "{future}"}}'
        assert self._probe(_FakeResponse(200, html)) == (False, "http_200")

    def test_redirect_to_parent_listing_marks_dead(self):
        response = _FakeResponse(
            200, "<html>listado</html>", url="https://example.com/ofertas", history=[object()]
        )
        assert self._probe(response) == (True, "redirect_to_listing")

    def test_redirect_to_home_marks_dead(self):
        response = _FakeResponse(200, "", url="https://example.com/", history=[object()])
        assert self._probe(response) == (True, "redirect_to_listing")

    def test_redirect_to_canonical_url_stays_alive(self):
        response = _FakeResponse(
            200, "", url="https://example.com/ofertas/123-backend-senior", history=[object()]
        )
        assert self._probe(response) == (False, "http_200")

    def test_redirect_to_login_wall_stays_alive(self):
        response = _FakeResponse(
            200, "", url="https://example.com/login?next=x", history=[object()]
        )
        assert self._probe(response) == (False, "http_200")

    def test_403_antibot_stays_alive(self):
        assert self._probe(_FakeResponse(403)) == (False, "http_403")


@pytest.mark.integration
@pytest.mark.django_db
class TestExpiresAt:
    def test_cron_deactivates_expired_without_probing(self):
        expired = _make_offer(expires_at=timezone.now() - timedelta(days=1))
        with patch("jobs.tasks._probe_offer", side_effect=AssertionError("no debe probar")):
            # La única activa vencida se apaga por fecha; no queda nada para probar.
            result = verify_active_offers()
        expired.refresh_from_db()
        assert expired.is_active is False
        assert result["expired"] == 1

    def test_save_new_offers_stores_and_updates_expires_at(self):
        first = timezone.now() + timedelta(days=5)
        later = timezone.now() + timedelta(days=20)
        data = JobOfferData(
            title="Backend Developer",
            company="Acme",
            location="Bogotá",
            summary="Descripción",
            url="https://example.com/ofertas/999",
            keywords="python",
            portal="hireline",
            expires_at=first,
        )
        JobService.save_new_offers([data])
        offer = JobOffer.objects.get(url__contains="/ofertas/999")
        assert offer.expires_at == first

        JobService.save_new_offers([JobOfferData(**{**data.__dict__, "expires_at": later})])
        offer.refresh_from_db()
        assert offer.expires_at == later


@pytest.mark.integration
@pytest.mark.django_db
class TestFeedAndDetail:
    def test_feed_hides_expired_offers(self, authed_client):
        alive = _make_offer(url="https://example.com/ofertas/1")
        _make_offer(
            url="https://example.com/ofertas/2", expires_at=timezone.now() - timedelta(hours=1)
        )
        body = authed_client.get("/api/jobs/jobs/?min_match=0").json()
        results = body["results"] if isinstance(body, dict) else body
        ids = {o["id"] for o in results}
        assert alive.id in ids
        assert len(ids) == 1

    def test_detail_returns_410_when_probe_finds_it_dead(self, authed_client, settings):
        settings.JOBS_ONDEMAND_CHECK = True
        offer = _make_offer()
        with patch("jobs.tasks.requests.get", return_value=_FakeResponse(404)):
            r = authed_client.get(f"/api/jobs/jobs/{offer.id}/")
        assert r.status_code == 410
        assert r.json()["code"] == "offer_unavailable"
        offer.refresh_from_db()
        assert offer.is_active is False

    def test_detail_skips_probe_when_recently_checked(self, authed_client, settings):
        settings.JOBS_ONDEMAND_CHECK = True
        offer = _make_offer(last_checked_at=timezone.now() - timedelta(hours=2))
        with patch("jobs.tasks.requests.get", side_effect=AssertionError("no debe probar")):
            r = authed_client.get(f"/api/jobs/jobs/{offer.id}/")
        assert r.status_code == 200

    def test_detail_alive_updates_last_checked_at(self, authed_client, settings):
        settings.JOBS_ONDEMAND_CHECK = True
        offer = _make_offer()
        with patch("jobs.tasks.requests.get", return_value=_FakeResponse(200, "<h1>Oferta</h1>")):
            r = authed_client.get(f"/api/jobs/jobs/{offer.id}/")
        assert r.status_code == 200
        offer.refresh_from_db()
        assert offer.last_checked_at is not None
        assert offer.is_active is True

    def test_unavailable_report_triggers_verification(
        self, authed_client, settings, django_capture_on_commit_callbacks
    ):
        settings.JOBS_ONDEMAND_CHECK = True
        offer = _make_offer()
        with (
            patch("jobs.tasks.requests.get", return_value=_FakeResponse(410)),
            django_capture_on_commit_callbacks(execute=True),
        ):
            r = authed_client.post(f"/api/jobs/jobs/{offer.id}/ignore/", {"reason": "unavailable"})
        assert r.status_code == 201
        offer.refresh_from_db()
        assert offer.is_active is False


@pytest.mark.integration
@pytest.mark.django_db
class TestCleanOldOffersKeepsApplications:
    def test_offers_with_applications_survive_cleanup(self, user):
        old = timezone.now() - timedelta(days=60)
        applied = _make_offer(url="https://example.com/ofertas/applied")
        orphan = _make_offer(url="https://example.com/ofertas/orphan")
        JobOffer.objects.filter(pk__in=[applied.pk, orphan.pk]).update(created_at=old)
        JobApplication.objects.create(user=user, offer=applied, status="applied")

        result = clean_old_offers(days_old=30)

        assert JobOffer.objects.filter(pk=applied.pk).exists()
        assert JobApplication.objects.filter(offer=applied).exists()
        assert not JobOffer.objects.filter(pk=orphan.pk).exists()
        assert result["offers_deleted"] == 1

"""Tests para `verify_active_offers` task.

Cubre:
- Detección universal 404 / 410 → is_active=False
- Detección por portal (marcador HTML) para Computrabajo
- Falso positivo evitado: 200 sin marcador → sigue viva
- 429/500 y otros errores transitorios → NO marcar como muerta
- Timeout / connection error → NO marcar como muerta
- last_checked_at se actualiza en TODAS las probadas
- Update masivo (una sola query para dead, otra para alive)
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
import requests

from jobs.models import JobOffer
from jobs.tasks import _probe_offer, verify_active_offers


class _FakeResponse:
    """Mock chico de requests.Response — solo lo que _probe_offer toca."""

    def __init__(self, status_code: int = 200, body: str = ""):
        self.status_code = status_code
        self._body = body.encode("utf-8")
        # raw.read() es lo que usa el probe cuando busca marcadores.
        self.raw = _FakeRaw(self._body)

    def close(self):
        pass


class _FakeRaw:
    def __init__(self, body: bytes):
        self._body = body

    def read(self, size: int = -1, decode_content: bool = False):
        if size == -1 or size >= len(self._body):
            return self._body
        return self._body[:size]


# --- Unit tests del probe ---------------------------------------------------


@pytest.mark.unit
class TestProbeOffer:
    def test_404_marks_dead(self):
        with patch("jobs.tasks.requests.get", return_value=_FakeResponse(404)):
            _, is_dead, reason = _probe_offer(1, "https://x", "computrabajo")
        assert is_dead is True
        assert reason == "http_404"

    def test_410_marks_dead(self):
        with patch("jobs.tasks.requests.get", return_value=_FakeResponse(410)):
            _, is_dead, reason = _probe_offer(1, "https://x", "linkedin")
        assert is_dead is True
        assert reason == "http_410"

    def test_computrabajo_200_with_dead_marker_marks_dead(self):
        """Caso real reportado por el user: Computrabajo devuelve 200 con
        'Esta oferta ya no está disponible' en el HTML."""
        html = "<html><body>Esta oferta ya no está disponible.</body></html>"
        with patch("jobs.tasks.requests.get", return_value=_FakeResponse(200, html)):
            _, is_dead, reason = _probe_offer(1, "https://ct", "computrabajo")
        assert is_dead is True
        assert reason.startswith("dead_marker:")

    def test_computrabajo_dead_marker_case_insensitive(self):
        """El marcador se compara en lowercase — casing del portal no debe
        romper la detección."""
        html = "<div>ESTA OFERTA YA NO ESTÁ DISPONIBLE</div>"
        with patch("jobs.tasks.requests.get", return_value=_FakeResponse(200, html)):
            _, is_dead, _ = _probe_offer(1, "https://ct", "computrabajo")
        assert is_dead is True

    def test_computrabajo_no_tilde_variant_also_detected(self):
        """Defensive: Computrabajo a veces sirve el mensaje sin tildes
        (encoding lío). Cubrimos ambas variantes."""
        html = "<p>Esta oferta ya no esta disponible</p>"
        with patch("jobs.tasks.requests.get", return_value=_FakeResponse(200, html)):
            _, is_dead, _ = _probe_offer(1, "https://ct", "computrabajo")
        assert is_dead is True

    def test_200_without_marker_stays_alive(self):
        """Oferta viva — 200 con contenido normal → NO marcar muerta."""
        html = "<html><body><h1>Desarrollador Fullstack</h1><p>Requisitos...</p></body></html>"
        with patch("jobs.tasks.requests.get", return_value=_FakeResponse(200, html)):
            _, is_dead, reason = _probe_offer(1, "https://ct", "computrabajo")
        assert is_dead is False
        assert reason == "http_200"

    def test_portal_without_markers_only_uses_http_status(self):
        """Portal sin marcadores registrados (ej: 'meli', 'torre'): solo
        confía en 404/410. Un 200 raro NUNCA lo marca muerto."""
        html = "cualquier cosa aquí, incluso 'no disponible' en texto libre"
        with patch("jobs.tasks.requests.get", return_value=_FakeResponse(200, html)):
            _, is_dead, _ = _probe_offer(1, "https://meli", "meli")
        assert is_dead is False

    def test_429_stays_alive(self):
        """Rate limit del portal — no significa que la oferta esté muerta."""
        with patch("jobs.tasks.requests.get", return_value=_FakeResponse(429)):
            _, is_dead, reason = _probe_offer(1, "https://x", "linkedin")
        assert is_dead is False
        assert reason == "http_429"

    def test_500_stays_alive(self):
        with patch("jobs.tasks.requests.get", return_value=_FakeResponse(500)):
            _, is_dead, _ = _probe_offer(1, "https://x", "computrabajo")
        assert is_dead is False

    def test_timeout_stays_alive(self):
        with patch(
            "jobs.tasks.requests.get", side_effect=requests.Timeout("slow portal")
        ):
            _, is_dead, reason = _probe_offer(1, "https://x", "linkedin")
        assert is_dead is False
        assert reason.startswith("network_error:")

    def test_connection_error_stays_alive(self):
        with patch(
            "jobs.tasks.requests.get",
            side_effect=requests.ConnectionError("dns fail"),
        ):
            _, is_dead, reason = _probe_offer(1, "https://x", "linkedin")
        assert is_dead is False
        assert reason == "network_error:ConnectionError"


# --- Integration tests de la task ------------------------------------------


@pytest.mark.integration
@pytest.mark.django_db
class TestVerifyActiveOffersTask:
    def _make_offer(self, **overrides) -> JobOffer:
        base = {
            "title": "Test Offer",
            "company": "Acme",
            "location": "Remote",
            "summary": "Test",
            "keywords": "python",
            "portal": "computrabajo",
        }
        base.update(overrides)
        return JobOffer.objects.create(**base)

    def test_empty_db_returns_zero(self):
        assert JobOffer.objects.count() == 0
        result = verify_active_offers()
        assert result["checked"] == 0
        assert result["marked_dead"] == 0

    def test_marks_404_offers_inactive(self):
        alive = self._make_offer(url="https://x/alive/1")
        dead = self._make_offer(url="https://x/dead/1")

        def fake_probe(offer_id, url, portal):
            # 'dead' recibe 404; 'alive' recibe 200.
            if "dead" in url:
                return offer_id, True, "http_404"
            return offer_id, False, "http_200"

        with patch("jobs.tasks._probe_offer", side_effect=fake_probe):
            result = verify_active_offers()

        assert result["marked_dead"] == 1
        dead.refresh_from_db()
        alive.refresh_from_db()
        assert dead.is_active is False
        assert alive.is_active is True

    def test_updates_last_checked_at_for_alive_offers(self):
        offer = self._make_offer(url="https://x/1")
        assert offer.last_checked_at is None

        with patch(
            "jobs.tasks._probe_offer",
            return_value=(offer.id, False, "http_200"),
        ):
            verify_active_offers()

        offer.refresh_from_db()
        assert offer.last_checked_at is not None

    def test_probe_crash_does_not_stop_task(self):
        """Un probe que revienta con excepción no debe tumbar el resto."""
        good = self._make_offer(url="https://x/good")
        bad = self._make_offer(url="https://x/bad")

        def flaky_probe(offer_id, url, portal):
            if "bad" in url:
                raise RuntimeError("boom")
            return offer_id, False, "http_200"

        with patch("jobs.tasks._probe_offer", side_effect=flaky_probe):
            result = verify_active_offers()

        # 'good' se procesó normalmente; 'bad' quedó sin update pero no
        # tumbó la task.
        assert result["checked"] == 2
        good.refresh_from_db()
        bad.refresh_from_db()
        assert good.last_checked_at is not None
        assert bad.last_checked_at is None
        assert bad.is_active is True  # sigue viva por precaución

    def test_inactive_offers_are_skipped(self):
        """No re-probeamos ofertas que ya marcamos inactive."""
        JobOffer.objects.create(
            title="Already dead",
            company="X",
            location="",
            summary="",
            keywords="",
            url="https://x/inactive",
            portal="computrabajo",
            is_active=False,
        )

        with patch(
            "jobs.tasks._probe_offer",
            return_value=(999, False, "http_200"),
        ) as mock_probe:
            result = verify_active_offers()

        assert result["checked"] == 0
        assert mock_probe.call_count == 0

    def test_reasons_counter_populated(self):
        """El summary devuelve counter por razón, útil para diagnóstico."""
        self._make_offer(url="https://x/1")
        self._make_offer(url="https://x/2")
        self._make_offer(url="https://x/3")

        # 1 dead (404) + 2 alive (200)
        calls = iter(
            [
                (1, True, "http_404"),
                (2, False, "http_200"),
                (3, False, "http_200"),
            ]
        )

        def fake_probe(offer_id, url, portal):
            return next(calls)

        with patch("jobs.tasks._probe_offer", side_effect=fake_probe):
            result = verify_active_offers()

        assert result["reasons"] == {"http_404": 1, "http_200": 2}

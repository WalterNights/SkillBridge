"""Tests para `MeliScraper` (Eightfold PCS-X de Mercado Libre).

Cubre:
- Flow feliz: bootstrap OK + search OK → parseo a JobOfferData.
- Bootstrap falla (401/500/network) → devuelve [] sin explotar.
- Search 401 (cookies rechazadas) → [] silencioso.
- Shape roto de la API → [] (fail-safe).
- URL absoluta a partir de `positionUrl` relativo.
- Modalidad `remote` marca el location con el prefijo `Remote —`.
- Freshness filter: descarta ofertas > 30 días o con TS inválido.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
import requests

from jobs.adapters.scrapers.base import ScraperError
from jobs.adapters.scrapers.meli import MeliScraper, _MAX_AGE_DAYS


def _ts_days_ago(days: int) -> int:
    """Helper: unix ts en segundos, `days` días atrás."""
    return int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp())


class _FakeResponse:
    """Mock chico del response — solo lo que el scraper toca."""

    def __init__(self, status_code: int = 200, json_body=None, text: str = ""):
        self.status_code = status_code
        self._json = json_body
        self.text = text or ""

    def json(self):
        if self._json is None:
            raise ValueError("no json body")
        return self._json


def _valid_positions_page(count_in_data: int = 40) -> dict:
    """Response de PCS-X con 2 positions frescas + campos completos.

    `count` en `data` es el total teórico de la query — dejamos 40 por
    default para que el scraper NO corte por "última página" (con menos
    positions que _PAGE_SIZE, cortaría al leer el len)."""
    return {
        "status": 200,
        "error": {"message": "", "body": ""},
        "data": {
            "count": count_in_data,
            "positions": [
                {
                    "id": 40834727,
                    "displayJobId": "115463",
                    "name": "Software Developer Frontend",
                    "locations": ["Medellín,Colombia"],
                    "creationTs": _ts_days_ago(5),
                    "postedTs": _ts_days_ago(5),
                    "department": "IT",
                    "workLocationOption": "onsite",
                    "positionUrl": "/careers/job/40834727",
                },
                {
                    "id": 40260731,
                    "displayJobId": "114075",
                    "name": "Product Designer",
                    "locations": ["Buenos Aires,Argentina"],
                    "creationTs": _ts_days_ago(2),
                    "postedTs": _ts_days_ago(2),
                    "department": "Design",
                    "workLocationOption": "remote",
                    "positionUrl": "/careers/job/40260731",
                },
            ],
        },
        "metadata": None,
    }


def _install_session_mock(mock_session_cls, bootstrap_resp, search_responses):
    """Configura el mock de `requests.Session()` para que:
       - `.get(_BOOTSTRAP_URL, ...)` devuelva `bootstrap_resp`.
       - `.get(_SEARCH_URL, ...)` devuelva sucesivos `search_responses`.

    Todo lo demás (`.headers.update`) es un no-op del MagicMock.
    """
    responses = list(search_responses)

    def _fake_get(url, **kwargs):
        if "careers" in url and "/api/" not in url:
            return bootstrap_resp
        return responses.pop(0) if responses else _FakeResponse(status_code=200, json_body={"data": {"positions": []}})

    session_instance = mock_session_cls.return_value
    session_instance.get.side_effect = _fake_get
    return session_instance


@pytest.mark.unit
class TestMeliScraperSearch:
    def test_empty_query_raises(self):
        scraper = MeliScraper()
        with pytest.raises(ScraperError):
            scraper.search("", "Bogotá")

    def test_happy_path_parses_positions(self):
        scraper = MeliScraper()
        with patch("jobs.adapters.scrapers.meli.requests.Session") as mock_sess:
            _install_session_mock(
                mock_sess,
                bootstrap_resp=_FakeResponse(status_code=200, text="<html/>"),
                # 2 positions en la primera página → como len < _PAGE_SIZE
                # (25), corta y no llama a la 2da.
                search_responses=[_FakeResponse(200, _valid_positions_page())],
            )
            offers = scraper.search("developer", "Bogotá")

        assert len(offers) == 2
        first = offers[0]
        assert first.title == "Software Developer Frontend"
        assert first.company == "Mercado Libre"
        # Coma con espacio (Eightfold la devuelve sin espacio).
        assert first.location == "Medellín, Colombia"
        assert first.portal == "meli"
        assert first.url == "https://mercadolibre.eightfold.ai/careers/job/40834727"

    def test_remote_position_gets_remote_marker(self):
        """`workLocationOption=remote` prepende "Remote —" al location
        para que `extract_modality` detecte remoto downstream."""
        scraper = MeliScraper()
        with patch("jobs.adapters.scrapers.meli.requests.Session") as mock_sess:
            _install_session_mock(
                mock_sess,
                bootstrap_resp=_FakeResponse(status_code=200, text=""),
                search_responses=[_FakeResponse(200, _valid_positions_page())],
            )
            offers = scraper.search("designer", "Bogotá")

        remote_offer = next(o for o in offers if o.title == "Product Designer")
        assert remote_offer.location.startswith("Remote")
        # Conservamos la ciudad base incluso en remotos.
        assert "Buenos Aires" in remote_offer.location

    def test_summary_includes_department_and_modality(self):
        scraper = MeliScraper()
        with patch("jobs.adapters.scrapers.meli.requests.Session") as mock_sess:
            _install_session_mock(
                mock_sess,
                bootstrap_resp=_FakeResponse(status_code=200, text=""),
                search_responses=[_FakeResponse(200, _valid_positions_page())],
            )
            offers = scraper.search("developer", "Bogotá")

        it_offer = next(o for o in offers if "IT" in (o.summary or ""))
        assert "Área: IT" in it_offer.summary
        assert "Modalidad:" in it_offer.summary


@pytest.mark.unit
class TestMeliScraperResilience:
    def test_bootstrap_500_returns_empty(self):
        scraper = MeliScraper()
        with patch("jobs.adapters.scrapers.meli.requests.Session") as mock_sess:
            _install_session_mock(
                mock_sess,
                bootstrap_resp=_FakeResponse(status_code=500, text="boom"),
                search_responses=[],
            )
            assert scraper.search("developer", "Bogotá") == []

    def test_bootstrap_network_error_returns_empty(self):
        scraper = MeliScraper()
        with patch("jobs.adapters.scrapers.meli.requests.Session") as mock_sess:
            session_instance = mock_sess.return_value
            session_instance.get.side_effect = requests.ConnectionError("dns fail")
            assert scraper.search("developer", "Bogotá") == []

    def test_search_401_returns_empty(self):
        """Cookies rechazadas por Eightfold → 401 en `/api/pcsx/search`.
        Comportamiento observado si el bootstrap no setea las cookies
        correctamente. El scraper no debe explotar."""
        scraper = MeliScraper()
        with patch("jobs.adapters.scrapers.meli.requests.Session") as mock_sess:
            _install_session_mock(
                mock_sess,
                bootstrap_resp=_FakeResponse(status_code=200),
                search_responses=[
                    _FakeResponse(status_code=401, text="Please try again later")
                ],
            )
            assert scraper.search("developer", "Bogotá") == []

    def test_search_non_json_returns_empty(self):
        scraper = MeliScraper()
        with patch("jobs.adapters.scrapers.meli.requests.Session") as mock_sess:
            _install_session_mock(
                mock_sess,
                bootstrap_resp=_FakeResponse(status_code=200),
                search_responses=[
                    _FakeResponse(status_code=200, json_body=None, text="<html>oops</html>")
                ],
            )
            assert scraper.search("developer", "Bogotá") == []

    def test_missing_positions_key_returns_empty(self):
        """Si Eightfold cambia el shape, degradamos limpio."""
        scraper = MeliScraper()
        with patch("jobs.adapters.scrapers.meli.requests.Session") as mock_sess:
            _install_session_mock(
                mock_sess,
                bootstrap_resp=_FakeResponse(status_code=200),
                search_responses=[
                    _FakeResponse(status_code=200, json_body={"data": {"count": 0}})
                ],
            )
            assert scraper.search("developer", "Bogotá") == []


@pytest.mark.unit
class TestMeliFreshnessFilter:
    def _base_item(self, **overrides):
        item = {
            "id": 1,
            "name": "Developer",
            "creationTs": _ts_days_ago(5),
            "positionUrl": "/careers/job/1",
        }
        item.update(overrides)
        return item

    def test_fresh_passes(self):
        assert MeliScraper._is_fresh(self._base_item()) is True

    def test_exactly_at_threshold_passes(self):
        assert (
            MeliScraper._is_fresh(self._base_item(creationTs=_ts_days_ago(_MAX_AGE_DAYS)))
            is True
        )

    def test_over_threshold_rejected(self):
        assert (
            MeliScraper._is_fresh(self._base_item(creationTs=_ts_days_ago(_MAX_AGE_DAYS + 5)))
            is False
        )

    def test_missing_ts_rejected(self):
        """Sin fecha confiable, mejor descartar que mostrar potencial
        oferta vieja."""
        item = self._base_item()
        item.pop("creationTs")
        assert MeliScraper._is_fresh(item) is False

    def test_falls_back_to_postedTs(self):
        """Si `creationTs` falta pero `postedTs` está, lo usamos."""
        item = self._base_item()
        item.pop("creationTs")
        item["postedTs"] = _ts_days_ago(3)
        assert MeliScraper._is_fresh(item) is True

    def test_invalid_ts_type_rejected(self):
        assert MeliScraper._is_fresh(self._base_item(creationTs="not-a-number")) is False

    def test_to_offer_rejects_stale_item(self):
        stale = self._base_item(creationTs=_ts_days_ago(120))
        assert MeliScraper._to_offer(stale, location_hint="") is None


@pytest.mark.unit
class TestMeliToOfferEdgeCases:
    def test_missing_name_returns_none(self):
        item = {
            "id": 1,
            "creationTs": _ts_days_ago(1),
            "positionUrl": "/careers/job/1",
        }
        assert MeliScraper._to_offer(item, location_hint="") is None

    def test_missing_id_returns_none(self):
        item = {
            "name": "Developer",
            "creationTs": _ts_days_ago(1),
        }
        assert MeliScraper._to_offer(item, location_hint="") is None

    def test_location_hint_fallback(self):
        """Sin `locations` estructurado ni `remote`, usamos el hint del
        caller para no dejar location vacío."""
        item = {
            "id": 1,
            "name": "Developer",
            "creationTs": _ts_days_ago(1),
            "positionUrl": "/careers/job/1",
        }
        offer = MeliScraper._to_offer(item, location_hint="Lima, Perú")
        assert offer is not None
        assert offer.location == "Lima, Perú"

    def test_url_defaults_to_id_when_positionUrl_missing(self):
        item = {
            "id": 999,
            "name": "Developer",
            "creationTs": _ts_days_ago(1),
        }
        offer = MeliScraper._to_offer(item, location_hint="")
        assert offer is not None
        assert offer.url == "https://mercadolibre.eightfold.ai/careers/job/999"

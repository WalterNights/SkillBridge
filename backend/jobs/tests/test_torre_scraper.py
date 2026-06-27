"""Tests para `TorreScraper`.

Cubre:
- search() exitoso con response JSON estructurado.
- search() degrada limpio cuando la API responde 500 / non-JSON / shape
  raro (no rompe el resto del scrape, devuelve []).
- _to_offer() normaliza correctamente los campos cuando vienen como
  dicts, listas, strings o ausentes (el shape de Torre varía).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from jobs.adapters.scrapers.base import ScraperError
from jobs.adapters.scrapers.torre import (
    TorreScraper,
    _OPPORTUNITY_URL_TEMPLATE,
    _OPPORTUNITY_URL_WITH_SLUG,
)


def _iso_now(days_ago: int = 0) -> str:
    """Helper: ISO 8601 con `Z` para `days_ago` días atrás. Usado por los
    fixtures para que la oferta NO sea descartada por el filtro de edad."""
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat().replace(
        "+00:00", "Z"
    )


def _fake_response(json_body=None, status_code: int = 200, text: str = ""):
    """Mock liviano del response de `requests.post`. Solo expone los
    campos que el scraper toca."""

    class _R:
        def __init__(self):
            self.status_code = status_code
            self.text = text or ""
            self._json = json_body

        def json(self):
            if self._json is None:
                raise ValueError("no json body")
            return self._json

    return _R()


_VALID_RESPONSE = {
    "total": 5282,
    "size": 10,
    "results": [
        {
            "id": "Yd6mbYOw",
            "objective": "Senior Product Designer",
            "slug": "acme-senior-product-designer-1",
            "tagline": "Diseña la próxima generación de productos digitales.",
            "organizations": [{"name": "Acme Inc"}],
            "locations": ["Bogotá, Colombia"],
            "remote": False,
            "skills": [
                {"name": "Figma", "experience": "potential-to-develop"},
                {"name": "User Research", "experience": "potential-to-develop"},
            ],
            "status": "open",
            "created": _iso_now(days_ago=5),
        },
        {
            "id": "AbCd1234",
            "objective": "Motion Designer",
            "organizations": [{"name": "Creative Studio"}],
            "locations": [],
            "remote": True,
            "skills": [{"name": "After Effects"}, {"name": "Cinema 4D"}],
            "status": "open",
            "created": _iso_now(days_ago=10),
        },
    ],
}


@pytest.mark.unit
class TestTorreScraperSearch:
    def test_parses_valid_response_into_offers(self):
        scraper = TorreScraper()
        with patch("jobs.adapters.scrapers.torre.requests.post") as mock_post:
            mock_post.return_value = _fake_response(json_body=_VALID_RESPONSE)
            offers = scraper.search("diseñador UX", "Bogotá")

        assert len(offers) == 2
        first = offers[0]
        assert first.title == "Senior Product Designer"
        assert first.company == "Acme Inc"
        assert first.location == "Bogotá, Colombia"
        assert first.portal == "torre"
        # Cuando hay slug, la URL lo usa para ser legible / shareable.
        assert first.url == _OPPORTUNITY_URL_WITH_SLUG.format(
            id="Yd6mbYOw", slug="acme-senior-product-designer-1"
        )

    def test_url_without_slug_falls_back_to_id_only(self):
        scraper = TorreScraper()
        with patch("jobs.adapters.scrapers.torre.requests.post") as mock_post:
            mock_post.return_value = _fake_response(json_body=_VALID_RESPONSE)
            offers = scraper.search("motion", "Bogotá")
        # La 2da oferta del fixture no tiene `slug` → fallback al template id-only.
        motion = next(o for o in offers if o.title == "Motion Designer")
        assert motion.url == _OPPORTUNITY_URL_TEMPLATE.format(id="AbCd1234")

    def test_body_includes_experience_field(self):
        """La API rebota con 400 si falta `experience` o `proficiency`
        dentro de `skill/role`. Caso real verificado contra producción
        2026-06-27 — sin este campo el scraper devolvia [] silenciosamente."""
        body = TorreScraper._build_body("designer")
        skill_role = body.get("skill/role")
        assert isinstance(skill_role, dict)
        assert skill_role.get("text") == "designer"
        assert skill_role.get("experience") == "potential-to-develop"

    def test_url_uses_torre_ai_domain_and_dash_separator(self):
        """Regresion guard: torre.co devuelve 404 (el dominio publico es
        torre.ai) y `/jobs/{id}/{slug}` también 404 (el formato correcto
        es id-slug concatenado con guion). Verificado contra prod
        2026-06-27. Sin este test, futuras tweaks pueden silenciosamente
        re-introducir el bug del 404."""
        scraper = TorreScraper()
        with patch("jobs.adapters.scrapers.torre.requests.post") as mock_post:
            mock_post.return_value = _fake_response(json_body=_VALID_RESPONSE)
            offers = scraper.search("designer", "X")
        first = offers[0]
        assert first.url.startswith("https://torre.ai/jobs/")
        assert "torre.co" not in first.url
        # id (Yd6mbYOw) y slug pegados con `-`, NO con `/`.
        assert (
            first.url == "https://torre.ai/jobs/Yd6mbYOw-acme-senior-product-designer-1"
        )

    def test_remote_opportunity_without_location_uses_Remote_marker(self):
        """Para que extract_modality detecte la modalidad remote, ponemos
        'Remote' como location cuando la opp es remota y no tiene
        location estructurado."""
        scraper = TorreScraper()
        with patch("jobs.adapters.scrapers.torre.requests.post") as mock_post:
            mock_post.return_value = _fake_response(json_body=_VALID_RESPONSE)
            offers = scraper.search("motion", "Bogotá")
        motion_offer = next(o for o in offers if "Motion" in o.title)
        assert motion_offer.location == "Remote"

    def test_empty_query_raises(self):
        scraper = TorreScraper()
        with pytest.raises(ScraperError):
            scraper.search("", "Bogotá")

    def test_500_response_returns_empty(self):
        scraper = TorreScraper()
        with patch("jobs.adapters.scrapers.torre.requests.post") as mock_post:
            mock_post.return_value = _fake_response(status_code=500, text="boom")
            offers = scraper.search("diseñador", "Bogotá")
        assert offers == []

    def test_non_json_response_returns_empty(self):
        scraper = TorreScraper()
        with patch("jobs.adapters.scrapers.torre.requests.post") as mock_post:
            # json_body=None hace que .json() tire ValueError
            mock_post.return_value = _fake_response(json_body=None, text="<html>oops</html>")
            offers = scraper.search("diseñador", "Bogotá")
        assert offers == []

    def test_missing_results_key_returns_empty(self):
        """Si la API cambia el shape, fail-silent — el resto del scrape
        no se rompe."""
        scraper = TorreScraper()
        with patch("jobs.adapters.scrapers.torre.requests.post") as mock_post:
            mock_post.return_value = _fake_response(json_body={"data": "unexpected"})
            offers = scraper.search("diseñador", "Bogotá")
        assert offers == []

    def test_request_exception_returns_empty(self):
        """Network failure no debe propagar — degrada limpio."""
        import requests as req

        scraper = TorreScraper()
        with patch("jobs.adapters.scrapers.torre.requests.post") as mock_post:
            mock_post.side_effect = req.ConnectionError("dns fail")
            offers = scraper.search("diseñador", "Bogotá")
        assert offers == []


@pytest.mark.unit
class TestTorreScraperToOffer:
    """Tests directos sobre `_to_offer` — robustez frente a shapes raros."""

    def test_missing_id_returns_none(self):
        offer = TorreScraper._to_offer({"objective": "Designer"}, location_hint="")
        assert offer is None

    def test_missing_title_returns_none(self):
        offer = TorreScraper._to_offer({"id": "X"}, location_hint="")
        assert offer is None

    def test_skills_as_strings_also_supported(self):
        """A veces la API devuelve `skills` como lista de strings simples
        en vez de dicts. Tiene que soportar ambos."""
        offer = TorreScraper._to_offer(
            {
                "id": "OPP-1",
                "objective": "Designer",
                "skills": ["Figma", "Sketch"],
                "status": "open",
                "created": _iso_now(days_ago=2),
            },
            location_hint="Bogotá",
        )
        assert offer is not None
        # Skills tageadas con el taxonomy llegan al summary fallback.
        assert "figma" in (offer.summary or "").lower() or "figma" in (
            offer.keywords or ""
        ).lower()

    def test_location_hint_fallback(self):
        """Sin location estructurado y sin remote, usamos el location
        pedido por el caller — no quedar con location vacío."""
        offer = TorreScraper._to_offer(
            {
                "id": "OPP-1",
                "objective": "Designer",
                "status": "open",
                "created": _iso_now(days_ago=2),
            },
            location_hint="Lima, Perú",
        )
        assert offer is not None
        assert offer.location == "Lima, Perú"

    def test_organization_as_dict_extracts_name(self):
        offer = TorreScraper._to_offer(
            {
                "id": "OPP-1",
                "objective": "Designer",
                "organizations": [{"name": "Big Co"}, {"name": "Other"}],
                "status": "open",
                "created": _iso_now(days_ago=2),
            },
            location_hint="",
        )
        assert offer is not None
        assert offer.company == "Big Co"


@pytest.mark.unit
class TestTorreFreshnessFilter:
    """Filtros de calidad post-incident 2026-06-27: el cliente
    jorgeluisq07 vio una oferta de Torre con match 87% que al clickear
    mostraba 'Este trabajo se encuentra cerrado' — publicada hace 4
    años. Torre marca status=open indefinidamente, así que combinamos
    status + created + deadline para descartar basura antes de guardar."""

    def _base_item(self, **overrides):
        item = {
            "id": "OPP-1",
            "objective": "Designer",
            "status": "open",
            "created": _iso_now(days_ago=5),
        }
        item.update(overrides)
        return item

    def test_open_and_recent_passes(self):
        assert TorreScraper._is_fresh_and_open(self._base_item()) is True

    def test_status_not_open_is_rejected(self):
        """Caso de la captura del cliente — oferta cerrada que Torre
        seguia devolviendo en _search."""
        assert TorreScraper._is_fresh_and_open(self._base_item(status="closed")) is False
        assert TorreScraper._is_fresh_and_open(self._base_item(status=None)) is False

    def test_created_more_than_30_days_old_is_rejected(self):
        """Aunque status=open, > 30 dias se descarta. La oferta de 4
        anios atras del incident habria sido descartada aca."""
        assert (
            TorreScraper._is_fresh_and_open(
                self._base_item(created=_iso_now(days_ago=45))
            )
            is False
        )

    def test_created_exactly_at_threshold_passes(self):
        """30 días exactos pasa (no <, <=)."""
        assert (
            TorreScraper._is_fresh_and_open(
                self._base_item(created=_iso_now(days_ago=30))
            )
            is True
        )

    def test_missing_created_is_rejected(self):
        """Sin fecha confiable, mejor descartar que aceptar y mostrar
        ofertas potencialmente viejas al usuario."""
        item = self._base_item()
        item.pop("created")
        assert TorreScraper._is_fresh_and_open(item) is False

    def test_malformed_created_is_rejected(self):
        assert (
            TorreScraper._is_fresh_and_open(self._base_item(created="not-a-date"))
            is False
        )

    def test_expired_deadline_is_rejected(self):
        """Si deadline ya pasó, descartar aunque status=open y created
        sea reciente — el employer ya cerró aplicaciones."""
        past_deadline = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat().replace(
            "+00:00", "Z"
        )
        assert (
            TorreScraper._is_fresh_and_open(
                self._base_item(deadline=past_deadline)
            )
            is False
        )

    def test_future_deadline_passes(self):
        future_deadline = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat().replace(
            "+00:00", "Z"
        )
        assert (
            TorreScraper._is_fresh_and_open(
                self._base_item(deadline=future_deadline)
            )
            is True
        )

    def test_to_offer_rejects_stale_item(self):
        """Integración: _to_offer ahora devuelve None si el item no
        pasa el filtro de freshness, incluso si tiene id+title válidos."""
        stale = {
            "id": "OPP-1",
            "objective": "Designer",
            "status": "open",
            "created": _iso_now(days_ago=400),  # 4 años
        }
        assert TorreScraper._to_offer(stale, location_hint="") is None

"""Tests para `PortalRouterService`.

Arquitectura post-rediseño 2026-06-27:
- `suggest_portals(profile)` (path crítico) es 100% determinístico —
  NO llama a Gemini. Tests verifican el clasificador + matching de
  categorías + el fallback ultra-rare cuando ningún scraper matchea.
- `preview_with_ai(profile)` (opt-in admin/cron) sí llama Gemini.
  Tests con mock para verificar happy path + degradación cuando
  falla la API o el JSON viene mal.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from jobs.services.portal_router import (
    PortalPlan,
    PortalRouterService,
    _parse_plans,
    _strip_markdown_fences,
)


@pytest.fixture
def designer_profile(django_user_model):
    """Perfil no-tech (diseñador UX). Sirve para verificar que el
    suggest_portals NO sugiera Hireline (tech-only)."""
    from users.models import UserProfile

    user = django_user_model.objects.create_user(
        username="design_user",
        email="design@example.com",
        password="pass",
    )
    return UserProfile.objects.create(
        user=user,
        first_name="Sam",
        last_name="Designer",
        phone="+5491100000000",
        city="Bogotá",
        professional_title="Diseñador UX/UI",
        skills="figma, adobe xd, sketch, ui design",
    )


# ---- _parse_plans / _strip_markdown_fences --------------------------


@pytest.mark.unit
class TestParsePlans:
    """Validación defensiva — el LLM puede devolver cualquier cosa."""

    def test_valid_list_parses_to_plans(self):
        data = [
            {"portal": "computrabajo", "query": "diseñador ux", "location": "Bogotá"},
            {"portal": "linkedin", "query": "ux designer", "location": ""},
        ]
        plans = _parse_plans(data, fallback_location="Bogotá")
        assert len(plans) == 2
        assert plans[0].portal == "computrabajo"
        assert plans[0].query == "diseñador ux"
        # Location vacía cae al fallback
        assert plans[1].location == "Bogotá"

    def test_unknown_portal_dropped(self):
        """El LLM inventó "monster.com" — lo descartamos en silencio."""
        data = [{"portal": "monster", "query": "x", "location": ""}]
        assert _parse_plans(data, "Lima") == []

    def test_empty_query_dropped(self):
        data = [{"portal": "computrabajo", "query": "", "location": "X"}]
        assert _parse_plans(data, "X") == []

    def test_non_list_returns_empty(self):
        assert _parse_plans({"portal": "x"}, "Y") == []
        assert _parse_plans("string", "Y") == []
        assert _parse_plans(None, "Y") == []


@pytest.mark.unit
def test_strip_markdown_fences():
    """Gemini a veces envuelve JSON en ```json … ``` aunque pidamos texto plano."""
    raw = '```json\n[{"portal": "linkedin"}]\n```'
    assert _strip_markdown_fences(raw) == '[{"portal": "linkedin"}]'

    raw_plain = '[{"portal": "linkedin"}]'
    assert _strip_markdown_fences(raw_plain) == raw_plain


# ---- suggest_portals (path crítico, sin AI) -------------------------


@pytest.mark.django_db
class TestSuggestPortals:
    """Path crítico — 100% determinístico, sin red, sin AI."""

    def test_tech_profile_includes_hireline_and_generalists(self, user_profile):
        """user_profile.professional_title = 'Backend Developer' → tech.
        Esperamos hireline (tech-only) + todos los `all`."""
        plans = PortalRouterService.suggest_portals(user_profile)
        portals = {p.portal for p in plans}
        assert "hireline" in portals  # tech matchea
        assert "computrabajo" in portals  # all matchea
        # query es el título crudo (path determinístico no lo refina)
        for p in plans:
            assert p.query == "Backend Developer"

    def test_designer_profile_excludes_tech_only(self, designer_profile):
        """Diseñador NO debe disparar Hireline (tech-only). Sí debe
        incluir weworkremotely si está marcado para design."""
        plans = PortalRouterService.suggest_portals(designer_profile)
        portals = {p.portal for p in plans}
        assert "hireline" not in portals, (
            "Hireline es tech-only — no debería sugerirse para diseñador"
        )
        # weworkremotely está marcado como ('tech', 'design', 'marketing')
        assert "weworkremotely" in portals
        # Los generalistas también
        assert "computrabajo" in portals

    def test_returns_at_least_one_plan(self, user_profile):
        """Garantía: nunca devolvemos lista vacía si el perfil tiene
        título. Aún para una categoría rara, los `all` sirven."""
        plans = PortalRouterService.suggest_portals(user_profile)
        assert len(plans) > 0

    def test_location_propagated_to_plans(self, user_profile):
        """Todos los plans heredan el city del perfil."""
        plans = PortalRouterService.suggest_portals(user_profile)
        for p in plans:
            assert p.location == user_profile.city

    def test_does_not_call_gemini(self, user_profile):
        """Regresión hard: el path crítico NUNCA debe tocar la API de
        Gemini. Si alguien futuro mete una llamada, este test grita."""
        with patch("jobs.services.portal_router.genai") as mock_genai:
            plans = PortalRouterService.suggest_portals(user_profile)
        assert mock_genai.GenerativeModel.call_count == 0
        assert mock_genai.configure.call_count == 0
        assert len(plans) > 0  # sanity: igualmente devolvió algo


# ---- preview_with_ai (opt-in, admin/cron) ---------------------------


@pytest.mark.django_db
class TestPreviewWithAI:
    """`preview_with_ai` SÍ usa Gemini — reservado para admin trigger
    y crons de optimización diaria. Mockeado para no pegar a la API
    real desde CI."""

    @patch("jobs.services.portal_router.genai")
    def test_gemini_response_used(self, mock_genai, settings, user_profile):
        settings.GEMINI_API_KEY = "fake-key"
        gemini_response = [
            {"portal": "linkedin", "query": "backend python", "location": "Buenos Aires"},
            {"portal": "hireline", "query": "backend developer", "location": ""},
        ]
        mock_model = MagicMock()
        mock_model.generate_content.return_value = MagicMock(text=json.dumps(gemini_response))
        mock_genai.GenerativeModel.return_value = mock_model

        plans = PortalRouterService.preview_with_ai(user_profile)

        portals = {p.portal for p in plans}
        assert portals == {"linkedin", "hireline"}
        linkedin_plan = next(p for p in plans if p.portal == "linkedin")
        assert linkedin_plan.query == "backend python"

    def test_returns_empty_without_api_key(self, settings, user_profile):
        """Sin GEMINI_API_KEY no llamamos a la API — devolvemos []."""
        settings.GEMINI_API_KEY = ""
        plans = PortalRouterService.preview_with_ai(user_profile)
        assert plans == []

    @patch("jobs.services.portal_router.genai")
    def test_gemini_exception_returns_empty(self, mock_genai, settings, user_profile):
        """Si Gemini tira (timeout, quota, network) → []. El caller
        decide qué hacer (típicamente caer al determinístico)."""
        settings.GEMINI_API_KEY = "fake-key"
        mock_genai.GenerativeModel.side_effect = RuntimeError("API down")

        plans = PortalRouterService.preview_with_ai(user_profile)
        assert plans == []

    @patch("jobs.services.portal_router.genai")
    def test_gemini_invalid_json_returns_empty(self, mock_genai, settings, user_profile):
        """Si Gemini devuelve texto que no es JSON → []."""
        settings.GEMINI_API_KEY = "fake-key"
        mock_model = MagicMock()
        mock_model.generate_content.return_value = MagicMock(text="esto no es json")
        mock_genai.GenerativeModel.return_value = mock_model

        plans = PortalRouterService.preview_with_ai(user_profile)
        assert plans == []

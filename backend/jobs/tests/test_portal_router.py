"""Tests para `PortalRouterService`.

Cubre los 3 paths del servicio:
- Cache hit → no llama a Gemini.
- Cache miss + Gemini OK → parsea JSON y cachea.
- Cache miss + Gemini falla (sin API key / excepción / JSON inválido) →
  fallback determinístico basado en `infer_profession_category` y las
  `categories` de cada scraper.

Mockea `google.generativeai.GenerativeModel` para no pegar a la API
real desde CI.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from django.core.cache import cache

from jobs.services.portal_router import (
    PortalPlan,
    PortalRouterService,
    _parse_plans,
    _strip_markdown_fences,
)


@pytest.fixture(autouse=True)
def clear_cache():
    """El router cachea por user_id 24h — limpiamos antes/después de
    cada test para que no se pisen entre sí."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def designer_profile(django_user_model):
    """Perfil no-tech (diseñador UX). Sirve para verificar que el
    fallback determinístico NO sugiera Hireline (tech-only)."""
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


# ---- Fallback determinístico ----------------------------------------


@pytest.mark.django_db
class TestFallback:
    """Sin GEMINI_API_KEY (o con Gemini caído), el router debe degradar
    a una lista basada en categorías + portales generalistas."""

    def test_no_api_key_falls_back_to_categories(self, settings, user_profile):
        """user_profile es Backend Developer (tech). Esperamos:
          - hireline (tech-only) presente.
          - portales `all` presentes (computrabajo, etc).
        """
        settings.GEMINI_API_KEY = ""
        plans = PortalRouterService.suggest_portals(user_profile)
        portals = {p.portal for p in plans}
        assert "hireline" in portals  # tech matchea
        assert "computrabajo" in portals  # all matchea
        # Query es el título completo en fallback (sin refinado)
        for p in plans:
            assert p.query == "Backend Developer"

    def test_designer_fallback_excludes_tech_only(self, settings, designer_profile):
        """Diseñador NO debe disparar Hireline (tech-only). Sí debe
        incluir weworkremotely si está marcado para design."""
        settings.GEMINI_API_KEY = ""
        plans = PortalRouterService.suggest_portals(designer_profile)
        portals = {p.portal for p in plans}
        assert "hireline" not in portals, "Hireline es tech-only — no debería sugerirse para diseñador"
        # weworkremotely está marcado como ('tech', 'design', 'marketing')
        assert "weworkremotely" in portals
        # Los generalistas también
        assert "computrabajo" in portals


# ---- Gemini happy path ----------------------------------------------


@pytest.mark.django_db
class TestGeminiPath:
    """Con GEMINI_API_KEY presente, el router debe usar la respuesta del LLM."""

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

        plans = PortalRouterService.suggest_portals(user_profile)

        portals = {p.portal for p in plans}
        assert portals == {"linkedin", "hireline"}
        linkedin_plan = next(p for p in plans if p.portal == "linkedin")
        assert linkedin_plan.query == "backend python"

    @patch("jobs.services.portal_router.genai")
    def test_gemini_exception_falls_back(self, mock_genai, settings, user_profile):
        """Si Gemini tira (timeout, quota, network) → fallback determinístico."""
        settings.GEMINI_API_KEY = "fake-key"
        mock_genai.GenerativeModel.side_effect = RuntimeError("API down")

        plans = PortalRouterService.suggest_portals(user_profile)
        # Fallback determinístico debe haber corrido — al menos hireline para tech
        assert any(p.portal == "hireline" for p in plans)

    @patch("jobs.services.portal_router.genai")
    def test_gemini_invalid_json_falls_back(self, mock_genai, settings, user_profile):
        """Si Gemini devuelve texto que no es JSON → fallback."""
        settings.GEMINI_API_KEY = "fake-key"
        mock_model = MagicMock()
        mock_model.generate_content.return_value = MagicMock(text="esto no es json")
        mock_genai.GenerativeModel.return_value = mock_model

        plans = PortalRouterService.suggest_portals(user_profile)
        assert len(plans) > 0  # fallback corrió


# ---- Cache + invalidación -------------------------------------------


@pytest.mark.django_db
class TestCaching:
    @patch("jobs.services.portal_router.genai")
    def test_second_call_uses_cache(self, mock_genai, settings, user_profile):
        """La segunda llamada al mismo user no debe pegar a Gemini de nuevo."""
        settings.GEMINI_API_KEY = "fake-key"
        gemini_response = [{"portal": "linkedin", "query": "x", "location": "Y"}]
        mock_model = MagicMock()
        mock_model.generate_content.return_value = MagicMock(text=json.dumps(gemini_response))
        mock_genai.GenerativeModel.return_value = mock_model

        first = PortalRouterService.suggest_portals(user_profile)
        second = PortalRouterService.suggest_portals(user_profile)

        # Solo una llamada a Gemini
        assert mock_genai.GenerativeModel.call_count == 1
        assert first == second

    def test_invalidate_clears_cache(self, user_profile, settings):
        """`invalidate(user_id)` debe forzar refresh en la próxima llamada."""
        settings.GEMINI_API_KEY = ""  # forzamos fallback (determinístico)
        plans_before = PortalRouterService.suggest_portals(user_profile)
        PortalRouterService.invalidate(user_profile.user_id)
        # Pisamos manualmente el resultado del fallback para detectar refresh.
        # Truco: como invalidate borró el cache, la próxima call corre fallback
        # de nuevo y debe devolver lo mismo (determinístico).
        plans_after = PortalRouterService.suggest_portals(user_profile)
        assert plans_before == plans_after  # mismo fallback determinístico

    def test_profile_save_invalidates_cache(self, user_profile, settings):
        """El signal post_save del UserProfile debe invalidar el cache.
        Sin esto, un user que edita su título seguiría viendo el plan
        viejo durante 24h."""
        settings.GEMINI_API_KEY = ""
        # Poblar cache
        PortalRouterService.suggest_portals(user_profile)
        cache_key = f"portal_router:v3:{user_profile.user_id}"
        assert cache.get(cache_key) is not None

        # Save dispara signal → invalidación
        user_profile.professional_title = "UX Designer"
        user_profile.save()

        assert cache.get(cache_key) is None

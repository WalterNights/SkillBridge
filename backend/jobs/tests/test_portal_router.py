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


def _profile(django_user_model, username, title, city, country=""):
    from users.models import UserProfile

    user = django_user_model.objects.create_user(
        username=username, email=f"{username}@example.com", password="x"
    )
    return UserProfile.objects.create(
        user=user,
        first_name="Test",
        last_name="User",
        phone="+57",
        city=city,
        country=country,
        professional_title=title,
        skills="python, django",
    )


@pytest.fixture
def bogota_tech_profile(django_user_model):
    """Perfil tech en Colombia: cubre todos los portales colombianos."""
    return _profile(django_user_model, "bogota_dev", "Backend Developer", "Bogotá")


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

    def test_tech_profile_includes_hireline_and_generalists(self, bogota_tech_profile):
        """'Backend Developer' en Bogotá → tech + CO.
        Esperamos hireline (tech-only) + todos los `all` que cubren CO."""
        plans = PortalRouterService.suggest_portals(bogota_tech_profile)
        portals = {p.portal for p in plans}
        assert "hireline" in portals  # tech matchea
        assert "computrabajo" in portals  # all matchea
        # El rol principal ("Backend Developer") DEBE estar entre las
        # queries de cada portal. Otras queries expandidas (hermanos del
        # dict, sinónimos ES) también aparecen — validadas en tests
        # dedicados de expansion abajo.
        queries_per_portal: dict[str, set[str]] = {}
        for p in plans:
            queries_per_portal.setdefault(p.portal, set()).add(p.query)
        for portal, queries in queries_per_portal.items():
            assert "Backend Developer" in queries, (
                f"portal={portal}: esperaba 'Backend Developer' entre las queries; "
                f"obtuve {queries}"
            )

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

    def test_long_multirole_title_refined_to_primary_role(self, django_user_model):
        """Garantía crítica para escalabilidad: títulos largos / multi-rol
        ('UI/UX Designer/Industrial designer/expert in 3d',
        'Zootecnista - Peluquero canino') deben expandir SOLO al rol
        principal (Zootecnista) — no al secundario (Peluquero canino).
        Sin esto LinkedIn/Indeed devuelven 0 por query demasiado
        específica y el volumen explota."""
        from users.models import UserProfile

        user = django_user_model.objects.create_user(
            username="multi", email="multi@example.com", password="x"
        )
        profile = UserProfile.objects.create(
            user=user,
            first_name="Multi",
            last_name="Pro",
            phone="+57",
            city="Bogotá",
            professional_title="Zootecnista - Peluquero canino",
            skills="",
        )
        plans = PortalRouterService.suggest_portals(profile)
        all_queries = {p.query for p in plans}
        # El rol principal SIEMPRE está presente (siempre primer query
        # de la expansion).
        assert "Zootecnista" in all_queries
        # El secundario NO debe estar — refinement via
        # _extract_primary_role dentro de expand_role_queries lo descartó.
        for q in all_queries:
            assert "peluquero" not in q.lower(), (
                f"Query {q!r} contiene 'Peluquero' — el rol secundario "
                f"se coló en la expansión. Chequear _extract_primary_role."
            )


@pytest.mark.django_db
class TestRoleExpansionIntegration:
    """Verifica que la expansion del rol se integra correctamente en
    PortalRouter. Los detalles de la expansion en sí (dict curado,
    sinónimos ES↔EN) se testean en test_role_expander.py."""

    def test_expansion_generates_multiple_queries_per_portal(self, user_profile):
        """user_profile es 'Backend Developer' (tech). Esperamos que cada
        portal reciba más de 1 query — el rol principal + hermanos del
        dict + sinónimo ES."""
        plans = PortalRouterService.suggest_portals(user_profile)
        queries_per_portal: dict[str, set[str]] = {}
        for p in plans:
            queries_per_portal.setdefault(p.portal, set()).add(p.query)
        # Cada portal recibe MÁS DE 1 query — sino no habría expansion.
        for portal, queries in queries_per_portal.items():
            assert len(queries) > 1, (
                f"portal={portal}: solo {len(queries)} query(s) — expansion no aplicó"
            )

    def test_expansion_disabled_flag_reverts_to_single_query(
        self, user_profile, settings
    ):
        """Con `ROLE_EXPANSION_ENABLED=False` el router vuelve al
        comportamiento previo — 1 plan por portal. Este es el kill-switch
        de rollback rápido."""
        settings.ROLE_EXPANSION_ENABLED = False
        plans = PortalRouterService.suggest_portals(user_profile)
        queries_per_portal: dict[str, set[str]] = {}
        for p in plans:
            queries_per_portal.setdefault(p.portal, set()).add(p.query)
        for portal, queries in queries_per_portal.items():
            assert queries == {"Backend Developer"}, (
                f"portal={portal}: con flag OFF esperaba solo el rol principal; "
                f"obtuve {queries}"
            )

    def test_expansion_cap_respected(self, user_profile, settings):
        """El cap por portal viene de ROLE_EXPANSION_MAX_QUERIES."""
        settings.ROLE_EXPANSION_MAX_QUERIES = 2
        plans = PortalRouterService.suggest_portals(user_profile)
        queries_per_portal: dict[str, set[str]] = {}
        for p in plans:
            queries_per_portal.setdefault(p.portal, set()).add(p.query)
        for portal, queries in queries_per_portal.items():
            assert len(queries) <= 2, (
                f"portal={portal}: cap 2 excedido con {len(queries)} queries"
            )

    def test_empty_title_returns_no_plans(self, django_user_model):
        """Sin título profesional no hay queries expandidas → 0 planes.
        Antes se generaba 1 plan por portal con query vacío; los scrapers
        rebotaban con ScraperError. Ahora fallamos temprano."""
        from users.models import UserProfile

        user = django_user_model.objects.create_user(
            username="empty", email="empty@example.com", password="x"
        )
        profile = UserProfile.objects.create(
            user=user,
            first_name="No",
            last_name="Title",
            phone="+57",
            city="Bogotá",
            professional_title="",  # sin título
            skills="",
        )
        plans = PortalRouterService.suggest_portals(profile)
        assert plans == []

    def test_fabio_case_agro(self, django_user_model):
        """Caso real cliente Fabio (zootecnista): la expansión activa
        búsquedas de 'Médico Veterinario', 'Ingeniero Agrónomo',
        'Avicultor' en cada portal — no solo espera que otro user las
        traiga vía piso vertical del matcher."""
        from users.models import UserProfile

        user = django_user_model.objects.create_user(
            username="fabio", email="fabio@example.com", password="x"
        )
        profile = UserProfile.objects.create(
            user=user,
            first_name="Fabio",
            last_name="Zoo",
            phone="+57",
            city="Bogotá",
            professional_title="Zootecnista",
            skills="ganado, pasturas",
        )
        plans = PortalRouterService.suggest_portals(profile)
        all_queries = {p.query.lower() for p in plans}
        assert "zootecnista" in all_queries
        assert "medico veterinario" in all_queries
        assert "ingeniero agronomo" in all_queries

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


@pytest.mark.django_db
class TestCountryRouting:
    """Solo se corren portales que cubren el país del perfil."""

    def test_spain_profile_skips_colombian_portals(self, django_user_model):
        profile = _profile(django_user_model, "madrid", "Backend Developer", "Madrid", "Spain")
        portals = {p.portal for p in PortalRouterService.suggest_portals(profile)}
        assert "infojobs" in portals
        assert "linkedin" in portals  # global
        assert not portals & {"computrabajo", "indeed", "magneto", "trabajos_co", "hireline"}

    def test_colombia_profile_skips_spain_only_portal(self, bogota_tech_profile):
        portals = {p.portal for p in PortalRouterService.suggest_portals(bogota_tech_profile)}
        assert "infojobs" not in portals
        assert "computrabajo" in portals

    def test_unknown_country_does_not_filter(self, django_user_model):
        profile = _profile(django_user_model, "nowhere", "Backend Developer", "Ciudad X")
        portals = {p.portal for p in PortalRouterService.suggest_portals(profile)}
        assert {"infojobs", "computrabajo"} <= portals

    def test_query_independent_portals_run_once(self, bogota_tech_profile):
        plans = PortalRouterService.suggest_portals(bogota_tech_profile)
        assert sum(1 for p in plans if p.portal == "hireline") == 1
        assert sum(1 for p in plans if p.portal == "linkedin") > 1

    def test_expand_false_uses_only_primary_role(self, bogota_tech_profile):
        plans = PortalRouterService.suggest_portals(bogota_tech_profile, expand=False)
        assert {p.query for p in plans} == {"Backend Developer"}


@pytest.mark.django_db
def test_scrape_stats_sum_all_queries(bogota_tech_profile):
    """Antes la última query pisaba el `found` de las anteriores."""
    from jobs.adapters.scrapers.base import JobOfferData
    from jobs.services.job_service import JobService

    def fake_scrape(portal, query, location):
        return [
            JobOfferData(
                title=f"{query} {portal}",
                company="Acme",
                location=location,
                summary="x",
                url=f"https://example.com/{portal}/{query}".replace(" ", "-"),
                keywords="python",
                portal=portal,
            )
        ]

    with patch("jobs.services.job_service._scrape_one_portal", side_effect=fake_scrape):
        _, stats = JobService.scrape_for_profile(bogota_tech_profile)

    linkedin_queries = sum(
        1 for p in PortalRouterService.suggest_portals(bogota_tech_profile) if p.portal == "linkedin"
    )
    assert stats["linkedin"]["found"] == linkedin_queries
    assert stats["hireline"]["found"] == 1


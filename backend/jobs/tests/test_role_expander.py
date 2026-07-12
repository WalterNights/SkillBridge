"""Tests de `expand_role_queries` — query expansion pre-scrape.

Cubre:
  - Casos base: título simple sin match en dict, con match, con multi-rol.
  - Sinónimo ES↔EN aplicado bidireccionalmente.
  - Dedup case + accent insensitive.
  - Cap por `ROLE_EXPANSION_MAX_QUERIES`.
  - Feature flag `ROLE_EXPANSION_ENABLED=False` para rollback.
  - Casos reales: Walter (tech fullstack) y Fabio (agro zootecnista).
"""

from __future__ import annotations

import pytest

from jobs.services.role_expander import (
    _dedupe_case_insensitive,
    _normalize_key,
    _swap_es_en,
    expand_role_queries,
)


@pytest.mark.unit
class TestNormalizeKey:
    def test_lowercase_and_no_accents(self):
        assert _normalize_key("Zootecnista") == "zootecnista"
        assert _normalize_key("MÉDICO VETERINARIO") == "medico veterinario"
        assert _normalize_key("Diseñador UI/UX") == "disenador ui/ux"

    def test_trims_whitespace(self):
        assert _normalize_key("  Backend Developer  ") == "backend developer"


@pytest.mark.unit
class TestSwapEsEn:
    def test_en_to_es(self):
        # "Developer" → "Desarrollador" (preserva capitalización del original
        # via case-insensitive replace).
        assert _swap_es_en("Full Stack Developer") == "Full Stack desarrollador"

    def test_es_to_en(self):
        assert _swap_es_en("Desarrollador Full Stack") == "developer Full Stack"

    def test_no_match_returns_none(self):
        """Sin ningún token en el mapa, no hay swap → None. Sin esto, el
        caller agregaría una variante idéntica al original y perdería una
        posición del cap."""
        assert _swap_es_en("Zootecnista") is None
        # "Manager" está en el mapa → swap a "gerente".
        assert _swap_es_en("Marketing Manager") == "Marketing gerente"

    def test_multiple_tokens_swapped(self):
        """Si el título tiene varios tokens con traducción, todos se
        swapean en un solo pass (sin re-procesamiento)."""
        result = _swap_es_en("Ingeniero Analista")
        assert result == "engineer analyst"

    def test_case_insensitive_matches_but_result_is_lowercase(self):
        """El replace no preserva el casing original del token — usamos
        lowercase en el reemplazo por simplicidad. Los portales normalizan
        casing igual, no perdemos hits."""
        result = _swap_es_en("BACKEND DEVELOPER")
        assert result == "BACKEND desarrollador"


@pytest.mark.unit
class TestDedupe:
    def test_preserves_order_removes_normalized_duplicates(self):
        result = _dedupe_case_insensitive([
            "Backend Developer",
            "backend developer",  # dup case-insensitive
            "Frontend Developer",
        ])
        assert result == ["Backend Developer", "Frontend Developer"]

    def test_accent_insensitive_dedup(self):
        result = _dedupe_case_insensitive(["Médico Veterinario", "medico veterinario"])
        assert result == ["Médico Veterinario"]


@pytest.mark.unit
class TestExpandRoleQueries:
    """Contrato principal — comportamiento visible desde el resto del
    sistema. Los tests de los helpers arriba cubren los internals."""

    def test_empty_title_returns_empty(self):
        assert expand_role_queries("") == []
        assert expand_role_queries("   ") == []

    def test_role_without_match_returns_only_primary(self):
        """Título sin match en el dict ni sinónimo aplicable → solo el
        rol principal. Ese es el fallback seguro — con la nueva feature
        el user NUNCA ve menos ofertas que antes, en el peor caso ve las
        mismas."""
        result = expand_role_queries("Astrofisico")
        assert result == ["Astrofisico"]

    def test_walter_case_tech_fullstack(self):
        """Caso real del user (screenshot 2026-07-08):
        title='FullStack Developer' → debe incluir hermanos backend/frontend
        + variante ES."""
        result = expand_role_queries(
            "FullStack Developer",
            category="tech",
            skills=["React", "Angular", "Node", "Python"],
        )
        # Primero siempre el rol principal.
        assert result[0] == "FullStack Developer"
        # Siguiente(s): variantes esperadas.
        normalized = [q.lower() for q in result]
        assert any("desarrollador" in q for q in normalized), (
            "esperaba variante ES para 'developer'"
        )
        assert any("backend" in q for q in normalized), "esperaba hermano backend"
        # Cap default = 4
        assert len(result) <= 4

    def test_fabio_case_agro_zootecnista(self):
        """Caso real cliente Fabio:
        title='Zootecnista' → debe incluir "Médico Veterinario" y
        "Ingeniero Agrónomo" para que scrapeemos activamente esas queries
        en Computrabajo/Magneto, no solo esperar que otro user las traiga."""
        result = expand_role_queries(
            "Zootecnista",
            category="agro",
            skills=["ganado", "pasturas"],
        )
        assert result[0] == "Zootecnista"
        normalized = [q.lower() for q in result]
        assert "medico veterinario" in normalized
        assert "ingeniero agronomo" in normalized

    def test_multi_role_title_uses_primary_only(self):
        """El helper _extract_primary_role del matcher normaliza títulos
        multi-rol. La expansion opera sobre el primer rol, no sobre los
        alternos — evita explosión combinatoria."""
        result = expand_role_queries("Backend Developer / DevOps Engineer")
        # Primary role = "Backend Developer" (split por " / ")
        assert result[0] == "Backend Developer"
        # NO debería incluir queries generados desde "DevOps Engineer".
        assert not any("sre" in q.lower() for q in result)

    def test_cap_respected(self, settings):
        settings.ROLE_EXPANSION_MAX_QUERIES = 2
        result = expand_role_queries("Full Stack Developer")
        assert len(result) == 2
        # Primary role siempre queda dentro del cap
        assert result[0] == "Full Stack Developer"

    def test_disabled_flag_returns_only_primary(self, settings):
        """`ROLE_EXPANSION_ENABLED=False` es el rollback rápido —
        comportamiento igual al pre-feature sin necesidad de redeploy.
        Crítico para responder rápido si el feature causa problemas."""
        settings.ROLE_EXPANSION_ENABLED = False
        result = expand_role_queries(
            "Full Stack Developer",
            category="tech",
            skills=["React", "Node"],
        )
        assert result == ["Full Stack Developer"]

    def test_primary_role_always_first(self):
        """Invariante importante: el rol EXACTO que declaró el user
        siempre va primero. Los portales suelen priorizar los primeros
        resultados, no queremos perder relevancia a la query principal."""
        result = expand_role_queries("Backend Developer")
        assert result[0] == "Backend Developer"

    def test_accent_insensitive_dict_lookup(self):
        """`Médico Veterinario` debe matchear la key `medico veterinario`
        del dict aunque el user lo escriba con tilde. Sin esto los
        títulos ES con tildes no expandirían."""
        result = expand_role_queries("Médico Veterinario")
        assert result[0] == "Médico Veterinario"
        normalized = [q.lower() for q in result]
        assert "zootecnista" in normalized  # hermano del dict

    def test_dedup_across_synonym_and_dict_siblings(self):
        """Si el sinónimo ES↔EN produce lo mismo que un hermano del dict,
        no debe aparecer 2 veces. Ej: 'Full Stack Developer' → sinónimo
        'Full Stack desarrollador' vs dict incluye 'desarrollador full
        stack' — casi equivalentes pero distintos strings; dedup opera
        solo sobre normalización, no similaridad."""
        # Este test verifica que no hay dup exact, no similarity.
        result = expand_role_queries("Backend Developer")
        # Normalización tiene que ser única en todo el output.
        normalized = [_normalize_key(q) for q in result]
        assert len(normalized) == len(set(normalized))

    def test_role_with_synonym_only_no_dict_entry(self):
        """Rol que no está en el dict pero sí tiene sinónimo ES/EN
        aplicable. Debe devolver [rol, rol_traducido] — no crash."""
        result = expand_role_queries("Ingeniero Analista")
        assert result[0] == "Ingeniero Analista"
        assert "engineer analyst" in [q.lower() for q in result]

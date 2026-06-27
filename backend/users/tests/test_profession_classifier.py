"""Tests para `infer_profession_category` — el clasificador determinístico
que mapea un título profesional libre a una categoría macro.

Crítico para el PortalRouter: si el classifier devuelve `general` para
títulos que SÍ tienen una categoría conocida, el fallback determinístico
no le activa los portales especializados (caso real del cliente
zootecnista, 2026-06-27).
"""

from __future__ import annotations

import pytest

from users.services.profession_classifier import infer_profession_category


@pytest.mark.unit
class TestInferProfessionCategory:
    @pytest.mark.parametrize(
        "title,expected",
        [
            # Tech — el patrón más rico, sanity check.
            ("Senior Backend Developer", "tech"),
            ("Full Stack Developer", "tech"),
            ("Data Scientist", "tech"),
            ("DevOps Engineer", "tech"),
            ("Programador Python", "tech"),
            # Design
            ("UI/UX Designer", "design"),
            ("Diseñadora UX", "design"),
            ("Motion Designer", "design"),
            ("Director de Arte", "design"),
            # Marketing
            ("Community Manager", "marketing"),
            ("Growth Marketer", "marketing"),
            ("SEO Specialist", "marketing"),
            # Sales
            ("Asesor Comercial", "sales"),
            ("Account Executive", "sales"),
            # Finance
            ("Contadora Pública", "finance"),
            ("Auditor Senior", "finance"),
            # HR
            ("Reclutadora Tech", "hr"),
            ("Talent Acquisition Lead", "hr"),
            # AGRO — agregado 2026-06-27, caso real del cliente zootecnista.
            # IMPORTANTE: 'agro' debe ganar antes que 'health' para
            # "Médico Veterinario" (sino caería en salud humana).
            ("Zootecnista", "agro"),
            ("Médico Veterinario", "agro"),
            ("Medico Veterinario Zootecnista", "agro"),
            ("Ingeniero Agrónomo", "agro"),
            ("Veterinaria de Pequeños Animales", "agro"),
            ("Coordinador de Producción Pecuaria", "agro"),
            ("Especialista en Nutrición Animal", "agro"),
            ("Asesor Técnico en Avicultura", "agro"),
            # Health humano — no debe confundirse con agro.
            ("Médico Pediatra", "health"),
            ("Enfermera Quirúrgica", "health"),
            ("Psicólogo Clínico", "health"),
            # Legal
            ("Abogada Penalista", "legal"),
            ("Compliance Officer", "legal"),
            # Operations
            ("Operations Manager", "operations"),
            ("Jefe de Producción", "operations"),
            # Fallback general
            ("Foo Bar Baz", "general"),
            ("", "general"),
        ],
    )
    def test_categories(self, title, expected):
        assert infer_profession_category(title) == expected, (
            f"{title!r} → esperaba {expected!r}"
        )

    def test_none_input_returns_general(self):
        assert infer_profession_category(None) == "general"

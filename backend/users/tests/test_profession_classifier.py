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
            # Edge case "Nutricionista Animal" (sin "nutrición") — sin la
            # entrada explícita 'nutricionista animal' en agro, esto
            # caería en health por matchear 'nutricionista'.
            ("Nutricionista Animal", "agro"),
            ("Asesor Técnico en Avicultura", "agro"),
            # Health humano — no debe confundirse con agro.
            ("Médico Pediatra", "health"),
            ("Enfermera Quirúrgica", "health"),
            ("Psicólogo Clínico", "health"),
            ("Nutricionista Deportiva", "health"),  # nutricionista humano
            # Legal
            ("Abogada Penalista", "legal"),
            ("Compliance Officer", "legal"),
            # Operations
            ("Operations Manager", "operations"),
            ("Jefe de Producción", "operations"),
            # ADMIN — agregado 2026-06-27. Solo términos puramente
            # administrativos para no robarle palabras a sales/operations.
            ("Administrador de Empresa", "admin"),
            ("Asistente Administrativa", "admin"),
            ("Auxiliar Administrativo", "admin"),
            ("Gerente General", "admin"),
            ("Director General", "admin"),
            ("CEO", "admin"),
            ("Secretaria Ejecutiva", "admin"),
            ("Recepcionista", "admin"),
            # TRADES — agregado 2026-06-27. Oficios concretos + servicios.
            ("Plomero", "trades"),
            ("Electricista", "trades"),
            ("Mecánico Industrial", "trades"),
            ("Soldador", "trades"),
            ("Carpintero", "trades"),
            ("Técnico en Refrigeración", "trades"),
            ("Vigilante", "trades"),
            ("Conductor de Camión", "trades"),
            ("Personal de Servicios Generales", "trades"),
            ("Operario de Planta", "trades"),
            ("Mensajero Motorizado", "trades"),
            # Anti-regresión: estos NO deberían caer en admin/trades aunque
            # contengan palabras superficialmente similares.
            ("Gerente Comercial", "sales"),         # "comercial" > "gerente"
            ("Director de Operaciones", "operations"),
            ("Director Comercial", "sales"),
            ("Operations Director", "operations"),  # "operations" matchea ✓
            # Fallback general
            ("Foo Bar Baz", "general"),
            ("", "general"),
            # PLURALES — bug crítico descubierto 2026-06-27.
            # El classifier viejo NO detectaba plurales (la `s` del
            # plural rompía el word boundary). Ofertas reales suelen
            # venir en plural ("Buscamos Diseñadores", "Veterinarios
            # necesarios") y caían todas a 'general'.
            ("Buscamos Zootecnistas para granja", "agro"),
            ("Veterinarios necesarios", "agro"),
            ("Empresas agrícolas", "agro"),
            ("Diseñadores Gráficos", "design"),
            ("Desarrolladores Backend", "tech"),
            ("Programadoras Junior", "tech"),
            ("Contadores Públicos", "finance"),
            ("Enfermeras Quirúrgicas", "health"),
            ("Abogadas Civilistas", "legal"),
            ("Plomeros con experiencia", "trades"),
            ("Electricistas industriales", "trades"),
            # PET CARE — agro incluye servicios para mascotas.
            # Caso real del cliente Fabio "Zootecnista - Peluquero canino".
            ("Peluquero canino", "agro"),
            ("Estilista canina", "agro"),
            ("Adiestrador canino", "agro"),
            ("Paseador de perros", "agro"),
            ("Auxiliar Veterinario", "agro"),
            ("Cuidador de animales", "agro"),
            # Docencia veterinaria queda en agro, no en education —
            # la palabra clave "veterinaria" gana antes que "docente".
            ("Docente de Veterinaria", "agro"),
            ("Profesor de Ciencias Agropecuarias", "agro"),
        ],
    )
    def test_categories(self, title, expected):
        assert infer_profession_category(title) == expected, (
            f"{title!r} → esperaba {expected!r}"
        )

    def test_none_input_returns_general(self):
        assert infer_profession_category(None) == "general"

    @pytest.mark.parametrize(
        "title",
        [
            # Lista de perfiles que el cliente mencionó como cobertura
            # mínima esperada (2026-06-27). Cada uno debe clasificar a
            # ALGO que no sea 'general' — sino el router no le activa
            # portales especializados y queda con el set 'all' solo.
            "Administrador de Empresa",
            "Abogado Civilista",
            "Médico Pediatra",
            "Ingeniero de Sistemas",
            "Desarrollador de Software",
            "Veterinario",
            "Zootecnista",
            "Enfermera",
            "Plomero",
            "Personal de Servicios Generales",
        ],
    )
    def test_real_world_titles_dont_fall_to_general(self, title):
        assert infer_profession_category(title) != "general", (
            f"{title!r} cayó a 'general' — el router no le va a sugerir "
            f"portales especializados. Considerar agregar al classifier."
        )

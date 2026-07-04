"""Tests de los extractores heurísticos country + modality + salary."""

import pytest

from jobs.utils.offer_attributes import (
    COUNTRY_UNKNOWN,
    MODALITY_HYBRID,
    MODALITY_ONSITE,
    MODALITY_REMOTE,
    MODALITY_UNKNOWN,
    extract_country,
    extract_modality,
    extract_salary,
)


@pytest.mark.unit
class TestExtractCountry:
    @pytest.mark.parametrize(
        "location,expected",
        [
            ("Ciudad de México, CDMX, México", "MX"),
            ("Bogotá, Cundinamarca, Colombia", "CO"),
            ("Buenos Aires, Argentina", "AR"),
            ("Santiago, Chile", "CL"),
            ("Lima, Perú", "PE"),
            ("Montevideo, Uruguay", "UY"),
            ("Madrid, España", "ES"),
            ("Miami, USA", "US"),
            ("Monterrey, Nuevo León, México", "MX"),
            ("Medellín", "CO"),
            ("CDMX", "MX"),
            # Sin tildes
            ("Mexico", "MX"),
            ("Bogota", "CO"),
        ],
    )
    def test_matches_known_countries(self, location, expected):
        assert extract_country(location) == expected

    def test_empty_location_returns_unknown(self):
        assert extract_country("") == COUNTRY_UNKNOWN
        assert extract_country(None) == COUNTRY_UNKNOWN

    def test_unrecognized_returns_unknown(self):
        assert extract_country("Algún lugar raro") == COUNTRY_UNKNOWN
        assert extract_country("Mars Colony") == COUNTRY_UNKNOWN


@pytest.mark.unit
class TestExtractModality:
    @pytest.mark.parametrize(
        "location,expected",
        [
            ("100% Remoto", MODALITY_REMOTE),
            ("Trabajo remoto desde casa", MODALITY_REMOTE),
            ("Remote (LATAM)", MODALITY_REMOTE),
            ("Home office full time", MODALITY_REMOTE),
            ("Teletrabajo", MODALITY_REMOTE),
            ("Bogotá - Híbrido", MODALITY_HYBRID),
            ("Hybrid - Mexico City", MODALITY_HYBRID),
            ("Presencial en Buenos Aires", MODALITY_ONSITE),
            ("On-site Monterrey", MODALITY_ONSITE),
            ("Trabajo en oficina", MODALITY_ONSITE),
        ],
    )
    def test_detects_modality_from_location(self, location, expected):
        assert extract_modality(location) == expected

    def test_detects_from_summary_when_location_silent(self):
        assert (
            extract_modality(
                "Ciudad de México", "Modalidad de trabajo: 100% remoto desde casa."
            )
            == MODALITY_REMOTE
        )

    def test_remote_takes_priority_over_hybrid_then_onsite(self):
        # Si el texto tiene los 3, ganan en orden: remote > hybrid > onsite
        assert extract_modality("Remote o presencial") == MODALITY_REMOTE
        assert extract_modality("Híbrido o presencial") == MODALITY_HYBRID

    def test_unknown_when_no_signal(self):
        assert extract_modality("") == MODALITY_UNKNOWN
        assert extract_modality(None) == MODALITY_UNKNOWN
        assert extract_modality("Buenos Aires") == MODALITY_UNKNOWN


@pytest.mark.unit
class TestExtractSalary:
    """Regla de diseño clave: preferir falsos negativos a falsos positivos.
    Mejor no mostrar salario que mostrar basura tomada de contexto no
    salarial (ej: "Django 3.5", "presupuesto 1000", "5 años"). Por eso
    todos los patrones EXIGEN símbolo monetario, moneda, o palabra clave."""

    @pytest.mark.parametrize(
        "summary,expected_contains",
        [
            # Patrón keyword + monto (más confiable)
            ("Salario: $3.000.000 COP", "3.000.000"),
            ("Sueldo mensual $2.500.000", "2.500.000"),
            ("Remuneración de $1.800.000 a $2.400.000", "1.800.000"),
            ("Pago 500 USD por mes", "500 USD"),
            # Palabra clave con formato variado
            ("Salario a convenir entre $4.000.000 y $6.000.000", "4.000.000"),
            # Símbolo + números (standalone) — SIEMPRE con currency
            ("Ofrecemos $1.500.000 - $2.000.000 COP más beneficios", "1.500.000"),
            ("USD 3000 a 4500", "USD 3000"),
            ("3.000.000 COP", "3.000.000 COP"),
            # Con unidad de tiempo (sin currency)
            ("$2.500.000 mensuales", "2.500.000"),
            ("$800.000 al mes", "800.000"),
        ],
    )
    def test_detects_salary_patterns(self, summary, expected_contains):
        detected = extract_salary(summary)
        assert detected, f"esperaba detectar salario en: {summary!r}"
        assert expected_contains in detected, (
            f"detectó {detected!r} pero esperaba que contenga {expected_contains!r}"
        )

    @pytest.mark.parametrize(
        "summary",
        [
            # Números sueltos sin señal salarial — NUNCA detectar
            "Experiencia con Django 3.5 y Python 3.11",
            "5 años de experiencia mínima",
            "Manejo de equipo de 15 personas",
            "Empresa con 500 empleados",
            "Presupuesto anual de 100 millones para el area",  # tricky: sin $/currency
            # Símbolo $ suelto (poco común pero posible)
            "Café de $5 en la cafetería",  # cap muy chico
            # Contexto tecnico
            "React 18, Node.js 20, TypeScript 5",
            # Empty / None
            "",
            None,
        ],
    )
    def test_does_not_detect_false_positives(self, summary):
        assert extract_salary(summary) == "", (
            f"NO debería detectar salario en: {summary!r}"
        )

    def test_normalizes_whitespace(self):
        """Portals meten \\n y tabs en el HTML — normalizamos a espacios simples."""
        result = extract_salary("Salario:\n\n$3.000.000\tCOP")
        assert "\n" not in result
        assert "\t" not in result
        assert "  " not in result  # no dobles espacios

    def test_caps_at_120_chars(self):
        """Cap defensivo — si el regex agarra mucho texto, truncar."""
        huge = "Salario: $3.000.000 " + ("mas beneficios " * 20)
        result = extract_salary(huge)
        assert len(result) <= 120

"""Tests de los extractores heurísticos country + modality."""

import pytest

from jobs.utils.offer_attributes import (
    COUNTRY_UNKNOWN,
    MODALITY_HYBRID,
    MODALITY_ONSITE,
    MODALITY_REMOTE,
    MODALITY_UNKNOWN,
    extract_country,
    extract_modality,
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

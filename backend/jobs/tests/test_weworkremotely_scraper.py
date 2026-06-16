"""Tests del helper de traducción ES→EN de WeWorkRemotely.

El search del sitio sólo indexa en inglés; cualquier query en español
devuelve 0 ofertas. El scraper traduce los términos comunes antes de
hacer fetch — estos tests aseguran que la traducción no se rompa.
"""

import pytest

from jobs.adapters.scrapers.weworkremotely import _translate_query_to_english


@pytest.mark.unit
class TestTranslateQueryToEnglish:
    def test_translates_common_spanish_titles(self):
        assert _translate_query_to_english("Desarrollador") == "developer"
        assert _translate_query_to_english("Ingeniero") == "engineer"
        assert _translate_query_to_english("Programador") == "programmer"

    def test_drops_spanish_stopwords(self):
        # "Ingeniero de Sistemas" → "engineer systems"
        assert _translate_query_to_english("Ingeniero de Sistemas") == "engineer systems"
        # "Desarrollador de Software" → "developer software"
        assert _translate_query_to_english("Desarrollador de Software") == "developer software"

    def test_leaves_english_queries_intact(self):
        assert _translate_query_to_english("backend developer") == "backend developer"
        assert _translate_query_to_english("React Engineer") == "react engineer"

    def test_handles_mixed_case_and_accents(self):
        assert _translate_query_to_english("DESARROLLADORA") == "developer"
        assert _translate_query_to_english("Ingeniería de Datos") == "engineering data"

    def test_unknown_terms_pass_through(self):
        # Si no hay traducción, deja la palabra tal cual — WWR puede
        # llegar a indexar tecnologías por nombre (kubernetes, rust).
        assert _translate_query_to_english("kubernetes rust") == "kubernetes rust"

    def test_empty_after_stopwords_falls_back_to_original(self):
        # Edge case: si la traducción y stop-word filter deja string vacío,
        # devolvemos el query original para no romper la URL.
        assert _translate_query_to_english("de la el") == "de la el"

"""Tests para JobMatchingService.

Cubre dos modos:
- Modo legacy (sin job_title/user_title): scoring puro por skills,
  backward-compat con consumidores viejos.
- Modo combinado (con títulos): peso 60% título + 40% skills, con
  fallback a título-solo cuando el job no enumera stack.
"""

import pytest

from jobs.services.matching_service import (
    JobMatchingService,
    _calc_title_score,
    _tokenize_title,
)


@pytest.mark.unit
class TestCalculateMatchPercentageLegacy:
    """Modo skills-only (sin titles). Backward-compat con consumidores viejos."""

    def test_all_skills_match_returns_100(self):
        result = JobMatchingService.calculate_match_percentage(
            job_keywords=["python", "django"],
            user_skills=["python", "django"],
        )
        assert result["match_percentage"] == 100
        assert set(result["matched_skills"]) == {"python", "django"}
        assert result["missing_skills"] == []

    def test_no_skills_match_returns_0(self):
        result = JobMatchingService.calculate_match_percentage(
            job_keywords=["java", "spring"],
            user_skills=["python", "django"],
        )
        assert result["match_percentage"] == 0
        assert result["matched_skills"] == []
        assert set(result["missing_skills"]) == {"java", "spring"}

    def test_partial_match_rounds_correctly(self):
        # 2 de 3 = 66.67% → redondea a 67
        result = JobMatchingService.calculate_match_percentage(
            job_keywords=["python", "django", "react"],
            user_skills=["python", "django"],
        )
        assert result["match_percentage"] == 67
        assert set(result["matched_skills"]) == {"python", "django"}
        assert result["missing_skills"] == ["react"]

    def test_empty_job_keywords_returns_zero(self):
        result = JobMatchingService.calculate_match_percentage(
            job_keywords=[],
            user_skills=["python"],
        )
        assert result["match_percentage"] == 0

    def test_case_insensitive_matching(self):
        result = JobMatchingService.calculate_match_percentage(
            job_keywords=["Python", "DJANGO"],
            user_skills=["python", "django"],
        )
        assert result["match_percentage"] == 100

    def test_whitespace_is_stripped(self):
        result = JobMatchingService.calculate_match_percentage(
            job_keywords=["  python  ", " django"],
            user_skills=["python", "django"],
        )
        assert result["match_percentage"] == 100

    def test_aliases_resolve_to_canonical_skill(self):
        result = JobMatchingService.calculate_match_percentage(
            job_keywords=["react.js"],
            user_skills=["react"],
        )
        assert result["match_percentage"] == 100
        assert "react" in result["matched_skills"]

    def test_multiple_aliases_normalize_consistently(self):
        result = JobMatchingService.calculate_match_percentage(
            job_keywords=["Node.js", "PostgreSQL", "C#", "Spring Boot"],
            user_skills=["node", "postgres", "csharp", "spring"],
        )
        assert result["match_percentage"] == 100
        assert set(result["matched_skills"]) == {"node", "postgresql", "csharp", "spring"}


@pytest.mark.unit
class TestTitleTokenization:
    """Smoke-tests del tokenizer de títulos. Cubre los casos que ya
    rompieron en review: stopwords y synonyms ES↔EN."""

    def test_strips_stopwords(self):
        assert _tokenize_title("desarrollador de software") == {"developer", "software"}

    def test_normalizes_es_en_role_synonyms(self):
        # ES "desarrollador" → canon "developer"
        assert _tokenize_title("Desarrollador Full Stack") == {"developer", "full", "stack"}
        # EN "developer" se queda en "developer"
        assert _tokenize_title("Full Stack Developer") == {"developer", "full", "stack"}

    def test_handles_punctuation_and_accents(self):
        assert _tokenize_title("Diseñador/a UX, Senior") == {"designer", "ux", "senior"}

    def test_empty_input_returns_empty_set(self):
        assert _tokenize_title("") == set()
        assert _tokenize_title("   ") == set()


@pytest.mark.unit
class TestTitleScore:
    """Recall sobre el cargo del usuario: qué fracción de sus palabras
    significativas aparece en el título del job."""

    def test_exact_match_returns_100(self):
        assert _calc_title_score("Full Stack Developer", "Full Stack Developer") == 100

    def test_es_en_synonym_match_returns_100(self):
        # "Desarrollador" canoniza a "developer" → matchea con job en EN
        assert _calc_title_score("Full Stack Developer", "Desarrollador Full Stack") == 100

    def test_job_with_extra_words_still_full_match(self):
        # User: "Full Stack Developer" / Job: "Senior Full Stack Developer Remote"
        # Las palabras del user están todas → 100%
        assert _calc_title_score(
            "Senior Full Stack Developer Remote", "Full Stack Developer"
        ) == 100

    def test_partial_overlap_returns_proportion(self):
        # User tokens {"backend", "developer"} vs job {"frontend", "developer"} → 1/2 = 50%
        assert _calc_title_score("Frontend Developer", "Backend Developer") == 50

    def test_zero_overlap_returns_zero(self):
        assert _calc_title_score("Marketing Manager", "Backend Developer") == 0

    def test_empty_user_title_returns_zero(self):
        assert _calc_title_score("Backend Developer", "") == 0


@pytest.mark.unit
class TestCalculateMatchPercentageCombined:
    """Modo combinado: 60% título + 40% skills, con fallback a título-solo
    cuando el job no trae stack listado."""

    def test_title_and_skills_full_match_returns_100(self):
        result = JobMatchingService.calculate_match_percentage(
            job_keywords=["python", "django"],
            user_skills=["python", "django"],
            job_title="Backend Developer",
            user_title="Backend Developer",
        )
        assert result["match_percentage"] == 100
        assert result["title_score"] == 100
        assert result["skill_score"] == 100

    def test_vague_job_with_title_match_relies_on_title(self):
        """Caso real: 'Buscamos desarrollador con experiencia' — sin keywords
        detectadas pero el rol coincide. Antes daba 0%, ahora levanta."""
        result = JobMatchingService.calculate_match_percentage(
            job_keywords=[],  # descripción vaga, sin stack
            user_skills=["python", "django"],
            job_title="Desarrollador Full Stack",
            user_title="Full Stack Developer",
        )
        # Título 100% (canoniza ES↔EN), capado a 70% para no inventar 100%
        assert result["match_percentage"] == 70
        assert result["skill_score"] == 0

    def test_title_match_with_no_skill_overlap_still_passes_threshold(self):
        """Job de Backend Developer en Java cuando user es Backend Developer Python.
        Antes: skills 0% → filtrado. Ahora: título 100%, combinado 60%."""
        result = JobMatchingService.calculate_match_percentage(
            job_keywords=["java", "spring"],
            user_skills=["python", "django"],
            job_title="Backend Developer",
            user_title="Backend Developer",
        )
        # 0.6 * 100 + 0.4 * 0 = 60
        assert result["match_percentage"] == 60

    def test_skills_match_but_title_mismatch_gets_low_score(self):
        """User es Backend Dev, job es Data Scientist que pide Python.
        Skills 100% pero rol no es el nuestro → no es buen match."""
        result = JobMatchingService.calculate_match_percentage(
            job_keywords=["python"],
            user_skills=["python"],
            job_title="Data Scientist",
            user_title="Backend Developer",
        )
        # 0.6 * 0 + 0.4 * 100 = 40 — pasa el umbral 25 pero está claramente abajo del 60+
        assert result["match_percentage"] == 40


@pytest.mark.django_db
class TestFilterJobsBySkills:
    """Tests de integración con DB. Usa el fixture user_profile cuyo
    professional_title es 'Backend Developer'."""

    def test_returns_jobs_above_combined_threshold(self, user_profile):
        from jobs.models import JobOffer

        # user_profile: title "Backend Developer", skills "python,django,postgresql,docker"
        high = JobOffer.objects.create(
            title="Senior Backend Developer",  # título 100%
            url="https://example.com/1",
            summary=".",
            keywords="python, django",  # skills 100% → combinado 100%
        )
        # Filler offer que NO debería pasar el threshold — su efecto es
        # estar en el queryset, no necesitamos un nombre para referenciarla.
        JobOffer.objects.create(
            title="Marketing Manager",
            url="https://example.com/2",
            summary=".",
            keywords="java, spring, kotlin",
        )

        results = JobMatchingService.filter_jobs_by_skills(
            JobOffer.objects.all(), user_profile, min_match_percentage=50
        )

        assert len(results) == 1
        assert results[0].id == high.id

    def test_vague_job_with_role_match_passes(self, user_profile):
        """Verificación clave del refactor: un job sin keywords detectadas
        pero cuyo título matchea el cargo del usuario YA NO se filtra."""
        from jobs.models import JobOffer

        vague = JobOffer.objects.create(
            title="Backend Developer Sr.",
            url="https://example.com/vague",
            summary="Buscamos desarrollador con experiencia.",
            keywords="",  # sin keywords detectadas
        )

        results = JobMatchingService.filter_jobs_by_skills(
            JobOffer.objects.all(), user_profile, min_match_percentage=25
        )

        # filter_jobs_by_skills enriquece los objetos que devuelve, no los
        # originales. Buscamos el job vago dentro del resultado.
        result_ids = {j.id for j in results}
        assert vague.id in result_ids
        vague_result = next(j for j in results if j.id == vague.id)
        assert vague_result.match_percentage == 70  # título capado

    def test_no_skills_no_title_returns_empty(self, user, db):
        from users.models import UserProfile

        profile = UserProfile.objects.create(
            user=user,
            first_name="No",
            last_name="Skills",
            phone="+1",
            city="-",
            professional_title="",  # sin título
            skills="",  # sin skills
            experience="-",
        )
        from jobs.models import JobOffer

        JobOffer.objects.create(
            title="x", url="https://example.com/x", summary=".", keywords="python"
        )

        assert JobMatchingService.filter_jobs_by_skills(JobOffer.objects.all(), profile) == []

    def test_results_sorted_by_match_desc(self, user_profile):
        from jobs.models import JobOffer

        # Ambos con título matcheado para asegurar que pasen el umbral
        JobOffer.objects.create(
            title="Backend Developer",  # título 100%
            url="https://example.com/a",
            summary=".",
            keywords="python, java",  # 1/2 = 50% skills → 0.6*100 + 0.4*50 = 80
        )
        JobOffer.objects.create(
            title="Senior Backend Developer",  # título 100%
            url="https://example.com/b",
            summary=".",
            keywords="python, django",  # 2/2 = 100% skills → combinado 100
        )

        results = JobMatchingService.filter_jobs_by_skills(
            JobOffer.objects.all(), user_profile, min_match_percentage=50
        )

        assert [j.match_percentage for j in results] == sorted(
            [j.match_percentage for j in results], reverse=True
        )
        assert results[0].title == "Senior Backend Developer"

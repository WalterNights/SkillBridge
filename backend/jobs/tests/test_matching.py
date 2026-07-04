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
    _extract_primary_role,
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
    """Cascada de casos del title_score:
    1. tokens iguales → 100
    2. user ⊆ job → 90
    3. job ⊆ user → 85
    4. overlap parcial → (overlap/user_tokens) * 80
    5. sin overlap pero same vertical → 45
    6. sin overlap sin vertical → 15
    """

    def test_exact_match_returns_100(self):
        assert _calc_title_score("Full Stack Developer", "Full Stack Developer") == 100

    def test_es_en_synonym_match_returns_100(self):
        # "Desarrollador" canoniza a "developer" → tokens iguales tras normalizar
        assert _calc_title_score("Full Stack Developer", "Desarrollador Full Stack") == 100

    def test_user_subset_of_job_returns_90(self):
        # User: "Full Stack Developer" ⊆ Job: "Senior Full Stack Developer Remote"
        # El rol esta en el job, este solo agrega seniority/modalidad.
        assert _calc_title_score(
            "Senior Full Stack Developer Remote", "Full Stack Developer"
        ) == 90

    def test_job_subset_of_user_returns_85(self):
        # User: "Senior Backend Developer" ⊇ Job: "Backend Developer"
        # Job es una version mas generica del rol; el user calza pero perdio
        # especificidad (senior).
        assert _calc_title_score("Backend Developer", "Senior Backend Developer") == 85

    def test_partial_overlap_returns_proportion_of_80(self):
        # User {"backend", "developer"} vs job {"frontend", "developer"} → 1/2 * 80 = 40
        assert _calc_title_score("Frontend Developer", "Backend Developer") == 40

    def test_zero_overlap_no_vertical_returns_floor_15(self):
        # Sin categoria compartida → piso minimo (aparece al fondo del feed).
        assert _calc_title_score("Marketing Manager", "Backend Developer") == 15

    def test_zero_overlap_same_vertical_returns_45(self):
        # Titulos que no comparten tokens pero comparten vertical macro
        # (agro). Rescata a Fabio (zootecnista) para ver "Medico Veterinario"
        # al 45%, no al 90% que inflaba el sistema anterior.
        assert _calc_title_score(
            "Medico Veterinario",
            "Zootecnista",
            job_category="agro",
            user_category="agro",
        ) == 45

    def test_zero_overlap_different_vertical_returns_floor_15(self):
        # Aunque los rectores tengan tokens en comun no pertenecen — pero
        # categorias distintas → piso 15, no 45.
        assert _calc_title_score(
            "Backend Developer",
            "Zootecnista",
            job_category="tech",
            user_category="agro",
        ) == 15

    def test_general_user_category_no_vertical_floor(self):
        # user_category = "general" no dispara piso vertical (comodin).
        assert _calc_title_score(
            "Backend Developer",
            "Marketing Manager",
            job_category="tech",
            user_category="general",
        ) == 15

    def test_empty_user_title_returns_zero(self):
        assert _calc_title_score("Backend Developer", "") == 0


@pytest.mark.unit
class TestCalculateMatchPercentageCombined:
    """Formula: match = max(0, title_score - skill_penalty).
    skill_penalty = (missing / total_job_skills) * 100 cuando el job lista
    skills; 0 cuando no lista."""

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
        assert result["skill_penalty"] == 0

    def test_vague_job_without_skills_uses_title_only(self):
        """Job sin keywords listadas — no penalizamos por falta de datos
        del portal. Match = title_score sin ajustes."""
        result = JobMatchingService.calculate_match_percentage(
            job_keywords=[],  # descripcion vaga, sin stack
            user_skills=["python", "django"],
            job_title="Desarrollador Full Stack",
            user_title="Full Stack Developer",
        )
        # Titulo 100% (canoniza ES↔EN), sin penalty → 100.
        assert result["match_percentage"] == 100
        assert result["skill_score"] == 0
        assert result["skill_penalty"] == 0

    def test_title_perfect_but_all_skills_missing_goes_to_zero(self):
        """Job Backend Developer que pide Java+Spring, user es Backend Developer
        con Python+Django. Titulo 100% pero le faltan las 2/2 skills → penalty
        100, match 0. Es honesto — no tenes ninguna de las skills que piden."""
        result = JobMatchingService.calculate_match_percentage(
            job_keywords=["java", "spring"],
            user_skills=["python", "django"],
            job_title="Backend Developer",
            user_title="Backend Developer",
        )
        assert result["match_percentage"] == 0
        assert result["title_score"] == 100
        assert result["skill_penalty"] == 100

    def test_title_perfect_half_skills_missing(self):
        """Titulo 100%, matcheas 1 de 2 skills → penalty 50, match 50."""
        result = JobMatchingService.calculate_match_percentage(
            job_keywords=["python", "docker"],
            user_skills=["python"],
            job_title="Backend Developer",
            user_title="Backend Developer",
        )
        assert result["match_percentage"] == 50
        assert result["skill_penalty"] == 50

    def test_screenshot_case_reported_by_user(self):
        """Caso concreto del screenshot que motivo el rewrite:
        Walter (Fullstack Developer) vs "Desarrollador FullStack (Middle)"
        con 13 skills pedidas, 4 matcheadas. Con la formula anterior daba
        90% (percibido como deshonesto). Con la nueva debe rondar 21%."""
        job_skills = [
            "react", "nodejs", "postgresql", "docker",
            "calidad", "comunicacion", "dotnet", "erp",
            "mongodb", "proactividad", "rest", "sql", "git",
        ]
        user_skills = ["react", "nodejs", "postgresql", "docker"]
        result = JobMatchingService.calculate_match_percentage(
            job_keywords=job_skills,
            user_skills=user_skills,
            job_title="Desarrollador FullStack (Middle)",
            user_title="Fullstack Developer",
        )
        # title: user "fullstack developer" ⊆ job "developer fullstack middle" → 90
        # penalty: 9/13 * 100 = 69
        # match: 90 - 69 = 21
        assert result["title_score"] == 90
        assert result["skill_penalty"] == 69
        assert result["match_percentage"] == 21

    def test_skills_match_but_title_mismatch_gets_low_score(self):
        """User es Backend Developer, job es Data Scientist que pide Python.
        Sin overlap de tokens ni misma categoria → title 15, sin skills
        faltantes → penalty 0, match 15. Aparece en el fondo del feed."""
        result = JobMatchingService.calculate_match_percentage(
            job_keywords=["python"],
            user_skills=["python"],
            job_title="Data Scientist",
            user_title="Backend Developer",
        )
        # title = 15 (piso sin overlap sin vertical), penalty = 0
        assert result["match_percentage"] == 15


@pytest.mark.unit
class TestExtractPrimaryRole:
    """El normalizer de `user_title` que destraba perfiles multi-rol.

    Antes de existir esta función, un perfil como "UI/UX Designer/
    Industrial designer/expert in 3d, augmented reality and animation"
    generaba 9 user_tokens y NI siquiera una oferta perfecta de
    'Diseñador UI/UX' alcanzaba el threshold de 60% (33% title × 0.6 +
    100% skills × 0.4 = 59.8%, borderline). Ahora ese perfil normaliza
    a 'UI/UX Designer' (3 tokens) y la oferta perfecta llega a 100%.
    """

    def test_empty_returns_empty(self):
        assert _extract_primary_role("") == ""
        assert _extract_primary_role(None) == ""  # type: ignore
        assert _extract_primary_role("   ") == ""

    def test_single_role_passes_through_unchanged(self):
        """Títulos simples no se modifican."""
        assert _extract_primary_role("Backend Developer") == "Backend Developer"
        assert _extract_primary_role("Senior Full Stack Engineer") == "Senior Full Stack Engineer"

    def test_protects_ui_ux_abbreviation(self):
        """`UI/UX` es parte del rol, no separador. No debe romperse."""
        assert _extract_primary_role("UI/UX Designer") == "UI/UX Designer"
        assert _extract_primary_role("UX/UI Designer Senior") == "UX/UI Designer Senior"

    def test_splits_multi_role_by_slash(self):
        """Slash entre roles sí separa."""
        assert (
            _extract_primary_role("Backend Developer / DevOps Engineer")
            == "Backend Developer"
        )

    def test_splits_by_comma(self):
        assert (
            _extract_primary_role("Data Scientist, ML Engineer")
            == "Data Scientist"
        )

    def test_splits_by_spanish_y(self):
        assert (
            _extract_primary_role("Diseñador UI/UX y Motion Designer")
            == "Diseñador UI/UX"
        )

    def test_splits_by_english_and(self):
        assert (
            _extract_primary_role("Frontend Engineer and Mobile Developer")
            == "Frontend Engineer"
        )

    def test_splits_by_pipe(self):
        assert (
            _extract_primary_role("Product Designer | UX Researcher")
            == "Product Designer"
        )

    def test_splits_by_dash_with_spaces(self):
        """Guion rodeado de espacios = separador. Caso real: cliente
        zootecnista que tenía 'Zootecnista - Peluquero canino'."""
        assert _extract_primary_role("Zootecnista - Peluquero canino") == "Zootecnista"
        assert _extract_primary_role("Designer — Photographer") == "Designer"
        assert _extract_primary_role("Marketing · Sales") == "Marketing"

    def test_dash_without_spaces_does_not_split(self):
        """Guion SIN espacios es parte del rol — 'Front-End Developer'
        no debe romperse en 'Front'."""
        assert _extract_primary_role("Front-End Developer") == "Front-End Developer"
        assert _extract_primary_role("Full-Stack Engineer") == "Full-Stack Engineer"

    def test_jorges_real_title(self):
        """Caso real del cliente jorgeluisq07 que motivó el fix."""
        result = _extract_primary_role(
            "UI/UX Designer/Industrial designer/expert in 3d, "
            "augmented reality and animation"
        )
        assert result == "UI/UX Designer"

    def test_protects_ai_ml_abbreviation(self):
        assert _extract_primary_role("AI/ML Engineer / Data Scientist") == "AI/ML Engineer"

    def test_combined_separators(self):
        """Cuando hay varios separadores, gana el más temprano."""
        # `,` aparece antes que `/` → split por `,` primero.
        assert (
            _extract_primary_role("UX Designer, 3D Modeler/Animator")
            == "UX Designer"
        )


@pytest.mark.unit
class TestSameVerticalFloor:
    """Piso vertical (reemplaza el "boost" del scoring anterior).

    Caso Fabio (zootecnista, 2026-06-29): ofertas del area del user con
    titulos que no comparten tokens salian a 0%.
      - 'Zootecnista' (user) vs 'Medico Veterinario' (job) -> overlap 0
      - 'Zootecnista' vs 'Avicultura' -> overlap 0

    El classifier reconoce ambos como `agro`. Antes: title 0 → boost a 50
    → combined 90 (deshonesto). Ahora: title 45 (piso vertical) → penalty
    proporcional a skills faltantes → match honesto entre 0 y 45.
    """

    AGRO = dict(job_category="agro", user_category="agro")

    def test_no_overlap_same_vertical_without_skills_returns_floor(self):
        """Caso central: titulos sin overlap, job sin skills detectadas.
        Fabio ve la oferta al 45% — pasa el threshold del feed (40)."""
        result = JobMatchingService.calculate_match_percentage(
            job_keywords=[],  # sin skills en el job
            user_skills=["ganado", "pasturas"],
            job_title="Medico Veterinario",
            user_title="Zootecnista",
            **self.AGRO,
        )
        assert result["match_percentage"] == 45
        assert result["title_score"] == 45
        assert result["skill_penalty"] == 0

    def test_no_overlap_same_vertical_with_generic_job_skills(self):
        """Job del mismo vertical con skills genericas que Fabio no tiene.
        Antes: se ignoraban las skills → 90. Ahora: penalizan honestamente."""
        result = JobMatchingService.calculate_match_percentage(
            job_keywords=["excel"],
            user_skills=["ganado", "pasturas"],
            job_title="Medico Veterinario",
            user_title="Zootecnista",
            **self.AGRO,
        )
        # title = 45 (piso), penalty = 1/1 * 100 = 100 → match = max(0, 45-100) = 0.
        # Realistico: el job pide 1 skill (excel) que el user no tiene,
        # y el titulo no calza directamente. No pasa el threshold.
        assert result["match_percentage"] == 0

    def test_direct_title_overlap_same_vertical_uses_100_not_floor(self):
        """Cuando el titulo SI matchea directamente, no aplica el piso —
        usa el score real (100). El piso es para RESCATAR casos sin overlap."""
        result = JobMatchingService.calculate_match_percentage(
            job_keywords=[],
            user_skills=["ganado"],
            job_title="Medico Veterinario y/o Zootecnista",
            user_title="Zootecnista",
            **self.AGRO,
        )
        # user tokens {zootecnista} ⊆ job tokens {medico, veterinario,
        # zootecnista} → title = 90. Sin skills → penalty 0 → 90.
        assert result["match_percentage"] == 90

    def test_no_overlap_same_vertical_with_matched_skills_stays_at_floor(self):
        """Job del vertical del user, sin overlap de titulo, pero user
        tiene todas las skills → penalty 0 → match = 45 (piso vertical)."""
        result = JobMatchingService.calculate_match_percentage(
            job_keywords=["veterinaria", "ganado"],
            user_skills=["veterinaria", "ganado"],  # 2/2 matcheadas
            job_title="Veterinario Senior",
            user_title="Zootecnista",
            **self.AGRO,
        )
        assert result["match_percentage"] == 45  # piso, sin penalty

    def test_different_category_uses_no_match_floor(self):
        """Si categorias difieren, cae al piso minimo (15)."""
        result = JobMatchingService.calculate_match_percentage(
            job_keywords=[],
            user_skills=["ganado"],
            job_title="Backend Developer",
            user_title="Zootecnista",
            job_category="tech",
            user_category="agro",
        )
        assert result["match_percentage"] == 15

    def test_general_user_category_no_vertical_floor(self):
        """user_category='general' NO dispara piso vertical (comodin)."""
        result = JobMatchingService.calculate_match_percentage(
            job_keywords=[],
            user_skills=["ganado"],
            job_title="Medico Veterinario",
            user_title="Foo Bar Baz",  # no clasifica
            job_category="agro",
            user_category="general",
        )
        assert result["match_percentage"] == 15  # piso minimo

    def test_backward_compat_without_categories(self):
        """Sin categorias no hay piso vertical — cae al piso minimo."""
        result = JobMatchingService.calculate_match_percentage(
            job_keywords=[],
            user_skills=["ganado"],
            job_title="Medico Veterinario",
            user_title="Zootecnista",
        )
        assert result["match_percentage"] == 15


@pytest.mark.unit
class TestMatchingWithMultiRoleTitle:
    """Garantías post-fix: el perfil de Jorge debe poder llegar al 60%
    con ofertas realistas. Antes del normalizer, ni siquiera una oferta
    perfecta alcanzaba el threshold."""

    JORGE_TITLE = (
        "UI/UX Designer/Industrial designer/expert in 3d, "
        "augmented reality and animation"
    )

    def test_perfect_ui_ux_offer_scores_well(self):
        """Oferta de 'Diseñador UI/UX Senior' con 3/4 skills matcheadas.
        Con la nueva formula: user_tokens {ui, ux, designer} ⊆ job_tokens
        → title 90. Penalty = 1/4 * 100 = 25. Match = 65 (buen tier)."""
        result = JobMatchingService.calculate_match_percentage(
            job_keywords=["figma", "sketch", "photoshop", "illustrator"],
            user_skills=["figma", "sketch", "photoshop"],  # 3/4 = 75%
            job_title="Diseñador UI/UX Senior",
            user_title=self.JORGE_TITLE,
        )
        # title: user {ui, ux, designer} ⊆ job {ui, ux, designer, senior}
        # → title = 90 (user es subset del job).
        # skills: 3/4 matched, 1/4 missing → penalty = 25.
        # match = 90 - 25 = 65 (buen tier: 60-79).
        assert result["match_percentage"] == 65

    def test_motion_designer_offer_still_filtered(self):
        """Oferta tangente ('Motion Designer Sr.') NO debe alcanzar 60%
        — sigue siendo otro rol aunque comparta 'designer'."""
        result = JobMatchingService.calculate_match_percentage(
            job_keywords=["after effects", "premiere"],
            user_skills=["figma", "photoshop"],  # 0 match
            job_title="Motion Designer Sr.",
            user_title=self.JORGE_TITLE,
        )
        # title: {ui, ux, designer} vs {motion, designer, sr} → overlap 1,
        # ni subset ni superset → parcial = 1/3 * 80 = 27.
        # skills: 2/2 missing → penalty = 100.
        # match = max(0, 27 - 100) = 0.
        assert result["match_percentage"] < 40


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
        """Un job sin keywords detectadas pero cuyo titulo matchea el cargo
        del usuario NO se penaliza — no castigamos por falta de datos
        del portal."""
        from jobs.models import JobOffer

        vague = JobOffer.objects.create(
            title="Backend Developer Sr.",
            url="https://example.com/vague",
            summary="Buscamos desarrollador con experiencia.",
            keywords="",  # sin keywords detectadas
        )

        results = JobMatchingService.filter_jobs_by_skills(
            JobOffer.objects.all(), user_profile, min_match_percentage=40
        )

        result_ids = {j.id for j in results}
        assert vague.id in result_ids
        vague_result = next(j for j in results if j.id == vague.id)
        # user "Backend Developer" ⊆ job "Backend Developer Sr." → title 90.
        # Sin skills → penalty 0 → match = 90.
        assert vague_result.match_percentage == 90

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

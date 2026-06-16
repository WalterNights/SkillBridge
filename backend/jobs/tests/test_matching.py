"""Tests de regresión para JobMatchingService.

Captura el comportamiento ACTUAL del matching antes del refactor del Commit 3
(unificación de taxonomía de skills). Tras el refactor estos tests deberían
seguir pasando, validando que la API pública del servicio no cambia.
"""
import pytest

from jobs.services.matching_service import JobMatchingService


@pytest.mark.unit
class TestCalculateMatchPercentage:
    """Tests unitarios de JobMatchingService.calculate_match_percentage."""

    def test_all_skills_match_returns_100(self):
        result = JobMatchingService.calculate_match_percentage(
            job_keywords=['python', 'django'],
            user_skills=['python', 'django'],
        )
        assert result['match_percentage'] == 100
        assert set(result['matched_skills']) == {'python', 'django'}
        assert result['missing_skills'] == []

    def test_no_skills_match_returns_0(self):
        result = JobMatchingService.calculate_match_percentage(
            job_keywords=['java', 'spring'],
            user_skills=['python', 'django'],
        )
        assert result['match_percentage'] == 0
        assert result['matched_skills'] == []
        assert set(result['missing_skills']) == {'java', 'spring'}

    def test_partial_match_rounds_correctly(self):
        # 2 de 3 = 66.67% → redondea a 67
        result = JobMatchingService.calculate_match_percentage(
            job_keywords=['python', 'django', 'react'],
            user_skills=['python', 'django'],
        )
        assert result['match_percentage'] == 67
        assert set(result['matched_skills']) == {'python', 'django'}
        assert result['missing_skills'] == ['react']

    def test_empty_job_keywords_returns_zero(self):
        result = JobMatchingService.calculate_match_percentage(
            job_keywords=[],
            user_skills=['python'],
        )
        assert result['match_percentage'] == 0

    def test_case_insensitive_matching(self):
        result = JobMatchingService.calculate_match_percentage(
            job_keywords=['Python', 'DJANGO'],
            user_skills=['python', 'django'],
        )
        assert result['match_percentage'] == 100

    def test_whitespace_is_stripped(self):
        result = JobMatchingService.calculate_match_percentage(
            job_keywords=['  python  ', ' django'],
            user_skills=['python', 'django'],
        )
        assert result['match_percentage'] == 100

    def test_aliases_resolve_to_canonical_skill(self):
        """Después del Commit 3: variantes como `react.js` matchean con
        `react` porque la taxonomía las trata como aliases del mismo skill.
        """
        result = JobMatchingService.calculate_match_percentage(
            job_keywords=['react.js'],
            user_skills=['react'],
        )
        assert result['match_percentage'] == 100
        assert 'react' in result['matched_skills']

    def test_multiple_aliases_normalize_consistently(self):
        """Varios aliases bidireccionales en una sola request."""
        result = JobMatchingService.calculate_match_percentage(
            job_keywords=['Node.js', 'PostgreSQL', 'C#', 'Spring Boot'],
            user_skills=['node', 'postgres', 'csharp', 'spring'],
        )
        assert result['match_percentage'] == 100
        assert set(result['matched_skills']) == {'node', 'postgresql', 'csharp', 'spring'}


@pytest.mark.django_db
class TestFilterJobsBySkills:
    """Tests de filter_jobs_by_skills con fixtures de DB reales."""

    def test_returns_only_jobs_above_threshold(self, user_profile):
        from jobs.models import JobOffer

        # user_profile.skills = "python, django, postgresql, docker"
        high = JobOffer.objects.create(
            title='Match alto', url='https://example.com/1',
            summary='.', keywords='python, django',  # 100%
        )
        low = JobOffer.objects.create(
            title='Match bajo', url='https://example.com/2',
            summary='.', keywords='java, spring, kotlin',  # 0%
        )

        results = JobMatchingService.filter_jobs_by_skills(
            JobOffer.objects.all(), user_profile, min_match_percentage=50
        )

        assert len(results) == 1
        assert results[0].id == high.id

    def test_empty_skills_returns_empty(self, user, db):
        from users.models import UserProfile

        profile = UserProfile.objects.create(
            user=user, first_name='No', last_name='Skills',
            phone='+1', city='-', professional_title='-',
            skills='', experience='-',
        )
        from jobs.models import JobOffer
        JobOffer.objects.create(
            title='x', url='https://example.com/x',
            summary='.', keywords='python',
        )

        assert JobMatchingService.filter_jobs_by_skills(
            JobOffer.objects.all(), profile
        ) == []

    def test_results_sorted_by_match_desc(self, user_profile):
        from jobs.models import JobOffer

        JobOffer.objects.create(
            title='50%', url='https://example.com/a',
            summary='.', keywords='python, java',  # python match → 50%
        )
        JobOffer.objects.create(
            title='100%', url='https://example.com/b',
            summary='.', keywords='python, django',  # ambos match → 100%
        )

        results = JobMatchingService.filter_jobs_by_skills(
            JobOffer.objects.all(), user_profile, min_match_percentage=50
        )

        assert [j.match_percentage for j in results] == sorted(
            [j.match_percentage for j in results], reverse=True
        )
        assert results[0].title == '100%'

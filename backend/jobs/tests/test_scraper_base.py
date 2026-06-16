"""Tests del módulo `jobs.adapters.scrapers.base`."""

import pytest

from jobs.adapters.scrapers.base import (
    JobOfferData,
    JobScraper,
    ScraperError,
    extract_keywords,
)


@pytest.mark.unit
class TestJobOfferData:
    def test_is_a_dataclass_with_required_fields(self):
        data = JobOfferData(
            title="t",
            company="c",
            location="l",
            summary="s",
            url="u",
            keywords="k",
        )
        assert data.title == "t"

    def test_is_frozen(self):
        data = JobOfferData(
            title="t",
            company="c",
            location="l",
            summary="s",
            url="u",
            keywords="k",
        )
        with pytest.raises(Exception):
            data.title = "x"  # type: ignore[misc]


@pytest.mark.unit
class TestExtractKeywords:
    def test_finds_canonical_skills(self):
        result = extract_keywords("We use Python and Django every day.")
        assert "python" in result.split(", ")
        assert "django" in result.split(", ")

    def test_normalizes_aliases(self):
        result = extract_keywords("Stack: React.js + Node.js + PostgreSQL")
        parts = set(result.split(", "))
        assert "react" in parts
        assert "node" in parts
        assert "postgresql" in parts

    def test_returns_canonical_only_no_aliases_leak(self):
        """`react.js` y `react` en el mismo texto cuentan como una sola."""
        result = extract_keywords("React.js and React are the same thing here.")
        parts = result.split(", ")
        assert parts.count("react") == 1
        assert "react.js" not in parts

    def test_empty_text_returns_empty_string(self):
        assert extract_keywords("") == ""

    def test_result_is_sorted(self):
        result = extract_keywords("Python, Java, AWS")
        parts = result.split(", ")
        assert parts == sorted(parts)


@pytest.mark.unit
class TestJobScraperABC:
    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            JobScraper()  # type: ignore[abstract]

    def test_subclass_must_implement_search(self):
        class Incomplete(JobScraper):
            portal_name = "incomplete"

        with pytest.raises(TypeError):
            Incomplete()  # type: ignore[abstract]


@pytest.mark.unit
def test_scraper_error_is_exception():
    assert issubclass(ScraperError, Exception)

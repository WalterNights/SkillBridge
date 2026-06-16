"""Tests de `JobService.save_new_offers`.

Verifica que el upsert por URL es idempotente y devuelve solo las nuevas.
"""

import pytest

from jobs.adapters.scrapers.base import JobOfferData
from jobs.models import JobOffer
from jobs.services.job_service import JobService


def _data(url: str, title: str = "A role") -> JobOfferData:
    return JobOfferData(
        title=title,
        company="Co",
        location="Remote",
        summary="Summary",
        url=url,
        keywords="python",
    )


@pytest.mark.django_db
class TestSaveNewOffers:
    def test_creates_offers_when_url_is_new(self):
        created = JobService.save_new_offers(
            [
                _data("https://example.com/a"),
                _data("https://example.com/b"),
            ]
        )
        assert len(created) == 2
        assert JobOffer.objects.count() == 2

    def test_does_not_duplicate_existing_url(self):
        JobOffer.objects.create(
            title="Old",
            company="Old",
            location="Old",
            summary="Old",
            url="https://example.com/a",
            keywords="python",
        )

        created = JobService.save_new_offers([_data("https://example.com/a")])

        assert created == []
        assert JobOffer.objects.count() == 1

    def test_partial_overlap_only_creates_new_ones(self):
        JobOffer.objects.create(
            title="Already there",
            company="X",
            location="X",
            summary="X",
            url="https://example.com/a",
            keywords="",
        )

        created = JobService.save_new_offers(
            [
                _data("https://example.com/a"),  # ya existe
                _data("https://example.com/b"),  # nueva
                _data("https://example.com/c"),  # nueva
            ]
        )

        assert len(created) == 2
        assert {o.url for o in created} == {
            "https://example.com/b",
            "https://example.com/c",
        }
        assert JobOffer.objects.count() == 3

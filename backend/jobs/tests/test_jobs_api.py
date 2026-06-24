"""Tests del endpoint /api/jobs/."""

import pytest

from jobs.models import JobOffer


@pytest.fixture
def offers_set():
    """Set diverso para tests de filtros: 4 ofertas en MX/CO con
    distintas modalidades."""
    return [
        JobOffer.objects.create(
            title="Remote MX 1", url="https://x.com/1",
            summary="", keywords="", portal="hireline",
            country="MX", modality="remote",
        ),
        JobOffer.objects.create(
            title="Onsite MX 1", url="https://x.com/2",
            summary="", keywords="", portal="hireline",
            country="MX", modality="onsite",
        ),
        JobOffer.objects.create(
            title="Hybrid CO 1", url="https://x.com/3",
            summary="", keywords="", portal="trabajos_co",
            country="CO", modality="hybrid",
        ),
        JobOffer.objects.create(
            title="Unknown AR 1", url="https://x.com/4",
            summary="", keywords="", portal="other",
            country="AR", modality="unknown",
        ),
    ]


@pytest.mark.integration
@pytest.mark.django_db
class TestJobsList:
    def test_unauthenticated_request_is_rejected(self, api_client):
        response = api_client.get("/api/jobs/jobs/")
        assert response.status_code == 401

    def test_returns_jobs_when_authenticated(self, authed_client, job_offer):
        response = authed_client.get("/api/jobs/jobs/")
        assert response.status_code == 200
        # DRF paginado: respuesta envuelta en `results`
        data = response.json()
        assert data["count"] == 1
        assert data["results"][0]["title"] == job_offer.title


@pytest.mark.integration
@pytest.mark.django_db
class TestJobsListFilters:
    def test_country_filter_single(self, authed_client, offers_set):
        response = authed_client.get("/api/jobs/jobs/?country=MX")
        assert response.status_code == 200
        titles = [r["title"] for r in response.json()["results"]]
        assert "Remote MX 1" in titles
        assert "Onsite MX 1" in titles
        assert "Hybrid CO 1" not in titles
        assert "Unknown AR 1" not in titles

    def test_country_filter_multi(self, authed_client, offers_set):
        response = authed_client.get("/api/jobs/jobs/?country=MX,CO")
        titles = sorted(r["title"] for r in response.json()["results"])
        assert titles == ["Hybrid CO 1", "Onsite MX 1", "Remote MX 1"]

    def test_modality_filter_single(self, authed_client, offers_set):
        response = authed_client.get("/api/jobs/jobs/?modality=remote")
        titles = [r["title"] for r in response.json()["results"]]
        assert titles == ["Remote MX 1"]

    def test_modality_filter_multi(self, authed_client, offers_set):
        response = authed_client.get("/api/jobs/jobs/?modality=remote,hybrid")
        titles = sorted(r["title"] for r in response.json()["results"])
        assert titles == ["Hybrid CO 1", "Remote MX 1"]

    def test_combined_country_and_modality(self, authed_client, offers_set):
        response = authed_client.get("/api/jobs/jobs/?country=MX&modality=remote")
        titles = [r["title"] for r in response.json()["results"]]
        assert titles == ["Remote MX 1"]

    def test_invalid_modality_silently_ignored(self, authed_client, offers_set):
        # ?modality=alien → no se filtra (no rompe el feed)
        response = authed_client.get("/api/jobs/jobs/?modality=alien")
        assert response.status_code == 200
        assert response.json()["count"] == 4

    def test_case_insensitive_country(self, authed_client, offers_set):
        # ?country=mx también funciona
        response = authed_client.get("/api/jobs/jobs/?country=mx")
        titles = [r["title"] for r in response.json()["results"]]
        assert {"Remote MX 1", "Onsite MX 1"} == set(titles)


@pytest.mark.integration
@pytest.mark.django_db
class TestFilterOptionsEndpoint:
    def test_returns_countries_and_modalities_with_counts(self, authed_client, offers_set):
        response = authed_client.get("/api/jobs/jobs/filter-options/")
        assert response.status_code == 200
        body = response.json()
        countries = {c["value"]: c["count"] for c in body["countries"]}
        assert countries == {"MX": 2, "CO": 1, "AR": 1}
        modalities = {m["value"]: m["count"] for m in body["modalities"]}
        assert modalities == {"remote": 1, "onsite": 1, "hybrid": 1, "unknown": 1}
        # Labels legibles incluidos
        for m in body["modalities"]:
            assert "label" in m

    def test_excludes_unknown_country_from_options(self, authed_client):
        JobOffer.objects.create(
            title="Sin país", url="https://x.com/xx",
            summary="", keywords="", portal="other",
            country="XX", modality="remote",
        )
        response = authed_client.get("/api/jobs/jobs/filter-options/")
        countries = [c["value"] for c in response.json()["countries"]]
        assert "XX" not in countries

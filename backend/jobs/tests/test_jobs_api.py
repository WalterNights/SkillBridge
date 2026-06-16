"""Tests del endpoint /api/jobs/."""

import pytest


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

"""Tests del dashboard admin — verifica paginación + auth + admin-only."""

import pytest


@pytest.mark.integration
@pytest.mark.django_db
class TestDashboardUserList:
    def test_requires_authentication(self, api_client):
        response = api_client.get("/api/dashboard/")
        assert response.status_code == 401

    def test_non_admin_user_is_forbidden(self, authed_client, user_profile):
        """Permisos endurecidos: solo admin lista perfiles. Antes el
        endpoint era IsAuthenticated y filtraba PII a cualquier user."""
        response = authed_client.get("/api/dashboard/")
        assert response.status_code == 403

    def test_admin_user_gets_paginated_response(self, api_client, admin_user, user_profile):
        api_client.force_authenticate(user=admin_user)
        response = api_client.get("/api/dashboard/")
        assert response.status_code == 200
        data = response.json()
        # Estructura paginada de DRF (regresión del fix viejo donde se
        # reemplazó APIView por ListAPIView).
        assert "count" in data
        assert "results" in data
        assert "next" in data
        assert "previous" in data


@pytest.mark.integration
@pytest.mark.django_db
class TestDashboardStats:
    def test_requires_authentication(self, api_client):
        response = api_client.get("/api/dashboard/stats/")
        assert response.status_code == 401

    def test_non_admin_user_is_forbidden(self, authed_client):
        response = authed_client.get("/api/dashboard/stats/")
        assert response.status_code == 403

    def test_admin_user_gets_stats(self, api_client, admin_user, user_profile):
        api_client.force_authenticate(user=admin_user)
        response = api_client.get("/api/dashboard/stats/")
        assert response.status_code == 200
        body = response.json()
        # Estructura esperada — el frontend depende de estas keys top-level.
        assert set(body.keys()) == {"users", "offers", "applications", "ignored"}
        assert {"total", "with_profile", "complete_profile"} <= set(body["users"].keys())
        assert {"total", "active", "inactive", "by_portal", "by_country"} <= set(body["offers"].keys())
        assert {"total", "by_status", "success_rate_pct"} <= set(body["applications"].keys())
        assert "total" in body["ignored"]

    def test_success_rate_handles_no_applications(self, api_client, admin_user):
        api_client.force_authenticate(user=admin_user)
        response = api_client.get("/api/dashboard/stats/")
        # Sin applications no debería dividir por cero — el view devuelve 0.0
        assert response.json()["applications"]["success_rate_pct"] == 0

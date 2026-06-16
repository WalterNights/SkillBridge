"""Tests del dashboard — verifica paginación + auth aplicada en Commit 1."""

import pytest


@pytest.mark.integration
@pytest.mark.django_db
class TestDashboardUserList:
    def test_requires_authentication(self, api_client):
        response = api_client.get("/api/dashboard/")
        assert response.status_code == 401

    def test_returns_paginated_response(self, authed_client, user_profile):
        response = authed_client.get("/api/dashboard/")
        assert response.status_code == 200
        data = response.json()
        # Asegura que el endpoint devuelve estructura paginada (regresión
        # del fix del Commit 1, donde se reemplazó APIView por ListAPIView).
        assert "count" in data
        assert "results" in data
        assert "next" in data
        assert "previous" in data

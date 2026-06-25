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


@pytest.mark.integration
@pytest.mark.django_db
class TestUserRoleUpdate:
    """PATCH /api/dashboard/users/{id}/role/ — promover/degradar staff/super."""

    @pytest.fixture
    def staff_only_user(self, django_user_model):
        """Admin staff pero NO superuser — para tests de gating de is_superuser."""
        return django_user_model.objects.create_user(
            username="staffadmin",
            email="staffadmin@example.com",
            password="testpass123",
            is_staff=True,
        )

    @pytest.fixture
    def target_user(self, django_user_model):
        """User regular sobre el que se aplican los cambios de rol."""
        return django_user_model.objects.create_user(
            username="target",
            email="target@example.com",
            password="testpass123",
        )

    def _url(self, user_id: int) -> str:
        return f"/api/dashboard/users/{user_id}/role/"

    def test_requires_authentication(self, api_client, target_user):
        response = api_client.patch(
            self._url(target_user.id), {"is_staff": True}, format="json"
        )
        assert response.status_code == 401

    def test_non_admin_is_forbidden(self, authed_client, target_user):
        response = authed_client.patch(
            self._url(target_user.id), {"is_staff": True}, format="json"
        )
        assert response.status_code == 403

    def test_404_when_target_missing(self, api_client, admin_user):
        api_client.force_authenticate(user=admin_user)
        response = api_client.patch(self._url(999999), {"is_staff": True}, format="json")
        assert response.status_code == 404

    def test_superuser_can_promote_to_staff(self, api_client, admin_user, target_user):
        api_client.force_authenticate(user=admin_user)
        response = api_client.patch(
            self._url(target_user.id), {"is_staff": True}, format="json"
        )
        assert response.status_code == 200
        target_user.refresh_from_db()
        assert target_user.is_staff is True
        body = response.json()
        assert body["is_staff"] is True
        assert body["id"] == target_user.id

    def test_superuser_can_demote_staff(self, api_client, admin_user, staff_only_user):
        api_client.force_authenticate(user=admin_user)
        response = api_client.patch(
            self._url(staff_only_user.id), {"is_staff": False}, format="json"
        )
        assert response.status_code == 200
        staff_only_user.refresh_from_db()
        assert staff_only_user.is_staff is False

    def test_superuser_can_promote_to_superuser(
        self, api_client, admin_user, target_user
    ):
        api_client.force_authenticate(user=admin_user)
        response = api_client.patch(
            self._url(target_user.id),
            {"is_staff": True, "is_superuser": True},
            format="json",
        )
        assert response.status_code == 200
        target_user.refresh_from_db()
        assert target_user.is_staff is True
        assert target_user.is_superuser is True

    def test_staff_admin_cannot_toggle_is_superuser(
        self, api_client, staff_only_user, target_user
    ):
        """Anti-escalado: un admin staff no puede crear/quitar superusers."""
        api_client.force_authenticate(user=staff_only_user)
        response = api_client.patch(
            self._url(target_user.id), {"is_superuser": True}, format="json"
        )
        assert response.status_code == 403
        assert response.json()["error"] == "superuser_required"
        target_user.refresh_from_db()
        assert target_user.is_superuser is False

    def test_staff_admin_can_toggle_is_staff(
        self, api_client, staff_only_user, target_user
    ):
        """Staff puede promover a otro a staff (siempre que no toque super)."""
        api_client.force_authenticate(user=staff_only_user)
        response = api_client.patch(
            self._url(target_user.id), {"is_staff": True}, format="json"
        )
        assert response.status_code == 200
        target_user.refresh_from_db()
        assert target_user.is_staff is True

    def test_self_demote_is_blocked(self, api_client, admin_user):
        """Anti-lockout: el admin no puede quitarse sus propios privilegios."""
        api_client.force_authenticate(user=admin_user)
        response = api_client.patch(
            self._url(admin_user.id), {"is_staff": False}, format="json"
        )
        assert response.status_code == 400
        assert response.json()["error"] == "self_demote_forbidden"
        admin_user.refresh_from_db()
        assert admin_user.is_staff is True

    def test_self_demote_superuser_is_blocked(self, api_client, admin_user):
        api_client.force_authenticate(user=admin_user)
        response = api_client.patch(
            self._url(admin_user.id), {"is_superuser": False}, format="json"
        )
        assert response.status_code == 400
        admin_user.refresh_from_db()
        assert admin_user.is_superuser is True

    def test_empty_payload_returns_400(self, api_client, admin_user, target_user):
        api_client.force_authenticate(user=admin_user)
        response = api_client.patch(self._url(target_user.id), {}, format="json")
        assert response.status_code == 400
        assert response.json()["error"] == "no_fields"

    def test_ignores_unknown_fields(self, api_client, admin_user, target_user):
        """Mass-assignment defense: sólo se aplican is_staff/is_superuser."""
        api_client.force_authenticate(user=admin_user)
        original_username = target_user.username
        response = api_client.patch(
            self._url(target_user.id),
            {"is_staff": True, "username": "hacker", "email": "evil@x.com"},
            format="json",
        )
        assert response.status_code == 200
        target_user.refresh_from_db()
        assert target_user.is_staff is True
        assert target_user.username == original_username
        assert target_user.email == "target@example.com"

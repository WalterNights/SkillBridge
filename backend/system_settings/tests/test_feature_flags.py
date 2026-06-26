"""Tests de los endpoints de feature flags.

Cubre:
- Endpoint público devuelve un dict {key: bool} y no requiere auth.
- Endpoint admin requiere is_staff.
- Admin puede togglear `value_bool` y editar `description` pero NO crear,
  borrar ni renombrar `key`.
- Data migration sembró el flag `show_low_match_filter`.
"""

from __future__ import annotations

import pytest

from system_settings.models import SystemSetting


@pytest.mark.django_db
class TestPublicFeatureFlags:
    """`GET /api/system/feature-flags/` — público, sin auth."""

    def test_returns_dict_of_flags(self, api_client):
        SystemSetting.objects.update_or_create(
            key="show_low_match_filter",
            defaults={"value_bool": True, "description": "x"},
        )
        response = api_client.get("/api/system/feature-flags/")
        assert response.status_code == 200
        body = response.json()
        # La data migration siembra el flag con default False; el setup
        # de este test lo cambia a True.
        assert body.get("show_low_match_filter") is True

    def test_no_auth_required(self, api_client):
        """Tiene que responder sin Authorization header — el SPA shell
        lo lee antes del login."""
        response = api_client.get("/api/system/feature-flags/")
        assert response.status_code == 200

    def test_seed_migration_created_default_flag(self, db):
        """Sanity check: la data migration sembró el flag inicial."""
        assert SystemSetting.objects.filter(key="show_low_match_filter").exists()


@pytest.mark.django_db
class TestAdminFeatureFlags:
    """`GET/PATCH /api/system/admin/feature-flags/{key}/` — requiere is_staff."""

    def test_anonymous_gets_401_or_403(self, api_client):
        response = api_client.get("/api/system/admin/feature-flags/")
        assert response.status_code in (401, 403)

    def test_regular_user_gets_403(self, authed_client):
        response = authed_client.get("/api/system/admin/feature-flags/")
        assert response.status_code == 403

    def test_admin_lists_flags(self, api_client, admin_user):
        api_client.force_authenticate(user=admin_user)
        response = api_client.get("/api/system/admin/feature-flags/")
        assert response.status_code == 200
        body = response.json()
        # DRF aplica paginación global → body es {count, results}.
        # En este endpoint chico no nos importa la paginación, pero
        # leemos `results` para no depender de si está habilitada.
        items = body.get("results", body) if isinstance(body, dict) else body
        keys = [item["key"] for item in items]
        assert "show_low_match_filter" in keys

    def test_admin_can_toggle_value_bool(self, api_client, admin_user):
        api_client.force_authenticate(user=admin_user)
        before = SystemSetting.objects.get(key="show_low_match_filter").value_bool
        response = api_client.patch(
            "/api/system/admin/feature-flags/show_low_match_filter/",
            {"value_bool": not before},
            format="json",
        )
        assert response.status_code == 200
        after = SystemSetting.objects.get(key="show_low_match_filter").value_bool
        assert after is (not before)

    def test_admin_cannot_change_key(self, api_client, admin_user):
        """`key` es read-only — los flags se crean en data migrations."""
        api_client.force_authenticate(user=admin_user)
        response = api_client.patch(
            "/api/system/admin/feature-flags/show_low_match_filter/",
            {"key": "renamed_flag"},
            format="json",
        )
        # 200 OK pero el key NO cambia (read-only en serializer)
        assert response.status_code == 200
        assert SystemSetting.objects.filter(key="show_low_match_filter").exists()
        assert not SystemSetting.objects.filter(key="renamed_flag").exists()

    def test_admin_cannot_create(self, api_client, admin_user):
        """POST no está expuesto — el ViewSet solo monta List+Retrieve+Update."""
        api_client.force_authenticate(user=admin_user)
        response = api_client.post(
            "/api/system/admin/feature-flags/",
            {"key": "new_flag", "value_bool": True},
            format="json",
        )
        assert response.status_code == 405  # Method Not Allowed

    def test_admin_cannot_delete(self, api_client, admin_user):
        api_client.force_authenticate(user=admin_user)
        response = api_client.delete(
            "/api/system/admin/feature-flags/show_low_match_filter/"
        )
        assert response.status_code == 405

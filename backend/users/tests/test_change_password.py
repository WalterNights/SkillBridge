"""Tests del endpoint POST /api/users/me/change-password/.

Cubre:
  - Auth gating (401 anon).
  - Rate limit (10/h por user).
  - Validación de pass actual.
  - Validación de coincidencia y diferencia con la actual.
  - Persistencia real del nuevo hash (login con la pass vieja falla,
    con la nueva funciona).
"""

import pytest


@pytest.fixture(autouse=True)
def _clear_ratelimit_cache():
    """@ratelimit(10/h, key='user') usa LocMem; sin reset, los tests
    se contaminan entre sí."""
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()


_URL = "/api/users/me/change-password/"
_INITIAL_PASS = "testpass123"
_NEW_PASS = "newpassword456"


@pytest.mark.integration
@pytest.mark.django_db
class TestChangePassword:
    def test_unauth_is_rejected(self, api_client):
        response = api_client.post(
            _URL,
            {
                "current_password": _INITIAL_PASS,
                "new_password": _NEW_PASS,
                "confirm_password": _NEW_PASS,
            },
            format="json",
        )
        assert response.status_code == 401

    def test_wrong_current_password_returns_400(self, authed_client):
        response = authed_client.post(
            _URL,
            {
                "current_password": "incorrect-wrong-pass",
                "new_password": _NEW_PASS,
                "confirm_password": _NEW_PASS,
            },
            format="json",
        )
        assert response.status_code == 400
        assert "current_password" in response.json()

    def test_confirm_mismatch_returns_400(self, authed_client):
        response = authed_client.post(
            _URL,
            {
                "current_password": _INITIAL_PASS,
                "new_password": _NEW_PASS,
                "confirm_password": "different-confirm",
            },
            format="json",
        )
        assert response.status_code == 400
        assert "confirm_password" in response.json()

    def test_new_password_too_short_returns_400(self, authed_client):
        response = authed_client.post(
            _URL,
            {
                "current_password": _INITIAL_PASS,
                "new_password": "short",
                "confirm_password": "short",
            },
            format="json",
        )
        assert response.status_code == 400
        assert "new_password" in response.json()

    def test_new_same_as_current_returns_400(self, authed_client):
        response = authed_client.post(
            _URL,
            {
                "current_password": _INITIAL_PASS,
                "new_password": _INITIAL_PASS,
                "confirm_password": _INITIAL_PASS,
            },
            format="json",
        )
        assert response.status_code == 400
        assert "new_password" in response.json()

    def test_happy_path_persists_new_hash(self, authed_client, user):
        response = authed_client.post(
            _URL,
            {
                "current_password": _INITIAL_PASS,
                "new_password": _NEW_PASS,
                "confirm_password": _NEW_PASS,
            },
            format="json",
        )
        assert response.status_code == 200
        user.refresh_from_db()
        # Old pass debe fallar, nueva debe funcionar
        assert user.check_password(_INITIAL_PASS) is False
        assert user.check_password(_NEW_PASS) is True

    def test_rate_limit_blocks_after_10_per_hour(self, authed_client):
        """10 intentos fallidos consecutivos → el 11 debe ser bloqueado
        (django-ratelimit con block=True devuelve 403)."""
        bad_payload = {
            "current_password": "wrong",
            "new_password": _NEW_PASS,
            "confirm_password": _NEW_PASS,
        }
        for i in range(10):
            r = authed_client.post(_URL, bad_payload, format="json")
            # Los 10 primeros fallan con 400 (current incorrecta)
            assert r.status_code == 400, f"intento {i} debería pasar el rate-limit"

        eleventh = authed_client.post(_URL, bad_payload, format="json")
        # 11º intento → bloqueado por rate-limit
        assert eleventh.status_code == 403

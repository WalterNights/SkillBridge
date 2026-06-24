"""Tests de los endpoints de 2FA TOTP.

Cubre:
  - Auth gating (401 sin token)
  - Status: enabled/disabled
  - Setup: genera secret, reusa si ya hay uno sin activar, 409 si activo
  - Activate: rechaza código inválido, acepta válido
  - Disable: rechaza código inválido, limpia secret al éxito
"""

import pytest
import pyotp


@pytest.fixture
def authed_user(user, api_client):
    """User autenticado + cliente listo para pegarle a /2fa/*."""
    api_client.force_authenticate(user=user)
    return user, api_client


@pytest.mark.integration
@pytest.mark.django_db
class TestStatus:
    URL = "/api/users/2fa/status/"

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.get(self.URL)
        assert response.status_code == 401

    def test_disabled_by_default(self, authed_user):
        user, client = authed_user
        response = client.get(self.URL)
        assert response.status_code == 200
        assert response.json() == {"enabled": False}

    def test_enabled_when_user_has_flag_on(self, authed_user):
        user, client = authed_user
        user.totp_enabled = True
        user.save()
        response = client.get(self.URL)
        assert response.json() == {"enabled": True}


@pytest.mark.integration
@pytest.mark.django_db
class TestSetup:
    URL = "/api/users/2fa/setup/"

    def test_generates_secret_first_time(self, authed_user):
        user, client = authed_user
        assert user.totp_secret == ""
        response = client.post(self.URL)
        assert response.status_code == 200
        body = response.json()
        assert "secret" in body
        assert "qr_data_url" in body
        assert body["qr_data_url"].startswith("data:image/png;base64,")
        # Persistido
        user.refresh_from_db()
        assert user.totp_secret == body["secret"]

    def test_reuses_existing_secret_if_not_activated(self, authed_user):
        user, client = authed_user
        # Primera llamada genera
        first = client.post(self.URL).json()
        # Segunda llamada NO regenera — devuelve el mismo
        second = client.post(self.URL).json()
        assert first["secret"] == second["secret"]

    def test_returns_409_if_already_enabled(self, authed_user):
        user, client = authed_user
        user.totp_secret = pyotp.random_base32()
        user.totp_enabled = True
        user.save()
        response = client.post(self.URL)
        assert response.status_code == 409
        assert response.json()["error"] == "already_enabled"


@pytest.mark.integration
@pytest.mark.django_db
class TestActivate:
    URL = "/api/users/2fa/activate/"

    def test_invalid_code_returns_400(self, authed_user):
        user, client = authed_user
        user.totp_secret = pyotp.random_base32()
        user.save()
        response = client.post(self.URL, {"code": "000000"}, format="json")
        assert response.status_code == 400
        assert response.json()["error"] == "invalid_code"
        # No se activó
        user.refresh_from_db()
        assert user.totp_enabled is False

    def test_valid_code_activates(self, authed_user):
        user, client = authed_user
        secret = pyotp.random_base32()
        user.totp_secret = secret
        user.save()
        current_code = pyotp.TOTP(secret).now()
        response = client.post(self.URL, {"code": current_code}, format="json")
        assert response.status_code == 200
        assert response.json() == {"enabled": True}
        user.refresh_from_db()
        assert user.totp_enabled is True
        # Secret NO se borra al activar — sigue ahí para verify futura
        assert user.totp_secret == secret

    def test_returns_400_if_no_secret_set(self, authed_user):
        user, client = authed_user
        response = client.post(self.URL, {"code": "123456"}, format="json")
        assert response.status_code == 400
        assert response.json()["error"] == "setup_required"

    def test_returns_409_if_already_enabled(self, authed_user):
        user, client = authed_user
        user.totp_secret = pyotp.random_base32()
        user.totp_enabled = True
        user.save()
        response = client.post(self.URL, {"code": "any"}, format="json")
        assert response.status_code == 409

    def test_accepts_code_with_spaces(self, authed_user):
        """Algunos authenticator apps muestran '123 456' — debe aceptarlo."""
        user, client = authed_user
        secret = pyotp.random_base32()
        user.totp_secret = secret
        user.save()
        current_code = pyotp.TOTP(secret).now()
        spaced = current_code[:3] + " " + current_code[3:]
        response = client.post(self.URL, {"code": spaced}, format="json")
        assert response.status_code == 200


@pytest.mark.integration
@pytest.mark.django_db
class TestDisable:
    URL = "/api/users/2fa/disable/"

    def test_noop_if_not_enabled(self, authed_user):
        user, client = authed_user
        response = client.post(self.URL, {"code": ""}, format="json")
        assert response.status_code == 200
        assert response.json() == {"enabled": False}

    def test_invalid_code_returns_400(self, authed_user):
        user, client = authed_user
        user.totp_secret = pyotp.random_base32()
        user.totp_enabled = True
        user.save()
        response = client.post(self.URL, {"code": "000000"}, format="json")
        assert response.status_code == 400
        # Sigue activo
        user.refresh_from_db()
        assert user.totp_enabled is True

    def test_valid_code_disables_and_clears_secret(self, authed_user):
        user, client = authed_user
        secret = pyotp.random_base32()
        user.totp_secret = secret
        user.totp_enabled = True
        user.save()
        current_code = pyotp.TOTP(secret).now()
        response = client.post(self.URL, {"code": current_code}, format="json")
        assert response.status_code == 200
        assert response.json() == {"enabled": False}
        user.refresh_from_db()
        assert user.totp_enabled is False
        assert user.totp_secret == ""  # cleared para forzar setup desde cero al re-enable

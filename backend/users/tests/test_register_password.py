"""Validación de contraseña en el registro (server-side).

Caso real 2026-10: un usuario no pudo registrarse con "buenas.1234" — el
frontend solo aceptaba ciertos símbolos — mientras el backend no validaba
nada (por API se podía registrar "1"). Ahora el server corre los
AUTH_PASSWORD_VALIDATORS de Django con mensajes en español.
"""

import pytest

from users.models import PasswordResetToken, User

REGISTER_URL = "/api/users/register/"
COMPANY_URL = "/api/companies/register/"
CHANGE_URL = "/api/users/me/change-password/"
RESET_VERIFY_URL = "/api/users/password-reset/verify/"


@pytest.fixture(autouse=True)
def _clear_ratelimit_cache():
    """El registro limita a 5/min por IP y el bucket se comparte entre tests."""
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()


def _register(api_client, password: str, username: str = "lautaro"):
    return api_client.post(
        REGISTER_URL,
        {"username": username, "email": f"{username}@example.com", "password": password},
        format="json",
    )


@pytest.mark.integration
@pytest.mark.django_db
class TestRegisterPassword:
    def test_password_with_dot_is_accepted(self, api_client):
        assert _register(api_client, "buenas.1234").status_code == 201
        assert User.objects.filter(username="lautaro").exists()

    @pytest.mark.parametrize(
        "password",
        [
            "1",  # muy corta
            "12345678",  # solo números
            "password",  # común
        ],
    )
    def test_weak_passwords_are_rejected(self, api_client, password):
        response = _register(api_client, password)
        assert response.status_code == 400
        assert response.json()["password"]
        assert not User.objects.filter(username="lautaro").exists()

    def test_password_too_similar_to_username_is_rejected(self, api_client):
        response = _register(api_client, "lautaro2026", username="lautaro2026")
        assert response.status_code == 400

    def test_every_error_message_is_in_spanish(self, api_client):
        """Cada mensaje, no solo alguno: el de largo mínimo de Django no tiene
        traducción y salía en inglés en producción."""
        messages = _register(api_client, "1").json()["password"]
        assert len(messages) >= 2
        for message in messages:
            assert "contraseña" in message.lower(), message

    def test_too_short_message_mentions_min_length(self, api_client):
        messages = _register(api_client, "ab.1").json()["password"]
        assert any("al menos 8 caracteres" in m for m in messages)

    def test_company_register_also_validates(self, api_client):
        response = api_client.post(
            COMPANY_URL,
            {
                "email": "rrhh@acme.com",
                "password": "12345678",
                "legal_name": "Acme",
                "responsible_name": "Ana",
                "responsible_role": "CEO",
                "responsible_email": "ana@acme.com",
            },
            format="json",
        )
        assert response.status_code == 400
        assert "password" in response.json()


@pytest.mark.integration
@pytest.mark.django_db
class TestChangeAndResetPassword:
    """Mismos validadores en cambio y restablecimiento de contraseña."""

    def test_change_password_rejects_weak_password(self, authed_client):
        response = authed_client.post(
            CHANGE_URL,
            {
                "current_password": "testpass123",
                "new_password": "12345678",
                "confirm_password": "12345678",
            },
            format="json",
        )
        assert response.status_code == 400
        assert response.json()["new_password"]

    def test_change_password_accepts_dot_symbol(self, authed_client, user):
        response = authed_client.post(
            CHANGE_URL,
            {
                "current_password": "testpass123",
                "new_password": "buenas.1234",
                "confirm_password": "buenas.1234",
            },
            format="json",
        )
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.check_password("buenas.1234")

    def test_reset_rejects_weak_password_with_valid_code(self, api_client, user):
        token = PasswordResetToken.objects.create(user=user, code="12345678")
        response = api_client.post(
            RESET_VERIFY_URL,
            {"email": user.email, "code": token.code, "new_password": "password"},
            format="json",
        )
        assert response.status_code == 400
        assert response.json()["new_password"]

    def test_reset_with_wrong_code_keeps_generic_error(self, api_client, user):
        """El error de código (anti user-enumeration) va antes que el de la
        contraseña: con código inválido no se dice nada de la contraseña."""
        response = api_client.post(
            RESET_VERIFY_URL,
            {"email": user.email, "code": "00000000", "new_password": "password"},
            format="json",
        )
        assert response.status_code == 400
        assert "new_password" not in response.json()

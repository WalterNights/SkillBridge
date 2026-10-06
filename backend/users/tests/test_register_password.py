"""Validación de contraseña en el registro (server-side).

Caso real 2026-10: un usuario no pudo registrarse con "buenas.1234" — el
frontend solo aceptaba ciertos símbolos — mientras el backend no validaba
nada (por API se podía registrar "1"). Ahora el server corre los
AUTH_PASSWORD_VALIDATORS de Django con mensajes en español.
"""

import pytest

from users.models import User

REGISTER_URL = "/api/users/register/"
COMPANY_URL = "/api/companies/register/"


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

    def test_error_messages_are_in_spanish(self, api_client):
        messages = " ".join(_register(api_client, "1").json()["password"])
        assert "contraseña" in messages.lower()

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

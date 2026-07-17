"""Tests del flow OAuth de LinkedIn.

Mockeamos las requests externas a `requests.post` (token) y
`requests.get` (userinfo) para no pegarle al servidor real de LinkedIn
durante los tests.
"""

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test.utils import override_settings

User = get_user_model()


@pytest.fixture(autouse=True)
def configure_linkedin_settings():
    """Setea las settings de LinkedIn para que los tests no peguen el
    503 de config-missing."""
    with override_settings(
        LINKEDIN_CLIENT_ID="test-client-id",
        LINKEDIN_CLIENT_SECRET="test-client-secret",
        LINKEDIN_REDIRECT_URI="http://localhost:8000/api/auth/linkedin/callback/",
        LINKEDIN_FRONTEND_COMPLETE_URL="http://localhost:4200/auth/linkedin/complete",
    ):
        yield


@pytest.fixture(autouse=True)
def clear_cache():
    """Asegurar que el cache esté limpio entre tests — el state token
    cachea en memoria y los tests interfieren si no se limpia."""
    cache.clear()
    yield
    cache.clear()


def _mock_token_response(status_code=200, json_data=None):
    """Crea un mock de la response del token endpoint."""
    mock = type("MockResponse", (), {})()
    mock.status_code = status_code
    mock.text = ""
    mock.json = lambda: json_data or {"access_token": "fake-access-token"}
    return mock


def _mock_userinfo_response(status_code=200, json_data=None):
    mock = type("MockResponse", (), {})()
    mock.status_code = status_code
    mock.text = ""
    default = {
        "sub": "linkedin-user-123",
        "email": "walter@example.com",
        "given_name": "Walter",
        "family_name": "Hernández",
    }
    mock.json = lambda: json_data or default
    return mock


@pytest.mark.integration
@pytest.mark.django_db
class TestLinkedInStart:
    def test_returns_302_to_linkedin_with_state(self, api_client):
        response = api_client.get("/api/auth/linkedin/start/")
        assert response.status_code == 302
        location = response["Location"]
        assert location.startswith("https://www.linkedin.com/oauth/v2/authorization")
        assert "state=" in location
        assert "client_id=test-client-id" in location
        assert "scope=openid+profile+email" in location

    def test_returns_503_when_not_configured(self, api_client):
        with override_settings(LINKEDIN_CLIENT_ID=""):
            response = api_client.get("/api/auth/linkedin/start/")
        assert response.status_code == 503


@pytest.mark.integration
@pytest.mark.django_db
class TestLinkedInCallback:
    def _start_and_get_state(self, api_client):
        """Helper — corre /start/ para obtener un state válido cacheado."""
        response = api_client.get("/api/auth/linkedin/start/")
        location = response["Location"]
        # Extraer state del URL
        from urllib.parse import parse_qs, urlparse
        qs = parse_qs(urlparse(location).query)
        return qs["state"][0]

    def test_creates_new_user_on_first_login(self, api_client):
        state = self._start_and_get_state(api_client)
        assert not User.objects.filter(linkedin_user_id="linkedin-user-123").exists()

        with patch("users.oauth_linkedin.requests.post") as mock_post, patch(
            "users.oauth_linkedin.requests.get"
        ) as mock_get:
            mock_post.return_value = _mock_token_response()
            mock_get.return_value = _mock_userinfo_response()
            response = api_client.get(
                f"/api/auth/linkedin/callback/?code=test-code&state={state}"
            )

        assert response.status_code == 302
        location = response["Location"]
        assert location.startswith("http://localhost:4200/auth/linkedin/complete")
        assert "access=" in location
        assert "refresh=" in location
        # Usuario creado
        user = User.objects.get(linkedin_user_id="linkedin-user-123")
        assert user.email == "walter@example.com"
        assert user.first_name == "Walter"
        assert not user.has_usable_password()

    def test_creates_userprofile_stub_on_first_login(self, api_client):
        """Regresión: sin este stub, un user que cierra el navegador antes
        de completar el wizard queda con `User` pero sin `UserProfile` —
        aparece huérfano en el admin y el matcher lo ignora."""
        from users.models import UserProfile

        state = self._start_and_get_state(api_client)
        with patch("users.oauth_linkedin.requests.post") as mock_post, patch(
            "users.oauth_linkedin.requests.get"
        ) as mock_get:
            mock_post.return_value = _mock_token_response()
            mock_get.return_value = _mock_userinfo_response()
            api_client.get(f"/api/auth/linkedin/callback/?code=test-code&state={state}")

        user = User.objects.get(linkedin_user_id="linkedin-user-123")
        profile = UserProfile.objects.get(user=user)
        # LinkedIn nos dio first/last name — los propagamos al perfil.
        assert profile.first_name == "Walter"
        assert profile.last_name == "Hernández"
        # Los demás campos requeridos quedan vacíos — el wizard los llena.
        assert profile.phone == ""
        assert profile.city == ""
        assert profile.professional_title == ""

    def test_idempotent_existing_linkedin_user(self, api_client, django_user_model):
        existing = django_user_model.objects.create_user(
            username="existing",
            email="existing@example.com",
            password="x",
        )
        existing.linkedin_user_id = "linkedin-user-123"
        existing.save()

        state = self._start_and_get_state(api_client)
        with patch("users.oauth_linkedin.requests.post") as mock_post, patch(
            "users.oauth_linkedin.requests.get"
        ) as mock_get:
            mock_post.return_value = _mock_token_response()
            mock_get.return_value = _mock_userinfo_response()
            response = api_client.get(
                f"/api/auth/linkedin/callback/?code=test-code&state={state}"
            )

        assert response.status_code == 302
        # No se creó un user nuevo — el existente queda
        assert User.objects.filter(linkedin_user_id="linkedin-user-123").count() == 1

    def test_links_existing_email_account(self, api_client, django_user_model):
        # User con mismo email pero sin linkedin_user_id (registrado con
        # password normal antes). Debería linkearse.
        existing = django_user_model.objects.create_user(
            username="walter_old",
            email="walter@example.com",
            password="x",
        )
        assert existing.linkedin_user_id is None

        state = self._start_and_get_state(api_client)
        with patch("users.oauth_linkedin.requests.post") as mock_post, patch(
            "users.oauth_linkedin.requests.get"
        ) as mock_get:
            mock_post.return_value = _mock_token_response()
            mock_get.return_value = _mock_userinfo_response()
            response = api_client.get(
                f"/api/auth/linkedin/callback/?code=test-code&state={state}"
            )

        assert response.status_code == 302
        existing.refresh_from_db()
        assert existing.linkedin_user_id == "linkedin-user-123"
        # NO se creó un nuevo user con el email duplicado
        assert User.objects.filter(email__iexact="walter@example.com").count() == 1

    def test_rejects_invalid_state(self, api_client):
        response = api_client.get(
            "/api/auth/linkedin/callback/?code=x&state=never-cached"
        )
        assert response.status_code == 302
        assert "error=invalid_state" in response["Location"]

    def test_rejects_missing_params(self, api_client):
        response = api_client.get("/api/auth/linkedin/callback/")
        assert response.status_code == 302
        assert "error=missing_params" in response["Location"]

    def test_handles_user_cancel(self, api_client):
        response = api_client.get(
            "/api/auth/linkedin/callback/?error=user_cancelled_login"
        )
        assert response.status_code == 302
        assert "error=user_cancelled_login" in response["Location"]

    def test_handles_token_exchange_failure(self, api_client):
        state = self._start_and_get_state(api_client)
        with patch("users.oauth_linkedin.requests.post") as mock_post:
            mock_post.return_value = _mock_token_response(
                status_code=400, json_data={"error": "invalid_grant"}
            )
            response = api_client.get(
                f"/api/auth/linkedin/callback/?code=test-code&state={state}"
            )
        assert response.status_code == 302
        assert "error=token_exchange_failed" in response["Location"]

    def test_state_is_single_use(self, api_client):
        state = self._start_and_get_state(api_client)
        with patch("users.oauth_linkedin.requests.post") as mock_post, patch(
            "users.oauth_linkedin.requests.get"
        ) as mock_get:
            mock_post.return_value = _mock_token_response()
            mock_get.return_value = _mock_userinfo_response()
            # Primera llamada — éxito
            r1 = api_client.get(
                f"/api/auth/linkedin/callback/?code=test-code&state={state}"
            )
            assert "access=" in r1["Location"]
            # Segunda llamada con el mismo state — invalid (state consumido)
            r2 = api_client.get(
                f"/api/auth/linkedin/callback/?code=test-code&state={state}"
            )
            assert "error=invalid_state" in r2["Location"]

"""Tests del lado empresa del marketplace.

Cubre:
  - POST /api/companies/register/ — happy path + validaciones + anti-
    enumeration + mass-assignment defense + rate-limit.
  - GET/PATCH /api/companies/me/ — gating por account_type + permisos.
  - JWT payload — account_type viaja en el token + user_name/photo
    se llenan desde CompanyProfile para cuentas empresa.
  - UserProfile.visible_to_companies — toggle desde el endpoint
    estándar de /profiles/.
"""

import pytest

from users.models import CompanyProfile, User, UserProfile


@pytest.fixture(autouse=True)
def _clear_ratelimit_cache():
    """Rate-limit decorators usan LocMem cache shared entre tests."""
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()


_VALID_COMPANY_PAYLOAD = {
    "email": "hello@acme.com",
    "password": "secret-pass-123",
    "legal_name": "Acme Inc.",
    "country": "CO",
    "city": "Medellín",
    "industry": "Tech",
    "website": "https://acme.com",
    "size": "11-50",
    "short_description": "Building rocket-fuel for SaaS.",
    "responsible_name": "Jane Doe",
    "responsible_role": "Head of People",
    "responsible_email": "jane@acme.com",
}


# ──────────────────────────────────────────────────────────────────────
# REGISTER
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.integration
@pytest.mark.django_db
class TestCompanyRegister:
    URL = "/api/companies/register/"

    def test_happy_path_creates_user_and_company(self, api_client):
        response = api_client.post(self.URL, _VALID_COMPANY_PAYLOAD, format="json")
        assert response.status_code == 201, response.json()

        # User: account_type forced to company, password hasheado.
        user = User.objects.get(email="hello@acme.com")
        assert user.account_type == User.ACCOUNT_TYPE_COMPANY
        assert user.is_staff is False
        assert user.is_superuser is False
        assert user.check_password("secret-pass-123") is True

        # CompanyProfile linked + datos persisted.
        company = CompanyProfile.objects.get(user=user)
        assert company.legal_name == "Acme Inc."
        assert company.responsible_email == "jane@acme.com"
        assert company.size == "11-50"

        # Response shape — usa CompanyProfileSerializer.
        body = response.json()
        assert "data" in body
        assert body["data"]["legal_name"] == "Acme Inc."
        assert body["data"]["user"]["account_type"] == "company"

    def test_username_derived_from_email(self, api_client):
        api_client.post(self.URL, _VALID_COMPANY_PAYLOAD, format="json")
        user = User.objects.get(email="hello@acme.com")
        assert user.username == "hello"

    def test_username_collision_gets_suffix(self, api_client, django_user_model):
        django_user_model.objects.create(
            username="hello", email="other@example.com"
        )
        api_client.post(self.URL, _VALID_COMPANY_PAYLOAD, format="json")
        user = User.objects.get(email="hello@acme.com")
        # Sufijo aleatorio agregado al username base.
        assert user.username.startswith("hello-")
        assert len(user.username) > len("hello-")

    def test_duplicate_email_returns_generic_error(self, api_client, django_user_model):
        """Anti user-enumeration: si el email ya existe, devolvemos
        mensaje genérico (no `email_taken`)."""
        django_user_model.objects.create(
            username="other", email="hello@acme.com"
        )
        response = api_client.post(self.URL, _VALID_COMPANY_PAYLOAD, format="json")
        assert response.status_code == 400
        body = response.json()
        # No revelamos `email` field error.
        assert "email" not in body
        assert body.get("error") == "No pudimos crear la cuenta con esos datos."

    def test_short_password_returns_400(self, api_client):
        payload = {**_VALID_COMPANY_PAYLOAD, "password": "short"}
        response = api_client.post(self.URL, payload, format="json")
        assert response.status_code == 400
        assert "password" in response.json()

    def test_missing_responsible_fields_return_400(self, api_client):
        payload = {**_VALID_COMPANY_PAYLOAD}
        del payload["responsible_name"]
        response = api_client.post(self.URL, payload, format="json")
        assert response.status_code == 400
        assert "responsible_name" in response.json()

    def test_account_type_cannot_be_forced_by_client(self, api_client):
        """Defensa contra mass-assignment: aunque el cliente mande
        `account_type: professional`, el view fuerza `company`."""
        payload = {**_VALID_COMPANY_PAYLOAD, "account_type": "professional"}
        response = api_client.post(self.URL, payload, format="json")
        assert response.status_code == 201
        user = User.objects.get(email="hello@acme.com")
        assert user.account_type == User.ACCOUNT_TYPE_COMPANY

    def test_is_staff_cannot_be_forced_by_client(self, api_client):
        payload = {**_VALID_COMPANY_PAYLOAD, "is_staff": True, "is_superuser": True}
        response = api_client.post(self.URL, payload, format="json")
        assert response.status_code == 201
        user = User.objects.get(email="hello@acme.com")
        assert user.is_staff is False
        assert user.is_superuser is False


# ──────────────────────────────────────────────────────────────────────
# COMPANY ME
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.integration
@pytest.mark.django_db
class TestCompanyMe:
    URL = "/api/companies/me/"

    def _create_company(self, api_client):
        api_client.post(
            "/api/companies/register/", _VALID_COMPANY_PAYLOAD, format="json"
        )
        return User.objects.get(email="hello@acme.com")

    def test_anon_is_401(self, api_client):
        response = api_client.get(self.URL)
        assert response.status_code == 401

    def test_professional_account_is_403(self, authed_client):
        """Una cuenta professional no puede leer /companies/me/."""
        response = authed_client.get(self.URL)
        assert response.status_code == 403
        assert response.json()["error"] == "account_type_mismatch"

    def test_company_can_read_own_profile(self, api_client):
        user = self._create_company(api_client)
        api_client.force_authenticate(user=user)
        response = api_client.get(self.URL)
        assert response.status_code == 200
        assert response.json()["legal_name"] == "Acme Inc."

    def test_company_can_patch_editable_fields(self, api_client):
        user = self._create_company(api_client)
        api_client.force_authenticate(user=user)
        response = api_client.patch(
            self.URL,
            {"short_description": "New pitch", "city": "Bogotá"},
            format="json",
        )
        assert response.status_code == 200
        user.company_profile.refresh_from_db()
        assert user.company_profile.short_description == "New pitch"
        assert user.company_profile.city == "Bogotá"


# ──────────────────────────────────────────────────────────────────────
# JWT PAYLOAD
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.integration
@pytest.mark.django_db
class TestJwtAccountType:
    LOGIN_URL = "/api/token/login/"

    def test_professional_login_has_account_type_in_payload(
        self, api_client, user, user_profile
    ):
        """El user fixture es un professional (default account_type)."""
        # Set known password
        user.set_password("testpass123")
        user.save()
        response = api_client.post(
            self.LOGIN_URL,
            {"username": user.username, "password": "testpass123"},
            format="json",
        )
        assert response.status_code == 200
        body = response.json()
        assert body["account_type"] == "professional"
        assert body["user_name"] == user_profile.first_name

    def test_company_login_has_account_type_and_uses_company_data(self, api_client):
        # Registrar empresa
        api_client.post(
            "/api/companies/register/", _VALID_COMPANY_PAYLOAD, format="json"
        )
        # Login (username derivado del email)
        response = api_client.post(
            self.LOGIN_URL,
            {"username": "hello", "password": "secret-pass-123"},
            format="json",
        )
        assert response.status_code == 200
        body = response.json()
        assert body["account_type"] == "company"
        # user_name viene del company.legal_name, NO del username del User.
        assert body["user_name"] == "Acme Inc."
        # professional_title se reusa para mostrar la industria.
        assert body["professional_title"] == "Tech"


# ──────────────────────────────────────────────────────────────────────
# UserProfile.visible_to_companies
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.integration
@pytest.mark.django_db
class TestVisibleToCompaniesToggle:
    URL = "/api/users/profiles/"

    def test_default_is_false(self, user_profile):
        assert user_profile.visible_to_companies is False

    def test_professional_can_opt_in(self, authed_client, user_profile):
        """El profesional puede activar el opt-in desde el endpoint
        estándar de profiles (usado por Settings)."""
        response = authed_client.post(
            self.URL, {"visible_to_companies": True}, format="json"
        )
        assert response.status_code in (200, 201)
        user_profile.refresh_from_db()
        assert user_profile.visible_to_companies is True

    def test_professional_can_opt_out(self, authed_client, user_profile):
        user_profile.visible_to_companies = True
        user_profile.save(update_fields=["visible_to_companies"])
        response = authed_client.post(
            self.URL, {"visible_to_companies": False}, format="json"
        )
        assert response.status_code in (200, 201)
        user_profile.refresh_from_db()
        assert user_profile.visible_to_companies is False


# ──────────────────────────────────────────────────────────────────────
# SEARCH PROFILES  (Fase 2 — feed empresa)
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.integration
@pytest.mark.django_db
class TestSearchProfiles:
    URL = "/api/companies/search-profiles/"

    def _make_company(self, api_client):
        api_client.post(
            "/api/companies/register/", _VALID_COMPANY_PAYLOAD, format="json"
        )
        return User.objects.get(email="hello@acme.com")

    def _make_visible_professional(
        self, django_user_model, username: str, *, title: str, skills: str, city: str = "Bogotá"
    ):
        user = django_user_model.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="x",
        )
        UserProfile.objects.create(
            user=user,
            first_name=username.title(),
            last_name="Pro",
            phone="+57",
            city=city,
            professional_title=title,
            skills=skills,
            experience="...",
            visible_to_companies=True,
        )
        return user

    def test_anon_is_401(self, api_client):
        response = api_client.post(self.URL, {}, format="json")
        assert response.status_code == 401

    def test_professional_account_is_403(self, authed_client):
        response = authed_client.post(
            self.URL, {"skills_required": ["react"]}, format="json"
        )
        assert response.status_code == 403
        assert response.json()["error"] == "account_type_mismatch"

    def test_empty_criteria_returns_empty_with_flag(self, api_client):
        company_user = self._make_company(api_client)
        api_client.force_authenticate(user=company_user)
        response = api_client.post(self.URL, {}, format="json")
        assert response.status_code == 200
        body = response.json()
        assert body["criteria_empty"] is True
        assert body["results"] == []

    def test_only_returns_visible_to_companies(self, api_client, django_user_model):
        company_user = self._make_company(api_client)
        api_client.force_authenticate(user=company_user)

        visible = self._make_visible_professional(
            django_user_model, "anna", title="Senior Frontend", skills="react, typescript"
        )
        # Profesional con perfil pero opt-out — NO debe aparecer.
        hidden = django_user_model.objects.create_user(
            username="hidden", email="hidden@example.com", password="x"
        )
        UserProfile.objects.create(
            user=hidden,
            first_name="Hidden",
            last_name="Pro",
            phone="+57",
            city="Bogotá",
            professional_title="Senior Frontend",
            skills="react, typescript",
            experience="...",
            visible_to_companies=False,
        )

        response = api_client.post(
            self.URL,
            {"skills_required": ["react"], "target_title": "Senior Frontend"},
            format="json",
        )
        assert response.status_code == 200
        names = [r["first_name"] for r in response.json()["results"]]
        assert "Anna" in names
        assert "Hidden" not in names

    def test_excludes_company_accounts_from_results(self, api_client, django_user_model):
        """Otra empresa registrada NO debe aparecer en el feed aunque
        tenga UserProfile residual."""
        company_user = self._make_company(api_client)
        # Visible profesional control
        self._make_visible_professional(
            django_user_model, "bea", title="Backend", skills="django"
        )
        # Otra empresa — defendemos el filter por account_type.
        other_company = django_user_model.objects.create_user(
            username="other-co",
            email="other-co@example.com",
            password="x",
        )
        other_company.account_type = User.ACCOUNT_TYPE_COMPANY
        other_company.save(update_fields=["account_type"])
        UserProfile.objects.create(
            user=other_company,
            first_name="Other",
            last_name="Co",
            phone="+57",
            city="Bogotá",
            professional_title="Backend",
            skills="django",
            experience="...",
            visible_to_companies=True,
        )

        api_client.force_authenticate(user=company_user)
        response = api_client.post(
            self.URL,
            {"skills_required": ["django"], "target_title": "Backend"},
            format="json",
        )
        names = [r["first_name"] for r in response.json()["results"]]
        assert "Bea" in names
        assert "Other" not in names

    def test_orders_by_match_desc(self, api_client, django_user_model):
        company_user = self._make_company(api_client)
        api_client.force_authenticate(user=company_user)

        self._make_visible_professional(
            django_user_model, "high", title="Senior Frontend",
            skills="react, typescript, node, redux"
        )
        self._make_visible_professional(
            django_user_model, "low", title="Backend",
            skills="python, django"
        )

        response = api_client.post(
            self.URL,
            {"skills_required": ["react", "typescript"], "target_title": "Frontend"},
            format="json",
        )
        results = response.json()["results"]
        assert len(results) == 2
        assert results[0]["first_name"] == "High"
        assert results[0]["match_percentage"] >= results[1]["match_percentage"]

    def test_min_match_filter(self, api_client, django_user_model):
        company_user = self._make_company(api_client)
        api_client.force_authenticate(user=company_user)

        # Match alto
        self._make_visible_professional(
            django_user_model, "match",
            title="Senior Frontend", skills="react, typescript"
        )
        # Match bajo
        self._make_visible_professional(
            django_user_model, "nope",
            title="Backend", skills="cobol"
        )

        response = api_client.post(
            self.URL,
            {
                "skills_required": ["react"],
                "target_title": "Frontend",
                "min_match": 50,
            },
            format="json",
        )
        names = [r["first_name"] for r in response.json()["results"]]
        assert "Match" in names
        assert "Nope" not in names

    def test_response_does_not_expose_pii(self, api_client, django_user_model):
        """SEGURIDAD: el feed empresa NO debe filtrar email ni teléfono.
        Solo nombre + título + ciudad + skills + match."""
        company_user = self._make_company(api_client)
        api_client.force_authenticate(user=company_user)

        self._make_visible_professional(
            django_user_model, "alice",
            title="Senior Frontend", skills="react"
        )
        response = api_client.post(
            self.URL,
            {"skills_required": ["react"], "target_title": "Frontend"},
            format="json",
        )
        row = response.json()["results"][0]
        # PII fields NO deben aparecer
        assert "email" not in row
        assert "phone" not in row
        assert "number_id" not in row
        # Datos esperados sí
        assert row["first_name"] == "Alice"
        assert row["professional_title"] == "Senior Frontend"
        assert "match_percentage" in row

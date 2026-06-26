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

from users.models import CompanyInterest, CompanyProfile, User, UserProfile


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


# ──────────────────────────────────────────────────────────────────────
# PROFILE DETAIL + RESUME + MARK INTEREST  (Fase 3)
# ──────────────────────────────────────────────────────────────────────


def _make_company_user(api_client) -> User:
    api_client.post(
        "/api/companies/register/", _VALID_COMPANY_PAYLOAD, format="json"
    )
    return User.objects.get(email="hello@acme.com")


def _make_visible_profile(django_user_model, username: str = "anna") -> UserProfile:
    user = django_user_model.objects.create_user(
        username=username, email=f"{username}@example.com", password="x"
    )
    return UserProfile.objects.create(
        user=user,
        first_name=username.title(),
        last_name="Pro",
        phone="+57",
        city="Bogotá",
        professional_title="Senior Frontend",
        skills="react, typescript",
        experience="...",
        summary="Awesome summary text.",
        visible_to_companies=True,
    )


@pytest.mark.integration
@pytest.mark.django_db
class TestProfileDetail:
    def _url(self, profile_id: int) -> str:
        return f"/api/companies/profiles/{profile_id}/"

    def test_anon_is_401(self, api_client):
        response = api_client.get(self._url(1))
        assert response.status_code == 401

    def test_professional_account_is_403(self, authed_client, user_profile):
        response = authed_client.get(self._url(user_profile.id))
        assert response.status_code == 403

    def test_company_can_view_visible_profile(self, api_client, django_user_model):
        company_user = _make_company_user(api_client)
        profile = _make_visible_profile(django_user_model)
        api_client.force_authenticate(user=company_user)
        response = api_client.get(self._url(profile.id))
        assert response.status_code == 200
        body = response.json()
        assert body["first_name"] == "Anna"
        assert body["summary"] == "Awesome summary text."
        # PII NO aparece
        assert "email" not in body
        assert "phone" not in body
        assert "number_id" not in body
        # Interest status default null
        assert body["interest_status"] is None

    def test_hidden_profile_returns_404(self, api_client, django_user_model):
        """Anti enumeration: profile que opt-out → 404 indistinguible
        de profile_id que no existe."""
        company_user = _make_company_user(api_client)
        # Profile con visible_to_companies=False
        hidden = django_user_model.objects.create_user(
            username="hidden", email="hidden@example.com", password="x"
        )
        UserProfile.objects.create(
            user=hidden, first_name="Hidden", last_name="Pro",
            phone="+57", city="X", professional_title="Backend",
            skills="x", experience="y", visible_to_companies=False,
        )
        api_client.force_authenticate(user=company_user)
        response = api_client.get(self._url(hidden.profile.id))
        assert response.status_code == 404

    def test_company_account_profile_id_returns_404(self, api_client):
        """Aunque la empresa pase su propio profile_id, no debe aparecer
        en el detalle del lado profesional (defensa por account_type)."""
        company_user = _make_company_user(api_client)
        # Crear un UserProfile residual para la empresa para forzar el filter.
        UserProfile.objects.create(
            user=company_user, first_name="X", last_name="Y",
            phone="+57", city="Z", professional_title="CEO",
            skills="", experience="", visible_to_companies=True,
        )
        api_client.force_authenticate(user=company_user)
        response = api_client.get(self._url(company_user.profile.id))
        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.django_db
class TestMarkInterest:
    def _url(self, profile_id: int) -> str:
        return f"/api/companies/profiles/{profile_id}/interest/"

    def test_anon_is_401(self, api_client):
        response = api_client.post(self._url(1), {}, format="json")
        assert response.status_code == 401

    def test_professional_account_is_403(self, authed_client, user_profile):
        response = authed_client.post(self._url(user_profile.id), {}, format="json")
        assert response.status_code == 403

    def test_first_mark_creates_interest_and_notification(
        self, api_client, django_user_model
    ):
        from notifications.models import Notification

        company_user = _make_company_user(api_client)
        profile = _make_visible_profile(django_user_model)
        api_client.force_authenticate(user=company_user)

        response = api_client.post(
            self._url(profile.id),
            {"message": "Te queremos en nuestro equipo."},
            format="json",
        )
        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "pending"
        assert body["message"] == "Te queremos en nuestro equipo."

        # Interest persisted
        assert CompanyInterest.objects.filter(
            company__user=company_user,
            professional=profile,
        ).exists()

        # Notification al profesional
        notif = Notification.objects.get(user=profile.user)
        assert notif.kind == "company_interest"
        assert "Acme Inc." in notif.title
        assert notif.metadata["company_legal_name"] == "Acme Inc."
        assert notif.metadata["responsible_name"] == "Jane Doe"

    def test_remark_updates_without_duplicate_notification(
        self, api_client, django_user_model
    ):
        """Re-marcar mismo profile → update silencioso (no spammea
        notificaciones)."""
        from notifications.models import Notification

        company_user = _make_company_user(api_client)
        profile = _make_visible_profile(django_user_model)
        api_client.force_authenticate(user=company_user)

        # Primer marcado → 201 + 1 notif
        api_client.post(self._url(profile.id), {}, format="json")
        assert Notification.objects.filter(user=profile.user).count() == 1

        # Segundo marcado con mensaje distinto → 200 + sigue 1 notif
        response2 = api_client.post(
            self._url(profile.id),
            {"message": "Update del mensaje."},
            format="json",
        )
        assert response2.status_code == 200
        assert Notification.objects.filter(user=profile.user).count() == 1

        # Pero el message del interest sí se actualizó
        interest = CompanyInterest.objects.get(
            company__user=company_user, professional=profile
        )
        assert interest.message == "Update del mensaje."

    def test_hidden_profile_cannot_be_marked(self, api_client, django_user_model):
        company_user = _make_company_user(api_client)
        hidden_user = django_user_model.objects.create_user(
            username="hidden", email="hidden@example.com", password="x"
        )
        UserProfile.objects.create(
            user=hidden_user, first_name="Hidden", last_name="Pro",
            phone="+57", city="X", professional_title="Backend",
            skills="x", experience="y", visible_to_companies=False,
        )
        api_client.force_authenticate(user=company_user)
        response = api_client.post(
            self._url(hidden_user.profile.id), {}, format="json"
        )
        assert response.status_code == 404
        # Y NO se creó interest ni notificación
        assert CompanyInterest.objects.count() == 0


@pytest.mark.integration
@pytest.mark.django_db
class TestResumeDownload:
    def _url(self, profile_id: int) -> str:
        return f"/api/companies/profiles/{profile_id}/resume/"

    def test_professional_account_is_403(self, authed_client, user_profile):
        response = authed_client.get(self._url(user_profile.id))
        assert response.status_code == 403

    def test_no_resume_returns_404(self, api_client, django_user_model):
        company_user = _make_company_user(api_client)
        profile = _make_visible_profile(django_user_model)
        # profile no tiene resume seteado
        api_client.force_authenticate(user=company_user)
        response = api_client.get(self._url(profile.id))
        assert response.status_code == 404

    def test_hidden_profile_returns_404(self, api_client, django_user_model):
        company_user = _make_company_user(api_client)
        hidden = django_user_model.objects.create_user(
            username="hidden", email="hidden@example.com", password="x"
        )
        UserProfile.objects.create(
            user=hidden, first_name="Hidden", last_name="Pro",
            phone="+57", city="X", professional_title="X",
            skills="", experience="", visible_to_companies=False,
        )
        api_client.force_authenticate(user=company_user)
        response = api_client.get(self._url(hidden.profile.id))
        assert response.status_code == 404


# ──────────────────────────────────────────────────────────────────────
# PROFESSIONAL INBOX  (Fase 4)
# ──────────────────────────────────────────────────────────────────────


def _setup_interest(api_client, django_user_model, *, professional_username="anna"):
    """Helper: registra empresa Acme y crea un CompanyInterest hacia
    un professional visible. Devuelve (interest, professional_user, company_user)."""
    company_user = _make_company_user(api_client)
    profile = _make_visible_profile(django_user_model, professional_username)
    api_client.force_authenticate(user=company_user)
    api_client.post(
        f"/api/companies/profiles/{profile.id}/interest/",
        {"message": "Te queremos!"},
        format="json",
    )
    interest = CompanyInterest.objects.get(professional=profile)
    return interest, profile.user, company_user


@pytest.mark.integration
@pytest.mark.django_db
class TestProfessionalInboxList:
    URL = "/api/users/me/company-interests/"

    def test_anon_is_401(self, api_client):
        response = api_client.get(self.URL)
        assert response.status_code == 401

    def test_company_account_is_403(self, api_client, django_user_model):
        company_user = _make_company_user(api_client)
        api_client.force_authenticate(user=company_user)
        response = api_client.get(self.URL)
        assert response.status_code == 403

    def test_professional_sees_own_interests(self, api_client, django_user_model):
        interest, prof_user, _ = _setup_interest(api_client, django_user_model)
        api_client.force_authenticate(user=prof_user)
        response = api_client.get(self.URL)
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        row = body["results"][0]
        assert row["company_legal_name"] == "Acme Inc."
        assert row["responsible_name"] == "Jane Doe"
        assert row["status"] == "pending"
        # Email NO debe aparecer en status=pending (privacidad)
        assert row["responsible_email"] == ""

    def test_email_revealed_only_when_accepted(self, api_client, django_user_model):
        interest, prof_user, _ = _setup_interest(api_client, django_user_model)
        # Aceptar
        interest.status = CompanyInterest.STATUS_ACCEPTED
        interest.save(update_fields=["status"])

        api_client.force_authenticate(user=prof_user)
        response = api_client.get(self.URL)
        row = response.json()["results"][0]
        assert row["responsible_email"] == "jane@acme.com"

    def test_email_hidden_when_dismissed(self, api_client, django_user_model):
        interest, prof_user, _ = _setup_interest(api_client, django_user_model)
        interest.status = CompanyInterest.STATUS_DISMISSED
        interest.save(update_fields=["status"])

        api_client.force_authenticate(user=prof_user)
        response = api_client.get(self.URL)
        row = response.json()["results"][0]
        assert row["responsible_email"] == ""

    def test_filter_by_status(self, api_client, django_user_model):
        interest, prof_user, _ = _setup_interest(api_client, django_user_model)
        api_client.force_authenticate(user=prof_user)

        # ?status=accepted → 0 resultados porque está pending
        r = api_client.get(self.URL + "?status=accepted")
        assert r.json()["total"] == 0

        # ?status=pending → 1
        r = api_client.get(self.URL + "?status=pending")
        assert r.json()["total"] == 1


@pytest.mark.integration
@pytest.mark.django_db
class TestProfessionalInboxRespond:
    def _url(self, interest_id: int) -> str:
        return f"/api/users/me/company-interests/{interest_id}/respond/"

    def test_company_account_is_403(self, api_client, django_user_model):
        interest, _, _ = _setup_interest(api_client, django_user_model)
        # ya estamos auth como company_user del _setup_interest
        response = api_client.post(
            self._url(interest.id), {"action": "accept"}, format="json"
        )
        assert response.status_code == 403

    def test_cannot_respond_other_users_interest(self, api_client, django_user_model):
        """SEGURIDAD: el profesional A NO puede responder un interest
        dirigido al profesional B."""
        interest, _, _ = _setup_interest(api_client, django_user_model, professional_username="anna")
        # Crear otro profesional
        other = django_user_model.objects.create_user(
            username="other", email="other@example.com", password="x"
        )
        UserProfile.objects.create(
            user=other, first_name="Other", last_name="X",
            phone="+57", city="X", professional_title="X",
            skills="", experience="", visible_to_companies=True,
        )
        api_client.force_authenticate(user=other)
        response = api_client.post(
            self._url(interest.id), {"action": "accept"}, format="json"
        )
        # No es 403, es 404 — el queryset filtra por ownership así que
        # ni siquiera reconoce el id.
        assert response.status_code == 404

    def test_accept_updates_status_and_notifies_company(
        self, api_client, django_user_model
    ):
        from notifications.models import Notification

        interest, prof_user, company_user = _setup_interest(
            api_client, django_user_model
        )
        # Cuántas notifs tenía la empresa antes
        notifs_before = Notification.objects.filter(user=company_user).count()

        api_client.force_authenticate(user=prof_user)
        response = api_client.post(
            self._url(interest.id), {"action": "accept"}, format="json"
        )
        assert response.status_code == 200
        assert response.json()["status"] == "accepted"
        # Email se revela en el response porque ya es accepted.
        assert response.json()["responsible_email"] == "jane@acme.com"

        interest.refresh_from_db()
        assert interest.status == CompanyInterest.STATUS_ACCEPTED

        # Notificación a la empresa creada
        assert Notification.objects.filter(user=company_user).count() == notifs_before + 1
        notif = Notification.objects.filter(user=company_user).first()
        assert notif.kind == "company_interest"
        assert "Anna Pro" in notif.title  # full name del profesional
        assert notif.metadata["professional_email"] == prof_user.email

    def test_dismiss_does_not_notify_company(self, api_client, django_user_model):
        """Privacidad: si el profesional descarta, la empresa NO recibe
        notificación de rechazo."""
        from notifications.models import Notification

        interest, prof_user, company_user = _setup_interest(
            api_client, django_user_model
        )
        notifs_before = Notification.objects.filter(user=company_user).count()

        api_client.force_authenticate(user=prof_user)
        response = api_client.post(
            self._url(interest.id), {"action": "dismiss"}, format="json"
        )
        assert response.status_code == 200
        assert response.json()["status"] == "dismissed"
        # Sin email en el response porque dismissed
        assert response.json()["responsible_email"] == ""
        # Sin nueva noti
        assert Notification.objects.filter(user=company_user).count() == notifs_before

    def test_invalid_action_returns_400(self, api_client, django_user_model):
        interest, prof_user, _ = _setup_interest(api_client, django_user_model)
        api_client.force_authenticate(user=prof_user)
        response = api_client.post(
            self._url(interest.id), {"action": "delete"}, format="json"
        )
        assert response.status_code == 400
        assert response.json()["error"] == "invalid_action"

    def test_idempotent_accept_does_not_re_notify(
        self, api_client, django_user_model
    ):
        from notifications.models import Notification

        interest, prof_user, company_user = _setup_interest(
            api_client, django_user_model
        )
        api_client.force_authenticate(user=prof_user)

        # Aceptar dos veces — la segunda no debe duplicar la noti.
        api_client.post(self._url(interest.id), {"action": "accept"}, format="json")
        first_count = Notification.objects.filter(user=company_user).count()
        api_client.post(self._url(interest.id), {"action": "accept"}, format="json")
        second_count = Notification.objects.filter(user=company_user).count()
        assert second_count == first_count

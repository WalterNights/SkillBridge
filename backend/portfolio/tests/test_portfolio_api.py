"""Tests del CRUD del portafolio.

Cubre:
- GET público sin auth devuelve el JSON completo.
- GET público con slug inexistente responde 404 (para que el frontend
  caiga al bundle estático).
- PUT admin requiere is_staff (401/403 para anónimos y regulares).
- PUT admin sobreescribe `content` y `content_en` completos.
- POST /images/ requiere is_staff.
- DELETE /images/<id>/ requiere is_staff.
"""

from __future__ import annotations

import io
from unittest.mock import patch

import pytest
import requests
from PIL import Image

from portfolio.models import Portfolio, PortfolioImage


@pytest.fixture
def portfolio(admin_user):
    return Portfolio.objects.create(
        slug="testfolio",
        owner=admin_user,
        content={"hero": {"titleTop": "Hola"}, "about": {"title": "yo"}},
        content_en={"hero": {"titleTop": "Hi"}, "about": {"title": "me"}},
    )


def _make_image_upload(name="cover.png", size=(4, 4)):
    """Construye un PNG in-memory válido para pasar el validator del modelo."""
    from django.core.files.uploadedfile import SimpleUploadedFile

    buf = io.BytesIO()
    Image.new("RGB", size, color=(200, 50, 20)).save(buf, format="PNG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")


# ═════════════════════════════════════════════════════════════════════
# GET público
# ═════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestPortfolioPublicGet:
    def test_returns_content_when_slug_exists(self, api_client, portfolio):
        r = api_client.get(f"/api/portfolio/{portfolio.slug}/")
        assert r.status_code == 200
        body = r.json()
        assert body["slug"] == "testfolio"
        assert body["content"]["hero"]["titleTop"] == "Hola"
        assert body["content_en"]["hero"]["titleTop"] == "Hi"
        assert body["images"] == []

    def test_returns_404_for_unknown_slug(self, api_client):
        r = api_client.get("/api/portfolio/nope/")
        assert r.status_code == 404

    def test_no_auth_required(self, api_client, portfolio):
        # Sin Authorization header, tiene que responder 200. El frontend
        # público lo lee al montar el shell.
        r = api_client.get(f"/api/portfolio/{portfolio.slug}/")
        assert r.status_code == 200


# ═════════════════════════════════════════════════════════════════════
# Admin PUT
# ═════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestPortfolioAdminPut:
    def test_anonymous_gets_401_or_403(self, api_client, portfolio):
        r = api_client.put(
            f"/api/portfolio/{portfolio.slug}/admin/",
            {"content": {}, "content_en": {}},
            format="json",
        )
        assert r.status_code in (401, 403)

    def test_regular_user_gets_403(self, authed_client, portfolio):
        r = authed_client.put(
            f"/api/portfolio/{portfolio.slug}/admin/",
            {"content": {"x": 1}, "content_en": {"x": 1}},
            format="json",
        )
        assert r.status_code == 403

    def test_admin_can_overwrite_content(self, api_client, admin_user, portfolio):
        api_client.force_authenticate(user=admin_user)
        payload = {
            "content": {"hero": {"titleTop": "Nuevo"}},
            "content_en": {"hero": {"titleTop": "New"}},
        }
        r = api_client.put(
            f"/api/portfolio/{portfolio.slug}/admin/",
            payload,
            format="json",
        )
        assert r.status_code == 200
        portfolio.refresh_from_db()
        assert portfolio.content["hero"]["titleTop"] == "Nuevo"
        assert portfolio.content_en["hero"]["titleTop"] == "New"

    def test_slug_is_read_only(self, api_client, admin_user, portfolio):
        """No se puede renombrar el slug via API — es el identificador
        estable de la URL pública."""
        api_client.force_authenticate(user=admin_user)
        r = api_client.patch(
            f"/api/portfolio/{portfolio.slug}/admin/",
            {"slug": "renamed"},
            format="json",
        )
        assert r.status_code == 200
        portfolio.refresh_from_db()
        assert portfolio.slug == "testfolio"


# ═════════════════════════════════════════════════════════════════════
# Imágenes
# ═════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestPortfolioImages:
    def test_anonymous_cannot_upload(self, api_client, portfolio):
        r = api_client.post(
            f"/api/portfolio/{portfolio.slug}/images/",
            {"image": _make_image_upload(), "project_id": "ranktitan"},
            format="multipart",
        )
        assert r.status_code in (401, 403)

    def test_regular_user_cannot_upload(self, authed_client, portfolio):
        r = authed_client.post(
            f"/api/portfolio/{portfolio.slug}/images/",
            {"image": _make_image_upload(), "project_id": "ranktitan"},
            format="multipart",
        )
        assert r.status_code == 403

    def test_admin_can_upload_and_url_returned(self, api_client, admin_user, portfolio):
        api_client.force_authenticate(user=admin_user)
        r = api_client.post(
            f"/api/portfolio/{portfolio.slug}/images/",
            {
                "image": _make_image_upload(),
                "project_id": "ranktitan",
                "alt_text": "RankTitan dashboard",
            },
            format="multipart",
        )
        assert r.status_code == 201
        body = r.json()
        assert body["project_id"] == "ranktitan"
        assert body["alt_text"] == "RankTitan dashboard"
        assert body["url"].startswith("http") or body["url"].startswith("/")
        assert PortfolioImage.objects.filter(
            portfolio=portfolio, project_id="ranktitan"
        ).exists()

    def test_admin_can_delete_image(self, api_client, admin_user, portfolio):
        api_client.force_authenticate(user=admin_user)
        img = PortfolioImage.objects.create(
            portfolio=portfolio,
            project_id="ranktitan",
            image=_make_image_upload("delete_me.png"),
        )
        r = api_client.delete(f"/api/portfolio/{portfolio.slug}/images/{img.pk}/")
        assert r.status_code == 204
        assert not PortfolioImage.objects.filter(pk=img.pk).exists()

    def test_regular_user_cannot_delete_image(self, authed_client, portfolio):
        img = PortfolioImage.objects.create(
            portfolio=portfolio,
            project_id="ranktitan",
            image=_make_image_upload("keep_me.png"),
        )
        r = authed_client.delete(f"/api/portfolio/{portfolio.slug}/images/{img.pk}/")
        assert r.status_code == 403
        assert PortfolioImage.objects.filter(pk=img.pk).exists()

    def test_upload_rejects_non_image(self, api_client, admin_user, portfolio):
        """Sanity: el validator del modelo (magic bytes) rechaza payload
        de texto renombrado con extensión de imagen."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        fake = SimpleUploadedFile("evil.png", b"not an image", content_type="image/png")
        api_client.force_authenticate(user=admin_user)
        r = api_client.post(
            f"/api/portfolio/{portfolio.slug}/images/",
            {"image": fake, "project_id": "x"},
            format="multipart",
        )
        assert r.status_code == 400


# ═════════════════════════════════════════════════════════════════════
# Seed data migration
# ═════════════════════════════════════════════════════════════════════

# ═════════════════════════════════════════════════════════════════════
# GitHub contributions
# ═════════════════════════════════════════════════════════════════════

@pytest.fixture
def portfolio_with_github(admin_user):
    """Portfolio con un social link de GitHub válido."""
    return Portfolio.objects.create(
        slug="withgh",
        owner=admin_user,
        content={
            "sidebar": {
                "socials": [{"id": "github", "url": "https://github.com/octocat"}],
            },
        },
        content_en={},
    )


@pytest.fixture
def portfolio_no_github(admin_user):
    """Portfolio sin el social link de GitHub."""
    return Portfolio.objects.create(
        slug="nogh",
        owner=admin_user,
        content={"sidebar": {"socials": [{"id": "linkedin", "url": "https://x.com/y"}]}},
        content_en={},
    )


@pytest.fixture(autouse=True)
def _clear_django_cache():
    """El locmem cache es compartido entre tests dentro del proceso —
    limpiamos siempre para no arrastrar entries de tests previos."""
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db
class TestGithubContributions:
    """Tests del path jogruber (fallback público sin token).

    Los tests explícitos de GraphQL viven en TestGithubGraphQL abajo —
    settings.GITHUB_TOKEN se seta ahí.
    """

    @pytest.fixture(autouse=True)
    def _no_github_token(self, settings):
        """Forzamos GITHUB_TOKEN vacío para que la view tome el path
        jogruber. Sin esto, un `.env` local con el token real hace que
        la view use GraphQL y los mocks de `requests.get` no apliquen."""
        settings.GITHUB_TOKEN = ""

    def _mock_response(self, monkeypatch, payload=None, exc=None):
        """Mock de requests.get para el path jogruber."""
        from portfolio import views as pf_views

        def fake_get(*args, **kwargs):
            if exc is not None:
                raise exc
            m = type("Resp", (), {})()
            m.raise_for_status = lambda: None
            m.json = lambda: payload
            return m

        monkeypatch.setattr(pf_views.requests, "get", fake_get)

    def test_returns_normalized_shape_on_success(
        self, api_client, portfolio_with_github, monkeypatch
    ):
        self._mock_response(
            monkeypatch,
            payload={
                "total": {"lastYear": 1200},
                "contributions": [{"date": "2026-01-01", "count": 3, "level": 2}],
            },
        )
        r = api_client.get(f"/api/portfolio/{portfolio_with_github.slug}/github-contributions/")
        assert r.status_code == 200
        body = r.json()
        assert body["username"] == "octocat"
        assert body["total"]["lastYear"] == 1200
        assert body["contributions"][0]["date"] == "2026-01-01"

    def test_returns_404_when_portfolio_has_no_github_link(
        self, api_client, portfolio_no_github
    ):
        r = api_client.get(f"/api/portfolio/{portfolio_no_github.slug}/github-contributions/")
        assert r.status_code == 404

    def test_returns_404_for_unknown_portfolio(self, api_client):
        r = api_client.get("/api/portfolio/nope/github-contributions/")
        assert r.status_code == 404

    def test_returns_502_when_upstream_fails(
        self, api_client, portfolio_with_github, monkeypatch
    ):
        self._mock_response(monkeypatch, exc=requests.RequestException("network down"))
        r = api_client.get(f"/api/portfolio/{portfolio_with_github.slug}/github-contributions/")
        assert r.status_code == 502

    def test_extracts_username_from_url_with_trailing_path(
        self, api_client, admin_user, monkeypatch
    ):
        """URL tipo https://github.com/foo/bar debe extraer 'foo'."""
        p = Portfolio.objects.create(
            slug="urlpath",
            owner=admin_user,
            content={
                "sidebar": {
                    "socials": [{"id": "github", "url": "https://github.com/torvalds/linux"}],
                },
            },
            content_en={},
        )
        captured = {}

        from portfolio import views as pf_views

        def fake_get(url, *args, **kwargs):
            captured["url"] = url
            m = type("Resp", (), {})()
            m.raise_for_status = lambda: None
            m.json = lambda: {"total": {}, "contributions": []}
            return m

        monkeypatch.setattr(pf_views.requests, "get", fake_get)
        r = api_client.get(f"/api/portfolio/{p.slug}/github-contributions/")
        assert r.status_code == 200
        assert "torvalds" in captured["url"]
        assert "linux" not in captured["url"]

    def test_rejects_invalid_username_gracefully(self, api_client, admin_user):
        """URL con caracteres no permitidos → 404 sin llamar al servicio."""
        p = Portfolio.objects.create(
            slug="badgh",
            owner=admin_user,
            content={
                "sidebar": {
                    "socials": [{"id": "github", "url": "https://github.com/../../etc/passwd"}],
                },
            },
            content_en={},
        )
        r = api_client.get(f"/api/portfolio/{p.slug}/github-contributions/")
        assert r.status_code == 404

    def test_second_call_hits_cache(
        self, api_client, portfolio_with_github, monkeypatch
    ):
        """La primera call pega al servicio externo, la segunda usa cache."""
        call_count = {"n": 0}
        from portfolio import views as pf_views

        def fake_get(*args, **kwargs):
            call_count["n"] += 1
            m = type("Resp", (), {})()
            m.raise_for_status = lambda: None
            m.json = lambda: {"total": {"lastYear": 99}, "contributions": []}
            return m

        monkeypatch.setattr(pf_views.requests, "get", fake_get)
        url = f"/api/portfolio/{portfolio_with_github.slug}/github-contributions/"
        r1 = api_client.get(url)
        r2 = api_client.get(url)
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert call_count["n"] == 1  # Segunda call usa cache


# ═════════════════════════════════════════════════════════════════════
# GitHub GraphQL path (requiere GITHUB_TOKEN)
# ═════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestGithubGraphQL:
    """Tests del path GraphQL — se activa cuando settings.GITHUB_TOKEN
    está seteado. Los mismos endpoints devuelven data del GraphQL oficial
    (que incluye contribuciones privadas si el token tiene scope y el
    user tiene el flag habilitado).
    """

    def _mock_post(self, monkeypatch, payload=None, exc=None):
        """Mock de requests.post — GraphQL usa POST, no GET."""
        from portfolio import views as pf_views

        captured = {}

        def fake_post(url, *args, **kwargs):
            captured["url"] = url
            captured["json"] = kwargs.get("json")
            captured["headers"] = kwargs.get("headers", {})
            if exc is not None:
                raise exc
            m = type("Resp", (), {})()
            m.raise_for_status = lambda: None
            m.json = lambda: payload
            return m

        monkeypatch.setattr(pf_views.requests, "post", fake_post)
        return captured

    def _fake_calendar(self, total=1060, first_date="2026-08-16"):
        """Devuelve un payload GraphQL válido con 1 semana × 7 días."""
        # 7 días desde first_date con contributionCount y level variados
        # cubriendo cada nivel del enum.
        return {
            "data": {
                "user": {
                    "contributionsCollection": {
                        "contributionCalendar": {
                            "totalContributions": total,
                            "weeks": [
                                {
                                    "contributionDays": [
                                        {"date": "2026-08-10", "contributionCount": 0, "contributionLevel": "NONE"},
                                        {"date": "2026-08-11", "contributionCount": 1, "contributionLevel": "FIRST_QUARTILE"},
                                        {"date": "2026-08-12", "contributionCount": 5, "contributionLevel": "SECOND_QUARTILE"},
                                        {"date": "2026-08-13", "contributionCount": 12, "contributionLevel": "THIRD_QUARTILE"},
                                        {"date": "2026-08-14", "contributionCount": 25, "contributionLevel": "FOURTH_QUARTILE"},
                                        {"date": "2026-08-15", "contributionCount": 3, "contributionLevel": "SECOND_QUARTILE"},
                                        {"date": "2026-08-16", "contributionCount": 8, "contributionLevel": "THIRD_QUARTILE"},
                                    ]
                                }
                            ],
                        }
                    }
                }
            }
        }

    def test_uses_graphql_when_token_is_set(
        self, api_client, portfolio_with_github, monkeypatch, settings
    ):
        settings.GITHUB_TOKEN = "ghp_faketoken"
        captured = self._mock_post(monkeypatch, payload=self._fake_calendar(total=1060))

        r = api_client.get(f"/api/portfolio/{portfolio_with_github.slug}/github-contributions/")
        assert r.status_code == 200
        body = r.json()
        assert body["username"] == "octocat"
        assert body["total"]["lastYear"] == 1060  # ← número real, no el jogruber
        assert len(body["contributions"]) == 7
        # Verifica mapping de niveles enum → int.
        assert body["contributions"][0]["level"] == 0  # NONE
        assert body["contributions"][4]["level"] == 4  # FOURTH_QUARTILE
        # URL fue la del GraphQL, no jogruber.
        assert "api.github.com/graphql" in captured["url"]
        # Header de Bearer bien inyectado.
        assert captured["headers"].get("Authorization") == "Bearer ghp_faketoken"

    def test_falls_back_to_jogruber_when_no_token(
        self, api_client, portfolio_with_github, monkeypatch, settings
    ):
        """Sin token, sigue funcionando el path público (backward compat)."""
        settings.GITHUB_TOKEN = ""
        from portfolio import views as pf_views

        def fake_get(*args, **kwargs):
            m = type("Resp", (), {})()
            m.raise_for_status = lambda: None
            m.json = lambda: {"total": {"lastYear": 216}, "contributions": []}
            return m

        monkeypatch.setattr(pf_views.requests, "get", fake_get)
        r = api_client.get(f"/api/portfolio/{portfolio_with_github.slug}/github-contributions/")
        assert r.status_code == 200
        assert r.json()["total"]["lastYear"] == 216

    def test_returns_502_when_graphql_returns_errors(
        self, api_client, portfolio_with_github, monkeypatch, settings
    ):
        """GraphQL puede devolver 200 con errors: [] — hay que detectarlo."""
        settings.GITHUB_TOKEN = "ghp_faketoken"
        self._mock_post(
            monkeypatch,
            payload={"errors": [{"message": "Bad credentials", "type": "UNAUTHORIZED"}]},
        )
        r = api_client.get(f"/api/portfolio/{portfolio_with_github.slug}/github-contributions/")
        assert r.status_code == 502

    def test_returns_502_when_user_not_found_on_graphql(
        self, api_client, portfolio_with_github, monkeypatch, settings
    ):
        """user: null en la respuesta = usuario inexistente."""
        settings.GITHUB_TOKEN = "ghp_faketoken"
        self._mock_post(monkeypatch, payload={"data": {"user": None}})
        r = api_client.get(f"/api/portfolio/{portfolio_with_github.slug}/github-contributions/")
        assert r.status_code == 502

    def test_returns_502_when_graphql_network_fails(
        self, api_client, portfolio_with_github, monkeypatch, settings
    ):
        settings.GITHUB_TOKEN = "ghp_faketoken"
        self._mock_post(monkeypatch, exc=requests.RequestException("dns fail"))
        r = api_client.get(f"/api/portfolio/{portfolio_with_github.slug}/github-contributions/")
        assert r.status_code == 502

    def test_cache_key_differs_between_graphql_and_jogruber(
        self, api_client, portfolio_with_github, monkeypatch, settings
    ):
        """Si el admin agrega el token después de que jogruber cacheó,
        el fetch GraphQL fresco NO debe reusar el cache viejo."""
        from portfolio import views as pf_views

        # Primera call: sin token, hace get, cachea "jogruber:{user}".
        settings.GITHUB_TOKEN = ""
        monkeypatch.setattr(
            pf_views.requests, "get",
            lambda *a, **k: type("R", (), {
                "raise_for_status": lambda self: None,
                "json": lambda self: {"total": {"lastYear": 216}, "contributions": []},
            })(),
        )
        url = f"/api/portfolio/{portfolio_with_github.slug}/github-contributions/"
        r1 = api_client.get(url)
        assert r1.json()["total"]["lastYear"] == 216

        # Segunda call: con token, tiene que hacer POST fresco y devolver 1060.
        settings.GITHUB_TOKEN = "ghp_now"
        self._mock_post(monkeypatch, payload=self._fake_calendar(total=1060))
        r2 = api_client.get(url)
        assert r2.json()["total"]["lastYear"] == 1060


@pytest.mark.django_db
class TestSeedMigration:
    def test_walternightsdev_exists_after_migrations(self, db):
        """La data migration 0002 sembró el portafolio si había superuser
        (en el ambiente de test hay al menos uno inicial de fixtures)."""
        # No asseramos existencia porque puede no haber superuser en el
        # test DB fresco. Testeamos que si existe, la estructura es válida.
        p = Portfolio.objects.filter(slug="walternightsdev").first()
        if p is None:
            pytest.skip("No superuser en test DB — el seed skipeó (comportamiento esperado).")
        assert "hero" in p.content
        assert "hero" in p.content_en
        assert p.content["hero"]["titleTop"]

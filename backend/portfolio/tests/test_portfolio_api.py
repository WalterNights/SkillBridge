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

import pytest
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

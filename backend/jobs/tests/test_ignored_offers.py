"""Tests del flow de ofertas ignoradas: ignore/unignore/list + exclusión del feed."""

import pytest

from jobs.models import IgnoredOffer, JobOffer


@pytest.fixture
def offers_pair():
    """Dos ofertas independientes para tests de exclusión."""
    a = JobOffer.objects.create(
        title="Offer A", url="https://x.com/a",
        summary="", keywords="", portal="hireline",
        country="MX", modality="remote",
    )
    b = JobOffer.objects.create(
        title="Offer B", url="https://x.com/b",
        summary="", keywords="", portal="hireline",
        country="MX", modality="remote",
    )
    return a, b


@pytest.mark.integration
@pytest.mark.django_db
class TestIgnoreOffer:
    def test_post_creates_ignored_record(self, authed_client, user, offers_pair):
        a, _ = offers_pair
        response = authed_client.post(f"/api/jobs/jobs/{a.id}/ignore/")
        assert response.status_code == 201
        body = response.json()
        assert body["ignored"] is True
        assert body["offer_id"] == a.id
        # Sin duplicados (title+company+portal unicos), cascaded_count = 1
        assert body["cascaded_count"] == 1
        assert IgnoredOffer.objects.filter(user=user, offer=a).exists()

    def test_post_is_idempotent(self, authed_client, user, offers_pair):
        a, _ = offers_pair
        authed_client.post(f"/api/jobs/jobs/{a.id}/ignore/")
        response = authed_client.post(f"/api/jobs/jobs/{a.id}/ignore/")
        # 200 (not 201) cuando ya existía
        assert response.status_code == 200
        assert IgnoredOffer.objects.filter(user=user, offer=a).count() == 1

    def test_delete_unignores(self, authed_client, user, offers_pair):
        a, _ = offers_pair
        IgnoredOffer.objects.create(user=user, offer=a)
        response = authed_client.delete(f"/api/jobs/jobs/{a.id}/ignore/")
        assert response.status_code == 204
        assert not IgnoredOffer.objects.filter(user=user, offer=a).exists()

    def test_delete_is_idempotent(self, authed_client, offers_pair):
        a, _ = offers_pair
        # No existe → DELETE igual responde 204
        response = authed_client.delete(f"/api/jobs/jobs/{a.id}/ignore/")
        assert response.status_code == 204

    def test_ignore_requires_auth(self, api_client, offers_pair):
        a, _ = offers_pair
        response = api_client.post(f"/api/jobs/jobs/{a.id}/ignore/")
        assert response.status_code == 401

    def test_ignore_nonexistent_offer_returns_404(self, authed_client):
        response = authed_client.post("/api/jobs/jobs/999999/ignore/")
        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.django_db
class TestIgnoreCascadeToDuplicates:
    """Bug reportado 2026-07-04: Computrabajo cambia el fragmento `#lc=...`
    entre scrapes → misma oferta se guarda como filas distintas. Cuando
    el user ignora una, las otras siguen apareciendo con match idéntico.
    Fix: al ignorar, cascadeamos a todo (title, company, portal) igual."""

    def _make_dup(self, url_suffix: str, *, title="Fullstack Bilingue 52172", portal="computrabajo"):
        return JobOffer.objects.create(
            title=title, company="PeakU",
            url=f"https://co.computrabajo.com/o/93AF7{url_suffix}",
            summary="", keywords="", portal=portal,
            country="CO", modality="remote",
        )

    def test_post_cascades_to_all_siblings(self, authed_client, user):
        """3 duplicados en DB (mismo title+company+portal, URL distinta).
        POST ignore de UNA marca las 3."""
        a = self._make_dup("#lc=Score0-16")
        b = self._make_dup("#lc=Score0-9")
        c = self._make_dup("#lc=Score0-1")

        response = authed_client.post(f"/api/jobs/jobs/{a.id}/ignore/")
        assert response.status_code == 201
        assert response.json()["cascaded_count"] == 3

        assert IgnoredOffer.objects.filter(user=user, offer=a).exists()
        assert IgnoredOffer.objects.filter(user=user, offer=b).exists()
        assert IgnoredOffer.objects.filter(user=user, offer=c).exists()

    def test_delete_cascades_to_all_siblings(self, authed_client, user):
        """DELETE tambien cascadea — designorar UNA libera a todas las
        duplicadas."""
        a = self._make_dup("#lc=Score0-16")
        b = self._make_dup("#lc=Score0-9")
        IgnoredOffer.objects.create(user=user, offer=a)
        IgnoredOffer.objects.create(user=user, offer=b)

        response = authed_client.delete(f"/api/jobs/jobs/{a.id}/ignore/")
        assert response.status_code == 204
        assert not IgnoredOffer.objects.filter(user=user, offer=a).exists()
        assert not IgnoredOffer.objects.filter(user=user, offer=b).exists()

    def test_cascade_does_not_touch_different_company(self, authed_client, user):
        """Mismo title + portal pero company distinta = OFERTAS DISTINTAS
        (dos empresas del mismo portal buscando el mismo cargo). NO
        cascadeamos."""
        peaku = self._make_dup("-1", title="Backend Developer")
        empresa_x = JobOffer.objects.create(
            title="Backend Developer", company="Empresa X",
            url="https://co.computrabajo.com/o/EMPX",
            summary="", keywords="", portal="computrabajo",
            country="CO", modality="remote",
        )

        authed_client.post(f"/api/jobs/jobs/{peaku.id}/ignore/")

        assert IgnoredOffer.objects.filter(user=user, offer=peaku).exists()
        assert not IgnoredOffer.objects.filter(user=user, offer=empresa_x).exists()

    def test_cascade_does_not_touch_different_portal(self, authed_client, user):
        """Mismo title + company pero portal distinto = ofertas cross-post.
        Las dejamos separadas — el user puede querer ver la que tiene
        proceso de aplicacion mas simple en un portal."""
        ct = self._make_dup("-1")
        linkedin = JobOffer.objects.create(
            title="Fullstack Bilingue 52172", company="PeakU",
            url="https://linkedin.com/jobs/1",
            summary="", keywords="", portal="linkedin",
            country="CO", modality="remote",
        )

        authed_client.post(f"/api/jobs/jobs/{ct.id}/ignore/")

        assert IgnoredOffer.objects.filter(user=user, offer=ct).exists()
        assert not IgnoredOffer.objects.filter(user=user, offer=linkedin).exists()

    def test_feed_excludes_all_cascaded_after_ignore(self, authed_client, user):
        """Integration: ignorar UNA duplicada saca a TODAS del feed."""
        a = self._make_dup("#lc=Score0-16")
        b = self._make_dup("#lc=Score0-9")

        authed_client.post(f"/api/jobs/jobs/{a.id}/ignore/")

        response = authed_client.get("/api/jobs/jobs/?min_match=0")
        titles = [r["title"] for r in response.json()["results"]]
        # Ninguna de las duplicadas debe aparecer.
        assert "Fullstack Bilingue 52172" not in titles


@pytest.mark.integration
@pytest.mark.django_db
class TestFeedExcludesIgnored:
    def test_feed_excludes_user_ignored_offers(self, authed_client, user, offers_pair):
        a, b = offers_pair
        IgnoredOffer.objects.create(user=user, offer=a)
        response = authed_client.get("/api/jobs/jobs/")
        titles = [r["title"] for r in response.json()["results"]]
        assert "Offer A" not in titles
        assert "Offer B" in titles

    def test_feed_only_excludes_own_ignored(self, authed_client, user, django_user_model, offers_pair):
        """User2 ignora la oferta → user (autenticado) la ve igual."""
        a, b = offers_pair
        other = django_user_model.objects.create_user(
            username="bob", email="bob@example.com", password="x",
        )
        IgnoredOffer.objects.create(user=other, offer=a)
        response = authed_client.get("/api/jobs/jobs/")
        titles = [r["title"] for r in response.json()["results"]]
        assert "Offer A" in titles
        assert "Offer B" in titles


@pytest.mark.integration
@pytest.mark.django_db
class TestIgnoredListEndpoint:
    def test_returns_only_user_ignored(self, authed_client, user, offers_pair):
        a, b = offers_pair
        IgnoredOffer.objects.create(user=user, offer=a)
        response = authed_client.get("/api/jobs/jobs/ignored/")
        assert response.status_code == 200
        titles = [r["title"] for r in response.json()]
        assert titles == ["Offer A"]

    def test_empty_when_no_ignored(self, authed_client, offers_pair):
        response = authed_client.get("/api/jobs/jobs/ignored/")
        assert response.status_code == 200
        assert response.json() == []

    def test_orders_by_most_recent_first(self, authed_client, user, offers_pair):
        from datetime import timedelta

        from django.utils import timezone

        a, b = offers_pair
        # Forzamos timestamps explícitos: a ignorada antes que b. Sin esto,
        # auto_now_add le da el mismo timestamp y el orden queda indefinido.
        now = timezone.now()
        IgnoredOffer.objects.create(user=user, offer=a)
        IgnoredOffer.objects.filter(user=user, offer=a).update(
            created_at=now - timedelta(minutes=5)
        )
        IgnoredOffer.objects.create(user=user, offer=b)
        IgnoredOffer.objects.filter(user=user, offer=b).update(created_at=now)
        response = authed_client.get("/api/jobs/jobs/ignored/")
        titles = [r["title"] for r in response.json()]
        assert titles == ["Offer B", "Offer A"]

    def test_requires_auth(self, api_client):
        response = api_client.get("/api/jobs/jobs/ignored/")
        assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.django_db
class TestCascadeCleanup:
    def test_ignored_records_die_with_offer(self, user, offers_pair):
        """Cuando clean_old_offers borra el JobOffer, el IgnoredOffer cascadea."""
        a, _ = offers_pair
        IgnoredOffer.objects.create(user=user, offer=a)
        assert IgnoredOffer.objects.filter(offer=a).exists()
        a.delete()
        assert not IgnoredOffer.objects.filter(offer_id=a.id).exists()

    def test_ignored_records_die_with_user(self, user, offers_pair):
        a, _ = offers_pair
        IgnoredOffer.objects.create(user=user, offer=a)
        user.delete()
        assert not IgnoredOffer.objects.filter(offer=a).exists()

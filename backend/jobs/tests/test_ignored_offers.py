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
        assert response.json() == {"ignored": True, "offer_id": a.id}
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

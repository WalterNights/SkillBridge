"""Tests de reseñas.

Cubre:
  - Elegibilidad: solo postulaciones reales cuentan (pending no), y el
    PUT se bloquea por debajo del mínimo.
  - Crear/editar mi reseña: validación, vuelve a pending al editar.
  - Landing: solo published + rating >= 4 + allow_public, sin PII extra.
  - Admin: gating y auditoría de moderación.
"""

import pytest
from django.utils import timezone

from applications.models import JobApplication
from jobs.models import JobOffer
from reviews.models import Review

GOOD_COMMENT = "El match con mi CV me ahorró horas filtrando ofertas."


@pytest.fixture(autouse=True)
def _clear_ratelimit_cache():
    """El rate limit comparte bucket entre tests (LocMem cache)."""
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()


@pytest.fixture(autouse=True)
def _min_applications(settings):
    settings.REVIEWS_MIN_APPLICATIONS = 3


def _make_applications(user, n: int, status: str = "applied") -> None:
    for i in range(n):
        offer = JobOffer.objects.create(
            title=f"Oferta {status} {i}",
            company="Acme",
            url=f"https://example.com/jobs/{status}-{i}-{user.pk}",
        )
        JobApplication.objects.create(
            user=user,
            offer=offer,
            status=status,
            applied_at=timezone.now() if status != "pending" else None,
        )


@pytest.mark.integration
@pytest.mark.django_db
class TestEligibility:
    def test_anonymous_cannot_read_me(self, api_client):
        assert api_client.get("/api/reviews/me/").status_code == 401

    def test_pending_applications_do_not_count(self, authed_client, user):
        _make_applications(user, 5, status="pending")
        body = authed_client.get("/api/reviews/me/").json()
        assert body["eligible"] is False
        assert body["applications_count"] == 0
        assert body["min_applications"] == 3
        assert body["review"] is None

    def test_status_without_applied_at_counts(self, authed_client, user):
        """Saltar de pending directo a interview implica haber aplicado."""
        offer = JobOffer.objects.create(title="X", company="Y", url="https://example.com/x")
        JobApplication.objects.create(user=user, offer=offer, status="interview")
        body = authed_client.get("/api/reviews/me/").json()
        assert body["applications_count"] == 1

    def test_put_blocked_below_minimum(self, authed_client, user):
        _make_applications(user, 2)
        r = authed_client.put(
            "/api/reviews/me/",
            {"rating": 5, "comment": GOOD_COMMENT, "allow_public": True},
            format="json",
        )
        assert r.status_code == 403
        assert not Review.objects.filter(user=user).exists()


@pytest.mark.integration
@pytest.mark.django_db
class TestMyReview:
    def test_create_review_starts_pending(self, authed_client, user):
        _make_applications(user, 3)
        r = authed_client.put(
            "/api/reviews/me/",
            {"rating": 5, "comment": GOOD_COMMENT, "allow_public": True},
            format="json",
        )
        assert r.status_code == 200
        body = r.json()
        assert body["eligible"] is True
        assert body["review"]["status"] == "pending"
        assert Review.objects.get(user=user).rating == 5

    def test_short_comment_rejected(self, authed_client, user):
        _make_applications(user, 3)
        r = authed_client.put(
            "/api/reviews/me/", {"rating": 5, "comment": "Muy bueno"}, format="json"
        )
        assert r.status_code == 400
        assert "comment" in r.json()

    def test_rating_out_of_range_rejected(self, authed_client, user):
        _make_applications(user, 3)
        r = authed_client.put(
            "/api/reviews/me/", {"rating": 6, "comment": GOOD_COMMENT}, format="json"
        )
        assert r.status_code == 400

    def test_user_cannot_self_publish(self, authed_client, user):
        _make_applications(user, 3)
        authed_client.put(
            "/api/reviews/me/",
            {"rating": 5, "comment": GOOD_COMMENT, "status": "published"},
            format="json",
        )
        assert Review.objects.get(user=user).status == Review.STATUS_PENDING

    def test_edit_resets_to_pending(self, authed_client, user, admin_user):
        _make_applications(user, 3)
        Review.objects.create(
            user=user,
            rating=5,
            comment=GOOD_COMMENT,
            status=Review.STATUS_PUBLISHED,
            moderated_by=admin_user,
            moderated_at=timezone.now(),
        )
        authed_client.put(
            "/api/reviews/me/",
            {"rating": 4, "comment": GOOD_COMMENT + " Editado.", "allow_public": True},
            format="json",
        )
        review = Review.objects.get(user=user)
        assert review.status == Review.STATUS_PENDING
        assert review.moderated_by is None
        assert Review.objects.filter(user=user).count() == 1

    def test_delete_own_review(self, authed_client, user):
        Review.objects.create(user=user, rating=5, comment=GOOD_COMMENT)
        assert authed_client.delete("/api/reviews/me/").status_code == 204
        assert not Review.objects.filter(user=user).exists()


@pytest.mark.integration
@pytest.mark.django_db
class TestLanding:
    def _review(self, django_user_model, username, **kwargs):
        u = django_user_model.objects.create_user(
            username=username, email=f"{username}@example.com", password="x"
        )
        defaults = {
            "rating": 5,
            "comment": GOOD_COMMENT,
            "allow_public": True,
            "status": Review.STATUS_PUBLISHED,
            "moderated_at": timezone.now(),
        }
        defaults.update(kwargs)
        return Review.objects.create(user=u, **defaults)

    def test_only_published_positive_consented(self, api_client, django_user_model):
        ok = self._review(django_user_model, "ok")
        self._review(django_user_model, "low", rating=3)
        self._review(django_user_model, "pending", status=Review.STATUS_PENDING)
        self._review(django_user_model, "rejected", status=Review.STATUS_REJECTED)
        self._review(django_user_model, "private", allow_public=False)

        r = api_client.get("/api/reviews/landing/")
        assert r.status_code == 200
        ids = [item["id"] for item in r.json()]
        assert ids == [ok.id]

    def test_payload_uses_short_name_and_no_pii(self, api_client, user, user_profile):
        Review.objects.create(
            user=user,
            rating=5,
            comment=GOOD_COMMENT,
            allow_public=True,
            status=Review.STATUS_PUBLISHED,
        )
        item = api_client.get("/api/reviews/landing/").json()[0]
        assert item["name"] == "Alice D."
        assert item["role"] == "Backend Developer"
        assert item["city"] == "Buenos Aires"
        assert item["photo_url"] is None
        assert "username" not in item and "email" not in item

    def test_empty_when_no_reviews(self, api_client):
        assert api_client.get("/api/reviews/landing/").json() == []


@pytest.mark.integration
@pytest.mark.django_db
class TestAdmin:
    def test_regular_user_forbidden(self, authed_client):
        assert authed_client.get("/api/reviews/admin/").status_code == 403

    def test_list_defaults_to_pending(self, api_client, admin_user, user):
        Review.objects.create(user=user, rating=5, comment=GOOD_COMMENT)
        api_client.force_authenticate(user=admin_user)
        body = api_client.get("/api/reviews/admin/").json()
        assert body["count"] == 1
        assert body["results"][0]["username"] == "alice"
        # 5 estrellas pero sin consentimiento → no llegaría al landing.
        assert body["results"][0]["landing_eligible"] is False

    def test_publish_records_moderator(self, api_client, admin_user, user):
        review = Review.objects.create(user=user, rating=5, comment=GOOD_COMMENT)
        api_client.force_authenticate(user=admin_user)
        r = api_client.patch(
            f"/api/reviews/admin/{review.pk}/", {"status": "published"}, format="json"
        )
        assert r.status_code == 200
        review.refresh_from_db()
        assert review.status == Review.STATUS_PUBLISHED
        assert review.moderated_by == admin_user
        assert review.moderated_at is not None

    def test_admin_cannot_rewrite_comment(self, api_client, admin_user, user):
        review = Review.objects.create(user=user, rating=2, comment=GOOD_COMMENT)
        api_client.force_authenticate(user=admin_user)
        api_client.patch(
            f"/api/reviews/admin/{review.pk}/",
            {"comment": "Excelente plataforma, la mejor.", "rating": 5},
            format="json",
        )
        review.refresh_from_db()
        assert review.comment == GOOD_COMMENT
        assert review.rating == 2

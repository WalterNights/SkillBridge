"""Smoke tests del endpoint /api/applications/.

Cubre:
  - Auth gating (401 sin token)
  - Anti-IDOR (404 al tocar applications de otro user)
  - Create idempotente (segundo POST devuelve la existente sin error)
  - Confirm flip status + applied_at
  - Delete (undo)
  - applied-ids endpoint para el badge del feed
"""

import pytest

from applications.models import JobApplication


@pytest.fixture
def other_user(django_user_model):
    return django_user_model.objects.create_user(
        username="bob", email="bob@example.com", password="bobpass123"
    )


@pytest.fixture
def my_application(user, job_offer):
    return JobApplication.objects.create(
        user=user, offer=job_offer, status="pending"
    )


@pytest.fixture
def others_application(other_user, job_offer):
    return JobApplication.objects.create(
        user=other_user, offer=job_offer, status="applied"
    )


@pytest.mark.integration
@pytest.mark.django_db
class TestApplicationCreate:
    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.post("/api/applications/", {"offer_id": 1})
        assert response.status_code == 401

    def test_create_records_pending(self, authed_client, job_offer):
        response = authed_client.post(
            "/api/applications/", {"offer_id": job_offer.id}
        )
        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "pending"
        assert body["applied_at"] is None
        assert body["offer"]["id"] == job_offer.id

    def test_create_is_idempotent(self, authed_client, job_offer):
        first = authed_client.post(
            "/api/applications/", {"offer_id": job_offer.id}
        )
        assert first.status_code == 201

        # Segundo POST con el mismo offer no crea otro — devuelve el existente.
        second = authed_client.post(
            "/api/applications/", {"offer_id": job_offer.id}
        )
        assert second.status_code == 200
        assert second.json()["id"] == first.json()["id"]
        assert JobApplication.objects.filter(offer=job_offer).count() == 1


@pytest.mark.integration
@pytest.mark.django_db
class TestApplicationConfirm:
    def test_confirm_sets_applied_at(self, authed_client, my_application):
        assert my_application.status == "pending"
        assert my_application.applied_at is None

        response = authed_client.post(
            f"/api/applications/{my_application.id}/confirm/"
        )
        assert response.status_code == 200

        my_application.refresh_from_db()
        assert my_application.status == "applied"
        assert my_application.applied_at is not None

    def test_cannot_confirm_others_application(
        self, authed_client, others_application
    ):
        # SEGURIDAD: id correcto, pero el queryset filtra por user → 404
        response = authed_client.post(
            f"/api/applications/{others_application.id}/confirm/"
        )
        assert response.status_code == 404
        others_application.refresh_from_db()
        assert others_application.status == "applied"  # sin tocar


@pytest.mark.integration
@pytest.mark.django_db
class TestApplicationDelete:
    def test_delete_removes_pending(self, authed_client, my_application):
        response = authed_client.delete(f"/api/applications/{my_application.id}/")
        assert response.status_code == 204
        assert not JobApplication.objects.filter(id=my_application.id).exists()

    def test_cannot_delete_others_application(
        self, authed_client, others_application
    ):
        response = authed_client.delete(
            f"/api/applications/{others_application.id}/"
        )
        assert response.status_code == 404
        assert JobApplication.objects.filter(id=others_application.id).exists()


@pytest.mark.integration
@pytest.mark.django_db
class TestApplicationList:
    def test_list_returns_only_own(
        self, authed_client, my_application, others_application
    ):
        response = authed_client.get("/api/applications/")
        assert response.status_code == 200
        body = response.json()
        ids = [a["id"] for a in body]
        assert my_application.id in ids
        assert others_application.id not in ids

    def test_applied_ids_only_returns_status_applied(
        self, authed_client, user, job_offer, django_user_model
    ):
        # User tiene una pending y una applied — solo applied debe salir.
        other_offer = type(job_offer).objects.create(
            title="Other", company="Co", location="Loc",
            summary="", keywords="", url="https://x.com/2",
        )
        JobApplication.objects.create(user=user, offer=job_offer, status="pending")
        applied = JobApplication.objects.create(
            user=user, offer=other_offer, status="applied"
        )

        response = authed_client.get("/api/applications/applied-ids/")
        assert response.status_code == 200
        ids = response.json()["applied_offer_ids"]
        assert ids == [applied.offer_id]

"""Smoke tests del endpoint /api/notifications/.

Cobertura mínima para asegurar:
  - GET lista solo las del usuario autenticado (anti-IDOR)
  - mark-read / toggle-save mutan el estado correcto
  - mark-all-read solo afecta al user actual
"""

import pytest

from notifications.models import Notification


@pytest.fixture
def other_user(django_user_model):
    return django_user_model.objects.create_user(
        username="bob", email="bob@example.com", password="bobpass123"
    )


@pytest.fixture
def my_notifs(user):
    """Tres notifs del user — unread match, read system, saved reminder."""
    return [
        Notification.objects.create(
            user=user, kind="match", title="3 nuevas ofertas", body="…", is_read=False
        ),
        Notification.objects.create(
            user=user, kind="system", title="CV actualizado", body="…", is_read=True
        ),
        Notification.objects.create(
            user=user, kind="reminder", title="Completá tu perfil", body="…", is_saved=True
        ),
    ]


@pytest.fixture
def others_notif(other_user):
    """Notif que NO debería ver `user`. Útil para validar el isolation."""
    return Notification.objects.create(
        user=other_user, kind="match", title="Secreto de Bob", body="…"
    )


@pytest.mark.integration
@pytest.mark.django_db
class TestNotificationList:
    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.get("/api/notifications/")
        assert response.status_code == 401

    def test_lists_only_own_notifications(
        self, authed_client, my_notifs, others_notif
    ):
        response = authed_client.get("/api/notifications/")
        assert response.status_code == 200
        titles = [n["title"] for n in response.json()]
        assert "Secreto de Bob" not in titles
        assert len(titles) == 3

    def test_status_unread_filter(self, authed_client, my_notifs):
        response = authed_client.get("/api/notifications/?status=unread")
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 2  # match + reminder (system está read)
        assert all(not n["is_read"] for n in body)

    def test_status_saved_filter(self, authed_client, my_notifs):
        response = authed_client.get("/api/notifications/?status=saved")
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["title"] == "Completá tu perfil"


@pytest.mark.integration
@pytest.mark.django_db
class TestNotificationActions:
    def test_mark_read_sets_is_read_true(self, authed_client, my_notifs):
        unread = my_notifs[0]
        assert unread.is_read is False

        response = authed_client.post(f"/api/notifications/{unread.id}/mark-read/")
        assert response.status_code == 200

        unread.refresh_from_db()
        assert unread.is_read is True

    def test_toggle_save_flips_is_saved(self, authed_client, my_notifs):
        target = my_notifs[0]
        assert target.is_saved is False

        response = authed_client.post(f"/api/notifications/{target.id}/toggle-save/")
        assert response.status_code == 200
        target.refresh_from_db()
        assert target.is_saved is True

        # Toggle de nuevo lo vuelve a False
        authed_client.post(f"/api/notifications/{target.id}/toggle-save/")
        target.refresh_from_db()
        assert target.is_saved is False

    def test_mark_all_read_only_affects_own_notifs(
        self, authed_client, my_notifs, others_notif
    ):
        response = authed_client.post("/api/notifications/mark-all-read/")
        assert response.status_code == 200
        # Eran 2 unread del user (1 match + 1 reminder); system ya estaba read.
        assert response.json()["updated"] == 2

        others_notif.refresh_from_db()
        assert others_notif.is_read is False  # NO se tocó

    def test_cannot_modify_other_users_notification(
        self, authed_client, others_notif
    ):
        # SEGURIDAD: id correcto, pero el queryset filtra por user → 404
        response = authed_client.post(
            f"/api/notifications/{others_notif.id}/mark-read/"
        )
        assert response.status_code == 404
        others_notif.refresh_from_db()
        assert others_notif.is_read is False

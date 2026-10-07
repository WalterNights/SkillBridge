"""DELETE /api/dashboard/users/{id}/ — eliminar cuentas desde el admin.

Cubre las reglas de permisos (solo admins, nadie se elimina a sí mismo,
solo un super-admin elimina admins) y que el borrado arrastra el perfil
(PROTECT) y lo que cuelga de la cuenta.
"""

import pytest

from applications.models import JobApplication
from jobs.models import JobOffer
from users.models import User, UserProfile


def _url(user_id: int) -> str:
    return f"/api/dashboard/users/{user_id}/"


@pytest.fixture
def staff_user(django_user_model):
    """Admin común (is_staff) sin super-admin."""
    return django_user_model.objects.create_user(
        username="staff", email="staff@example.com", password="x", is_staff=True
    )


@pytest.fixture
def victim(user):
    """Usuario normal con perfil y una postulación."""
    UserProfile.objects.create(
        user=user, first_name="Ana", last_name="G", phone="+57", city="Bogotá"
    )
    offer = JobOffer.objects.create(title="Dev", company="Acme", url="https://example.com/o/1")
    JobApplication.objects.create(user=user, offer=offer, status="applied")
    return user


@pytest.mark.integration
@pytest.mark.django_db
class TestAdminUserDelete:
    def test_regular_user_forbidden(self, authed_client, django_user_model):
        other = django_user_model.objects.create_user(
            username="other", email="other@example.com", password="x"
        )
        assert authed_client.delete(_url(other.id)).status_code == 403

    def test_admin_deletes_user_with_profile_and_data(self, api_client, staff_user, victim):
        api_client.force_authenticate(user=staff_user)
        response = api_client.delete(_url(victim.id))
        assert response.status_code == 204
        assert not User.objects.filter(pk=victim.pk).exists()
        assert not UserProfile.objects.filter(user_id=victim.pk).exists()
        assert not JobApplication.objects.filter(user_id=victim.pk).exists()

    def test_cannot_delete_self(self, api_client, admin_user):
        api_client.force_authenticate(user=admin_user)
        response = api_client.delete(_url(admin_user.id))
        assert response.status_code == 400
        assert response.json()["error"] == "self_delete_forbidden"
        assert User.objects.filter(pk=admin_user.pk).exists()

    def test_staff_cannot_delete_another_admin(self, api_client, staff_user, admin_user):
        api_client.force_authenticate(user=staff_user)
        response = api_client.delete(_url(admin_user.id))
        assert response.status_code == 403
        assert User.objects.filter(pk=admin_user.pk).exists()

    def test_superuser_can_delete_admin(self, api_client, admin_user, staff_user):
        api_client.force_authenticate(user=admin_user)
        assert api_client.delete(_url(staff_user.id)).status_code == 204
        assert not User.objects.filter(pk=staff_user.pk).exists()

    def test_unknown_user_returns_404(self, api_client, admin_user):
        api_client.force_authenticate(user=admin_user)
        assert api_client.delete(_url(999999)).status_code == 404

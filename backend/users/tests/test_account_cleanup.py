"""Tests de la limpieza de cuentas con perfil incompleto.

Cubre:
- Qué se borra: incompletas (sin perfil o con campos vacíos) pasado el plazo.
- Qué NO se borra: completas, dentro del plazo, staff/superuser.
- Empresas: misma regla con su CompanyProfile.
- dry-run, tarea apagada/encendida y el comando de gestión.
"""

from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.utils import timezone

from users.models import CompanyProfile, User, UserProfile
from users.services.account_cleanup import delete_incomplete_accounts, is_profile_complete
from users.tasks import delete_incomplete_accounts as delete_task


def _user(username: str, days_ago: int = 10, **extra) -> User:
    user = User.objects.create_user(
        username=username, email=f"{username}@example.com", password="x", **extra
    )
    User.objects.filter(pk=user.pk).update(date_joined=timezone.now() - timedelta(days=days_ago))
    user.refresh_from_db()
    return user


def _profile(user: User, **overrides) -> UserProfile:
    data = {
        "first_name": "Ana",
        "last_name": "Gómez",
        "phone": "+573001112233",
        "city": "Bogotá",
        "professional_title": "Backend Developer",
    }
    data.update(overrides)
    return UserProfile.objects.create(user=user, **data)


@pytest.mark.integration
@pytest.mark.django_db
class TestAccountCleanup:
    def test_deletes_old_accounts_without_or_with_partial_profile(self):
        no_profile = _user("sin_perfil")
        partial = _user("parcial")
        _profile(partial, professional_title="")

        result = delete_incomplete_accounts()

        assert set(result.deleted_ids) == {no_profile.id, partial.id}
        assert not User.objects.filter(id__in=[no_profile.id, partial.id]).exists()
        assert not UserProfile.objects.filter(user_id=partial.id).exists()

    def test_keeps_complete_recent_and_staff_accounts(self):
        complete = _user("completo")
        _profile(complete)
        recent = _user("reciente", days_ago=2)
        staff = _user("staff", is_staff=True)

        result = delete_incomplete_accounts()

        assert result.count == 0
        assert User.objects.filter(id__in=[complete.id, recent.id, staff.id]).count() == 3

    def test_company_accounts_use_company_profile_rule(self):
        incomplete = _user("empresa_a", account_type=User.ACCOUNT_TYPE_COMPANY)
        CompanyProfile.objects.create(user=incomplete, legal_name="Acme", responsible_name="")
        complete = _user("empresa_b", account_type=User.ACCOUNT_TYPE_COMPANY)
        CompanyProfile.objects.create(
            user=complete, legal_name="Acme", responsible_name="Ana", responsible_role="CEO"
        )

        assert is_profile_complete(complete) is True
        result = delete_incomplete_accounts()

        assert result.deleted_ids == [incomplete.id]
        assert User.objects.filter(id=complete.id).exists()

    def test_dry_run_deletes_nothing(self):
        user = _user("sin_perfil")
        result = delete_incomplete_accounts(dry_run=True)
        assert result.deleted_ids == [user.id]
        assert User.objects.filter(id=user.id).exists()

    def test_task_is_noop_while_disabled(self, settings):
        settings.INCOMPLETE_ACCOUNT_CLEANUP_ENABLED = False
        user = _user("sin_perfil")
        assert delete_task() == {"status": "disabled", "deleted": 0}
        assert User.objects.filter(id=user.id).exists()

    def test_task_deletes_when_enabled(self, settings):
        settings.INCOMPLETE_ACCOUNT_CLEANUP_ENABLED = True
        user = _user("sin_perfil")
        assert delete_task() == {"status": "success", "deleted": 1}
        assert not User.objects.filter(id=user.id).exists()

    def test_grace_days_is_configurable(self, settings):
        settings.INCOMPLETE_ACCOUNT_GRACE_DAYS = 30
        user = _user("sin_perfil", days_ago=10)
        assert delete_incomplete_accounts().count == 0
        assert User.objects.filter(id=user.id).exists()

    def test_command_dry_run_lists_accounts(self):
        _user("sin_perfil")
        out = StringIO()
        call_command("delete_incomplete_accounts", "--dry-run", stdout=out)
        assert "Se eliminarían 1 cuentas" in out.getvalue()
        assert "sin_perfil" in out.getvalue()
        assert User.objects.filter(username="sin_perfil").exists()

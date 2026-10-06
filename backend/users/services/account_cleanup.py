"""Limpieza de cuentas que se registraron pero nunca completaron el perfil.

Regla: si pasan `settings.INCOMPLETE_ACCOUNT_GRACE_DAYS` (5) desde el
registro y el perfil sigue incompleto, la cuenta se elimina. Corre a diario
con la tarea `users.delete_incomplete_accounts`, y se puede previsualizar
con `manage.py delete_incomplete_accounts --dry-run`.

"Completo" usa la MISMA regla que el JWT (`is_profile_complete`), que es
la que decide si el frontend manda al usuario al wizard de `/profile`.

Nunca se tocan cuentas `is_staff` / `is_superuser`.
"""

from __future__ import annotations

import logging
from contextlib import suppress
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.utils import timezone

from users.models import User

logger = logging.getLogger(__name__)


def is_profile_complete(user: User) -> bool:
    """True si el usuario completó su perfil (profesional o empresa)."""
    if user.account_type == User.ACCOUNT_TYPE_COMPANY:
        try:
            company = user.company_profile
        except ObjectDoesNotExist:
            return False
        return bool(company.legal_name and company.responsible_name and company.responsible_role)

    try:
        profile = user.profile
    except ObjectDoesNotExist:
        return False
    return bool(
        profile.first_name
        and profile.last_name
        and profile.city
        and profile.phone
        and profile.professional_title
    )


@dataclass(frozen=True)
class CleanupResult:
    deleted_ids: list[int]
    dry_run: bool

    @property
    def count(self) -> int:
        return len(self.deleted_ids)


def find_incomplete_accounts(now=None) -> list[User]:
    """Cuentas no-staff registradas hace más del período de gracia y con el
    perfil todavía incompleto."""
    now = now or timezone.now()
    cutoff = now - timedelta(days=settings.INCOMPLETE_ACCOUNT_GRACE_DAYS)
    candidates = User.objects.filter(
        is_staff=False, is_superuser=False, date_joined__lt=cutoff
    ).select_related("profile", "company_profile")
    return [user for user in candidates if not is_profile_complete(user)]


def delete_incomplete_accounts(dry_run: bool = False, now=None) -> CleanupResult:
    """Elimina (o solo lista, con `dry_run`) las cuentas incompletas vencidas.

    `UserProfile.user` y `CompanyProfile.user` son PROTECT: se borra el
    perfil parcial primero y después la cuenta, en una transacción por
    usuario para que una falla no deje a nadie a medio borrar.
    """
    accounts = find_incomplete_accounts(now)
    if dry_run:
        return CleanupResult(deleted_ids=[u.id for u in accounts], dry_run=True)

    deleted_ids: list[int] = []
    for user in accounts:
        user_id = user.id  # delete() deja el pk en None
        try:
            with transaction.atomic():
                for relation in ("profile", "company_profile"):
                    with suppress(ObjectDoesNotExist):
                        getattr(user, relation).delete()
                user.delete()
            deleted_ids.append(user_id)
        except Exception:
            logger.exception("No se pudo eliminar la cuenta incompleta %s", user_id)

    logger.info("delete_incomplete_accounts: %d cuentas eliminadas", len(deleted_ids))
    return CleanupResult(deleted_ids=deleted_ids, dry_run=False)

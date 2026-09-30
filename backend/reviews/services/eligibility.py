"""Quién puede dejar una reseña.

Una postulación cuenta como "real" cuando el usuario confirmó que
aplicó (`applied_at` seteado por el botón "Sí, apliqué") o cuando la
movió a un estado que implica haber aplicado. Los `pending` (click en
"Aplicar" sin confirmar) no cuentan.
"""

from __future__ import annotations

from django.conf import settings
from django.db.models import Q

from applications.models import JobApplication

# Estados que implican que el user efectivamente aplicó, aunque haya
# saltado de `pending` directo a uno de estos sin pasar por `applied`.
_APPLIED_STATUSES = JobApplication.ACTIVE_STATUSES | {"rejected"}


def count_real_applications(user) -> int:
    return (
        JobApplication.objects.filter(user=user)
        .filter(Q(applied_at__isnull=False) | Q(status__in=_APPLIED_STATUSES))
        .count()
    )


def min_applications_required() -> int:
    return settings.REVIEWS_MIN_APPLICATIONS


def is_eligible(user) -> bool:
    return count_real_applications(user) >= min_applications_required()

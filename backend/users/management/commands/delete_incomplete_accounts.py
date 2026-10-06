"""Elimina (o previsualiza) cuentas que no completaron el perfil a tiempo.

Uso en el server, antes de activar la tarea diaria:

    python manage.py delete_incomplete_accounts --dry-run   # solo lista
    python manage.py delete_incomplete_accounts             # borra
"""

from django.conf import settings
from django.core.management.base import BaseCommand

from users.models import User
from users.services.account_cleanup import delete_incomplete_accounts


class Command(BaseCommand):
    help = (
        "Elimina cuentas no-staff con el perfil incompleto después de "
        "INCOMPLETE_ACCOUNT_GRACE_DAYS días desde el registro."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Solo lista las cuentas que se eliminarían, sin borrar nada.",
        )

    def handle(self, *args, dry_run: bool = False, **options):
        result = delete_incomplete_accounts(dry_run=dry_run)
        verb = "Se eliminarían" if dry_run else "Eliminadas"
        self.stdout.write(
            f"{verb} {result.count} cuentas incompletas "
            f"(gracia: {settings.INCOMPLETE_ACCOUNT_GRACE_DAYS} días)."
        )
        if dry_run:
            for user in User.objects.filter(id__in=result.deleted_ids).order_by("date_joined"):
                self.stdout.write(
                    f"  - #{user.id} {user.username} <{user.email}> "
                    f"({user.account_type}, registrado {user.date_joined:%Y-%m-%d})"
                )

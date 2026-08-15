"""Seed inicial del portafolio `walternightsdev`.

Crea el Portfolio con el contenido bootstrap (ES + EN) y lo asigna al
primer superuser disponible. Si no hay ningún superuser al aplicar
(fresh install sin `createsuperuser`), skipea con un warning — el admin
puede correr `manage.py createsuperuser` y despues editar el owner via
`/admin/portfolio/portfolio/`.

Idempotente: usa update_or_create. Re-aplicar no duplica ni pisa edits
posteriores si el slug ya existe (solo actualiza campos vacíos).
"""

from __future__ import annotations

import logging

from django.db import migrations

logger = logging.getLogger(__name__)

SLUG = "walternightsdev"


def seed_walternightsdev(apps, schema_editor):
    Portfolio = apps.get_model("portfolio", "Portfolio")
    User = apps.get_model("users", "User")

    # Import diferido para que el archivo no se cargue en cada startup
    # de Django, solo cuando corre la migration.
    from portfolio.initial_content import (
        WALTERNIGHTSDEV_ES,
        WALTERNIGHTSDEV_EN,
    )

    if Portfolio.objects.filter(slug=SLUG).exists():
        # Ya existe (ej: en dev el admin editó el JSON via API) — no lo
        # pisamos.
        return

    owner = User.objects.filter(is_superuser=True).order_by("pk").first()
    if owner is None:
        # Fresh install sin superuser: sin owner no podemos crear el
        # portafolio (owner es NOT NULL). Skipeamos con warning; el
        # admin correrá createsuperuser + re-aplicará (o creará via
        # Django admin).
        logger.warning(
            "portfolio: no hay superuser para asignar como owner del "
            "portafolio '%s'. Skipeando seed. Correr `manage.py "
            "createsuperuser` y crear el portafolio via /admin/.",
            SLUG,
        )
        return

    Portfolio.objects.create(
        slug=SLUG,
        owner=owner,
        content=WALTERNIGHTSDEV_ES,
        content_en=WALTERNIGHTSDEV_EN,
    )


def unseed_walternightsdev(apps, schema_editor):
    Portfolio = apps.get_model("portfolio", "Portfolio")
    Portfolio.objects.filter(slug=SLUG).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("portfolio", "0001_initial"),
        # Necesitamos que el modelo User exista para el owner FK.
        ("users", "0018_cv_multilang_and_display_prefs"),
    ]

    operations = [
        migrations.RunPython(seed_walternightsdev, reverse_code=unseed_walternightsdev),
    ]

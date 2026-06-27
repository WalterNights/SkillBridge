"""Arregla las URLs de las ofertas de Torre ya guardadas en DB.

Bug: la primera version del TorreScraper construyo URLs como
`https://torre.co/jobs/{id}` o `https://torre.co/jobs/{id}/{slug}`.
Verificado en produccion 2026-06-27: torre.co redirige 301 a torre.ai
pero a un path que no existe → 404. El formato correcto es:
  - sin slug: https://torre.ai/jobs/{id}      (redirige al detail)
  - con slug: https://torre.ai/jobs/{id}-{slug}   (resuelve directo)

Esta migration transforma las URLs viejas in-place. Los conflictos
unique se resuelven borrando la oferta vieja en favor de la nueva
(la nueva URL es la correcta, asi que la vieja era basura).
"""

import re

from django.db import migrations
from django.db.utils import IntegrityError


_OLD_WITH_SLUG = re.compile(r"^https?://torre\.co/jobs/([^/]+)/(.+?)/?$")
_OLD_NO_SLUG = re.compile(r"^https?://torre\.co/jobs/([^/?#]+)/?$")


def _migrate_url(old: str) -> str | None:
    """Devuelve la URL nueva o None si la vieja ya esta en el formato OK."""
    if not old or "torre.co" not in old:
        return None
    m = _OLD_WITH_SLUG.match(old)
    if m:
        return f"https://torre.ai/jobs/{m.group(1)}-{m.group(2)}"
    m = _OLD_NO_SLUG.match(old)
    if m:
        return f"https://torre.ai/jobs/{m.group(1)}"
    return None


def fix_torre_urls(apps, schema_editor):
    JobOffer = apps.get_model("jobs", "JobOffer")
    qs = JobOffer.objects.filter(portal="torre", url__icontains="torre.co")
    migrated = 0
    deleted_dups = 0
    for offer in qs:
        new_url = _migrate_url(offer.url)
        if not new_url or new_url == offer.url:
            continue
        # Verificar si la URL nueva ya existe (caso raro: scrape post-fix
        # ya guardo la version torre.ai antes de correr esta migration).
        if JobOffer.objects.filter(url=new_url).exclude(pk=offer.pk).exists():
            offer.delete()
            deleted_dups += 1
            continue
        offer.url = new_url
        try:
            offer.save(update_fields=["url"])
            migrated += 1
        except IntegrityError:
            offer.delete()
            deleted_dups += 1


def reverse_noop(apps, schema_editor):
    """No reversible — las URLs viejas eran basura, no las restauramos."""
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("jobs", "0010_add_ignored_offer"),
    ]

    operations = [
        migrations.RunPython(fix_torre_urls, reverse_code=reverse_noop),
    ]

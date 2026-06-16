"""Tests de `JobService.scrape_all_portals` — orquestación paralela."""

from unittest.mock import patch

import pytest

from jobs.adapters.scrapers.base import JobOfferData
from jobs.models import JobOffer
from jobs.services.job_service import JobService


def _offer(url: str, portal: str = "computrabajo") -> JobOfferData:
    return JobOfferData(
        title=f"Role at {portal}",
        company="Co",
        location="X",
        summary=".",
        url=url,
        keywords="python",
        portal=portal,
    )


@pytest.mark.django_db
class TestScrapeAllPortals:
    # Los tests pasan `portals=[...]` explícitos para no depender del registry
    # (que hoy tiene solo Computrabajo activo — ver registry.py).

    def test_returns_offers_from_all_portals(self):
        """Cada portal devuelve sus ofertas, todas se persisten."""

        def fake_scrape_one(portal, query, location):
            if portal == "computrabajo":
                return [
                    _offer("https://co.example/1", "computrabajo"),
                    _offer("https://co.example/2", "computrabajo"),
                ]
            if portal == "elempleo":
                return [_offer("https://el.example/1", "elempleo")]
            return []

        with patch("jobs.services.job_service._scrape_one_portal", side_effect=fake_scrape_one):
            created = JobService.scrape_all_portals(
                "dev", "Bogotá", portals=["computrabajo", "elempleo"]
            )

        assert len(created) == 3
        portals = {o.portal for o in created}
        assert portals == {"computrabajo", "elempleo"}

    def test_one_portal_failing_does_not_break_others(self):
        """Si un portal explota, los demás siguen y devuelven sus ofertas."""

        def fake_scrape_one(portal, query, location):
            if portal == "computrabajo":
                raise RuntimeError("Computrabajo blocked us")
            if portal == "elempleo":
                return [_offer("https://el.example/x", "elempleo")]
            return []

        with patch("jobs.services.job_service._scrape_one_portal", side_effect=fake_scrape_one):
            created = JobService.scrape_all_portals(
                "dev", "Bogotá", portals=["computrabajo", "elempleo"]
            )

        assert len(created) == 1
        assert created[0].portal == "elempleo"

    def test_persists_portal_field_in_db(self):
        """El campo `portal` del DTO termina en el modelo."""

        def fake_scrape_one(portal, query, location):
            return [_offer(f"https://x.example/{portal}", portal)]

        with patch("jobs.services.job_service._scrape_one_portal", side_effect=fake_scrape_one):
            JobService.scrape_all_portals(
                "dev", "X", portals=["computrabajo", "elempleo"]
            )

        portals_in_db = set(JobOffer.objects.values_list("portal", flat=True))
        assert "computrabajo" in portals_in_db
        assert "elempleo" in portals_in_db

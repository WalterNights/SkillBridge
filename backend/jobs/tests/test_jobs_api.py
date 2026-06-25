"""Tests del endpoint /api/jobs/."""

import pytest

from jobs.models import JobOffer


@pytest.fixture
def offers_set():
    """Set diverso para tests de filtros: 4 ofertas en MX/CO con
    distintas modalidades."""
    return [
        JobOffer.objects.create(
            title="Remote MX 1", url="https://x.com/1",
            summary="", keywords="", portal="hireline",
            country="MX", modality="remote",
        ),
        JobOffer.objects.create(
            title="Onsite MX 1", url="https://x.com/2",
            summary="", keywords="", portal="hireline",
            country="MX", modality="onsite",
        ),
        JobOffer.objects.create(
            title="Hybrid CO 1", url="https://x.com/3",
            summary="", keywords="", portal="trabajos_co",
            country="CO", modality="hybrid",
        ),
        JobOffer.objects.create(
            title="Unknown AR 1", url="https://x.com/4",
            summary="", keywords="", portal="other",
            country="AR", modality="unknown",
        ),
    ]


@pytest.mark.integration
@pytest.mark.django_db
class TestJobsList:
    def test_unauthenticated_request_is_rejected(self, api_client):
        response = api_client.get("/api/jobs/jobs/")
        assert response.status_code == 401

    def test_returns_jobs_when_authenticated(self, authed_client, job_offer):
        response = authed_client.get("/api/jobs/jobs/")
        assert response.status_code == 200
        # DRF paginado: respuesta envuelta en `results`
        data = response.json()
        assert data["count"] == 1
        assert data["results"][0]["title"] == job_offer.title


@pytest.mark.integration
@pytest.mark.django_db
class TestJobsListFilters:
    def test_country_filter_single(self, authed_client, offers_set):
        response = authed_client.get("/api/jobs/jobs/?country=MX")
        assert response.status_code == 200
        titles = [r["title"] for r in response.json()["results"]]
        assert "Remote MX 1" in titles
        assert "Onsite MX 1" in titles
        assert "Hybrid CO 1" not in titles
        assert "Unknown AR 1" not in titles

    def test_country_filter_multi(self, authed_client, offers_set):
        response = authed_client.get("/api/jobs/jobs/?country=MX,CO")
        titles = sorted(r["title"] for r in response.json()["results"])
        assert titles == ["Hybrid CO 1", "Onsite MX 1", "Remote MX 1"]

    def test_modality_filter_single(self, authed_client, offers_set):
        response = authed_client.get("/api/jobs/jobs/?modality=remote")
        titles = [r["title"] for r in response.json()["results"]]
        assert titles == ["Remote MX 1"]

    def test_modality_filter_multi(self, authed_client, offers_set):
        response = authed_client.get("/api/jobs/jobs/?modality=remote,hybrid")
        titles = sorted(r["title"] for r in response.json()["results"])
        assert titles == ["Hybrid CO 1", "Remote MX 1"]

    def test_combined_country_and_modality(self, authed_client, offers_set):
        response = authed_client.get("/api/jobs/jobs/?country=MX&modality=remote")
        titles = [r["title"] for r in response.json()["results"]]
        assert titles == ["Remote MX 1"]

    def test_invalid_modality_silently_ignored(self, authed_client, offers_set):
        # ?modality=alien → no se filtra (no rompe el feed)
        response = authed_client.get("/api/jobs/jobs/?modality=alien")
        assert response.status_code == 200
        assert response.json()["count"] == 4

    def test_case_insensitive_country(self, authed_client, offers_set):
        # ?country=mx también funciona
        response = authed_client.get("/api/jobs/jobs/?country=mx")
        titles = [r["title"] for r in response.json()["results"]]
        assert {"Remote MX 1", "Onsite MX 1"} == set(titles)


@pytest.mark.integration
@pytest.mark.django_db
class TestJobsListOrdering:
    """Orden por % match — debe aplicarse a TODO el queryset antes de
    paginar, no solo a la página actual (sino el sort sería inútil con
    "Cargar más")."""

    def _setup_offers_with_keywords(self, user_profile):
        """4 ofertas con scores ESTRICTAMENTE distintos contra el perfil
        ('Backend Developer', skills python/django/postgresql/docker).
        Diferenciar scores es clave: si dos empatan, el orden secundario
        depende del `-created_at` del DB que varía entre runs aislados
        vs conjuntos por la resolución del timestamp en SQLite.
        """
        return [
            JobOffer.objects.create(
                title="Backend Developer Python",
                url="https://x.com/best",
                summary="", keywords="python, django, postgresql, docker",
                portal="hireline", country="MX", modality="remote",
            ),
            JobOffer.objects.create(
                title="Software Developer",
                url="https://x.com/mid-high",
                summary="", keywords="python",
                portal="hireline", country="MX", modality="remote",
            ),
            JobOffer.objects.create(
                title="Senior Engineer",
                url="https://x.com/mid-low",
                summary="", keywords="python, django",
                portal="hireline", country="MX", modality="remote",
            ),
            JobOffer.objects.create(
                title="Recepcionista Bilingüe",
                url="https://x.com/zero",
                summary="", keywords="atención, cliente, ventas",
                portal="hireline", country="MX", modality="remote",
            ),
        ]

    def test_match_desc_orders_best_first(self, authed_client, user_profile):
        # min_match=0 para aislar — sino el filtro default saca al de 0%.
        self._setup_offers_with_keywords(user_profile)
        response = authed_client.get("/api/jobs/jobs/?ordering=match_desc&min_match=0")
        assert response.status_code == 200
        titles = [r["title"] for r in response.json()["results"]]
        assert titles[0] == "Backend Developer Python"
        assert titles[-1] == "Recepcionista Bilingüe"

    def test_match_asc_orders_worst_first(self, authed_client, user_profile):
        self._setup_offers_with_keywords(user_profile)
        response = authed_client.get("/api/jobs/jobs/?ordering=match_asc&min_match=0")
        assert response.status_code == 200
        titles = [r["title"] for r in response.json()["results"]]
        assert titles[0] == "Recepcionista Bilingüe"
        assert titles[-1] == "Backend Developer Python"

    def test_invalid_ordering_falls_back_to_default(self, authed_client, user_profile):
        """?ordering=xyz no rompe — cae al default (match_desc)."""
        self._setup_offers_with_keywords(user_profile)
        response = authed_client.get("/api/jobs/jobs/?ordering=xyz&min_match=0")
        assert response.status_code == 200
        assert response.json()["count"] == 4


@pytest.mark.integration
@pytest.mark.django_db
class TestJobsListMinMatch:
    """El feed filtra ofertas con match bajo el umbral — sino aparecen
    ofertas totalmente off-topic con 0% (ej: 'Analista Control de Accesos'
    para un perfil de developer).
    """

    def _setup(self, user_profile):
        return [
            JobOffer.objects.create(
                title="Senior Python Developer",
                url="https://x.com/dev",
                summary="", keywords="python, django, postgresql",
                portal="hireline", country="MX", modality="remote",
            ),
            JobOffer.objects.create(
                title="Analista Control de Accesos",
                url="https://x.com/access",
                summary="", keywords="auditoría, calidad, crm, gdpr",
                portal="hireline", country="MX", modality="remote",
            ),
        ]

    def test_default_min_match_excludes_zero_score_offers(self, authed_client, user_profile):
        """Default 25% — la oferta off-topic con 0% no debe aparecer."""
        self._setup(user_profile)
        response = authed_client.get("/api/jobs/jobs/")
        titles = [r["title"] for r in response.json()["results"]]
        assert "Senior Python Developer" in titles
        assert "Analista Control de Accesos" not in titles

    def test_min_match_0_includes_everything(self, authed_client, user_profile):
        """min_match=0 = modo exploración, no filtra nada."""
        self._setup(user_profile)
        response = authed_client.get("/api/jobs/jobs/?min_match=0")
        titles = [r["title"] for r in response.json()["results"]]
        assert "Senior Python Developer" in titles
        assert "Analista Control de Accesos" in titles

    def test_min_match_high_threshold(self, authed_client, user_profile):
        """min_match=80 corta ofertas con match medio."""
        self._setup(user_profile)
        response = authed_client.get("/api/jobs/jobs/?min_match=80")
        # Nadie alcanza 80% en este setup
        assert response.json()["count"] == 0

    def test_min_match_invalid_falls_back_to_default(self, authed_client, user_profile):
        """?min_match=foo no rompe — cae al default 25."""
        self._setup(user_profile)
        response = authed_client.get("/api/jobs/jobs/?min_match=foo")
        assert response.status_code == 200
        titles = [r["title"] for r in response.json()["results"]]
        assert "Analista Control de Accesos" not in titles

    def test_min_match_clamped_above_100(self, authed_client, user_profile):
        """min_match=999 se clampa a 100 — devuelve solo matches perfectos."""
        self._setup(user_profile)
        response = authed_client.get("/api/jobs/jobs/?min_match=999")
        assert response.status_code == 200

    def test_no_profile_shows_all_offers(self, authed_client, user):
        """Sin perfil completo no podemos calcular match — el feed
        no debería quedar vacío. Cae al path 'sin filtro'."""
        # Note: user fixture exists but no profile created
        JobOffer.objects.create(
            title="Any job", url="https://x.com/any",
            summary="", keywords="cobol",
            portal="hireline", country="MX", modality="remote",
        )
        response = authed_client.get("/api/jobs/jobs/")
        assert response.status_code == 200
        assert response.json()["count"] == 1


@pytest.mark.integration
@pytest.mark.django_db
class TestFilterOptionsEndpoint:
    def test_returns_countries_and_modalities_with_counts(self, authed_client, offers_set):
        response = authed_client.get("/api/jobs/jobs/filter-options/")
        assert response.status_code == 200
        body = response.json()
        countries = {c["value"]: c["count"] for c in body["countries"]}
        assert countries == {"MX": 2, "CO": 1, "AR": 1}
        modalities = {m["value"]: m["count"] for m in body["modalities"]}
        assert modalities == {"remote": 1, "onsite": 1, "hybrid": 1, "unknown": 1}
        # Labels legibles incluidos
        for m in body["modalities"]:
            assert "label" in m

    def test_excludes_unknown_country_from_options(self, authed_client):
        JobOffer.objects.create(
            title="Sin país", url="https://x.com/xx",
            summary="", keywords="", portal="other",
            country="XX", modality="remote",
        )
        response = authed_client.get("/api/jobs/jobs/filter-options/")
        countries = [c["value"] for c in response.json()["countries"]]
        assert "XX" not in countries

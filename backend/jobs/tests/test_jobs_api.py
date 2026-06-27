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

        Todas marcadas `category='tech'` explícito — el filtro estricto
        del feed (2026-06-27) descarta 'general' para users de vertical
        específico, y este test mide ORDEN por match%, no clasificación.
        """
        return [
            JobOffer.objects.create(
                title="Backend Developer Python",
                url="https://x.com/best",
                summary="", keywords="python, django, postgresql, docker",
                portal="hireline", country="MX", modality="remote",
                category="tech",
            ),
            JobOffer.objects.create(
                title="Software Developer",
                url="https://x.com/mid-high",
                summary="", keywords="python",
                portal="hireline", country="MX", modality="remote",
                category="tech",
            ),
            JobOffer.objects.create(
                title="Senior Engineer",
                url="https://x.com/mid-low",
                summary="", keywords="python, django",
                portal="hireline", country="MX", modality="remote",
                category="tech",
            ),
            JobOffer.objects.create(
                # Tech con skills java/kotlin → 0% match con perfil python.
                # Sustituye al ejemplo viejo de "Recepcionista" que era
                # category general — el filtro nuevo lo descartaría
                # antes de calcular score.
                title="Mobile Developer Kotlin",
                url="https://x.com/zero",
                summary="", keywords="java, kotlin, swift",
                portal="hireline", country="MX", modality="remote",
                category="tech",
            ),
        ]

    def test_match_desc_orders_best_first(self, authed_client, user_profile):
        # min_match=0 para aislar — sino el filtro default saca al de 0%.
        self._setup_offers_with_keywords(user_profile)
        response = authed_client.get("/api/jobs/jobs/?ordering=match_desc&min_match=0")
        assert response.status_code == 200
        titles = [r["title"] for r in response.json()["results"]]
        assert titles[0] == "Backend Developer Python"
        assert titles[-1] == "Mobile Developer Kotlin"

    def test_match_asc_orders_worst_first(self, authed_client, user_profile):
        self._setup_offers_with_keywords(user_profile)
        response = authed_client.get("/api/jobs/jobs/?ordering=match_asc&min_match=0")
        assert response.status_code == 200
        titles = [r["title"] for r in response.json()["results"]]
        assert titles[0] == "Mobile Developer Kotlin"
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
        """Ofertas tageadas tech explícito — user_profile es Backend
        Developer (categoría tech) y el filtro estricto del feed
        (2026-06-27) excluye 'general' para users con vertical
        específica. Sin marcar category='tech', estos tests fallarían
        por el filtro, no por el threshold de match%."""
        return [
            JobOffer.objects.create(
                title="Senior Python Developer",
                url="https://x.com/dev",
                summary="", keywords="python, django, postgresql",
                portal="hireline", country="MX", modality="remote",
                category="tech",
            ),
            JobOffer.objects.create(
                title="Analista Control de Accesos",
                url="https://x.com/access",
                summary="", keywords="auditoría, calidad, crm, gdpr",
                portal="hireline", country="MX", modality="remote",
                category="tech",
            ),
        ]

    def test_default_min_match_excludes_zero_score_offers(self, authed_client, user_profile):
        """Default 50% — la oferta off-topic con 0% no debe aparecer."""
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
        """?min_match=foo no rompe — cae al default 50."""
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
class TestFeedFiltersByUserCategory:
    """Guarantía crítica de privacidad/separación de verticales: cada
    user solo ve ofertas de su categoría profesional (+ 'general'). Un
    abogado nunca debe ver 'Senior React Native Developer' aunque otro
    user lo haya scrapeado y esté en la DB compartida."""

    def _setup_offers(self):
        """Crea 3 ofertas — una de cada categoría — para validar el filtro."""
        from jobs.models import JobOffer

        return {
            "tech": JobOffer.objects.create(
                title="Senior React Native Developer",
                url="https://x.com/dev1",
                summary="React Native, TypeScript",
                keywords="react native",
                portal="hireline",
                category="tech",
            ),
            "legal": JobOffer.objects.create(
                title="Abogada Penalista",
                url="https://x.com/legal1",
                summary="Derecho penal y procesal",
                keywords="derecho penal",
                portal="computrabajo",
                category="legal",
            ),
            "general": JobOffer.objects.create(
                title="Asistente Multifuncional",
                url="https://x.com/gen1",
                summary="Apoyo en general",
                keywords="",
                portal="trabajando",
                category="general",
            ),
        }

    def _make_user_with_profile(self, django_user_model, *, title):
        from users.models import UserProfile

        user = django_user_model.objects.create_user(
            username=f"u_{title[:5]}".replace(" ", "_"),
            email=f"{title.replace(' ', '_')}@example.com",
            password="x",
        )
        UserProfile.objects.create(
            user=user,
            first_name="X",
            last_name="Y",
            phone="+57",
            city="Bogotá",
            professional_title=title,
            skills="",
            experience="",
        )
        return user

    def test_tech_user_only_sees_tech_offers(self, api_client, django_user_model):
        """User con título 'Backend Developer' (categoría tech) SOLO ve
        ofertas tech. NO ve legal ni 'general' (comodín fue eliminado
        2026-06-27 — reporte de cliente: 'NADA que no tenga que ver
        con la profesión')."""
        self._setup_offers()
        user = self._make_user_with_profile(django_user_model, title="Backend Developer")
        api_client.force_authenticate(user=user)
        response = api_client.get("/api/jobs/jobs/?min_match=0")
        titles = {r["title"] for r in response.json()["results"]}
        assert "Senior React Native Developer" in titles
        # 'general' YA NO se muestra a users con vertical específica.
        assert "Asistente Multifuncional" not in titles
        assert "Abogada Penalista" not in titles

    def test_legal_user_only_sees_legal_offers(self, api_client, django_user_model):
        """Mirror del test anterior — abogada SOLO ve ofertas legales."""
        self._setup_offers()
        user = self._make_user_with_profile(django_user_model, title="Abogada Civilista")
        api_client.force_authenticate(user=user)
        response = api_client.get("/api/jobs/jobs/?min_match=0")
        titles = {r["title"] for r in response.json()["results"]}
        assert "Abogada Penalista" in titles
        assert "Asistente Multifuncional" not in titles
        assert "Senior React Native Developer" not in titles

    def test_general_user_sees_everything(self, api_client, django_user_model):
        """User cuyo título no clasifica (categoría 'general') ve todas
        las ofertas — es el comodín / fallback."""
        self._setup_offers()
        user = self._make_user_with_profile(
            django_user_model, title="Foo Bar Baz Random"
        )
        api_client.force_authenticate(user=user)
        response = api_client.get("/api/jobs/jobs/?min_match=0")
        titles = {r["title"] for r in response.json()["results"]}
        assert "Senior React Native Developer" in titles
        assert "Abogada Penalista" in titles
        assert "Asistente Multifuncional" in titles

    def test_user_without_profile_sees_everything(self, api_client, django_user_model):
        """Sin UserProfile, no podemos clasificar — fallback a 'general'
        que muestra todo. Sin esto, users sin perfil verían feed vacío."""
        self._setup_offers()
        user = django_user_model.objects.create_user(
            username="noprofile", email="np@example.com", password="x"
        )
        api_client.force_authenticate(user=user)
        response = api_client.get("/api/jobs/jobs/?min_match=0")
        titles = {r["title"] for r in response.json()["results"]}
        assert len(titles) == 3


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

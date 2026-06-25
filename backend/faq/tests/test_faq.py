"""Tests del sistema FAQ.

Cubre:
  - Endpoints públicos (lista, categorías, view-count) sin auth.
  - Submit (user ask): auth required, rate-limit, AI mockeado,
    persistencia en cola pending.
  - Admin endpoints: gating, moderación con timestamp/auditoría,
    stats agregadas.
"""

from unittest.mock import patch

import pytest

from faq.models import FaqCategory, FaqQuestion


@pytest.fixture(autouse=True)
def _clear_ratelimit_cache():
    """`@ratelimit(5/h, key='user')` comparte el bucket entre tests
    (LocMem cache persiste dentro del proceso). Limpiar antes/después
    para que cada test arranque con cuota fresca."""
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()


# ──────────────────────────────────────────────────────────────────────
# PUBLIC ENDPOINTS
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.integration
@pytest.mark.django_db
class TestFaqPublicList:
    def test_anonymous_can_list_published_faqs(self, api_client):
        """`/api/faq/` es público — devuelve solo status=published."""
        # La data migration carga 10 seeds + 5 cats. Verificamos eso.
        response = api_client.get("/api/faq/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 10  # seed inicial
        for entry in data:
            # No debe exponer fields internos
            assert "ai_draft" not in entry
            assert "status" not in entry
            assert "submitted_by" not in entry

    def test_filter_by_category(self, api_client):
        response = api_client.get("/api/faq/?category=cv")
        assert response.status_code == 200
        data = response.json()
        for entry in data:
            assert entry["category"]["slug"] == "cv"

    def test_rejected_faqs_are_hidden(self, api_client):
        FaqQuestion.objects.create(
            question="Pregunta rechazada",
            answer="Respuesta interna",
            status=FaqQuestion.STATUS_REJECTED,
            source=FaqQuestion.SOURCE_USER,
        )
        response = api_client.get("/api/faq/")
        questions = [row["question"] for row in response.json()]
        assert "Pregunta rechazada" not in questions

    def test_pending_faqs_are_hidden(self, api_client):
        FaqQuestion.objects.create(
            question="Pregunta pendiente",
            answer="Draft",
            status=FaqQuestion.STATUS_PENDING,
            source=FaqQuestion.SOURCE_USER,
        )
        response = api_client.get("/api/faq/")
        questions = [row["question"] for row in response.json()]
        assert "Pregunta pendiente" not in questions


@pytest.mark.integration
@pytest.mark.django_db
class TestFaqCategoryList:
    def test_anonymous_can_list_categories(self, api_client):
        response = api_client.get("/api/faq/categories/")
        assert response.status_code == 200
        data = response.json()
        names = {row["name"] for row in data}
        # Los 5 del seed inicial
        assert {"Cuenta", "CV", "Matches", "Postulaciones", "Privacidad"} <= names

    def test_inactive_categories_are_hidden(self, api_client):
        cat = FaqCategory.objects.create(name="Hidden Cat", is_active=False)
        response = api_client.get("/api/faq/categories/")
        names = {row["name"] for row in response.json()}
        assert cat.name not in names


@pytest.mark.integration
@pytest.mark.django_db
class TestFaqViewCount:
    def test_view_count_increments(self, api_client):
        faq = FaqQuestion.objects.create(
            question="Q",
            answer="A",
            status=FaqQuestion.STATUS_PUBLISHED,
            source=FaqQuestion.SOURCE_SEED,
        )
        before = faq.view_count
        response = api_client.post(f"/api/faq/{faq.id}/view/")
        assert response.status_code == 204
        faq.refresh_from_db()
        assert faq.view_count == before + 1

    def test_view_count_404_for_unpublished(self, api_client):
        faq = FaqQuestion.objects.create(
            question="Q", status=FaqQuestion.STATUS_PENDING
        )
        response = api_client.post(f"/api/faq/{faq.id}/view/")
        assert response.status_code == 404


# ──────────────────────────────────────────────────────────────────────
# USER ASK
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.integration
@pytest.mark.django_db
class TestFaqAsk:
    @patch("faq.views.generate_answer")
    def test_unauth_is_rejected(self, mock_ai, api_client):
        response = api_client.post(
            "/api/faq/ask/", {"question": "¿Cómo funciona?"}, format="json"
        )
        assert response.status_code == 401
        mock_ai.assert_not_called()

    @patch("faq.views.generate_answer")
    def test_too_short_is_400(self, mock_ai, authed_client):
        response = authed_client.post(
            "/api/faq/ask/", {"question": "hola"}, format="json"
        )
        assert response.status_code == 400
        mock_ai.assert_not_called()

    @patch("faq.views.generate_answer")
    def test_too_long_is_400(self, mock_ai, authed_client):
        response = authed_client.post(
            "/api/faq/ask/", {"question": "x" * 301}, format="json"
        )
        assert response.status_code == 400
        mock_ai.assert_not_called()

    @patch("faq.views.generate_answer")
    def test_success_creates_pending_question_with_ai_draft(
        self, mock_ai, authed_client, user
    ):
        mock_ai.return_value = "Respuesta generada por la AI."
        response = authed_client.post(
            "/api/faq/ask/",
            {"question": "¿Cómo funciona el matching?"},
            format="json",
        )
        assert response.status_code == 200
        body = response.json()
        assert body["has_ai_answer"] is True
        assert body["ai_answer"] == "Respuesta generada por la AI."

        faq = FaqQuestion.objects.get(id=body["id"])
        assert faq.status == FaqQuestion.STATUS_PENDING
        assert faq.source == FaqQuestion.SOURCE_USER
        assert faq.ai_draft == "Respuesta generada por la AI."
        assert faq.answer == "Respuesta generada por la AI."
        assert faq.submitted_by == user

    @patch("faq.views.generate_answer")
    def test_ai_failure_still_creates_question(self, mock_ai, authed_client):
        """Si Gemini cae, la pregunta NO se pierde — queda sin draft
        para que el admin la responda manualmente."""
        from faq.services.faq_responder import FaqResponderError

        mock_ai.side_effect = FaqResponderError("gemini down")
        response = authed_client.post(
            "/api/faq/ask/",
            {"question": "¿Qué pasa si la AI cae?"},
            format="json",
        )
        assert response.status_code == 200
        body = response.json()
        assert body["has_ai_answer"] is False
        assert body["ai_answer"] == ""

        faq = FaqQuestion.objects.get(id=body["id"])
        assert faq.status == FaqQuestion.STATUS_PENDING
        assert faq.ai_draft == ""

    @patch("faq.views.generate_answer")
    def test_rate_limit_blocks_after_5_per_hour(self, mock_ai, authed_client):
        mock_ai.return_value = "ok"
        for i in range(5):
            r = authed_client.post(
                "/api/faq/ask/",
                {"question": f"Pregunta {i} válida para pasar validación."},
                format="json",
            )
            assert r.status_code == 200, f"intento {i} debería pasar"

        sixth = authed_client.post(
            "/api/faq/ask/",
            {"question": "Pregunta sexta debería pegar el rate limit."},
            format="json",
        )
        # django-ratelimit con `block=True` devuelve 403 por default.
        assert sixth.status_code == 403


# ──────────────────────────────────────────────────────────────────────
# ADMIN
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.integration
@pytest.mark.django_db
class TestFaqAdminList:
    def test_requires_admin(self, authed_client):
        response = authed_client.get("/api/faq/admin/")
        assert response.status_code == 403

    def test_anon_is_401(self, api_client):
        response = api_client.get("/api/faq/admin/")
        assert response.status_code == 401

    def test_default_returns_only_pending(self, api_client, admin_user):
        FaqQuestion.objects.create(
            question="Q pending", status=FaqQuestion.STATUS_PENDING
        )
        FaqQuestion.objects.create(
            question="Q published", status=FaqQuestion.STATUS_PUBLISHED
        )
        api_client.force_authenticate(user=admin_user)
        response = api_client.get("/api/faq/admin/")
        assert response.status_code == 200
        results = response.json().get("results", response.json())
        questions = [r["question"] for r in results]
        assert "Q pending" in questions
        assert "Q published" not in questions

    def test_filter_status_all(self, api_client, admin_user):
        api_client.force_authenticate(user=admin_user)
        response = api_client.get("/api/faq/admin/?status=all")
        assert response.status_code == 200


@pytest.mark.integration
@pytest.mark.django_db
class TestFaqAdminCreate:
    """POST /api/faq/admin/ — admin curáa una FAQ manualmente."""

    URL = "/api/faq/admin/"

    def test_requires_admin(self, authed_client):
        response = authed_client.post(
            self.URL,
            {"question": "¿X?", "answer": "Y"},
            format="json",
        )
        assert response.status_code == 403

    def test_anon_is_401(self, api_client):
        response = api_client.post(
            self.URL,
            {"question": "¿X?", "answer": "Y"},
            format="json",
        )
        assert response.status_code == 401

    def test_creates_seed_published_by_default(self, api_client, admin_user):
        api_client.force_authenticate(user=admin_user)
        cat = FaqCategory.objects.get(slug="cv")
        response = api_client.post(
            self.URL,
            {
                "question": "¿Puedo subir CV en Word?",
                "answer": "Aceptamos solo PDF por ahora.",
                "category_id": cat.id,
            },
            format="json",
        )
        assert response.status_code == 201
        body = response.json()
        # Defaults forzados por el view, no el cliente:
        assert body["source"] == "seed"
        assert body["status"] == "published"
        assert body["submitted_by"] is None
        assert body["moderated_by"] == admin_user.id
        assert body["moderated_at"] is not None

        faq = FaqQuestion.objects.get(pk=body["id"])
        assert faq.category_id == cat.id
        assert faq.ai_draft == ""

    def test_can_create_as_draft_pending(self, api_client, admin_user):
        """Admin puede crear con status=pending para guardar como borrador
        sin publicar."""
        api_client.force_authenticate(user=admin_user)
        response = api_client.post(
            self.URL,
            {
                "question": "¿Borrador?",
                "answer": "Respuesta a refinar.",
                "status": "pending",
            },
            format="json",
        )
        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "pending"
        # No registramos moderación porque no se publicó.
        assert body["moderated_by"] is None
        assert body["moderated_at"] is None

    def test_client_cannot_force_source_user(self, api_client, admin_user):
        """Defensa contra mass-assignment: aunque el cliente mande
        `source: user`, el view lo overridea a `seed`."""
        api_client.force_authenticate(user=admin_user)
        response = api_client.post(
            self.URL,
            {
                "question": "¿Hack?",
                "answer": "Nope.",
                "source": "user",  # ignorado
                "submitted_by": 9999,  # ignorado
            },
            format="json",
        )
        assert response.status_code == 201
        body = response.json()
        assert body["source"] == "seed"
        assert body["submitted_by"] is None

    def test_question_is_required(self, api_client, admin_user):
        api_client.force_authenticate(user=admin_user)
        response = api_client.post(
            self.URL,
            {"answer": "Solo respuesta sin pregunta"},
            format="json",
        )
        assert response.status_code == 400
        assert "question" in response.json()


@pytest.mark.integration
@pytest.mark.django_db
class TestFaqAdminModeration:
    def test_publish_records_moderator(self, api_client, admin_user):
        from django.utils import timezone

        faq = FaqQuestion.objects.create(
            question="Q usuaria",
            answer="Borrador AI",
            ai_draft="Borrador AI",
            status=FaqQuestion.STATUS_PENDING,
            source=FaqQuestion.SOURCE_USER,
        )
        api_client.force_authenticate(user=admin_user)
        before = timezone.now()
        response = api_client.patch(
            f"/api/faq/admin/{faq.id}/",
            {"status": "published", "answer": "Respuesta editada por el admin."},
            format="json",
        )
        assert response.status_code == 200
        faq.refresh_from_db()
        assert faq.status == "published"
        assert faq.answer == "Respuesta editada por el admin."
        assert faq.moderated_by == admin_user
        assert faq.moderated_at is not None
        assert faq.moderated_at >= before
        # ai_draft NO se modifica desde el admin (read-only)
        assert faq.ai_draft == "Borrador AI"

    def test_reject_with_note(self, api_client, admin_user):
        faq = FaqQuestion.objects.create(
            question="Q ofensiva", status=FaqQuestion.STATUS_PENDING
        )
        api_client.force_authenticate(user=admin_user)
        response = api_client.patch(
            f"/api/faq/admin/{faq.id}/",
            {"status": "rejected", "moderation_note": "Lenguaje ofensivo."},
            format="json",
        )
        assert response.status_code == 200
        faq.refresh_from_db()
        assert faq.status == "rejected"
        assert faq.moderation_note == "Lenguaje ofensivo."

    def test_source_is_read_only(self, api_client, admin_user):
        """Defensa contra que el admin convierta una pregunta user en
        seed (rompería la estadística de origen)."""
        faq = FaqQuestion.objects.create(
            question="Q",
            source=FaqQuestion.SOURCE_USER,
            status=FaqQuestion.STATUS_PENDING,
        )
        api_client.force_authenticate(user=admin_user)
        response = api_client.patch(
            f"/api/faq/admin/{faq.id}/", {"source": "seed"}, format="json"
        )
        assert response.status_code == 200
        faq.refresh_from_db()
        assert faq.source == FaqQuestion.SOURCE_USER  # unchanged

    def test_change_category(self, api_client, admin_user):
        cat = FaqCategory.objects.get(slug="cv")
        faq = FaqQuestion.objects.create(question="Q", status="pending")
        api_client.force_authenticate(user=admin_user)
        response = api_client.patch(
            f"/api/faq/admin/{faq.id}/", {"category_id": cat.id}, format="json"
        )
        assert response.status_code == 200
        faq.refresh_from_db()
        assert faq.category_id == cat.id


@pytest.mark.integration
@pytest.mark.django_db
class TestFaqAdminStats:
    def test_requires_admin(self, authed_client):
        response = authed_client.get("/api/faq/admin/stats/")
        assert response.status_code == 403

    def test_stats_structure(self, api_client, admin_user):
        api_client.force_authenticate(user=admin_user)
        response = api_client.get("/api/faq/admin/stats/")
        assert response.status_code == 200
        body = response.json()
        assert "totals" in body
        assert {"all", "pending", "published", "rejected"} <= body["totals"].keys()
        assert "approval_rate_pct" in body
        assert "by_category" in body
        assert "by_source" in body
        assert "recent_user_questions" in body

    def test_approval_rate_is_zero_when_no_decisions(self, api_client, admin_user):
        FaqQuestion.objects.exclude(status=FaqQuestion.STATUS_PUBLISHED).delete()
        # Solo published del seed → decided=10, published=10 → 100%
        api_client.force_authenticate(user=admin_user)
        response = api_client.get("/api/faq/admin/stats/")
        assert response.json()["approval_rate_pct"] == 100.0

    def test_approval_rate_calculation(self, api_client, admin_user):
        # Limpiamos seed para tener un setup determinístico
        FaqQuestion.objects.all().delete()
        FaqQuestion.objects.create(question="Q1", status="published")
        FaqQuestion.objects.create(question="Q2", status="published")
        FaqQuestion.objects.create(question="Q3", status="rejected")
        FaqQuestion.objects.create(question="Q4", status="pending")
        api_client.force_authenticate(user=admin_user)
        response = api_client.get("/api/faq/admin/stats/")
        body = response.json()
        # decided = 3 (2 pub + 1 rej), published = 2 → 66.7%
        assert body["approval_rate_pct"] == pytest.approx(66.7, abs=0.1)
        assert body["totals"]["pending"] == 1
        assert body["totals"]["published"] == 2
        assert body["totals"]["rejected"] == 1

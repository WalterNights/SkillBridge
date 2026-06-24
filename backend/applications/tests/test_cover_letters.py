"""Tests del endpoint /api/cover-letters/.

Cubre:
  - Auth gating (401 sin token)
  - Anti-IDOR (404 al tocar cartas de otro user)
  - POST /api/cover-letters/ con Gemini mockeado
  - POST con tone/language inválido → 400
  - POST con oferta inexistente → 404
  - POST con Gemini caído → 502
  - GET ?job_offer_id=X recupera la existente
  - POST regenera y sobreescribe (resetea user_edited)
  - PATCH edita content y marca user_edited=True
  - DELETE borra la carta
"""

from unittest.mock import patch

import pytest

from applications.models import CoverLetter
from applications.cover_letter_generator import CoverLetterGenerationError


# --- Fixtures ---------------------------------------------------------------


@pytest.fixture
def other_user(django_user_model):
    return django_user_model.objects.create_user(
        username="bob", email="bob@example.com", password="bobpass123"
    )


@pytest.fixture
def my_letter(user, job_offer):
    return CoverLetter.objects.create(
        user=user,
        offer=job_offer,
        offer_title_snapshot=job_offer.title,
        offer_company_snapshot=job_offer.company,
        offer_url_snapshot=job_offer.url,
        content="Estimados,\n\nEste es el contenido inicial.\n\nSaludos.",
        tone="cercano",
        language="es",
    )


@pytest.fixture
def others_letter(other_user, job_offer):
    return CoverLetter.objects.create(
        user=other_user,
        offer=job_offer,
        offer_title_snapshot=job_offer.title,
        offer_company_snapshot=job_offer.company,
        offer_url_snapshot=job_offer.url,
        content="Carta de Bob.",
        tone="formal",
        language="es",
    )


# Texto mock devuelto por Gemini — largo suficiente para no caer en el
# guard "respuesta demasiado corta" del generator.
_MOCK_LETTER = (
    "Me llamó la atención su búsqueda para el puesto de Senior Backend Engineer en Acme Corp. "
    "El énfasis en arquitectura distribuida calza con lo que vengo construyendo los últimos años.\n\n"
    "Mi experiencia con Django y PostgreSQL me permitió liderar la migración de un monolito a microservicios "
    "en mi empresa actual, reduciendo el latency promedio en 40%. Conozco bien el stack que usan y manejo Docker en producción.\n\n"
    "Me encantaría conversar sobre el rol. ¿Cuándo te queda bien una llamada esta semana?\n\n"
    "Saludos,\nAlice Doe"
)


# --- POST /api/cover-letters/ ----------------------------------------------


@pytest.mark.integration
@pytest.mark.django_db
class TestCoverLetterCreate:
    def test_unauthenticated_returns_401(self, api_client, job_offer):
        response = api_client.post(
            "/api/cover-letters/", {"job_offer_id": job_offer.id, "tone": "cercano", "language": "es"}
        )
        assert response.status_code == 401

    def test_create_generates_and_persists(self, authed_client, user_profile, job_offer):
        with patch(
            "applications.views.generate_cover_letter", return_value=_MOCK_LETTER
        ) as mock_gen:
            response = authed_client.post(
                "/api/cover-letters/",
                {"job_offer_id": job_offer.id, "tone": "cercano", "language": "es"},
            )

        assert response.status_code == 201
        body = response.json()
        assert body["content"] == _MOCK_LETTER
        assert body["tone"] == "cercano"
        assert body["language"] == "es"
        assert body["user_edited"] is False
        assert body["offer_title_snapshot"] == job_offer.title
        # El generator fue llamado con el perfil del user
        assert mock_gen.call_count == 1
        kwargs = mock_gen.call_args.kwargs
        assert "Backend Developer" in kwargs["user_profile"]["professional_title"]

    def test_missing_offer_id_returns_400(self, authed_client):
        response = authed_client.post("/api/cover-letters/", {"tone": "cercano"})
        assert response.status_code == 400
        assert "job_offer_id" in response.json()

    def test_invalid_tone_returns_400(self, authed_client, job_offer):
        response = authed_client.post(
            "/api/cover-letters/",
            {"job_offer_id": job_offer.id, "tone": "rude", "language": "es"},
        )
        assert response.status_code == 400
        assert "tone" in response.json()

    def test_invalid_language_returns_400(self, authed_client, job_offer):
        response = authed_client.post(
            "/api/cover-letters/",
            {"job_offer_id": job_offer.id, "tone": "cercano", "language": "fr"},
        )
        assert response.status_code == 400

    def test_nonexistent_offer_returns_404(self, authed_client):
        response = authed_client.post(
            "/api/cover-letters/",
            {"job_offer_id": 99999, "tone": "cercano", "language": "es"},
        )
        assert response.status_code == 404

    def test_gemini_failure_returns_502(self, authed_client, user_profile, job_offer):
        with patch(
            "applications.views.generate_cover_letter",
            side_effect=CoverLetterGenerationError("Gemini está caído"),
        ):
            response = authed_client.post(
                "/api/cover-letters/",
                {"job_offer_id": job_offer.id, "tone": "cercano", "language": "es"},
            )
        assert response.status_code == 502
        assert response.json()["error"] == "generation_failed"

    def test_regenerate_overwrites_and_resets_user_edited(
        self, authed_client, user_profile, job_offer, my_letter
    ):
        """Segundo POST para la misma (user, offer) sobreescribe la carta
        existente y resetea user_edited=False — el user pidió una versión
        nueva, sus ediciones previas se pierden."""
        my_letter.user_edited = True
        my_letter.save(update_fields=["user_edited"])

        new_text = _MOCK_LETTER + " Versión regenerada."
        with patch("applications.views.generate_cover_letter", return_value=new_text):
            response = authed_client.post(
                "/api/cover-letters/",
                {"job_offer_id": job_offer.id, "tone": "formal", "language": "es"},
            )

        assert response.status_code == 200  # update, no create
        body = response.json()
        assert body["content"] == new_text
        assert body["tone"] == "formal"
        assert body["user_edited"] is False
        # Sigue habiendo solo una carta para esta (user, offer)
        assert CoverLetter.objects.filter(user=my_letter.user, offer=job_offer).count() == 1


# --- GET y filtering --------------------------------------------------------


@pytest.mark.integration
@pytest.mark.django_db
class TestCoverLetterRetrieve:
    def test_list_only_returns_own(self, authed_client, my_letter, others_letter):
        response = authed_client.get("/api/cover-letters/")
        assert response.status_code == 200
        ids = [letter["id"] for letter in response.json()]
        assert my_letter.id in ids
        assert others_letter.id not in ids

    def test_filter_by_job_offer_id(self, authed_client, my_letter, job_offer):
        response = authed_client.get(
            f"/api/cover-letters/?job_offer_id={job_offer.id}"
        )
        assert response.status_code == 200
        results = response.json()
        assert len(results) == 1
        assert results[0]["id"] == my_letter.id

    def test_cannot_access_others_letter(self, authed_client, others_letter):
        response = authed_client.get(f"/api/cover-letters/{others_letter.id}/")
        # Anti-IDOR: el queryset filtra por user → 404, no 403
        assert response.status_code == 404


# --- PATCH / DELETE ---------------------------------------------------------


@pytest.mark.integration
@pytest.mark.django_db
class TestCoverLetterEdit:
    def test_patch_updates_content_and_marks_edited(self, authed_client, my_letter):
        response = authed_client.patch(
            f"/api/cover-letters/{my_letter.id}/",
            {"content": "Contenido editado por el user."},
            format="json",
        )
        assert response.status_code == 200
        body = response.json()
        assert body["content"] == "Contenido editado por el user."
        assert body["user_edited"] is True

    def test_patch_without_content_returns_400(self, authed_client, my_letter):
        response = authed_client.patch(
            f"/api/cover-letters/{my_letter.id}/", {}, format="json"
        )
        assert response.status_code == 400

    def test_delete_removes_letter(self, authed_client, my_letter):
        response = authed_client.delete(f"/api/cover-letters/{my_letter.id}/")
        assert response.status_code == 204
        assert not CoverLetter.objects.filter(id=my_letter.id).exists()

    def test_cannot_delete_others_letter(self, authed_client, others_letter):
        response = authed_client.delete(f"/api/cover-letters/{others_letter.id}/")
        assert response.status_code == 404
        assert CoverLetter.objects.filter(id=others_letter.id).exists()

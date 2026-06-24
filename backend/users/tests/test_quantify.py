"""Tests del endpoint /api/users/cv/quantify/.

Cubre:
  - Auth gating (401)
  - text vacío → 400
  - Gemini mockeado → 200 con 3 sugerencias
  - Gemini falla → 502 con detail
  - Sanitización: max 3 sugerencias incluso si modelo devuelve más
  - Sugerencias vacías → 502 con mensaje
"""

from unittest.mock import patch

import pytest

from users.services.achievement_quantifier import QuantifyError


@pytest.mark.integration
@pytest.mark.django_db
class TestQuantifyEndpoint:
    URL = "/api/users/cv/quantify/"

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.post(self.URL, {"text": "hice cosas"})
        assert response.status_code == 401

    def test_missing_text_returns_400(self, authed_client):
        response = authed_client.post(self.URL, {})
        assert response.status_code == 400

    def test_empty_text_returns_400(self, authed_client):
        response = authed_client.post(self.URL, {"text": "   "})
        assert response.status_code == 400

    def test_happy_path_returns_three_suggestions(self, authed_client):
        with patch(
            "users.views.quantify_achievement",
            return_value=[
                "Lideré un equipo de +5 ingenieros, reduciendo bugs en producción un 30%.",
                "Optimicé el pipeline de CI logrando builds 40% más rápidos.",
                "Implementé tests automáticos cubriendo +85% del código crítico.",
            ],
        ) as mock_q:
            response = authed_client.post(
                self.URL,
                {
                    "text": "Trabajé en el equipo de plataforma",
                    "role_title": "Senior Engineer",
                    "company": "Acme",
                },
            )

        assert response.status_code == 200
        body = response.json()
        assert "suggestions" in body
        assert len(body["suggestions"]) == 3
        assert mock_q.call_count == 1
        kwargs = mock_q.call_args.kwargs
        assert kwargs["original_text"] == "Trabajé en el equipo de plataforma"
        assert kwargs["role_title"] == "Senior Engineer"
        assert kwargs["company"] == "Acme"

    def test_gemini_failure_returns_502(self, authed_client):
        with patch(
            "users.views.quantify_achievement",
            side_effect=QuantifyError("Gemini está caído"),
        ):
            response = authed_client.post(self.URL, {"text": "hice cosas"})
        assert response.status_code == 502
        body = response.json()
        assert body["error"] == "quantify_failed"
        assert "Gemini" in body["detail"]


@pytest.mark.unit
class TestQuantifierService:
    """Tests del servicio (sin tocar la view ni la API)."""

    def test_empty_text_raises(self):
        from users.services.achievement_quantifier import (
            QuantifyError,
            quantify_achievement,
        )

        with pytest.raises(QuantifyError, match="vacío"):
            quantify_achievement(original_text="")

    def test_too_long_text_raises(self):
        from users.services.achievement_quantifier import (
            QuantifyError,
            quantify_achievement,
        )

        with pytest.raises(QuantifyError, match="largo"):
            quantify_achievement(original_text="x" * 2001)

    def test_parses_valid_gemini_response(self, mocker):
        """Mockeamos GenerativeModel.generate_content para devolver un
        JSON válido y verificamos que el servicio lo parsea correctamente."""
        from users.services import achievement_quantifier

        mocker.patch.object(
            achievement_quantifier.settings, "GEMINI_API_KEY", "fake-key", create=True
        )
        mocker.patch.object(
            achievement_quantifier.settings, "GEMINI_MODEL", "fake-model", create=True
        )
        mocker.patch("users.services.achievement_quantifier.genai.configure")

        fake_response = mocker.Mock()
        fake_response.text = '{"suggestions": ["Lideré +5", "Optimicé 40%", "Reduje 30%"]}'
        fake_model = mocker.Mock()
        fake_model.generate_content.return_value = fake_response
        mocker.patch(
            "users.services.achievement_quantifier.genai.GenerativeModel",
            return_value=fake_model,
        )

        out = achievement_quantifier.quantify_achievement(
            original_text="lideré el equipo",
        )
        assert out == ["Lideré +5", "Optimicé 40%", "Reduje 30%"]

    def test_strips_markdown_fences(self, mocker):
        from users.services import achievement_quantifier

        mocker.patch.object(
            achievement_quantifier.settings, "GEMINI_API_KEY", "fake-key", create=True
        )
        mocker.patch.object(
            achievement_quantifier.settings, "GEMINI_MODEL", "fake-model", create=True
        )
        mocker.patch("users.services.achievement_quantifier.genai.configure")

        fake_response = mocker.Mock()
        fake_response.text = '```json\n{"suggestions": ["A", "B", "C"]}\n```'
        fake_model = mocker.Mock()
        fake_model.generate_content.return_value = fake_response
        mocker.patch(
            "users.services.achievement_quantifier.genai.GenerativeModel",
            return_value=fake_model,
        )

        out = achievement_quantifier.quantify_achievement(original_text="x")
        assert out == ["A", "B", "C"]

    def test_caps_at_three_suggestions(self, mocker):
        from users.services import achievement_quantifier

        mocker.patch.object(
            achievement_quantifier.settings, "GEMINI_API_KEY", "fake-key", create=True
        )
        mocker.patch.object(
            achievement_quantifier.settings, "GEMINI_MODEL", "fake-model", create=True
        )
        mocker.patch("users.services.achievement_quantifier.genai.configure")

        fake_response = mocker.Mock()
        fake_response.text = '{"suggestions": ["A", "B", "C", "D", "E"]}'
        fake_model = mocker.Mock()
        fake_model.generate_content.return_value = fake_response
        mocker.patch(
            "users.services.achievement_quantifier.genai.GenerativeModel",
            return_value=fake_model,
        )

        out = achievement_quantifier.quantify_achievement(original_text="x")
        assert out == ["A", "B", "C"]

    def test_empty_suggestions_list_raises(self, mocker):
        from users.services import achievement_quantifier

        mocker.patch.object(
            achievement_quantifier.settings, "GEMINI_API_KEY", "fake-key", create=True
        )
        mocker.patch.object(
            achievement_quantifier.settings, "GEMINI_MODEL", "fake-model", create=True
        )
        mocker.patch("users.services.achievement_quantifier.genai.configure")

        fake_response = mocker.Mock()
        fake_response.text = '{"suggestions": []}'
        fake_model = mocker.Mock()
        fake_model.generate_content.return_value = fake_response
        mocker.patch(
            "users.services.achievement_quantifier.genai.GenerativeModel",
            return_value=fake_model,
        )

        with pytest.raises(QuantifyError):
            achievement_quantifier.quantify_achievement(original_text="x")

"""Tests del endpoint /api/users/cv/audit/.

Cubre:
  - Auth gating (401)
  - User sin perfil → 404
  - Gemini mockeado → 200 con la estructura completa
  - Gemini falla → 502
  - Gemini omite categorías → se rellenan con defaults (defensive)
  - Score fuera de rango → cappeado a [0,100]
"""

from unittest.mock import patch

import pytest

from users.services.cv_auditor import AuditError


_FULL_AUDIT_PAYLOAD = {
    "score": 78,
    "overall": "El CV está sólido, con experiencia clara. Faltan métricas en algunas descripciones.",
    "categories": [
        {"key": "summary", "label": "Resumen profesional", "severity": "ok", "message": "Buen resumen, 3 oraciones claras."},
        {"key": "experience", "label": "Experiencia", "severity": "warning", "message": "Cuantificá los 2 últimos roles."},
        {"key": "skills", "label": "Habilidades", "severity": "ok", "message": "10 skills relevantes al rol."},
        {"key": "education", "label": "Educación", "severity": "ok", "message": "Completa."},
        {"key": "contact", "label": "Datos de contacto", "severity": "critical", "message": "Falta tu LinkedIn URL."},
        {"key": "length", "label": "Largo del CV", "severity": "ok", "message": "Bien."},
    ],
    "top_recommendations": [
        "Agregá tu LinkedIn URL — los reclutadores lo buscan primero.",
        "Cuantificá tus últimas 2 experiencias con números concretos.",
        "Sumá 2-3 skills más recientes al tope de la lista.",
    ],
}


@pytest.mark.integration
@pytest.mark.django_db
class TestCvAuditEndpoint:
    URL = "/api/users/cv/audit/"

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.post(self.URL)
        assert response.status_code == 401

    def test_no_profile_returns_404(self, authed_client):
        # `user` fixture no crea profile por sí solo
        response = authed_client.post(self.URL)
        assert response.status_code == 404
        assert response.json()["error"] == "profile_missing"

    def test_happy_path(self, authed_client, user_profile):
        with patch(
            "users.views.audit_cv",
            return_value=_FULL_AUDIT_PAYLOAD,
        ) as mock_audit:
            response = authed_client.post(self.URL)

        assert response.status_code == 200
        body = response.json()
        assert body["score"] == 78
        assert "overall" in body
        assert len(body["categories"]) == 6
        assert len(body["top_recommendations"]) == 3
        assert mock_audit.call_count == 1
        # El servicio recibió el payload normalizado del perfil
        payload = mock_audit.call_args[0][0]
        assert payload["professional_title"] == "Backend Developer"
        assert "skills" in payload

    def test_gemini_failure_returns_502(self, authed_client, user_profile):
        with patch(
            "users.views.audit_cv",
            side_effect=AuditError("Gemini caído"),
        ):
            response = authed_client.post(self.URL)
        assert response.status_code == 502
        assert response.json()["error"] == "audit_failed"


@pytest.mark.unit
class TestAuditNormalization:
    """Tests del _normalize_audit que no requieren Gemini ni DB."""

    def test_caps_score_to_range(self):
        from users.services import cv_auditor

        out = cv_auditor._normalize_audit({"score": 150, "overall": "x", "categories": [], "top_recommendations": []})
        assert out["score"] == 100

        out = cv_auditor._normalize_audit({"score": -10, "overall": "x", "categories": [], "top_recommendations": []})
        assert out["score"] == 0

    def test_invalid_score_falls_back_to_50(self):
        from users.services import cv_auditor

        out = cv_auditor._normalize_audit({"score": "not a number", "overall": "x", "categories": [], "top_recommendations": []})
        assert out["score"] == 50

    def test_fills_missing_categories_with_defaults(self):
        from users.services import cv_auditor

        out = cv_auditor._normalize_audit(
            {
                "score": 70,
                "overall": "ok",
                "categories": [
                    {"key": "summary", "severity": "ok", "message": "good"},
                ],
                "top_recommendations": [],
            }
        )
        # Las 6 categorías deben estar presentes incluso si Gemini omitió 5
        keys = [c["key"] for c in out["categories"]]
        assert keys == ["summary", "experience", "skills", "education", "contact", "length"]
        # Las omitidas reciben severity=warning + mensaje default
        non_summary = [c for c in out["categories"] if c["key"] != "summary"]
        assert all(c["severity"] == "warning" for c in non_summary)
        assert all(c["message"] for c in non_summary)

    def test_invalid_severity_falls_back_to_warning(self):
        from users.services import cv_auditor

        out = cv_auditor._normalize_audit(
            {
                "score": 70,
                "overall": "ok",
                "categories": [
                    {"key": "summary", "severity": "fantastic", "message": "x"},
                ],
                "top_recommendations": [],
            }
        )
        summary = next(c for c in out["categories"] if c["key"] == "summary")
        assert summary["severity"] == "warning"

    def test_top_recommendations_capped_at_three(self):
        from users.services import cv_auditor

        out = cv_auditor._normalize_audit(
            {
                "score": 70,
                "overall": "x",
                "categories": [],
                "top_recommendations": ["a", "b", "c", "d", "e"],
            }
        )
        assert len(out["top_recommendations"]) == 3
        assert out["top_recommendations"] == ["a", "b", "c"]

"""Test de regresión del endpoint /api/users/resume-analyzer/.

Verifica el contrato actual de respuesta. Después del Commit 4
(CV analyzer detrás de interfaz `CVAnalyzer`), el endpoint debe
seguir devolviendo exactamente la misma estructura JSON.

El servicio Gemini se mockea — los tests no llaman a la API real.
"""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

GEMINI_FAKE_RESPONSE = {
    "first_name": "Alice",
    "last_name": "Doe",
    "phone_code": "+54",
    "phone_number": "1112345678",
    "country": "Argentina",
    "city": "Buenos Aires",
    "professional_title": "Backend Developer",
    "summary": "Five years building Django services.",
    "education": [{"degree": "Lic. Informática", "school": "UBA"}],
    "skills": "python, django, postgresql",
    "experience": [{"role": "Backend Engineer", "years": 5}],
    "linkedin_url": "https://linkedin.com/in/alice",
    "portfolio_url": "",
    "full_name": "Alice Doe",
}


@pytest.fixture
def fake_pdf():
    """PDF mínimo de 1KB. Suficiente para pasar la validación de tamaño."""
    pdf_bytes = b"%PDF-1.4\n" + b" " * 1024 + b"\n%%EOF"
    return SimpleUploadedFile("cv.pdf", pdf_bytes, content_type="application/pdf")


def _stub_analyzer(mocker, *, validate=(True, None), analyze=None, analyze_raises=None):
    """Reemplaza `get_cv_analyzer` en la vista por un Mock configurable.

    Hooks de seguridad: si `analyze` no se pasa, devuelve GEMINI_FAKE_RESPONSE.
    """
    analyzer = mocker.Mock()
    analyzer.validate.return_value = validate
    if analyze_raises is not None:
        analyzer.analyze.side_effect = analyze_raises
    else:
        analyzer.analyze.return_value = analyze if analyze is not None else GEMINI_FAKE_RESPONSE
    mocker.patch("users.views.get_cv_analyzer", return_value=analyzer)
    return analyzer


@pytest.mark.integration
@pytest.mark.django_db
class TestResumeAnalyzer:
    # El endpoint pasó a requerir autenticación (anti cost-bomb a Gemini).
    # Todos los casos usan `authed_client` salvo el regression que valida
    # que sin sesión devuelve 401 en lugar de procesar el PDF.

    def test_rejects_unauthenticated(self, api_client, fake_pdf):
        response = api_client.post(
            "/api/users/resume-analyzer/",
            {"resume": fake_pdf},
            format="multipart",
        )
        assert response.status_code == 401

    def test_rejects_request_without_file(self, authed_client):
        response = authed_client.post("/api/users/resume-analyzer/", {})
        assert response.status_code == 400
        assert "error" in response.json()

    def test_returns_extracted_data_on_success(self, authed_client, fake_pdf, mocker):
        _stub_analyzer(mocker)
        response = authed_client.post(
            "/api/users/resume-analyzer/",
            {"resume": fake_pdf},
            format="multipart",
        )
        assert response.status_code == 200
        data = response.json()

        # Contrato público — el frontend espera estas claves.
        expected_keys = {
            "first_name",
            "last_name",
            "number_id",
            "phone_code",
            "phone_number",
            "country",
            "city",
            "professional_title",
            "summary",
            "education",
            "skills",
            "experience",
            "linkedin_url",
            "portfolio_url",
            "full_name",
        }
        assert expected_keys.issubset(data.keys())
        assert data["first_name"] == "Alice"
        assert data["skills"] == "python, django, postgresql"

    def test_returns_400_on_validation_failure(self, authed_client, fake_pdf, mocker):
        _stub_analyzer(mocker, validate=(False, "Archivo muy grande"))
        response = authed_client.post(
            "/api/users/resume-analyzer/",
            {"resume": fake_pdf},
            format="multipart",
        )
        assert response.status_code == 400
        assert response.json()["error"] == "Archivo muy grande"

    def test_returns_500_on_analyzer_exception(self, authed_client, fake_pdf, mocker):
        _stub_analyzer(mocker, analyze_raises=RuntimeError("Gemini down"))
        response = authed_client.post(
            "/api/users/resume-analyzer/",
            {"resume": fake_pdf},
            format="multipart",
        )
        assert response.status_code == 500

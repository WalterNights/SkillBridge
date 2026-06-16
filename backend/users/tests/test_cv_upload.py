"""Test de regresión del endpoint /api/users/resume-analyzer/.

Verifica el contrato actual de respuesta. Después del Commit 4
(CV analyzer detrás de interfaz `CVAnalyzer`), el endpoint debe
seguir devolviendo exactamente la misma estructura JSON.

El servicio Gemini se mockea — los tests no llaman a la API real.
"""
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile


GEMINI_FAKE_RESPONSE = {
    'first_name': 'Alice',
    'last_name': 'Doe',
    'phone_code': '+54',
    'phone_number': '1112345678',
    'country': 'Argentina',
    'city': 'Buenos Aires',
    'professional_title': 'Backend Developer',
    'summary': 'Five years building Django services.',
    'education': [{'degree': 'Lic. Informática', 'school': 'UBA'}],
    'skills': 'python, django, postgresql',
    'experience': [{'role': 'Backend Engineer', 'years': 5}],
    'linkedin_url': 'https://linkedin.com/in/alice',
    'portfolio_url': '',
    'full_name': 'Alice Doe',
}


@pytest.fixture
def fake_pdf():
    """PDF mínimo de 1KB. Suficiente para pasar la validación de tamaño."""
    pdf_bytes = b'%PDF-1.4\n' + b' ' * 1024 + b'\n%%EOF'
    return SimpleUploadedFile('cv.pdf', pdf_bytes, content_type='application/pdf')


@pytest.fixture
def mock_gemini(mocker):
    """Reemplaza GeminiCVService en la vista para no llamar a la API real."""
    mock_class = mocker.patch('users.views.GeminiCVService')
    instance = mock_class.return_value
    instance.validate_cv_file.return_value = (True, None)
    instance.analyze_cv.return_value = GEMINI_FAKE_RESPONSE
    return mock_class


@pytest.mark.integration
@pytest.mark.django_db
class TestResumeAnalyzer:
    def test_rejects_request_without_file(self, api_client):
        response = api_client.post('/api/users/resume-analyzer/', {})
        assert response.status_code == 400
        assert 'error' in response.json()

    def test_returns_extracted_data_on_success(self, api_client, fake_pdf, mock_gemini):
        response = api_client.post(
            '/api/users/resume-analyzer/',
            {'resume': fake_pdf},
            format='multipart',
        )
        assert response.status_code == 200
        data = response.json()

        # Contrato público — el frontend espera estas claves.
        expected_keys = {
            'first_name', 'last_name', 'number_id', 'phone_code', 'phone_number',
            'country', 'city', 'professional_title', 'summary', 'education',
            'skills', 'experience', 'linkedin_url', 'portfolio_url', 'full_name',
        }
        assert expected_keys.issubset(data.keys())
        assert data['first_name'] == 'Alice'
        assert data['skills'] == 'python, django, postgresql'

    def test_returns_400_on_validation_failure(self, api_client, fake_pdf, mocker):
        mock_class = mocker.patch('users.views.GeminiCVService')
        instance = mock_class.return_value
        instance.validate_cv_file.return_value = (False, 'Archivo muy grande')

        response = api_client.post(
            '/api/users/resume-analyzer/',
            {'resume': fake_pdf},
            format='multipart',
        )
        assert response.status_code == 400
        assert response.json()['error'] == 'Archivo muy grande'

    def test_returns_500_on_gemini_exception(self, api_client, fake_pdf, mocker):
        mock_class = mocker.patch('users.views.GeminiCVService')
        instance = mock_class.return_value
        instance.validate_cv_file.return_value = (True, None)
        instance.analyze_cv.side_effect = RuntimeError('Gemini down')

        response = api_client.post(
            '/api/users/resume-analyzer/',
            {'resume': fake_pdf},
            format='multipart',
        )
        assert response.status_code == 500

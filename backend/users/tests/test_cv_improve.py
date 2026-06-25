"""Tests del endpoint /api/users/cv/improve/.

Cubre:
  - Auth gating (401 sin sesión)
  - User sin perfil → 404
  - Lifetime cap: 1 uso por user normal (segundo intento → 429)
  - Admins bypassean el lifetime cap
  - Marca cv_improved_at SOLO en éxito (no en error)
  - Permite corrección de fechas via normalizer (mismo count + mismo
    company/position preservados)
"""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from users.services.cv_improver import _normalize_improved


_VALID_IMPROVE_PAYLOAD = {
    "summary": "FullStack Developer con 3+ años…",
    "professional_title": "FullStack Developer",
    "skills": "react, node, python",
    "soft_skills": "leadership, communication",
    "experience": [],
}


@pytest.fixture(autouse=True)
def _clear_ratelimit_cache():
    """El decorador @ratelimit(5/h, key='user') comparte el bucket entre
    tests (cache LocMem persiste dentro del proceso). Limpiamos antes
    de cada test para que cada uno arranque con 5 turnos disponibles."""
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()


@pytest.mark.integration
@pytest.mark.django_db
class TestCvImproveAuth:
    def test_unauth_is_rejected(self, api_client):
        response = api_client.post("/api/users/cv/improve/")
        assert response.status_code == 401

    def test_user_without_profile_is_404(self, authed_client):
        response = authed_client.post("/api/users/cv/improve/")
        assert response.status_code == 404
        assert response.json()["error"] == "profile_missing"


@pytest.mark.integration
@pytest.mark.django_db
class TestCvImproveLifetimeCap:
    @patch("users.views.improve_cv")
    def test_first_use_marks_timestamp(self, mock_improve, authed_client, user_profile):
        mock_improve.return_value = _VALID_IMPROVE_PAYLOAD
        response = authed_client.post("/api/users/cv/improve/")
        assert response.status_code == 200
        user_profile.refresh_from_db()
        assert user_profile.cv_improved_at is not None

    @patch("users.views.improve_cv")
    def test_second_use_returns_429(self, mock_improve, authed_client, user_profile):
        # Marcamos como usado antes (timestamp arbitrario en el pasado).
        user_profile.cv_improved_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
        user_profile.save(update_fields=["cv_improved_at"])

        response = authed_client.post("/api/users/cv/improve/")
        assert response.status_code == 429
        assert response.json()["error"] == "already_used"
        # No debe haber llamado a Gemini para el segundo intento
        mock_improve.assert_not_called()

    @patch("users.views.improve_cv")
    def test_failed_improve_does_not_consume_lifetime(
        self, mock_improve, authed_client, user_profile
    ):
        """Si Gemini falla con ImproveError, el user puede reintentar
        sin haber gastado su único uso."""
        from users.services.cv_improver import ImproveError

        mock_improve.side_effect = ImproveError("gemini down")
        response = authed_client.post("/api/users/cv/improve/")
        assert response.status_code == 502
        user_profile.refresh_from_db()
        assert user_profile.cv_improved_at is None

    @patch("users.views.improve_cv")
    def test_admin_can_use_multiple_times(
        self, mock_improve, api_client, admin_user, django_user_model
    ):
        from users.models import UserProfile

        mock_improve.return_value = _VALID_IMPROVE_PAYLOAD
        UserProfile.objects.create(
            user=admin_user,
            first_name="Admin",
            last_name="User",
            phone="+1",
            city="Bogota",
            professional_title="Admin",
            skills="x",
            experience="y",
        )
        api_client.force_authenticate(user=admin_user)

        # Primer uso → 200
        response = api_client.post("/api/users/cv/improve/")
        assert response.status_code == 200

        # Segundo uso → 200 también (admin bypass — no se incrementa lifetime).
        response = api_client.post("/api/users/cv/improve/")
        assert response.status_code == 200

        # Y el timestamp NO se marca para admins (preserva el cap para
        # cuando saquen el is_staff temporal).
        admin_user.profile.refresh_from_db()
        assert admin_user.profile.cv_improved_at is None


@pytest.mark.unit
class TestNormalizerDates:
    """Verifica que el normalizer ahora deja pasar correcciones de fecha
    razonables (era un bug — antes forzaba siempre el original)."""

    def test_dates_get_overridden_when_corrected(self):
        original = {
            "experience": [
                {
                    "company": "Acme",
                    "position": "Dev",
                    "start_date": "Enero 2025",
                    "end_date": "Noviembre 2026",  # futuro / error
                    "description": "• Bullet",
                }
            ]
        }
        improved = {
            "experience": [
                {
                    "company": "Acme",
                    "position": "Dev",
                    "start_date": "Enero 2024",  # corregido
                    "end_date": "Presente",  # corregido
                    "description": "• Bullet mejorado",
                }
            ]
        }
        result = _normalize_improved(improved, original)
        entry = result["experience"][0]
        assert entry["start_date"] == "Enero 2024"
        assert entry["end_date"] == "Presente"
        assert entry["company"] == "Acme"  # preservada
        assert entry["position"] == "Dev"  # preservada
        assert entry["description"] == "• Bullet mejorado"

    def test_dates_fallback_to_original_when_missing(self):
        original = {
            "experience": [
                {
                    "company": "Acme",
                    "position": "Dev",
                    "start_date": "2023",
                    "end_date": "2024",
                    "description": "• Bullet",
                }
            ]
        }
        improved = {
            "experience": [
                {
                    "company": "Acme",
                    "position": "Dev",
                    # Sin start_date / end_date → fallback al original
                    "description": "• Bullet mejorado",
                }
            ]
        }
        result = _normalize_improved(improved, original)
        entry = result["experience"][0]
        assert entry["start_date"] == "2023"
        assert entry["end_date"] == "2024"

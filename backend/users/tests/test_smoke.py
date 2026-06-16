"""Smoke tests — verifican que la app levanta y los URLs resuelven."""
import pytest
from django.conf import settings


def test_dashboard_app_is_installed():
    """Regresión del Commit 1: dashboard fue agregado a INSTALLED_APPS."""
    assert 'dashboard' in settings.INSTALLED_APPS


def test_required_apps_are_installed():
    for app in ('users', 'jobs', 'dashboard', 'rest_framework', 'corsheaders'):
        assert app in settings.INSTALLED_APPS, f"Falta {app} en INSTALLED_APPS"


def test_auth_user_model_is_custom():
    assert settings.AUTH_USER_MODEL == 'users.User'


@pytest.mark.parametrize('url_name,expected_path', [
    ('token_obtain_pair', '/api/token/'),
    ('token_refresh', '/api/token/refresh/'),
    ('custom_token_obtain_pair', '/api/token/login/'),
    ('user-register', '/api/users/register/'),
    ('analyzer-resume', '/api/users/resume-analyzer/'),
    ('password-reset-request', '/api/users/password-reset/request/'),
    ('password-reset-verify', '/api/users/password-reset/verify/'),
])
def test_url_names_resolve(url_name, expected_path):
    from django.urls import reverse
    assert reverse(url_name) == expected_path

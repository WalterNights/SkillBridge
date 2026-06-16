"""Fixtures compartidas por todos los tests del backend."""
import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    """Cliente HTTP de DRF, sin autenticación por defecto."""
    return APIClient()


@pytest.fixture
def user(django_user_model):
    """Usuario regular autenticable."""
    return django_user_model.objects.create_user(
        username='alice',
        email='alice@example.com',
        password='testpass123',
    )


@pytest.fixture
def admin_user(django_user_model):
    """Usuario con is_staff=True (rol admin)."""
    return django_user_model.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='adminpass123',
    )


@pytest.fixture
def authed_client(api_client, user):
    """API client autenticado como `user`."""
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def user_profile(user):
    """Perfil del usuario `user` con un set conocido de skills."""
    from users.models import UserProfile
    return UserProfile.objects.create(
        user=user,
        first_name='Alice',
        last_name='Doe',
        phone='+541112345678',
        city='Buenos Aires',
        professional_title='Backend Developer',
        skills='python, django, postgresql, docker',
        experience='5 años en backend con Django y PostgreSQL.',
    )


@pytest.fixture
def job_offer():
    """Una oferta de trabajo con keywords conocidas."""
    from jobs.models import JobOffer
    return JobOffer.objects.create(
        title='Senior Backend Engineer',
        company='Acme Corp',
        location='Remote',
        url='https://example.com/jobs/123',
        summary='Backend role.',
        keywords='python, django, react',
    )

"""Tests de regresión de auth: register + login JWT."""
import pytest


@pytest.mark.integration
@pytest.mark.django_db
class TestUserRegistration:
    def test_creates_user_with_valid_data(self, api_client):
        response = api_client.post('/api/users/register/', {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'StrongPass123!',
        }, format='json')
        assert response.status_code == 201
        assert response.json()['message']

    def test_rejects_missing_fields(self, api_client):
        response = api_client.post('/api/users/register/', {
            'username': 'incomplete',
        }, format='json')
        assert response.status_code == 400


@pytest.mark.integration
@pytest.mark.django_db
class TestJWTLogin:
    def test_returns_token_pair_with_valid_credentials(self, api_client, user):
        response = api_client.post('/api/token/login/', {
            'username': user.username,
            'password': 'testpass123',
        }, format='json')
        assert response.status_code == 200
        body = response.json()
        assert 'access' in body
        assert 'refresh' in body
        # CustomTokenObtainPairSerializer agrega estos campos extra:
        assert body['user_id'] == user.id
        assert body['username'] == user.username
        assert body['rol'] == 'user'

    def test_rejects_invalid_credentials(self, api_client, user):
        response = api_client.post('/api/token/login/', {
            'username': user.username,
            'password': 'wrong',
        }, format='json')
        assert response.status_code == 401

    def test_refresh_endpoint_uses_correct_name(self, api_client):
        """Regresión del fix del Commit 1: name='token_refresh' (era 'tokee_refresh')."""
        from django.urls import reverse
        # Si el typo vuelve, reverse() lanza NoReverseMatch.
        url = reverse('token_refresh')
        assert url == '/api/token/refresh/'

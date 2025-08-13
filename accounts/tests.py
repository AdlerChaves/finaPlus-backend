import pytest
from rest_framework.test import APIClient
from rest_framework import status
from django.urls import reverse
from mixer.backend.django import mixer
from .models import User, Company

# Marca todos os testes neste módulo para terem acesso ao banco de dados
pytestmark = pytest.mark.django_db

# -- Fixtures --

@pytest.fixture
def api_client():
    """Retorna um cliente de API para fazer requisições."""
    return APIClient()

@pytest.fixture
def company():
    """Cria uma empresa para os testes."""
    return mixer.blend(Company, nome='Test Company', cnpj='12345678000195')

@pytest.fixture
def user(company):
    """Cria um usuário associado a uma empresa."""
    return mixer.blend(User, company=company, email='test@example.com', username='testuser')

@pytest.fixture
def authenticated_client(api_client, user):
    """Retorna um cliente de API autenticado."""
    api_client.force_authenticate(user=user)
    return api_client

# -- Testes de Views --

class TestUserCreateView:
    def test_user_registration_succeeds(self, api_client):
        """
        Verifica se um novo usuário e empresa podem ser criados com sucesso.
        """
        url = reverse('register')
        data = {
            # O campo username não é mais necessário, pois ele será o email
            "email": "newuser@example.com",
            "password": "strongpassword123",
            "first_name": "Test", # Adicionar campos que agora são esperados
            "last_name": "User",
            "company": {
                "name": "New Test Company",
                "cnpj": "98765432000195"
            }
        }
        response = api_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert User.objects.filter(username=data['email']).exists()
        assert Company.objects.filter(cnpj=data['company']['cnpj']).exists()

class TestMyTokenObtainPairView:
    def test_login_sets_cookies(self, api_client, user):
        """
        Verifica se o login retorna os cookies de acesso e atualização.
        """
        user.set_password('testpassword')
        user.save()
        url = reverse('token_obtain_pair')
        # Altere 'email' para 'username'
        data = {'username': user.username, 'password': 'testpassword'}

        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert 'access_token' in response.cookies
        assert 'refresh_token' in response.cookies


class TestLogoutView:
    def test_logout_deletes_cookies(self, authenticated_client):
        """
        Verifica se o logout remove os cookies de autenticação.
        """
        url = reverse('logout')
        response = authenticated_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.cookies['access_token'].value == ''
        assert response.cookies['refresh_token'].value == ''

class TestCurrentUserView:
    def test_get_current_user_data(self, authenticated_client, user):
        """
        Verifica se a view retorna os dados do usuário logado.
        """
        url = reverse('me')
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['email'] == user.email

    def test_update_current_user_data(self, authenticated_client):
        """
        Verifica se é possível atualizar os dados do usuário logado.
        """
        url = reverse('me')
        data = {'first_name': 'Updated', 'last_name': 'Name'}
        response = authenticated_client.patch(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['first_name'] == 'Updated'
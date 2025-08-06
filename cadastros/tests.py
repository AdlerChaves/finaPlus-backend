import pytest
from rest_framework.test import APIClient
from rest_framework import status
from django.urls import reverse
from mixer.backend.django import mixer
from .models import Customer, Supplier, Address
from accounts.models import User, Company
from django.contrib.auth.models import Permission

pytestmark = pytest.mark.django_db

# -- Fixtures --

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def company():
    return mixer.blend(Company)

@pytest.fixture
def user(company):
    # Dando as permissões necessárias para o usuário
    user = mixer.blend(User, company=company)
    # Busca as permissões existentes no banco de dados
    permissions = Permission.objects.filter(
        codename__in=['view_customer', 'change_customer', 'add_customer', 'delete_customer', 
                      'view_supplier', 'change_supplier', 'add_supplier', 'delete_supplier']
    )
    user.user_permissions.set(permissions)
    return user

@pytest.fixture
def authenticated_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client

# -- Testes de Customer --

class TestCustomerViewSet:
    def test_list_customers_returns_only_from_same_company(self, authenticated_client, user, company):
        """
        Garante que um usuário só pode listar os clientes da sua própria empresa.
        """
        mixer.blend(Customer, company=company)  # Cliente da mesma empresa
        other_company = mixer.blend(Company)
        mixer.blend(Customer, company=other_company)  # Cliente de outra empresa

        url = reverse('customer-list')
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['company'] == company.id

    def test_create_customer_with_address(self, authenticated_client, user):
        """
        Testa a criação de um cliente com endereço em uma única requisição.
        """
        url = reverse('customer-list')
        data = {
            "name": "New Customer",
            "document": "11122233344",
            "email": "customer@test.com",
            "phone": "11987654321",
            "address": {
                "cep": "12345-678",
                "street": "Test Street",
                "number": "123",
                "neighborhood": "Test Neighborhood",
                "city": "Test City",
                "state": "TS"
            }
        }
        response = authenticated_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert Customer.objects.filter(name="New Customer").exists()
        assert Address.objects.filter(cep="12345-678").exists()

# -- Testes de Supplier --

class TestSupplierViewSet:
    def test_list_suppliers(self, authenticated_client, company):
        """
        Testa a listagem de fornecedores.
        """
        mixer.blend(Supplier, company=company)
        url = reverse('supplier-list')
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) > 0

    def test_create_supplier(self, authenticated_client, user):
        """
        Testa a criação de um novo fornecedor.
        """
        url = reverse('supplier-list')
        data = {
            "name": "New Supplier",
            "document": "55667788000199",
            "email": "supplier@test.com",
            "phone": "11234567890"
        }
        response = authenticated_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['user'] == user.id

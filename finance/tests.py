import pytest
from rest_framework.test import APIClient
from rest_framework import status
from django.urls import reverse
from mixer.backend.django import mixer
from decimal import Decimal
from .models import BankAccount, Category, Transaction
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
    user = mixer.blend(User, company=company)
    permissions = Permission.objects.filter(
        codename__in=['view_transaction', 'change_transaction', 'add_transaction', 'delete_transaction']
    )
    user.user_permissions.set(permissions)
    return user

@pytest.fixture
def authenticated_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client

@pytest.fixture
def bank_account(company):
    return mixer.blend(BankAccount, company=company, initial_balance=Decimal('1000.00'))

@pytest.fixture
def category(company):
    return mixer.blend(Category, company=company, type='saida')


# -- Testes de Sinais (Signals) --

def test_balance_update_on_transaction_creation(bank_account):
    """
    Testa se o saldo da conta é atualizado corretamente ao criar uma transação.
    """
    initial_balance = bank_account.initial_balance
    transaction_amount = Decimal('250.50')

    mixer.blend(
        Transaction,
        bank_account=bank_account,
        amount=transaction_amount,
        type='saida',
        company=bank_account.company
    )

    bank_account.refresh_from_db()
    expected_balance = initial_balance - transaction_amount
    assert bank_account.initial_balance == expected_balance

def test_balance_update_on_transaction_delete(bank_account):
    """
    Testa se o saldo da conta é revertido corretamente ao deletar uma transação.
    """
    initial_balance = bank_account.initial_balance
    transaction_amount = Decimal('100.00')
    transaction = mixer.blend(
        Transaction,
        bank_account=bank_account,
        amount=transaction_amount,
        type='entrada',
        company=bank_account.company
    )
    
    # Saldo após a criação da transação
    bank_account.refresh_from_db()
    assert bank_account.initial_balance == initial_balance + transaction_amount

    # Deleta a transação e verifica se o saldo foi revertido
    transaction.delete()
    bank_account.refresh_from_db()
    assert bank_account.initial_balance == initial_balance

# -- Testes de Views --

class TestTransactionViewSet:
    def test_create_transaction_updates_balance(self, authenticated_client, bank_account, category, user):
        """
        Testa a criação de uma transação através da API e verifica a atualização do saldo.
        """
        url = reverse('transaction-list')
        initial_balance = bank_account.initial_balance
        transaction_amount = Decimal('50.00')
        data = {
            "description": "API Test Transaction",
            "amount": transaction_amount,
            "type": "saida",
            "bank_account": bank_account.id,
            "category": category.id
        }

        response = authenticated_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED

        bank_account.refresh_from_db()
        expected_balance = initial_balance - transaction_amount
        assert bank_account.initial_balance == expected_balance

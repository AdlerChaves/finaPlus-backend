from rest_framework import serializers
from .models import Category, BankAccount, Transaction, CreditCard, Payable

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        # O campo 'company' será preenchido automaticamente pela view, não pelo usuário
        fields = ['id', 'name', 'type', 'dre_classification', 'dfc_classification']
        read_only_fields = ['company']


class BankAccountSerializer(serializers.ModelSerializer):
    # Transforma o valor booleano em um texto mais legível na resposta da API
    status = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = BankAccount
        fields = ['id', 'name', 'type', 'initial_balance', 'is_active', 'notes', 'status']
        read_only_fields = ['company']

    # Adicionando um método para retornar o status como "Ativa" ou "Inativa"
    def get_status_display(self, obj):
        return "Ativa" if obj.is_active else "Inativa"
    
class TransactionSerializer(serializers.ModelSerializer):
    # Para mostrar os nomes em vez dos IDs na resposta da API
    category_name = serializers.CharField(source='category.name', read_only=True)
    bank_account_name = serializers.CharField(source='bank_account.name', read_only=True)

    class Meta:
        model = Transaction
        fields = [
            'id', 'description', 'amount', 'transaction_date', 'type', 
            'category', 'category_name', 'bank_account', 'bank_account_name', 'notes'
        ]
        # O usuário e a empresa serão preenchidos automaticamente
        read_only_fields = ['company', 'user']

class CreditCardSerializer(serializers.ModelSerializer):
    # Para mostrar o nome da conta na resposta da API
    associated_account_name = serializers.CharField(source='associated_account.name', read_only=True)
    status = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = CreditCard
        fields = [
            'id', 'name', 'brand', 'last_digits', 'credit_limit', 
            'closing_day', 'due_day', 'associated_account', 
            'associated_account_name', 'is_active', 'status'
        ]
        read_only_fields = ['company']

    def get_status_display(self, obj):
        return "Ativo" if obj.is_active else "Inativo"
    

class PayableSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = Payable
        fields = '__all__' # Por enquanto, vamos expor todos os campos
        read_only_fields = ['company', 'user']
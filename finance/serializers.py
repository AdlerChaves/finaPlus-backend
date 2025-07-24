from rest_framework import serializers
from .models import Category, BankAccount, Transaction, CreditCard, Payable, Receivable
from cadastros.serializers import CustomerSerializer 

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
       
        fields = ['id', 'name', 'type', 'user', 'company', 'dre_classification', 'dfc_classification'] 
        
        read_only_fields = ['user', 'company']

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

    category_name = serializers.CharField(source='category.name', read_only=True, required=False)
    bank_account_name = serializers.CharField(source='bank_account.name', read_only=True, required=False)

    
    # Adicione estes campos para tratar valores nulos corretamente
    category = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        required=False,
        allow_null=True
    )
    bank_account = serializers.PrimaryKeyRelatedField(
        queryset=BankAccount.objects.all(),
        required=False,
        allow_null=True
    )
    credit_card = serializers.PrimaryKeyRelatedField(
        queryset=CreditCard.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = Transaction
        fields = [
            'id',
            'description',
            'amount',
            'transaction_date',
            'type',
            'category',
            'notes',
            'bank_account',
            'credit_card',
            'user',
            'company',
            'category_name',
            'bank_account_name'
        ]
        read_only_fields = ['user', 'company']

    def validate(self, data):
        """
        Validação para garantir que ou a conta bancária ou o cartão de crédito seja fornecido.
        """
        if not data.get('bank_account') and not data.get('credit_card'):
            raise serializers.ValidationError("É necessário fornecer uma conta bancária ou um cartão de crédito.")
        return data

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
    transaction_date = serializers.DateField(source='transaction.transaction_date', read_only=True)
    
    transaction = TransactionSerializer(read_only=True)

    class Meta:
        model = Payable
        # A lista de fields foi corrigida abaixo
        fields = [
            'id', 
            'description', 
            'amount', 
            'due_date', 
            'status', 
            'category', 
            'category_name', 
            'transaction',
            'transaction_date'
        ]

        read_only_fields = ['user']

class ReceivableSerializer(serializers.ModelSerializer):
    # Para incluir o nome do cliente na resposta da API
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    # Para incluir os dados completos do cliente, se necessário no futuro
    customer = CustomerSerializer(read_only=True)
    # Campo para receber o ID do cliente ao criar/atualizar
    customer_id = serializers.IntegerField(write_only=True)


    class Meta:
        model = Receivable
        fields = [
            'id',
            'customer',
            'customer_id',
            'customer_name',
            'description',
            'amount',
            'due_date',
            'payment_date',
            'status',
            'payment_method',
            'notes',
            'created_at',
        ]
        read_only_fields = ['user', 'company']

    def create(self, validated_data):
        # Associa o customer_id recebido ao campo 'customer' do modelo
        validated_data['customer_id'] = validated_data.pop('customer_id')
        return super().create(validated_data)

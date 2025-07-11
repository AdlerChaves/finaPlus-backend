from rest_framework import serializers
from .models import Customer, Address, Supplier, SupplierAddress, SupplierBankAccount

class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        exclude = ('customer',)

class CustomerSerializer(serializers.ModelSerializer):
    # Usamos o AddressSerializer para lidar com o endereço de forma aninhada
    address = AddressSerializer(required=False, allow_null=True)

    class Meta:
        model = Customer
        fields = [
            'id',
            'name',
            'customer_type',
            'document',
            'email',
            'phone',
            'birth_date',
            'status',
            'notes',
            'address', # Campo aninhado
            'created_at',
            'updated_at'
        ]
    
    def create(self, validated_data):
        address_data = validated_data.pop('address', None)
        customer = Customer.objects.create(**validated_data)

        if address_data:
            Address.objects.create(customer=customer, **address_data)
        
        return customer

    def update(self, instance, validated_data):
        address_data = validated_data.pop('address', None)

        # Atualiza os campos do cliente
        instance = super().update(instance, validated_data)

        # Se dados de endereço foram enviados, atualiza ou cria o endereço
        if address_data:
            address_instance, created = Address.objects.update_or_create(
                customer=instance,
                defaults=address_data
            )
        
        return instance
    
class SupplierAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupplierAddress
        exclude = ('id', 'supplier')

class SupplierBankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupplierBankAccount
        exclude = ('id', 'supplier')

class SupplierSerializer(serializers.ModelSerializer):
    # Serializers aninhados para lidar com os dados relacionados em uma única requisição
    address = SupplierAddressSerializer(required=False, allow_null=True)
    bank_account = SupplierBankAccountSerializer(required=False, allow_null=True)

    class Meta:
        model = Supplier
        fields = '__all__'
        read_only_fields = ('user', 'company') # Esses campos serão preenchidos automaticamente

    def create(self, validated_data):
        address_data = validated_data.pop('address', None)
        bank_account_data = validated_data.pop('bank_account', None)
        
        supplier = Supplier.objects.create(**validated_data)

        if address_data:
            SupplierAddress.objects.create(supplier=supplier, **address_data)
        
        if bank_account_data:
            SupplierBankAccount.objects.create(supplier=supplier, **bank_account_data)
            
        return supplier

    def update(self, instance, validated_data):
        address_data = validated_data.pop('address', None)
        bank_account_data = validated_data.pop('bank_account', None)

        # Atualiza os campos do fornecedor
        instance = super().update(instance, validated_data)

        # Atualiza ou cria o endereço
        if address_data:
            SupplierAddress.objects.update_or_create(supplier=instance, defaults=address_data)
        
        # Atualiza ou cria a conta bancária
        if bank_account_data:
            SupplierBankAccount.objects.update_or_create(supplier=instance, defaults=bank_account_data)

        return instance
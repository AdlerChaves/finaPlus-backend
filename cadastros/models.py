from django.db import models
from accounts.models import User, Company

class Customer(models.Model):
    class CustomerType(models.TextChoices):
        PESSOA_FISICA = 'PF', 'Pessoa Física'
        PESSOA_JURIDICA = 'PJ', 'Pessoa Jurídica'

    class StatusType(models.TextChoices):
        ACTIVE = 'active', 'Ativo'
        INACTIVE = 'inactive', 'Inativo'

    # Relacionamentos
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='customers')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='customers')

    # Informações Básicas
    name = models.CharField(max_length=255, help_text="Nome completo ou Razão Social")
    customer_type = models.CharField(max_length=2, choices=CustomerType.choices, default=CustomerType.PESSOA_FISICA)
    document = models.CharField(max_length=20, unique=True, help_text="CPF ou CNPJ")
    email = models.EmailField(max_length=255)
    phone = models.CharField(max_length=20)
    birth_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=StatusType.choices, default=StatusType.ACTIVE)
    notes = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Address(models.Model):
    # O endereço pertence a um cliente. Se o cliente for deletado, o endereço também será.
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE, related_name='address')

    cep = models.CharField(max_length=9)
    street = models.CharField(max_length=255)
    number = models.CharField(max_length=20)
    complement = models.CharField(max_length=100, blank=True, null=True)
    neighborhood = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=2)
    country = models.CharField(max_length=50, default='Brasil')

    def __str__(self):
        return f"Endereço de {self.customer.name}"
    
class Supplier(models.Model):
    class SupplierType(models.TextChoices):
        PESSOA_JURIDICA = 'PJ', 'Pessoa Jurídica'
        PESSOA_FISICA = 'PF', 'Pessoa Física'

    class StatusType(models.TextChoices):
        ACTIVE = 'active', 'Ativo'
        INACTIVE = 'inactive', 'Inativo'

    # Relacionamentos
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='suppliers')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='suppliers')

    # Dados do Fornecedor
    name = models.CharField(max_length=255, help_text="Nome completo ou Razão Social")
    trade_name = models.CharField(max_length=255, blank=True, null=True, help_text="Nome Fantasia")
    supplier_type = models.CharField(max_length=2, choices=SupplierType.choices, default=SupplierType.PESSOA_JURIDICA)
    document = models.CharField(max_length=20, unique=True, help_text="CPF ou CNPJ")
    state_registration = models.CharField(max_length=20, blank=True, null=True)
    municipal_registration = models.CharField(max_length=20, blank=True, null=True)
    
    # Contato
    contact_name = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=20)
    cellphone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(max_length=255)

    # Outros
    category = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=10, choices=StatusType.choices, default=StatusType.ACTIVE)
    notes = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

# Adicione o modelo de Endereço do Fornecedor
class SupplierAddress(models.Model):
    supplier = models.OneToOneField(Supplier, on_delete=models.CASCADE, related_name='address')
    cep = models.CharField(max_length=9)
    street = models.CharField(max_length=255)
    number = models.CharField(max_length=20)
    complement = models.CharField(max_length=100, blank=True, null=True)
    neighborhood = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=2)
    country = models.CharField(max_length=50, default='Brasil')

    def __str__(self):
        return f"Endereço de {self.supplier.name}"

# Adicione o modelo de Dados Bancários do Fornecedor
class SupplierBankAccount(models.Model):
    class AccountType(models.TextChoices):
        CORRENTE = 'corrente', 'Corrente'
        POUPANCA = 'poupanca', 'Poupança'
        PJ = 'pj', 'PJ'

    supplier = models.OneToOneField(Supplier, on_delete=models.CASCADE, related_name='bank_account')
    bank = models.CharField(max_length=100)
    agency = models.CharField(max_length=20)
    account = models.CharField(max_length=20)
    account_type = models.CharField(max_length=10, choices=AccountType.choices, default=AccountType.CORRENTE)
    pix_key = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Conta de {self.supplier.name}"
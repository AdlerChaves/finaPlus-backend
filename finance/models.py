from django.db import models
from django.utils import timezone
from django.db.models.signals import post_init 
from django.dispatch import receiver
from django.core.validators import MinValueValidator, MaxValueValidator
from accounts.models import User, Company

class Category(models.Model):
    # Opções para os tipos e classificações
    TYPE_CHOICES = [
        ('entrada', 'Entrada'),
        ('saida', 'Saída'),
    ]
    DRE_CHOICES = [
        ('receita_bruta', 'Receita Bruta'),
        ('deducao_venda', 'Dedução de Venda'),
        ('custos_variaveis', 'Custos Variáveis'),
        ('despesa_operacional', 'Despesa Operacional'),
        ('despesa_administrativa', 'Despesa Administrativa'),
        ('despesa_comercial', 'Despesa Comercial'),
        ('receita_financeira', 'Receita Financeira'),
        ('despesa_financeira', 'Despesa Financeira'),
        ('imposto_lucro', 'Imposto sobre o Lucro'),
        ('nao_se_aplica', 'Não se Aplica'),
    ]
    DFC_CHOICES = [
        ('operacional', 'Operacional'),
        ('investimento', 'Investimento'),
        ('financiamento', 'Financiamento'),
        ('nao_se_aplica', 'Não se Aplica'),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='categories')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=7, choices=TYPE_CHOICES)
    dre_classification = models.CharField(max_length=30, choices=DRE_CHOICES)
    dfc_classification = models.CharField(max_length=30, choices=DFC_CHOICES)

    class Meta:
        # Garante que não haja categorias com o mesmo nome na mesma empresa
        unique_together = ('company', 'name')
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"

    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"
    

class BankAccount(models.Model):
    ACCOUNT_TYPE_CHOICES = [
        ('Conta Corrente', 'Conta Corrente'),
        ('Conta Poupança', 'Conta Poupança'),
        ('Caixa', 'Caixa'),
        ('Investimento', 'Investimento'),
        ('Outro', 'Outro'),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='bank_accounts')
    name = models.CharField(max_length=100, verbose_name="Nome da Conta")
    type = models.CharField(max_length=20, choices=ACCOUNT_TYPE_CHOICES, verbose_name="Tipo de Conta")
    initial_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name="Saldo Inicial")
    is_active = models.BooleanField(default=True, verbose_name="Ativa?")
    notes = models.TextField(blank=True, null=True, verbose_name="Observações")

    class Meta:
        verbose_name = "Conta Bancária"
        verbose_name_plural = "Contas Bancárias"
        # Garante que não haja contas com o mesmo nome na mesma empresa
        unique_together = ('company', 'name')

    def __str__(self):
        return f"{self.name} ({self.company.name})"
    
class CreditCard(models.Model):
    CARD_BRAND_CHOICES = [
        ('Visa', 'Visa'),
        ('MasterCard', 'MasterCard'),
        ('Elo', 'Elo'),
        ('American Express', 'American Express'),
        ('Hipercard', 'Hipercard'),
        ('Diners Club', 'Diners Club'),
        ('Outra', 'Outra'),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='credit_cards')
    name = models.CharField(max_length=100, verbose_name="Nome do Cartão")
    brand = models.CharField(max_length=20, choices=CARD_BRAND_CHOICES, verbose_name="Bandeira")
    last_digits = models.CharField(max_length=4, verbose_name="Últimos 4 dígitos")
    credit_limit = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Limite de Crédito")
    closing_day = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(31)], verbose_name="Dia de Fechamento")
    due_day = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(31)], verbose_name="Dia de Vencimento")
    associated_account = models.ForeignKey(BankAccount, on_delete=models.PROTECT, related_name='credit_cards', verbose_name="Conta Associada")
    is_active = models.BooleanField(default=True, verbose_name="Ativo?")

    class Meta:
        verbose_name = "Cartão de Crédito"
        verbose_name_plural = "Cartões de Crédito"
        # Garante que os últimos 4 dígitos sejam únicos por empresa
        unique_together = ('company', 'last_digits')

    def __str__(self):
        return f"{self.name} (final {self.last_digits})"
    
class Transaction(models.Model):
    TRANSACTION_TYPE_CHOICES = [
        ('entrada', 'Entrada'),
        ('saida', 'Saída'),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='transactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE) 
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_date = models.DateField(default=timezone.now)
    type = models.CharField(max_length=7, choices=TRANSACTION_TYPE_CHOICES, default='saida') 
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True) 
    notes = models.TextField(blank=True, null=True) 
    bank_account = models.ForeignKey(BankAccount, on_delete=models.CASCADE, null=True, blank=True)
    credit_card = models.ForeignKey(CreditCard, on_delete=models.CASCADE, null=True, blank=True, related_name='transactions')
    

    class Meta:
        verbose_name = "Transação"
        verbose_name_plural = "Transações"

    def __str__(self):
        return f"{self.description} - {self.amount}"
    
@receiver(post_init, sender=Transaction)
def store_original_state(sender, instance, **kwargs):
    
    instance._original_state = {
        'amount': instance.amount,
        'type': instance.type,
        'bank_account_id': instance.bank_account_id
    }
    

    

class Payable(models.Model):
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('pago', 'Pago'),
        ('vencido', 'Vencido'),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='payables')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='payables')
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, null=True, blank=True, related_name="payables", verbose_name="Transação de Origem (Cartão)")
    
    description = models.CharField(max_length=255, verbose_name="Descrição")
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Valor a Pagar")
    due_date = models.DateField(verbose_name="Data de Vencimento")
    payment_date = models.DateField(null=True, blank=True, verbose_name="Data de Pagamento")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pendente')
    
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    # Se for pago via débito em conta
    paid_from_account = models.ForeignKey(BankAccount, on_delete=models.SET_NULL, null=True, blank=True, related_name='paid_payables')
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Conta a Pagar"
        verbose_name_plural = "Contas a Pagar"
        ordering = ['due_date']

    def __str__(self):
        return f"{self.description} - Venc: {self.due_date}"
    


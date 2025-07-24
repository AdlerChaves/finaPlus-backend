from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Transaction, Payable, BankAccount
from django.utils import timezone
from django.db.models import Sum
from decimal import Decimal

@receiver(post_save, sender=Transaction)
def update_balance_on_save(sender, instance, created, **kwargs):
    """
    Atualiza o saldo da(s) conta(s) bancária(s) quando uma transação é criada ou alterada.
    """
    # Se a transação foi recém-criada, a lógica é simples
    if created:
        if instance.bank_account:
            if instance.type == 'entrada':
                instance.bank_account.initial_balance += instance.amount
            elif instance.type == 'saida':
                instance.bank_account.initial_balance -= instance.amount
            instance.bank_account.save()
        return # Finaliza a execução aqui

    # ---- LÓGICA DE ATUALIZAÇÃO CORRIGIDA E ROBUSTA ----
    
    original_state = instance._original_state
    original_account_id = original_state.get('bank_account_id')
    original_amount = original_state.get('amount', 0)
    original_type = original_state.get('type')

    # 1. SEMPRE reverte a transação da CONTA ANTIGA, se ela existia.
    if original_account_id:
        try:
            # Pega a conta original do banco de dados
            original_account = BankAccount.objects.get(pk=original_account_id)
            if original_type == 'entrada':
                original_account.initial_balance -= original_amount
            elif original_type == 'saida':
                original_account.initial_balance += original_amount
            original_account.save()
        except BankAccount.DoesNotExist:
            pass # Ignora se a conta original foi deletada

    # 2. SEMPRE aplica a transação na CONTA NOVA, se ela existe.
    if instance.bank_account:
        # Pega a conta do banco de dados novamente para garantir o saldo mais recente
        # Isso é importante caso a conta nova e a antiga sejam a mesma
        current_account = BankAccount.objects.get(pk=instance.bank_account.id)
        if instance.type == 'entrada':
            current_account.initial_balance += instance.amount
        elif instance.type == 'saida':
            current_account.initial_balance -= instance.amount
        current_account.save()

        
@receiver(post_delete, sender=Transaction)
def update_balance_on_delete(sender, instance, **kwargs):
    """
    Atualiza o saldo da conta bancária quando uma transação é deletada.
    """
    # --- INÍCIO DA CORREÇÃO ---
    try:
        # Tenta acessar a conta bancária. Se ela não existir (porque está sendo deletada),
        # o bloco 'except' será acionado.
        bank_account_to_update = instance.bank_account
        
        if bank_account_to_update:
            # Se a conta existir, recalcula o saldo normalmente
            total_incomes = Transaction.objects.filter(
                bank_account=bank_account_to_update, type='entrada'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            total_expenses = Transaction.objects.filter(
                bank_account=bank_account_to_update, type='saida'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            bank_account_to_update.current_balance = total_incomes - total_expenses
            bank_account_to_update.save()

    except BankAccount.DoesNotExist:
        # Se a conta bancária não existe mais, simplesmente não fazemos nada.
        # Isso acontece quando a própria conta está sendo deletada.
        pass




# @receiver(post_save, sender=Payable)
# def create_transaction_from_payable(sender, instance, created, **kwargs):
#     """
#     Cria uma transação de 'saida' quando uma conta a pagar (Payable) 
#     é marcada como 'pago'.
#     """
#     # A lógica só roda se o status for 'pago' e ainda não houver uma transação associada.
#     if instance.status == 'pago' and not instance.transaction:
        
#         # Lógica para encontrar o cartão de crédito (se houver)
#         # Usamos hasattr para verificar com segurança se a relação 'card_expense' existe.
#         credit_card_instance = None
#         if hasattr(instance, 'card_expense') and instance.card_expense:
#             credit_card_instance = instance.card_expense.credit_card

#         # Cria a transação de saída
#         transaction = Transaction.objects.create(
#             company=instance.company,
#             description=f"Pagamento de conta: {instance.description}",
#             amount=instance.amount,
#             transaction_date=instance.payment_date or timezone.now().date(),
#             type='saida',
#             category=instance.category,
#             bank_account=instance.bank_account,
#             credit_card=credit_card_instance,  # Associa o cartão de crédito encontrado
#             is_paid=True
#         )
        
#         # Associa a transação criada de volta à conta a pagar
#         instance.transaction = transaction
#         instance.save(update_fields=['transaction'])
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Transaction, Payable, BankAccount

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

        
# --- SINAL PARA EXCLUSÃO DE TRANSAÇÕES ---
@receiver(post_delete, sender=Transaction)
def update_balance_on_delete(sender, instance, **kwargs):
    """
    Reverte o saldo da conta bancária quando uma transação é excluída.
    """
    if instance.bank_account:
        if instance.type == 'entrada':
            instance.bank_account.initial_balance -= instance.amount
        elif instance.type == 'saida':
            instance.bank_account.initial_balance += instance.amount
        instance.bank_account.save()

# --- SEU SINAL EXISTENTE (EXEMPLO) ---
# Se o seu sinal para criar transação a partir de Payable estiver aqui, mantenha-o.
@receiver(post_save, sender=Payable)
def create_transaction_from_payable(sender, instance, created, **kwargs):
    """
    Cria uma transação de saída quando uma nova conta a pagar é criada.
    """
    if created:
        Transaction.objects.create(
            user=instance.user,
            company=instance.user.company,
            description=f"{instance.description} (Compra Original)",
            amount=instance.amount,
            transaction_date=instance.due_date,
            credit_card=instance.transaction.credit_card, 
            type='saida'
        )
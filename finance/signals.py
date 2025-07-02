from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Transaction

@receiver(post_save, sender=Transaction)
def update_balance_on_transaction(sender, instance, created, **kwargs):
    """
    Este é o nosso "vigia". Ele é chamado toda vez que uma
    transação é salva.
    """
    # A lógica só executa se for uma transação NOVA
    if created:
        bank_account = instance.bank_account

        # Se a conta bancária existir (transações de cartão não têm conta direta)
        if bank_account:
            # Se for uma transação de SAÍDA, SUBTRAI do saldo
            if instance.transaction_type == 'saida':
                bank_account.initial_balance -= instance.amount

            # Se for uma transação de ENTRADA, SOMA ao saldo
            elif instance.transaction_type == 'entrada':
                bank_account.initial_balance += instance.amount

            # Salva a conta bancária com o novo saldo
            bank_account.save()
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from finance.models import Payable
from finance.utils import send_whatsapp_message

class Command(BaseCommand):
    # --- ALTERAÇÃO 1: Texto de ajuda atualizado ---
    help = 'Envia lembretes via WhatsApp para contas a pagar que vencem no dia atual.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Iniciando o envio de lembretes de contas a pagar...'))

        # --- ALTERAÇÃO 2: A data alvo agora é a data de hoje ---
        target_due_date = timezone.now().date()

        # Filtra as contas a pagar que estão pendentes e vencem na data alvo
        payables_to_remind = Payable.objects.filter(
            due_date=target_due_date,
            status='pendente'
        ).select_related('user')

        if not payables_to_remind.exists():
            self.stdout.write(self.style.SUCCESS(f"Nenhuma conta a pagar com vencimento para hoje ({target_due_date.strftime('%d/%m/%Y')}) encontrada."))
            return

        for payable in payables_to_remind:
            user = payable.user
            if user and user.phone:
                formatted_amount = f"R$ {payable.amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

                # --- ALTERAÇÃO 3: Mensagem ajustada para "vence hoje" ---
                message = (
                    f"Olá, {user.first_name}! 👋\n\n"
                    f"Este é um lembrete do FinanPlus.\n\n"
                    f"A sua conta '*{payable.description}*' no valor de *{formatted_amount}* "
                    f"*vence hoje*, dia {payable.due_date.strftime('%d/%m/%Y')}.\n\n"
                    "Não se esqueça de efetuar o pagamento! 😉"
                )

                send_whatsapp_message(user.phone, message)
            else:
                self.stdout.write(self.style.WARNING(
                    f"A conta a pagar ID {payable.id} não tem um utilizador associado ou o utilizador não tem telemóvel."
                ))

        self.stdout.write(self.style.SUCCESS('Processo de envio de lembretes concluído.'))
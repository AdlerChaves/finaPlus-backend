from django.urls import reverse
from django_rest_passwordreset.signals import reset_password_token_created
from django.core.mail import send_mail
from django.dispatch import receiver

@receiver(reset_password_token_created)
def password_reset_token_created(sender, instance, reset_password_token, *args, **kwargs):
    """
    Manipulador para o sinal reset_password_token_created.
    Envia um e-mail para o usuário quando um token de reset de senha é criado.
    """
    # Monta a URL para o frontend.
    # O link que o usuário receberá no e-mail.
    # ATENÇÃO: Verifique se o endereço (127.0.0.1:5500) corresponde ao seu frontend.
    reset_password_url = f"http://127.0.0.1:5500/telas/password_reset_confirm.html?token={reset_password_token.key}"

    # Corpo do e-mail
    email_plaintext_message = (
        f"Olá {reset_password_token.user.get_full_name() or reset_password_token.user.username},\n\n"
        "Você solicitou uma redefinição de senha para sua conta no FinançaPlus.\n\n"
        f"Clique no link abaixo ou copie e cole no seu navegador para criar uma nova senha:\n\n"
        f"{reset_password_url}\n\n"
        "Se você não solicitou isso, por favor, ignore este e-mail.\n\n"
        "Obrigado,\nEquipe FinançaPlus"
    )

    # Envia o e-mail (que será impresso no console)
    send_mail(
        # Título do e-mail
        "Redefinição de Senha para FinançaPlus",
        # Mensagem
        email_plaintext_message,
        # E-mail de origem
        "noreply@financaplus.com",
        # E-mail de destino
        [reset_password_token.user.email]
    )
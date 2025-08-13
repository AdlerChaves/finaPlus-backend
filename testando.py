from django.utils import timezone
from datetime import timedelta
from accounts.models import User
from finance.models import Payable, Category

# --- CONFIGURAÇÃO DO TESTE ---
# 1. Coloque aqui o seu número de WhatsApp no formato internacional (código do país + DDD + número)
SEU_NUMERO_WHATSAPP = "5511983998794" 

# 2. Use o username de um utilizador que já exista na sua base de dados
USERNAME_PARA_TESTE = "admin" # ou "adlerchaves", "testuser", etc.
# --- FIM DA CONFIGURAÇÃO ---


# Encontra o utilizador
try:
    user_para_teste = User.objects.get(username=USERNAME_PARA_TESTE)
    print(f"Utilizador '{user_para_teste.username}' encontrado.")
except User.DoesNotExist:
    print(f"ERRO: Utilizador com username '{USERNAME_PARA_TESTE}' não encontrado. Verifique o username e tente novamente.")
    # Saia da shell com quit() se o utilizador não existir

# Atualiza o número de telemóvel do utilizador para o teste
user_para_teste.phone = SEU_NUMERO_WHATSAPP
user_para_teste.save()
print(f"Número de telemóvel do utilizador '{user_para_teste.username}' atualizado para {SEU_NUMERO_WHATSAPP}.")

# Calcula a data de vencimento (exatamente 3 dias a partir de hoje)
data_vencimento = timezone.now().date() + timedelta(days=3)
print(f"A data de vencimento alvo para o lembrete é: {data_vencimento.strftime('%d/%m/%Y')}")

# Pega numa categoria qualquer para associar (ou cria uma se não houver)
categoria, created = Category.objects.get_or_create(
    company=user_para_teste.company, 
    name="Categoria de Teste para Lembrete",
    defaults={'type': 'saida'}
)

# Cria a conta a pagar de teste
Payable.objects.create(
    company=user_para_teste.company,
    user=user_para_teste,
    description="Conta de Luz - Teste de Lembrete",
    amount=150.75,
    due_date=data_vencimento,
    status='pendente',
    category=categoria
)

print("\n>>> DADOS DE TESTE CRIADOS COM SUCESSO! <<<")
print("Uma conta a pagar foi criada com vencimento para daqui a 3 dias.")
print("Pode sair da shell (use quit()) e executar o comando de lembretes.")
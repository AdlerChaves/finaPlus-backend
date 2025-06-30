from django.apps import AppConfig

class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        # Adicione esta linha para teste
        print("====== CARREGANDO SINAIS DA APP ACCOUNTS ======") 
        import accounts.signals

from django.db import models
from django.contrib.auth.models import AbstractUser

class Company(models.Model):
    name = models.CharField(max_length=255, verbose_name="Nome da Empresa")
    cnpj = models.CharField(max_length=18, unique=True, null=True, blank=True, verbose_name="CNPJ")
    business_area = models.CharField(max_length=100, null=True, blank=True, verbose_name="Área de Atuação")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class User(AbstractUser):
    # CARGOS DEFINIDOS
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Administrador'
        FINANCE = 'finance', 'Financeiro'
        MANAGER = 'manager', 'Gestor'
        ANALYST = 'analyst', 'Analista'
        GENERIC = 'employee', 'Colaborador'

    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True, related_name='users')
    
    # NOVOS CAMPOS ADICIONADOS
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.ADMIN, verbose_name="Cargo")
    permissions_list = models.JSONField(default=list, blank=True, null=True, verbose_name="Lista de Permissões")

    # Preferências do Sistema
    theme = models.CharField(max_length=10, default='light', verbose_name="Tema") 
    currency = models.CharField(max_length=5, default='BRL', verbose_name="Moeda Padrão")
    language = models.CharField(max_length=10, default='pt-BR', verbose_name="Idioma")

    # Preferências de Notificação
    notify_weekly_goals = models.BooleanField(default=True, verbose_name="Notificar metas semanais")
    notify_large_transactions = models.BooleanField(default=True, verbose_name="Notificar grandes transações")
    notify_bills_reminder = models.BooleanField(default=True, verbose_name="Lembrete de contas a pagar")
   



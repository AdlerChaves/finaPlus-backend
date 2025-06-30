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
    # Campos adicionais que você pode querer no futuro
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True, related_name='users')

    # Removendo first_name e last_name padrão para usar um campo 'full_name' se preferir
    # ou pode mantê-los. Para simplificar, vamos usar o padrão por enquanto.
    pass


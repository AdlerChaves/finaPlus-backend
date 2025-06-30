from django.contrib import admin
from .models import User, Company

# Registre seus modelos aqui para que apareçam no painel de administração.
admin.site.register(User)
admin.site.register(Company)
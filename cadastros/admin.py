from django.contrib import admin
from .models import Address, Customer, Supplier

admin.site.register(Address)
admin.site.register(Customer)
admin.site.register(Supplier)

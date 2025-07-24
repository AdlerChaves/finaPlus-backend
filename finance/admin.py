from django.contrib import admin
from .models import Category, BankAccount, Transaction, CreditCard, Payable, Receivable

admin.site.register(Category)
admin.site.register(BankAccount)
admin.site.register(Transaction)
admin.site.register(CreditCard)
admin.site.register(Payable)
admin.site.register(Receivable)

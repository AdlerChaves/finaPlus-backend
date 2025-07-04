from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, BankAccountViewSet, TransactionViewSet, CreditCardViewSet, PayableViewSet


router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'bank-accounts', BankAccountViewSet, basename='bankaccount')
router.register(r'transactions', TransactionViewSet, basename='transaction')
router.register(r'credit-cards', CreditCardViewSet, basename='creditcard')
router.register(r'payables', PayableViewSet, basename='payable')




urlpatterns = [
    path('', include(router.urls)),
    
]
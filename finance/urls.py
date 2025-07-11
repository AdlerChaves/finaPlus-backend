from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, BankAccountViewSet, TransactionViewSet, CreditCardViewSet, PayableViewSet
from .views import CreateCardExpenseView, MarkAsPaidView, CardStatementView, CardBillView, MonthlyBillsView, CardBillDetailView, PayCardBillView



router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'bank-accounts', BankAccountViewSet, basename='bankaccount')
router.register(r'transactions', TransactionViewSet, basename='transaction')
router.register(r'credit-cards', CreditCardViewSet, basename='creditcard')
router.register(r'payables', PayableViewSet, basename='payable')




urlpatterns = [
    path('', include(router.urls)),
    path('payables/<int:pk>/mark_as_paid/', MarkAsPaidView.as_view(), name='payable-mark-as-paid'),
    path('card-statement/', CardStatementView.as_view(), name='card-statement'),
    path('card-expense/', CreateCardExpenseView.as_view(), name='create-card-expense'),
    path('card-bill/', CardBillView.as_view(), name='card-bill'),
    path('monthly-bills/', MonthlyBillsView.as_view(), name='monthly-bills'),
    path('card-bill-detail/', CardBillDetailView.as_view(), name='card-bill-detail'),
    path('pay-card-bill/', PayCardBillView.as_view(), name='pay-card-bill'),

    
]
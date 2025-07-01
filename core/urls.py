from django.contrib import admin
from django.urls import path, include
from .views import home
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from finance.views import CreateCardExpenseView, MarkAsPaidView, CardStatementView, CardBillView

urlpatterns = [
    path('', home, name='home'),
    path('admin/', admin.site.urls),

    path('api/accounts/', include('accounts.urls')),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/accounts/password_reset/', include('django_rest_passwordreset.urls', namespace='password_reset')),

    path('api/finance/payables/<int:pk>/mark_as_paid/', MarkAsPaidView.as_view(), name='payable-mark-as-paid'),
    path('api/finance/card-statement/', CardStatementView.as_view(), name='card-statement'),
    path('api/finance/card-expense/', CreateCardExpenseView.as_view(), name='create-card-expense'),
    path('api/finance/card-bill/', CardBillView.as_view(), name='card-bill'),


    # A rota geral para o router vem por último.
    path('api/finance/', include('finance.urls')),

]

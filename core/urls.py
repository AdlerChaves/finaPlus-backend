from django.contrib import admin
from django.urls import path, include
from .views import home
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path('', home, name='home'),
    path('admin/', admin.site.urls),
    path('api/accounts/', include('accounts.urls')),

        # Endpoints de Token JWT
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/finance/', include('finance.urls')),

    path('api/accounts/password_reset/', include('django_rest_passwordreset.urls', namespace='password_reset')),


]

from django.contrib import admin
from rest_framework import routers
from django.urls import path, include
from .views import home
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from accounts.views import UserViewSet, GroupViewSet

router = routers.DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'groups', GroupViewSet)


urlpatterns = [
    path('', home, name='home'),
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),

    path('api/accounts/', include('accounts.urls')),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/accounts/password_reset/', include('django_rest_passwordreset.urls', namespace='password_reset')),


    # A rota geral para o router vem por último.
    path('api/finance/', include('finance.urls')),
    path('api/cadastros/', include('cadastros.urls')),

]

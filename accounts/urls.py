from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserCreateView, CompanyUserViewSet, CurrentUserView, MyTokenObtainPairView, LogoutView, ChangePasswordView, DeleteAccountView 
from rest_framework_simplejwt.views import TokenRefreshView


router = DefaultRouter()
router.register (r'users', CompanyUserViewSet, basename='company-user')

urlpatterns = [
    path('register/', UserCreateView.as_view(), name='register'),
    path('', include(router.urls)),
    path('me/', CurrentUserView.as_view(), name='me'),
    
    path('token/', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', LogoutView.as_view(), name='logout'),

    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('delete-account/', DeleteAccountView.as_view(), name='delete-account'),
   
]
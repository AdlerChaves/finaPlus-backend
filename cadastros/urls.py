from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CustomerViewSet, SupplierViewSet

router = DefaultRouter()
router.register(r'customers', CustomerViewSet, basename='customer')
router.register(r'suppliers', SupplierViewSet, basename='supplier')

urlpatterns = [
    path('', include(router.urls)),
]
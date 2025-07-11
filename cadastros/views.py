from rest_framework import viewsets, permissions
from .models import Customer, Supplier
from .serializers import CustomerSerializer, SupplierSerializer

class CustomerViewSet(viewsets.ModelViewSet):
    """
    API endpoint que permite que clientes sejam visualizados ou editados.
    """
    serializer_class = CustomerSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Garante que o usuário só possa ver os clientes da sua própria empresa.
        """
        return Customer.objects.filter(company=self.request.user.company)

    def perform_create(self, serializer):
        """
        Associa automaticamente a empresa e o usuário ao criar um novo cliente.
        """
        serializer.save(
            company=self.request.user.company,
            user=self.request.user
        )

class SupplierViewSet(viewsets.ModelViewSet):
    """
    API endpoint para visualizar e editar Fornecedores.
    """
    serializer_class = SupplierSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Filtra os fornecedores para mostrar apenas os da empresa do usuário logado.
        """
        return Supplier.objects.filter(company=self.request.user.company)

    def perform_create(self, serializer):
        """
        Associa automaticamente a empresa e o usuário ao criar um novo fornecedor.
        """
        serializer.save(
            company=self.request.user.company,
            user=self.request.user
        )
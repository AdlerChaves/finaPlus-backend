from rest_framework import generics
from .models import User
from .serializers import UserSerializer

# Este view vai lidar com a criação (POST) de novos usuários/empresas
class UserCreateView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
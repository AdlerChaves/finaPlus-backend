from django.contrib.auth.models import Group, User
from rest_framework import generics, viewsets, permissions, status
from rest_framework.response import Response
from .models import User
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser
from .serializers import UserSerializer, CompanyUserSerializer, CurrentUserSerializer, GroupSerializer
from rest_framework_simplejwt.views import TokenObtainPairView


# --------------------------------------------------------------------------
# CÓDIGO NOVO - Adicione esta classe para o Login com Cookies
# --------------------------------------------------------------------------
class MyTokenObtainPairView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            access_token = response.data.pop('access')
            refresh_token = response.data.pop('refresh')

            cookie_response = Response(response.data)
            
            cookie_response.set_cookie(
                'access_token',
                access_token,
                httponly=True,
                samesite='Lax',
                # secure=True, # Lembre-se de descomentar em produção (HTTPS)
            )
            cookie_response.set_cookie(
                'refresh_token',
                refresh_token,
                httponly=True,
                samesite='Lax',
                # secure=True, # Lembre-se de descomentar em produção (HTTPS)
            )
            return cookie_response
        
        return response

# --------------------------------------------------------------------------
# CÓDIGO NOVO - Adicione esta classe para o Logout
# --------------------------------------------------------------------------
class LogoutView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        response = Response({"detail": "Logout realizado com sucesso."}, status=status.HTTP_200_OK)
        # Apaga os cookies de autenticação
        response.delete_cookie('access_token')
        response.delete_cookie('refresh_token')
        return response

# --------------------------------------------------------------------------
# SEU CÓDIGO EXISTENTE - Nenhuma alteração necessária aqui
# --------------------------------------------------------------------------
class UserCreateView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

class CompanyUserViewSet(viewsets.ModelViewSet):
    """
    API endpoint para gerir os usuários de uma empresa.
    """
    serializer_class = CompanyUserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return User.objects.filter(company=self.request.user.company)

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)

class CurrentUserView(generics.RetrieveAPIView):
    """
    Retorna os dados do usuário autenticado.
    """
    serializer_class = CurrentUserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user
    

class GroupViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint que permite que grupos sejam visualizados.
    """
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    # Apenas administradores podem ver a lista de grupos
    permission_classes = [IsAdminUser]

# ViewSet para gerenciar usuários
class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint para visualizar usuários e gerenciar seus grupos.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    # Apenas administradores podem gerenciar usuários
    permission_classes = [IsAdminUser]

    # Esta é a ação customizada para atualizar os grupos
    @action(detail=True, methods=['post'])
    def update_groups(self, request, pk=None):
        user = self.get_object() # Pega o usuário (ex: /api/users/5/)
        
        # Pega os IDs dos grupos enviados no corpo da requisição
        group_ids = request.data.get('groups', [])
        
        # Limpa os grupos atuais do usuário
        user.groups.clear()
        
        # Adiciona os novos grupos
        for group_id in group_ids:
            try:
                group = Group.objects.get(id=group_id)
                user.groups.add(group)
            except Group.DoesNotExist:
                # Ignora se um ID de grupo inválido for enviado
                pass
        
        # Retorna os dados atualizados do usuário
        serializer = self.get_serializer(user)
        return Response(serializer.data)
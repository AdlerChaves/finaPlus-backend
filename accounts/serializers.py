from django.contrib.auth.models import Group, User
from rest_framework import serializers
from .models import User, Company
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.db import transaction  

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.username
        return token

    def validate(self, attrs):
        # Verifica se a chave 'email' foi enviada na requisição
        if 'email' in attrs:
            # Renomeia a chave 'email' para 'username'
            attrs['username'] = attrs.pop('email')
        
        # Chama o método de validação da classe pai com os dados ajustados
        data = super().validate(attrs)
        
        return data

class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ['id', 'name', 'cnpj', 'business_area']

       
class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['id', 'name']

class UserSerializer(serializers.ModelSerializer):
    company = CompanySerializer()
    groups = GroupSerializer(many=True, read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'email', 'password', 'company', 'first_name', 'last_name', 'phone', 'groups']
        extra_kwargs = {
            'password': {'write_only': True, 'style': {'input_type': 'password'}},
        }

    def create(self, validated_data):
        company_data = validated_data.pop('company')
        groups_data = validated_data.pop('groups', [])
        cnpj = company_data.get('cnpj')
        
        if cnpj and Company.objects.filter(cnpj=cnpj).exists():
            raise serializers.ValidationError({
                "company": {"cnpj": ["Uma empresa com este CNPJ já foi cadastrada."]}
            })

        company = Company.objects.create(**company_data)
        
        # Usamos o email como username e passamos os novos campos
        user = User.objects.create_user(
            username=validated_data['email'], # Usar email como username
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            phone=validated_data.get('phone', ''),
            company=company,
            permissions_list=["pagamentos", "movimentacoes", "relatorios", "cadastros", "contas", "configuracoes", "dashboard"],
        )

        # Adiciona o usuário ao grupo 'Administrador' por padrão
        # Se o grupo não existir, ele será criado
        admin_group, _ = Group.objects.get_or_create(name='Administrador')
        user.groups.add(admin_group)
        
        return user 

    

class CompanyUserSerializer(serializers.ModelSerializer):
    """
    Serializer para um admin criar e gerir usuários dentro da sua própria empresa.
    """
    # Campo para receber os IDs dos grupos durante a criação/edição.
    groups = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Group.objects.all(),
        required=False 
    )
    # Senha é apenas para escrita e obrigatória na criação.
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    class Meta:
        model = User
        # Os campos que o frontend vai enviar
        fields = [
            'id', 'username', 'first_name', 'last_name', 'email', 
            'is_active', 'password', 'groups'
        ]
        # Username é gerado a partir do email, então é apenas de leitura na resposta.
        read_only_fields = ['username']

    def create(self, validated_data):
        # Remove os grupos dos dados validados para tratar separadamente.
        groups_data = validated_data.pop('groups', [])
        
        # Define o username como o email (uma prática comum e segura).
        validated_data['username'] = validated_data.get('email')
        
        # Usa create_user para garantir que a senha seja criptografada corretamente.
        user = User.objects.create_user(**validated_data)
        
        # Associa os grupos ao usuário recém-criado.
        if groups_data:
            user.groups.set(groups_data)
            
        return user
    
    def update(self, instance, validated_data):
        # Remove os grupos para tratá-los separadamente
        groups_data = validated_data.pop('groups', None)

        # Atualiza a senha apenas se uma nova for fornecida
        password = validated_data.pop('password', None)
        if password:
            instance.set_password(password)

        # Atualiza os outros campos do usuário
        instance = super().update(instance, validated_data)

        # Atualiza os grupos se eles foram enviados na requisição
        if groups_data is not None:
            instance.groups.set(groups_data)
            
        instance.save()
        return instance
    


class CurrentUserSerializer(serializers.ModelSerializer):
    """
    Serializer para os dados do usuário logado (endpoint /me/).
    """
    class Meta:
        model = User
        fields = [
            'id', 'first_name', 'last_name', 'email', 'phone', 'role', 'permissions_list', 
            'theme', 'currency', 'language', 'notify_weekly_goals', 
            'notify_large_transactions', 'notify_bills_reminder'
        ]

    def update(self, instance, validated_data):
        # Pega o número de telemóvel dos dados validados, se existir
        phone_number = validated_data.get('phone')

        # Se um número de telemóvel foi enviado e não está vazio...
        if phone_number:
            # Garante que o número comece com +55
            if not phone_number.startswith('+55'):
                validated_data['phone'] = f"+55{phone_number}"
        
        # Continua com o processo de atualização normal
        return super().update(instance, validated_data)

class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer para a troca de senha do usuário.
    """
    current_password = serializers.CharField(style={"input_type": "password"}, required=True)
    new_password = serializers.CharField(style={"input_type": "password"}, required=True)

    def validate_current_password(self, value):
        if not self.context['request'].user.check_password(value):
            raise serializers.ValidationError("A senha atual está incorreta.")
        return value

    def validate_new_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError("A nova senha deve ter pelo menos 8 caracteres.")
        # Você pode adicionar mais validações aqui (ex: complexidade)
        return value


from django.contrib.auth.models import Group, User
from rest_framework import serializers
from .models import User, Company

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
    username = serializers.CharField(read_only=True)
    groups = GroupSerializer(many=True, read_only=True)
    
    groups_to_add = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Group.objects.all(),
        write_only=True,
        required=False,
        source='groups' 
    )

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'company', 'groups', 'groups_to_add'] ### ADICIONADO 'groups_to_add'
        extra_kwargs = {
            'password': {'write_only': True, 'style': {'input_type': 'password'}},
            'email': {
                'required': True,
                'error_messages': {
                    'unique': "Este endereço de e-mail já está em uso.",
                    'invalid': "Por favor, insira um endereço de e-mail válido."
                }
            }
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

        user = User.objects.create_user(
            username=validated_data['email'],
            email=validated_data['email'],
            password=validated_data['password'],
            company=company
        )
        
        if groups_data:
            user.groups.set(groups_data)
            
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
            'id', 'first_name', 'last_name', 'email', 'role', 'permissions_list', 'theme', 'currency', 'language',
            'notify_weekly_goals', 'notify_large_transactions', 'notify_bills_reminder'
       
        ]

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


from rest_framework import serializers
from .models import User, Company

class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ['id', 'name', 'cnpj', 'business_area']

class UserSerializer(serializers.ModelSerializer):
    company = CompanySerializer()
    username = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'company']
        extra_kwargs = {
            'password': {'write_only': True, 'style': {'input_type': 'password'}},
            # Adicionamos a validação de e-mail aqui
            'email': {
                'required': True,
                'error_messages': {
                    'unique': "Este endereço de e-mail já está em uso.",
                    'invalid': "Por favor, insira um endereço de e-mail válido."
                }
            }
        }

    # O método 'create' permanece o mesmo
    def create(self, validated_data):
        company_data = validated_data.pop('company')
        
        # --- LÓGICA DE VALIDAÇÃO CUSTOMIZADA PARA CNPJ ---
        # Verificamos manualmente se o CNPJ já existe para fornecer uma mensagem customizada.
        cnpj = company_data.get('cnpj')
        if cnpj and Company.objects.filter(cnpj=cnpj).exists():
            # Usamos 'raise serializers.ValidationError' para retornar um erro 400 limpo.
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
        return user

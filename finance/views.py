from django.db.models import ProtectedError
from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Category, BankAccount, Transaction, CreditCard
from .serializers import CategorySerializer, BankAccountSerializer, TransactionSerializer, CreditCardSerializer

class CategoryViewSet(viewsets.ModelViewSet):
    """
    API endpoint que permite que as categorias sejam visualizadas ou editadas.
    AGORA SUPORTA FILTRO POR TIPO (entrada/saida).
    """
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Esta view agora filtra as categorias por tipo se o parâmetro 'type' for fornecido.
        Ex: /api/finance/categories/?type=saida
        """
        user = self.request.user
        queryset = Category.objects.filter(company=user.company)
        
        # --- LÓGICA DE FILTRO ADICIONADA AQUI ---
        category_type = self.request.query_params.get('type')
        if category_type:
            queryset = queryset.filter(type=category_type)
        
        return queryset

    def perform_create(self, serializer):
        """
        Associa a categoria à empresa do usuário ao criar.
        """
        serializer.save(company=self.request.user.company)



class BankAccountViewSet(viewsets.ModelViewSet):
    serializer_class = BankAccountSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return BankAccount.objects.filter(company=self.request.user.company)

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)

    # --- MÉTODO DE EXCLUSÃO CUSTOMIZADO ADICIONADO AQUI ---
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            # Tenta deletar o objeto normalmente
            self.perform_destroy(instance)
            # Se a exclusão for bem-sucedida, retorna a resposta padrão 204
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ProtectedError:
            # Se um ProtectedError for capturado, retorna um erro 400 com uma mensagem clara
            return Response(
                {"detail": "Esta conta não pode ser excluída pois possui transações ou cartões de crédito associados a ela."},
                status=status.HTTP_400_BAD_REQUEST
            )
class TransactionViewSet(viewsets.ModelViewSet):
    """
    API endpoint para visualizar e editar transações.
    """
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # ... (esta função não precisa de alterações) ...
        user = self.request.user
        queryset = Transaction.objects.filter(company=user.company)
        transaction_type = self.request.query_params.get('type')
        if transaction_type:
            queryset = queryset.filter(type=transaction_type)
        return queryset

    def perform_create(self, serializer):
        """
        Garante que a criação da transação e a atualização do saldo da conta
        aconteçam de forma segura e atómica.
        """
        # 'atomic' garante que se algo falhar, tudo é desfeito.
        with transaction.atomic():
            # 1. Salva a nova transação e a associa ao usuário/empresa
            new_transaction = serializer.save(
                company=self.request.user.company, 
                user=self.request.user
            )

            # 2. Pega a conta bancária associada à transação
            bank_account = new_transaction.bank_account
            
            # --- A LÓGICA CHAVE ESTÁ AQUI ---
            # 3. Verifica o tipo da transação e atualiza o saldo
            if new_transaction.type == 'saida':
                bank_account.initial_balance -= new_transaction.amount # Subtrai se for saída
            elif new_transaction.type == 'entrada':
                bank_account.initial_balance += new_transaction.amount # SOMA se for entrada
            
            # 4. Salva a conta bancária com o novo saldo atualizado
            bank_account.save()

class CreditCardViewSet(viewsets.ModelViewSet):
    """
    API endpoint para gerenciar cartões de crédito.
    """
    serializer_class = CreditCardSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CreditCard.objects.filter(company=self.request.user.company)

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)
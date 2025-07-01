from rest_framework.decorators import action
from decimal import Decimal
from rest_framework.views import APIView
from django.db.models import ProtectedError
from django.db import models
from django.utils import timezone
from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Category, BankAccount, Transaction, CreditCard, Payable
from .serializers import CategorySerializer, BankAccountSerializer, TransactionSerializer, CreditCardSerializer, PayableSerializer
from dateutil.relativedelta import relativedelta

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

class PayableViewSet(viewsets.ModelViewSet):
    serializer_class = PayableSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # ... (sua lógica de get_queryset permanece a mesma) ...
        return Payable.objects.filter(company=self.request.user.company)

    def perform_create(self, serializer):
        # ... (sua lógica de perform_create permanece a mesma) ...
        serializer.save(company=self.request.user.company, user=self.request.user)

# --- NOVA VIEW DEDICADA PARA MARCAR COMO PAGO ---
class MarkAsPaidView(APIView):
    """
    View específica para marcar uma conta a pagar como paga.
    Agora aceita bank_account_id, payment_date e amount.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, format=None):
        company = request.user.company
        try:
            payable = Payable.objects.get(pk=pk, company=company)
        except Payable.DoesNotExist:
            return Response({'error': 'Conta a pagar não encontrada.'}, status=status.HTTP_404_NOT_FOUND)

        if payable.status == 'pago':
            return Response({'error': 'Esta conta já foi marcada como paga.'}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Captura os novos dados da requisição
        bank_account_id = request.data.get('bank_account_id')
        payment_date_str = request.data.get('payment_date')
        paid_amount_str = request.data.get('amount')

        if not all([bank_account_id, payment_date_str, paid_amount_str]):
            return Response({'error': 'Conta bancária, data e valor do pagamento são obrigatórios.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            bank_account = BankAccount.objects.get(id=bank_account_id, company=company)
            paid_amount = Decimal(paid_amount_str)
            payment_date = timezone.datetime.strptime(payment_date_str, '%Y-%m-%d').date()
        except (BankAccount.DoesNotExist, InvalidOperation, ValueError):
            return Response({'error': 'Dados inválidos fornecidos.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Lógica de negócio: por enquanto, consideramos o pagamento integral.
        if paid_amount != payable.amount:
            return Response({'error': 'Pagamento parcial ainda não implementado. O valor pago deve ser igual ao valor da conta.'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            # 2. Atualiza a conta a pagar com os dados recebidos
            payable.status = 'pago'
            payable.payment_date = payment_date
            payable.paid_from_account = bank_account
            payable.save()

            # 3. Cria a transação de saída com o valor e data corretos
            Transaction.objects.create(
                company=company,
                user=request.user,
                description=f"Pagamento: {payable.description}",
                amount=paid_amount, # Usa o valor pago
                transaction_date=payment_date, # Usa a data do pagamento
                type='saida',
                category=payable.category,
                bank_account=bank_account
            )

            # 4. Subtrai o valor do saldo da conta bancária
            bank_account.initial_balance -= paid_amount
            bank_account.save()

        return Response({'success': 'Conta marcada como paga com sucesso.'}, status=status.HTTP_200_OK)

    



class CreateCardExpenseView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        data = request.data
        user = request.user
        company = user.company

        # --- Validação dos campos obrigatórios ---
        required_fields = ['description', 'amount', 'transaction_date', 'credit_card_id', 'installments', 'category_id']
        if not all(field in data for field in required_fields):
            return Response({"error": "Campos obrigatórios ausentes."}, status=status.HTTP_400_BAD_REQUEST)

        # --- Bloco TRY...EXCEPT MELHORADO ---
        try:
            total_amount = Decimal(data['amount'])
            installments = int(data['installments'])
            if installments < 1:
                return Response({"error": "O número de parcelas deve ser ao menos 1."}, status=status.HTTP_400_BAD_REQUEST)
            
            credit_card = CreditCard.objects.get(id=data['credit_card_id'], company=company)
            category = Category.objects.get(id=data['category_id'], company=company, type='saida')
            purchase_date = timezone.datetime.strptime(data['transaction_date'], '%Y-%m-%d').date()

        except CreditCard.DoesNotExist:
            return Response({"error": "O cartão de crédito selecionado não foi encontrado."}, status=status.HTTP_400_BAD_REQUEST)
        except Category.DoesNotExist:
            return Response({"error": "A categoria selecionada não foi encontrada ou não é uma categoria de saída."}, status=status.HTTP_400_BAD_REQUEST)
        except (ValueError, TypeError, InvalidOperation):
            # Captura erros de conversão de data, número de parcelas ou valor
            return Response({"error": "Verifique os valores de data, valor e parcelas. Eles parecem ser inválidos."}, status=status.HTTP_400_BAD_REQUEST)
        
        
        # --- Lógica de Negócios ---
        with transaction.atomic():
            # 1. Cria a transação única com o valor total
            main_transaction = Transaction.objects.create(
                company=company,
                user=user,
                description=data['description'],
                amount=total_amount,
                transaction_date=purchase_date,
                type='saida',
                category=category,
                bank_account=credit_card.associated_account,
                credit_card=credit_card
            )

            # 2. Calcula as parcelas
            installment_amount = total_amount / installments

            # 3. Calcula a data de vencimento da primeira fatura
            first_due_date = purchase_date
            # Se a compra foi feita no dia do fechamento ou depois, a fatura é no próximo mês
            if purchase_date.day >= credit_card.closing_day:
                first_due_date += relativedelta(months=1)
            
            # Ajusta o dia do vencimento
            first_due_date = first_due_date.replace(day=credit_card.due_day)

            # 4. Cria uma conta a pagar para cada parcela
            for i in range(installments):
                due_date = first_due_date + relativedelta(months=i)
                Payable.objects.create(
                    company=company,
                    user=user,
                    transaction=main_transaction, # Link para a transação principal
                    description=f"{data['description']} ({i+1}/{installments})",
                    amount=installment_amount,
                    due_date=due_date,
                    category=category,
                    status='pendente'
                )
        
        return Response({"success": f"{installments} parcelas criadas com sucesso."}, status=status.HTTP_201_CREATED)
    
class CardStatementView(APIView):
    """
    View para buscar e calcular a fatura de um cartão de crédito
    para um determinado mês e ano.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        card_id = request.query_params.get('card_id')
        month = request.query_params.get('month')
        year = request.query_params.get('year')

        if not all([card_id, month, year]):
            return Response({'error': 'card_id, month e year são obrigatórios.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            card = CreditCard.objects.get(id=card_id, company=request.user.company)
            month = int(month)
            year = int(year)
        except (CreditCard.DoesNotExist, ValueError):
            return Response({'error': 'Dados inválidos ou cartão não encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        # --- Lógica de Cálculo do Período da Fatura ---
        closing_day = card.closing_day

        # Define o fim do período da fatura
        end_date = timezone.datetime(year, month, closing_day).date()
        # O início do período é no mês anterior
        start_date = end_date - relativedelta(months=1)
        # Ajusta para o dia seguinte ao fechamento anterior
        start_date += relativedelta(days=1)
        
        # --- Busca as transações ---
        transactions_in_statement = Transaction.objects.filter(
            company=request.user.company,
            credit_card_id=card_id,
            transaction_date__range=[start_date, end_date]
        )

        # Calcula o total
        total_amount = transactions_in_statement.aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')

        # Serializa os dados para a resposta
        serializer = TransactionSerializer(transactions_in_statement, many=True)

        # Monta a resposta final
        response_data = {
            'card_name': card.name,
            'due_day': card.due_day,
            'closing_day': card.closing_day,
            'statement_period': {
                'start': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d'),
            },
            'total_amount': total_amount,
            'transactions': serializer.data
        }

        return Response(response_data, status=status.HTTP_200_OK)
    

class CardBillView(APIView):
    """
    View para calcular e retornar o valor total da fatura de um cartão
    de crédito para um determinado mês e ano.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        card_id = request.query_params.get('card_id')
        month = request.query_params.get('month')
        year = request.query_params.get('year')

        if not all([card_id, month, year]):
            return Response(
                {'error': 'card_id, month e year são parâmetros obrigatórios.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            card = CreditCard.objects.get(id=card_id, company=request.user.company)
            month = int(month)
            year = int(year)
        except (CreditCard.DoesNotExist, ValueError):
            return Response({'error': 'Dados inválidos ou cartão não encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        # Filtra as contas a pagar (parcelas) pela data de vencimento e pelo cartão
        # Esta é a lógica central
        bill_items = Payable.objects.filter(
            company=request.user.company,
            transaction__credit_card=card, # Filtra pelas parcelas do cartão correto
            due_date__year=year,           # Filtra pelo ano de vencimento
            due_date__month=month          # Filtra pelo mês de vencimento
        )

        # Calcula o total da fatura somando o valor de cada parcela
        total_amount = bill_items.aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')

        # Monta a resposta final
        response_data = {
            'card_name': card.name,
            'bill_date': f"{month:02d}/{year}",
            'due_date': f"{card.due_day:02d}/{month:02d}/{year}",
            'total_amount': total_amount,
            'item_count': bill_items.count(),
            'items': PayableSerializer(bill_items, many=True).data # Lista de parcelas
        }

        return Response(response_data, status=status.HTTP_200_OK)
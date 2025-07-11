from rest_framework.decorators import action
from django.db.models import Sum, Q
from decimal import Decimal, InvalidOperation   
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
    
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Esta view agora filtra as categorias por tipo se o parâmetro 'type' for fornecido.
        Ex: /api/finance/categories/?type=saida
        """
        user = self.request.user
        queryset = Category.objects.filter(company=user.company)
        
        category_type = self.request.query_params.get('type')
        if category_type:
            queryset = queryset.filter(type=category_type)
        
        return queryset

    def perform_create(self, serializer):
        """
        CORREÇÃO: Associa tanto o usuário quanto a empresa à nova categoria.
        """
        serializer.save(user=self.request.user, company=self.request.user.company)




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
        user = self.request.user
        queryset = Transaction.objects.filter(company=user.company)

        transaction_type_filter = self.request.query_params.get('type')
        if transaction_type_filter:
            # A correção é usar o nome correto do campo do modelo: 'type'
            queryset = queryset.filter(type=transaction_type_filter)

        # Lógica de filtro por data (se você já a implementou)
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')

        if start_date and end_date:
            queryset = queryset.filter(transaction_date__range=[start_date, end_date])

        return queryset

    def perform_create(self, serializer):
        
        with transaction.atomic():
            
            new_transaction = serializer.save(
                company=self.request.user.company, 
                user=self.request.user
            )

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
    """
    ViewSet para gerenciar contas a pagar (Payables).
    """
    queryset = Payable.objects.all()
    serializer_class = PayableSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Sobrescreve o método get_queryset para filtrar as contas
        pela empresa do usuário logado e, opcionalmente, por mês e ano.
        """
        # Filtra pela empresa do usuário
        queryset = Payable.objects.filter(company=self.request.user.company)

        month = self.request.query_params.get('month', None)
        year = self.request.query_params.get('year', None)

        if month is not None and year is not None:
            try:
                month = int(month)
                year = int(year)
                # Filtra apenas as contas manuais (sem transação de cartão)
                queryset = queryset.filter(
                    due_date__year=year,
                    due_date__month=month,
                    transaction__isnull=True
                )
            except (ValueError, TypeError):
                pass
        
        # A função get_queryset DEVE retornar o queryset
        return queryset.order_by('due_date')

    def perform_create(self, serializer):
        
        serializer.save(company=self.request.user.company)
        serializer.save(user=self.request.user)

class MarkAsPaidView(APIView):
    """
    View específica para marcar uma conta a pagar como paga.
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
        
        # Pagamento parcial não é permitido por enquanto
        if paid_amount != payable.amount:
            return Response({'error': 'O valor pago deve ser igual ao valor da conta.'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            # Atualiza a conta a pagar
            payable.status = 'pago'
            payable.save()

            Transaction.objects.create( 
                company=company,
                description=f"Pagamento: {payable.description}",
                amount=paid_amount,
                transaction_date=payment_date,
                type='saida', 
                bank_account=bank_account
                
            )

        return Response({'success': 'Conta marcada como paga com sucesso.'}, status=status.HTTP_200_OK)

    



class CreateCardExpenseView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        company = request.user.company
        description = request.data.get('description')
        amount_str = request.data.get('amount')
        installments = int(request.data.get('installments', 1))
        credit_card_id = request.data.get('credit_card_id')
        category_id = request.data.get('category_id')
        transaction_date_str = request.data.get('transaction_date')

        # Validações de entrada
        if not all([description, amount_str, credit_card_id, category_id, transaction_date_str]):
            return Response({'error': 'Todos os campos são obrigatórios'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            amount = Decimal(amount_str)
            credit_card = CreditCard.objects.get(id=credit_card_id, company=company)
            category = Category.objects.get(id=category_id, company=company)
            transaction_date = timezone.datetime.strptime(transaction_date_str, '%Y-%m-%d').date()
        except (CreditCard.DoesNotExist, Category.DoesNotExist):
            return Response({'error': 'Cartão de crédito ou categoria não encontrados.'}, status=status.HTTP_404_NOT_FOUND)
        except (InvalidOperation, ValueError):
            return Response({'error': 'Dados inválidos.'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            # Cria a transação principal (a compra original)
            # --- BLOCO CORRIGIDO ---
            main_transaction = Transaction.objects.create(
                user=request.user, 
                company=company,
                description=f"{description} (Compra Original)",
                amount=amount,
                transaction_date=transaction_date,
                type='saida', 
                credit_card=credit_card
                # Os campos 'user' e 'category' foram removidos pois não pertencem ao modelo Transaction
            )

            # Cria as parcelas (Payable)
            installment_amount = amount / installments
            for i in range(1, installments + 1):
                due_date = transaction_date + relativedelta(months=i)
                Payable.objects.create(
                    user=request.user,
                    company=company,
                    transaction=main_transaction,
                    description=f"{description} ({i}/{installments})",
                    amount=installment_amount,
                    due_date=due_date,
                    status='pendente',
                    category=category
                )

        return Response({'success': 'Despesa registrada e parcelas criadas com sucesso!'}, status=status.HTTP_201_CREATED)
    
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
    
class MonthlyBillsView(APIView):
    """
    View para buscar e agrupar todas as contas a pagar de um mês,
    separando contas manuais e faturas de cartão com status de pagamento correto
    (Pendente, Pago, Vencido).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        month_str = request.query_params.get('month')
        year_str = request.query_params.get('year')

        if not all([month_str, year_str]):
            return Response({'error': 'Mês e ano são obrigatórios.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            month = int(month_str)
            year = int(year_str)
        except ValueError:
            return Response({'error': 'Mês e ano devem ser números.'}, status=status.HTTP_400_BAD_REQUEST)

        today = timezone.now().date()

        # 1. Processa as contas manuais
        manual_bills_qs = Payable.objects.filter(
            company=request.user.company,
            due_date__year=year,
            due_date__month=month,
            transaction__isnull=True
        )
        
        # Serializa e depois ajusta o status
        manual_bills_data = PayableSerializer(manual_bills_qs, many=True).data
        for bill in manual_bills_data:
            due_date = timezone.datetime.strptime(bill['due_date'], '%Y-%m-%d').date()
            if bill['status'] != 'pago' and due_date < today:
                bill['status'] = 'vencido'

        # 2. Lógica aprimorada para faturas de cartão
        card_bills_data = []
        active_cards = CreditCard.objects.filter(company=request.user.company, is_active=True)

        for card in active_cards:
            payables_for_month = Payable.objects.filter(
                company=request.user.company,
                transaction__credit_card=card,
                due_date__year=year,
                due_date__month=month
            )

            if payables_for_month.exists():
                total_amount = payables_for_month.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
                
                # --- LÓGICA DO STATUS (PAGO, VENCIDO, PENDENTE) ---
                payment_status = ''
                all_items_paid = all(p.status == 'pago' for p in payables_for_month)
                
                if all_items_paid:
                    payment_status = 'pago'
                else:
                    # Se não está paga, verifica se está vencida
                    card_due_date = timezone.datetime(year, month, card.due_day).date()
                    if card_due_date < today:
                        payment_status = 'vencido'
                    else:
                        payment_status = 'pendente'

                card_bills_data.append({
                    "card_id": card.id,
                    "card_name": card.name,
                    "due_day": card.due_day,
                    "total_amount": total_amount,
                    "status": payment_status
                })

        # 3. Formata a resposta final
        response_data = {
            "manual_bills": manual_bills_data,
            "card_bills": card_bills_data
        }

        return Response(response_data, status=status.HTTP_200_OK)
    
class CardBillDetailView(APIView):
    """
    View para obter os detalhes completos de uma fatura de cartão de crédito
    para um mês e ano específicos.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        card_id = request.query_params.get('card_id')
        month_str = request.query_params.get('month')
        year_str = request.query_params.get('year')

        if not all([card_id, month_str, year_str]):
            return Response(
                {'error': 'Os parâmetros card_id, month e year são obrigatórios.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            card = CreditCard.objects.get(id=card_id, company=request.user.company)
            month = int(month_str)
            year = int(year_str)
        except (CreditCard.DoesNotExist, ValueError):
            return Response({'error': 'Dados inválidos ou cartão não encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        # Busca apenas as parcelas (Payable) com vencimento no mês e ano da fatura.
        bill_items = Payable.objects.filter(
            company=request.user.company,
            transaction__credit_card=card,
            due_date__year=year,
            due_date__month=month
        ).select_related('transaction', 'category').order_by('due_date')

        # Calcula o total da fatura
        total_amount = bill_items.aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')

        # Lógica para status e valor pago da fatura
        # Uma fatura é 'paga' se todas as suas parcelas daquele mês estiverem pagas.
        bill_status = 'pago' if bill_items.exists() and all(item.status == 'pago' for item in bill_items) else 'pendente'
        paid_amount = sum(item.amount for item in bill_items if item.status == 'pago')

        # Monta a resposta final
        response_data = {
            'card_name': f"{card.name} (final {card.last_digits})",
            'bill_period': f"{month:02d}/{year}",
            'due_date': f"{card.due_day:02d}/{month:02d}/{year}",
            'total_amount': total_amount,
            'paid_amount': paid_amount,
            'status': bill_status,
            'transactions': PayableSerializer(bill_items, many=True).data,
            # A chave 'installments' agora retorna os mesmos itens da fatura,
            # garantindo que apenas as parcelas do mês sejam exibidas.
            'installments': PayableSerializer(bill_items, many=True).data
        }

        return Response(response_data, status=status.HTTP_200_OK)
    

class PayCardBillView(APIView):
    """
    Endpoint para registrar o pagamento de uma fatura de cartão de crédito.
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        card_id = request.data.get('card_id')
        month_str = request.data.get('month') # Renomeado para indicar que é string
        year_str = request.data.get('year')   # Renomeado para indicar que é string
        bank_account_id = request.data.get('bank_account_id')
        amount_paid = request.data.get('amount')
        payment_date = request.data.get('payment_date')

        if not all([card_id, month_str, year_str, bank_account_id, amount_paid, payment_date]):
            return Response(
                {'error': 'Todos os campos são obrigatórios.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # --- LINHAS CORRIGIDAS ABAIXO ---
            month = int(month_str)
            year = int(year_str)
            card = CreditCard.objects.get(id=card_id, company=request.user.company)
            bank_account = BankAccount.objects.get(id=bank_account_id, company=request.user.company)
            amount_paid_decimal = Decimal(amount_paid)
        except (CreditCard.DoesNotExist, BankAccount.DoesNotExist):
            return Response({'error': 'Cartão ou conta bancária não encontrados.'}, status=status.HTTP_404_NOT_FOUND)
        except (InvalidOperation, ValueError): # Adicionado ValueError para capturar erro de conversão
            return Response({'error': 'Dados de entrada inválidos (valor, mês ou ano).'}, status=status.HTTP_400_BAD_REQUEST)

        # Encontra todas as parcelas (Payable) que compõem a fatura
        payables_to_update = Payable.objects.filter(
            company=request.user.company,
            transaction__credit_card=card,
            due_date__year=year,
            due_date__month=month,
            status__in=['pendente', 'vencido']
        )

        if not payables_to_update.exists():
            return Response({'error': 'Não há faturas pendentes para este período.'}, status=status.HTTP_400_BAD_REQUEST)

        Transaction.objects.create(
            user=request.user,
            company=request.user.company,
            bank_account=bank_account,
            description=f"Pagamento Fatura {card.name} - {month:02d}/{year}",
            amount=amount_paid_decimal,
            type='saida',
            transaction_date=payment_date
        )
        
        payables_to_update.update(status='pago')

        return Response({'success': 'Fatura paga com sucesso!'}, status=status.HTTP_200_OK)
    

    
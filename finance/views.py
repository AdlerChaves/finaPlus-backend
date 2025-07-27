from rest_framework.decorators import action
from django.db.models import Sum, Q
from decimal import Decimal, InvalidOperation  
from datetime import timedelta 
from rest_framework.views import APIView
from django.db.models import ProtectedError
from django.db import models
from django.utils import timezone
from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Category, BankAccount, Transaction, CreditCard, Payable, Receivable
from .serializers import CategorySerializer, BankAccountSerializer, TransactionSerializer, CreditCardSerializer, PayableSerializer, ReceivableSerializer
from dateutil.relativedelta import relativedelta
from django.db.models.functions import TruncMonth
from accounts.permissions import CanEditFinance, CanViewFinance

class CategoryViewSet(viewsets.ModelViewSet):
    
    serializer_class = CategorySerializer
    permission_classes = [CanEditFinance]

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
    permission_classes = [CanEditFinance]

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
    permission_classes = [CanEditFinance]


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
    permission_classes = [CanEditFinance]

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
                user=request.user,
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
    


class ReceivableViewSet(viewsets.ModelViewSet):
    """
    API endpoint para visualizar e gerenciar Contas a Receber.
    """
    serializer_class = ReceivableSerializer
    permission_classes = [IsAuthenticated]

    # --- MÉTODO A SER SUBSTITUÍDO ---
    def get_queryset(self):
        """
        Filtra as contas a receber pela empresa do usuário
        e aplica filtros de query params.
        """
        user = self.request.user
        queryset = Receivable.objects.filter(company=user.company).select_related('customer')

        # --- INÍCIO DA CORREÇÃO ---
        # Adicionada a lógica para o filtro por período (mês/ano)
        period = self.request.query_params.get('period-filter')
        if period:
            try:
                year, month = map(int, period.split('-'))
                queryset = queryset.filter(due_date__year=year, due_date__month=month)
            except (ValueError, TypeError):
                # Ignora o filtro se o formato for inválido
                pass
        # --- FIM DA CORREÇÃO ---

        # Filtro por status (lógica existente mantida)
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)

        # Filtro por cliente (lógica existente mantida)
        customer_id = self.request.query_params.get('client_id')
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
        
        # Filtro de busca (lógica existente mantida)
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(description__icontains=search) |
                Q(customer__name__icontains=search)
            )

        return queryset.order_by('due_date')
    

class ReceivablesSummaryView(APIView):
    """
    View para fornecer um resumo dos dados de Contas a Receber.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        company = request.user.company
        queryset = Receivable.objects.filter(company=company)

        # Aplica os mesmos filtros da sua lista principal
        period = request.query_params.get('period-filter')
        if period:
            year, month = map(int, period.split('-'))
            queryset = queryset.filter(due_date__year=year, due_date__month=month)

        # --- CORREÇÃO AQUI ---
        # A variável foi renomeada de 'status' para 'status_filter'
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        customer_id = request.query_params.get('client_id')
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)

        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(description__icontains=search) | Q(customer__name__icontains=search)
            )

        # Calcula os totais
        total_received = queryset.filter(status='received').aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        total_to_receive_qs = queryset.filter(status__in=['pending', 'overdue'])
        total_to_receive = total_to_receive_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        # Dados para o gráfico
        summary_by_status = queryset.values('status').annotate(total_amount=Sum('amount')).order_by('status')
        chart_data = {'labels': [], 'data': []}
        status_map = {'pending': 'Pendente', 'received': 'Recebido', 'overdue': 'Vencido'}

        for item in summary_by_status:
            chart_data['labels'].append(status_map.get(item['status'], item['status']))
            chart_data['data'].append(item['total_amount'])

        response_data = {
            'total_received': total_received,
            'total_to_receive': total_to_receive,
            'chart_data': chart_data
        }

        # Agora 'status' refere-se corretamente ao módulo importado
        return Response(response_data, status=status.HTTP_200_OK)
    

class DashboardView(APIView):
    
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        company = request.user.company
        today = timezone.now().date()
        
        # --- 1. Cálculos para os Cartões de Resumo ---

        balance_data = BankAccount.objects.filter(company=company, is_active=True).aggregate(
            total_balance=Sum('initial_balance')
        )
        current_balance = balance_data['total_balance'] or Decimal('0.00')

        start_of_month = today.replace(day=1)
        
        monthly_income_data = Transaction.objects.filter(
            company=company, type='entrada', transaction_date__gte=start_of_month
        ).aggregate(total=Sum('amount'))
        monthly_income = monthly_income_data['total'] or Decimal('0.00')

        monthly_expenses_data = Transaction.objects.filter(
            company=company, type='saida', transaction_date__gte=start_of_month
        ).aggregate(total=Sum('amount'))
        monthly_expenses = monthly_expenses_data['total'] or Decimal('0.00')
        
        monthly_result = monthly_income - monthly_expenses
        
        # --- CORREÇÃO: Usando os status em PORTUGUÊS para Contas a Pagar ---
        payables_data = Payable.objects.filter(
            company=company,
            due_date__year=today.year,
            due_date__month=today.month,
            status__in=['pendente', 'vencido']  # <-- CORRIGIDO
        ).aggregate(total=Sum('amount'))
        total_payables = payables_data['total'] or Decimal('0.00')

        # --- CORREÇÃO: Usando os status em INGLÊS para Contas a Receber ---
        receivables_data = Receivable.objects.filter(
            company=company,
            due_date__year=today.year,
            due_date__month=today.month,
            status__in=['pending', 'overdue']  # <-- CORRIGIDO
        ).aggregate(total=Sum('amount'))
        total_receivables = receivables_data['total'] or Decimal('0.00')

        # --- 2. Alertas e Insights ---
        seven_days_from_now = today + timedelta(days=7)
        
        # --- CORREÇÃO: Usando os status em PORTUGUÊS para Vencimentos Próximos ---
        upcoming_payables_qs = Payable.objects.filter(
            company=company,
            status__in=['pendente', 'vencido'],  # <-- CORRIGIDO
            due_date__gte=today,
            due_date__lte=seven_days_from_now
        ).order_by('due_date')
        
        # --- CORREÇÃO: Usando os status em INGLÊS para Recebimentos Próximos ---
        upcoming_receivables_qs = Receivable.objects.filter(
            company=company,
            status__in=['pending', 'overdue'],  # <-- CORRIGIDO
            due_date__gte=today,
            due_date__lte=seven_days_from_now
        ).order_by('due_date')
        
        # --- 3. Últimos Lançamentos ---
        recent_transactions_qs = Transaction.objects.filter(
            company=company
        ).select_related('category', 'bank_account', 'credit_card').order_by('-transaction_date', '-id')[:5]

        # --- 4. Montagem da Resposta ---
        response_data = {
            "summary_cards": {
                "current_balance": current_balance,
                "monthly_income": monthly_income,
                "monthly_expenses": monthly_expenses,
                "monthly_result": monthly_result,
                "total_payables": total_payables,
                "total_receivables": total_receivables,
            },
            "alerts": {
                "upcoming_payables": PayableSerializer(upcoming_payables_qs, many=True).data,
                "upcoming_receivables": ReceivableSerializer(upcoming_receivables_qs, many=True).data
            },
            "recent_transactions": TransactionSerializer(recent_transactions_qs, many=True).data,
            "user_info": {
            "name": f"{request.user.first_name} {request.user.last_name}".strip()
        }
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
    

class IncomeExpenseChartView(APIView):
    """
    Fornece dados agregados para o gráfico de Receitas vs. Despesas.
    Retorna os totais de receitas e despesas dos últimos 6 meses.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        company = request.user.company
        today = timezone.now().date()
        
        # Define o período de 6 meses atrás a partir do primeiro dia do mês atual
        six_months_ago = today.replace(day=1) - relativedelta(months=5)

        # Agrupa as transações por mês
        transactions_data = Transaction.objects.filter(
            company=company,
            transaction_date__gte=six_months_ago
        ).annotate(
            month=TruncMonth('transaction_date')
        ).values('month', 'type').annotate(
            total_amount=Sum('amount')
        ).order_by('month')

        # Estrutura os dados para o gráfico
        chart_data = {}
        for item in transactions_data:
            month_str = item['month'].strftime('%Y-%m')
            if month_str not in chart_data:
                chart_data[month_str] = {'income': 0, 'expense': 0}
            
            if item['type'] == 'entrada':
                chart_data[month_str]['income'] = item['total_amount']
            elif item['type'] == 'saida':
                chart_data[month_str]['expense'] = item['total_amount']
        
        # Garante que todos os 6 meses estejam presentes, mesmo que sem dados
        labels = []
        income_data = []
        expense_data = []
        current_month = six_months_ago
        for _ in range(6):
            month_str = current_month.strftime('%Y-%m')
            # Formata o label para "Mês/Ano" (ex: "Jul/25")
            label_formatted = current_month.strftime('%b/%y').capitalize()
            labels.append(label_formatted)
            
            data = chart_data.get(month_str, {'income': 0, 'expense': 0})
            income_data.append(data['income'])
            expense_data.append(data['expense'])
            
            current_month += relativedelta(months=1)
            
        response = {
            'labels': labels,
            'income_data': income_data,
            'expense_data': expense_data,
        }
        return Response(response, status=status.HTTP_200_OK)
    
class CashFlowChartView(APIView):
    """
    Fornece dados para o gráfico de Fluxo de Caixa Acumulado.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        company = request.user.company
        today = timezone.now().date()
        
        # 1. Define o período de 6 meses atrás
        six_months_ago = today.replace(day=1) - relativedelta(months=5)

        # 2. Calcula o saldo inicial (o saldo total de todas as contas 6 meses atrás)
        transactions_before_period = Transaction.objects.filter(
            company=company,
            transaction_date__lt=six_months_ago
        )
        initial_balance = transactions_before_period.aggregate(
            total=Sum('amount', filter=Q(type='entrada')) - Sum('amount', filter=Q(type='saida'))
        )['total'] or Decimal('0.00')

        # 3. Pega os totais de entrada e saída de cada mês no período
        monthly_changes = Transaction.objects.filter(
            company=company,
            transaction_date__gte=six_months_ago
        ).annotate(
            month=TruncMonth('transaction_date')
        ).values('month').annotate(
            total_income=Sum('amount', filter=Q(type='entrada')),
            total_expense=Sum('amount', filter=Q(type='saida'))
        ).order_by('month')

        # 4. Calcula o fluxo de caixa acumulado
        labels = []
        cumulative_balance_data = []
        current_balance = initial_balance
        
        # Mapeia os resultados para fácil acesso
        monthly_map = {
            change['month'].strftime('%Y-%m'): {
                'income': change['total_income'] or 0,
                'expense': change['total_expense'] or 0
            } for change in monthly_changes
        }

        current_month_iterator = six_months_ago
        for _ in range(6):
            month_str = current_month_iterator.strftime('%Y-%m')
            label_formatted = current_month_iterator.strftime('%b/%y').capitalize()
            labels.append(label_formatted)

            # Calcula o resultado do mês e atualiza o saldo acumulado
            month_data = monthly_map.get(month_str, {'income': 0, 'expense': 0})
            net_change = month_data['income'] - month_data['expense']
            current_balance += net_change
            
            cumulative_balance_data.append(current_balance)
            
            current_month_iterator += relativedelta(months=1)

        response = {
            'labels': labels,
            'cumulative_balance': cumulative_balance_data,
        }
        return Response(response, status=status.HTTP_200_OK)
    

class DFCView(APIView):
    """
    Fornece dados para a Demonstração do Fluxo de Caixa (DFC).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        company = request.user.company
        year = request.query_params.get('year', timezone.now().year)
        
        try:
            year = int(year)
        except (ValueError, TypeError):
            return Response({'error': 'Ano inválido.'}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Definir datas de início e fim
        start_date = timezone.datetime(year, 1, 1).date()
        end_date = timezone.datetime(year, 12, 31).date()

        # 2. Calcular Saldos
        saldo_inicial = self._get_saldo_ate_data(company, start_date - timedelta(days=1))
        saldo_final = self._get_saldo_ate_data(company, end_date)

        # 3. Calcular Fluxos de Caixa por Atividade
        fluxo_operacional = self._get_fluxo_por_classificacao(company, start_date, end_date, 'operacional')
        fluxo_investimento = self._get_fluxo_por_classificacao(company, start_date, end_date, 'investimento')
        fluxo_financiamento = self._get_fluxo_por_classificacao(company, start_date, end_date, 'financiamento')

        # 4. Variação de Caixa
        variacao_caixa = saldo_final - saldo_inicial

        # 5. Dados para Gráfico de Evolução (mensal)
        saldo_evolucao = self._get_evolucao_saldo_mensal(company, year, saldo_inicial)

        # 6. Montar a resposta
        response_data = {
            'summary': {
                'saldo_inicial': saldo_inicial,
                'saldo_final': saldo_final,
                'variacao_caixa': variacao_caixa,
                'fluxo_operacional': fluxo_operacional['total'],
                'fluxo_investimento': fluxo_investimento['total'],
                'fluxo_financiamento': fluxo_financiamento['total'],
            },
            'statement': {
                'operacional': fluxo_operacional,
                'investimento': fluxo_investimento,
                'financiamento': fluxo_financiamento,
            },
            'charts': {
                'composicao_fluxo': {
                    'labels': ['Operacional', 'Investimento', 'Financiamento'],
                    'data': [
                        fluxo_operacional['total'],
                        fluxo_investimento['total'],
                        fluxo_financiamento['total']
                    ]
                },
                'evolucao_saldo': saldo_evolucao
            }
        }
        return Response(response_data, status=status.HTTP_200_OK)

    def _get_saldo_ate_data(self, company, date):
        """Calcula o saldo total da empresa até uma data específica."""
        saldo = BankAccount.objects.filter(company=company).aggregate(
            total=Sum('initial_balance')
        )['total'] or Decimal('0.00')

        transacoes_passadas = Transaction.objects.filter(
            company=company,
            transaction_date__lte=date,
            bank_account__isnull=False
        )
        
        saldo_transacoes = transacoes_passadas.aggregate(
            entradas=Sum('amount', filter=Q(type='entrada')),
            saidas=Sum('amount', filter=Q(type='saida'))
        )
        
        entradas = saldo_transacoes.get('entradas') or Decimal('0.00')
        saidas = saldo_transacoes.get('saidas') or Decimal('0.00')
        
        return saldo + entradas - saidas

    def _get_fluxo_por_classificacao(self, company, start_date, end_date, classificacao):
        """Calcula o fluxo de caixa para uma classificação DFC específica."""
        transacoes = Transaction.objects.filter(
            company=company,
            transaction_date__range=[start_date, end_date],
            category__dfc_classification=classificacao
        )

        entradas = transacoes.filter(type='entrada').aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        saidas = transacoes.filter(type='saida').aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        return {
            'entradas': entradas,
            'saidas': saidas,
            'total': entradas - saidas
        }

    def _get_evolucao_saldo_mensal(self, company, year, saldo_inicial):
        """Retorna dados para o gráfico de evolução do saldo de caixa mensal."""
        labels = []
        data = []
        saldo_acumulado = saldo_inicial
        
        for month in range(1, 13):
            labels.append(timezone.datetime(year, month, 1).strftime('%b'))
            
            start_of_month = timezone.datetime(year, month, 1)
            end_of_month = start_of_month + relativedelta(months=1) - timedelta(days=1)

            transacoes_mes = Transaction.objects.filter(
                company=company,
                transaction_date__range=[start_of_month, end_of_month],
                bank_account__isnull=False
            )
            
            resultado_mes = transacoes_mes.aggregate(
                entradas=Sum('amount', filter=Q(type='entrada')),
                saidas=Sum('amount', filter=Q(type='saida'))
            )
            
            entradas = resultado_mes.get('entradas') or Decimal('0.00')
            saidas = resultado_mes.get('saidas') or Decimal('0.00')
            
            saldo_acumulado += (entradas - saidas)
            data.append(saldo_acumulado)
            
        return {'labels': labels, 'data': data}



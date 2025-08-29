from django.http import JsonResponse

def home(request):
    return JsonResponse({'message': 'Bem-vindo à API do FinançaPlus!'})


def health_check(request):
    """
    Um endpoint simples que retorna 200 OK.
    Usado pelo Application Load Balancer para verificar a saúde da aplicação.
    """
    return JsonResponse({"status": "ok", "message": "Application is healthy."})
import requests
import os

def send_whatsapp_message(phone_number, message):
    """
    Envia uma mensagem de texto via Evolution API.
    """
    # É uma boa prática guardar URLs e chaves de API em variáveis de ambiente
    api_url = os.environ.get("EVOLUTION_API_URL", "http://localhost:8081/message/sendText/FinanceApp")
    api_key = os.environ.get("EVOLUTION_API_KEY", "123456") # Substitua pela sua chave se não usar .env

    if not phone_number:
        print("Número de telemóvel não fornecido. A mensagem não foi enviada.")
        return False

    payload = {
        "number": phone_number,
        "textMessage": { "text": message }
    }
    headers = {
        "apikey": api_key,
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(api_url, json=payload, headers=headers)
        response.raise_for_status()  # Lança um erro para respostas HTTP 4xx/5xx
        print(f"Mensagem enviada com sucesso para {phone_number}: {response.json()}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Erro ao enviar mensagem para {phone_number}: {e}")
        return False
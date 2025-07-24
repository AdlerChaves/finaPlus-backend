from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken

class CookieJWTAuthentication(JWTAuthentication):
    """
    Classe de autenticação personalizada que extrai o JWT do cookie 'access_token'.
    """
    def authenticate(self, request):
        # Pega o token do cookie chamado 'access_token'
        raw_token = request.COOKIES.get('access_token')
        if raw_token is None:
            return None # Nenhum token encontrado, autenticação falha silenciosamente

        try:
            # Valida o token
            validated_token = self.get_validated_token(raw_token)
            # Retorna o usuário e o token validado, conforme esperado pelo DRF
            return self.get_user(validated_token), validated_token
        except InvalidToken:
            # Se o token for inválido, tenta usar o refresh token para obter um novo
            # (Lógica de refresh pode ser adicionada aqui no futuro)
            return None
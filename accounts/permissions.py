from rest_framework import permissions

class HasPermission(permissions.BasePermission):
    """
    Classe de permissão genérica que verifica a permissão do Django.
    O atributo 'permission_required' deve ser definido na view.
    """
    def has_permission(self, request, view):
        # A view deve ter um atributo 'permission_required'
        required_permission = getattr(view, 'permission_required', None)
        if not required_permission:
            # Se a view não especificar uma permissão, negamos o acesso por segurança.
            return False
        
        # O usuário deve estar autenticado e ter a permissão necessária.
        return request.user and request.user.is_authenticated and request.user.has_perm(required_permission)

# --- Abaixo estão as classes específicas que você usará nas suas views ---

class CanViewCadastros(HasPermission):
    def has_permission(self, request, view):
        # Define a permissão necessária antes de chamar a lógica principal
        view.permission_required = 'cadastros.view_customer' 
        return super().has_permission(request, view)

class CanEditCadastros(HasPermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            view.permission_required = 'cadastros.view_customer'
        else:
            view.permission_required = 'cadastros.change_customer'
        return super().has_permission(request, view)

class CanViewFinance(HasPermission):
    def has_permission(self, request, view):
        view.permission_required = 'finance.view_transaction'
        return super().has_permission(request, view)

class CanEditFinance(HasPermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            view.permission_required = 'finance.view_transaction'
        else:
            view.permission_required = 'finance.change_transaction'
        return super().has_permission(request, view)
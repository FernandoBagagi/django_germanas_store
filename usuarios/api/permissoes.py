from rest_framework.permissions import SAFE_METHODS, BasePermission

from usuarios.models import Usuario


class CadastroCompleto(BasePermission):
    message = 'Complete seu cadastro para continuar.'

    def has_permission(self, request, view):
        return bool(
            isinstance(request.user, Usuario) and not request.user.cadastro_pendente
        )


class PermissaoProdutos(CadastroCompleto):
    message = 'Você não tem permissão para esta operação.'

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        if request.method in SAFE_METHODS:
            return True
        return request.user.papel in ('ADMIN', 'VENDEDOR')

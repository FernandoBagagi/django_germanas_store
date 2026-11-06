from django.contrib.auth import logout
from django.core.exceptions import PermissionDenied


class VerificarSessao:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            versao = request.session.get('versao_autenticacao')
            if versao != request.user.versao_autenticacao:
                logout(request)
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.user.is_authenticated and request.user.cadastro_pendente:
            rota = request.resolver_match
            permitidos = {
                'minha_conta',
                'editar_conta',
                'desativar_conta',
                'sair',
                'redefinir_senha',
                'senha_enviada',
                'confirmar_senha',
                'senha_concluida',
            }
            if rota.namespace == 'admin' or (
                rota.namespace == 'usuarios' and rota.url_name not in permitidos
            ):
                raise PermissionDenied('Complete seu cadastro para continuar.')


def registrar_sessao(sender, request, user, **kwargs) -> None:
    request.session['versao_autenticacao'] = user.versao_autenticacao

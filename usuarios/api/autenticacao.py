from django.db import transaction
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken

from usuarios.models import Usuario


class AutenticacaoJWT(JWTAuthentication):
    def get_user(self, validated_token):
        usuario = super().get_user(validated_token)
        if validated_token.get('versao_autenticacao') != usuario.versao_autenticacao:
            raise AuthenticationFailed('Acesso revogado. Entre novamente.')
        return usuario


def emitir_tokens(usuario: Usuario) -> dict[str, str]:
    refresh = RefreshToken.for_user(usuario)
    refresh['versao_autenticacao'] = usuario.versao_autenticacao
    return {'access': str(refresh.access_token), 'refresh': str(refresh)}


@transaction.atomic
def renovar_tokens(valor: str) -> dict[str, str]:
    # Simple JWT aceita o JWT codificado; a anotação upstream usa Token.
    refresh = RefreshToken(valor)  # type: ignore[arg-type]
    usuario = Usuario.objects.filter(pk=refresh['user_id'], is_active=True).first()
    if not usuario or refresh.get('versao_autenticacao') != usuario.versao_autenticacao:
        raise AuthenticationFailed('Acesso revogado. Entre novamente.')
    refresh.blacklist()
    return emitir_tokens(usuario)

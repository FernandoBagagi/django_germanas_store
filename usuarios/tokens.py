from typing import cast

from django.contrib.auth.tokens import PasswordResetTokenGenerator

from usuarios.models import Usuario


class GeradorRecuperacao(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        valor = super()._make_hash_value(user, timestamp)
        usuario = cast(Usuario, user)
        return f'{valor}{usuario.versao_autenticacao}{usuario.is_active}'


gerador_recuperacao = GeradorRecuperacao()

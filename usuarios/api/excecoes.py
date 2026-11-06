from django.core.exceptions import ValidationError
from django.db import IntegrityError
from rest_framework.response import Response
from rest_framework.views import exception_handler


def tratar_excecao(erro, contexto):
    if isinstance(erro, ValidationError):
        dados = (
            erro.message_dict
            if hasattr(erro, 'message_dict')
            else {'detail': erro.messages}
        )
        return Response(dados, status=400)
    if isinstance(erro, IntegrityError):
        return Response(
            {'detail': 'Já existe registro com estes identificadores.'}, status=400
        )
    return exception_handler(erro, contexto)

import re
from datetime import date
from zoneinfo import ZoneInfo

from django.core.exceptions import ValidationError
from django.utils import timezone

DDDS = {
    11,
    12,
    13,
    14,
    15,
    16,
    17,
    18,
    19,
    21,
    22,
    24,
    27,
    28,
    31,
    32,
    33,
    34,
    35,
    37,
    38,
    41,
    42,
    43,
    44,
    45,
    46,
    47,
    48,
    49,
    51,
    53,
    54,
    55,
    61,
    62,
    63,
    64,
    65,
    66,
    67,
    68,
    69,
    71,
    73,
    74,
    75,
    77,
    79,
    81,
    82,
    83,
    84,
    85,
    86,
    87,
    88,
    89,
    91,
    92,
    93,
    94,
    95,
    96,
    97,
    98,
    99,
}


INFORME_CPF = 'Informe um CPF válido.'


def normalizar_cpf(valor: str) -> str:
    if not re.fullmatch(r'[0-9.\-\s]+', valor):
        raise ValidationError(INFORME_CPF)
    cpf = re.sub(r'\D', '', valor)
    if len(cpf) != 11 or len(set(cpf)) == 1:
        raise ValidationError(INFORME_CPF)
    for tamanho in (9, 10):
        soma = sum(int(cpf[i]) * (tamanho + 1 - i) for i in range(tamanho))
        digito = (soma * 10) % 11 % 10
        if int(cpf[tamanho]) != digito:
            raise ValidationError(INFORME_CPF)
    return cpf


def normalizar_telefone(valor: str) -> str:
    if not re.fullmatch(r'\+?[0-9()\s.\-]+', valor):
        raise ValidationError('Informe um telefone brasileiro com DDD.')
    numero = re.sub(r'\D', '', valor)
    if valor.startswith('+'):
        if not numero.startswith('55'):
            raise ValidationError('Informe um telefone brasileiro com DDD.')
        numero = numero[2:]
    if (
        len(numero) not in (10, 11)
        or int(numero[:2]) not in DDDS
        or (len(numero) == 10 and numero[2] not in '2345')
        or (len(numero) == 11 and numero[2] != '9')
    ):
        raise ValidationError('Informe um telefone brasileiro com DDD válido.')
    return numero


def validar_maioridade(valor: date) -> None:
    hoje = timezone.localdate(timezone=ZoneInfo('America/Bahia'))
    idade = hoje.year - valor.year - ((hoje.month, hoje.day) < (valor.month, valor.day))
    if idade < 18:
        raise ValidationError('O usuário deve ter pelo menos 18 anos.')

from collections.abc import Callable
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from produtos.models import Produto

pytestmark = pytest.mark.django_db


def test_produto_persistido(produto: Produto) -> None:
    produto.full_clean()
    salvo = Produto.objects.get(pk=produto.pk)
    assert isinstance(salvo.id, int)
    assert salvo.id > 0
    assert str(salvo) == produto.nome_comercial
    assert salvo.descricao == produto.descricao
    assert salvo.url_imagem == produto.url_imagem
    assert salvo.preco == produto.preco
    assert salvo.preco.as_tuple().exponent == -2
    assert Produto._meta.verbose_name == 'produto'
    assert Produto._meta.verbose_name_plural == 'produtos'


@pytest.mark.parametrize(
    ('campo', 'valor'),
    [
        ('nome_comercial', ''),
        ('descricao', ''),
        ('url_imagem', 'invalida'),
        ('preco', Decimal('-0.01')),
        ('preco', Decimal('1.001')),
    ],
)
def test_validacao_modelo(produto: Produto, campo: str, valor: object) -> None:
    setattr(produto, campo, valor)
    with pytest.raises(ValidationError):
        produto.full_clean()


@pytest.mark.parametrize('alteracoes', [{'preco': Decimal('-0.01')}, {'id': 0}])
def test_restricoes_banco(
    criar_produto: Callable[..., Produto], alteracoes: dict
) -> None:
    with pytest.raises(IntegrityError), transaction.atomic():
        criar_produto(**alteracoes)

from collections.abc import Callable
from decimal import Decimal

import pytest
from faker import Faker
from rest_framework.test import APIClient

from produtos.models import Produto


@pytest.fixture
def gerador() -> Faker:
    return Faker('pt_BR')


@pytest.fixture
def criar_produto(gerador: Faker) -> Callable[..., Produto]:
    def criar(**alteracoes: object) -> Produto:
        dados = {
            'nome_comercial': gerador.unique.sentence(nb_words=3),
            'descricao': gerador.paragraph(),
            'url_imagem': gerador.image_url(),
            'preco': gerador.pydecimal(left_digits=4, right_digits=2, positive=True),
        }
        dados.update(alteracoes)
        return Produto.objects.create(**dados)

    return criar


@pytest.fixture
def produto(criar_produto: Callable[..., Produto]) -> Produto:
    return criar_produto()


@pytest.fixture
def catalogo(criar_produto: Callable[..., Produto], gerador: Faker) -> list[Produto]:
    termo = gerador.uuid4()
    preco = gerador.pydecimal(left_digits=3, right_digits=2, positive=True)
    return [
        criar_produto(nome_comercial=termo.upper(), preco=preco),
        criar_produto(
            descricao=f'{gerador.sentence()} {termo.upper()}',
            preco=preco + Decimal('10.00'),
        ),
        criar_produto(preco=preco + Decimal('20.00')),
    ]


@pytest.fixture
def cliente_api() -> APIClient:
    return APIClient()

from collections.abc import Callable

import pytest
from faker import Faker
from rest_framework.test import APIClient

from produtos.models import Produto

pytestmark = pytest.mark.django_db


def test_listagem(cliente_api: APIClient, produto: Produto) -> None:
    resposta = cliente_api.get('/api/v1/produtos/')
    assert resposta.status_code == 200
    assert resposta.data['count'] == 1
    assert resposta.data['results'] == [
        {
            'id': produto.id,
            'nome_comercial': produto.nome_comercial,
            'descricao': produto.descricao,
            'url_imagem': produto.url_imagem,
            'preco': f'{produto.preco:.2f}',
        }
    ]


def test_busca_nome_ou_descricao(
    cliente_api: APIClient, catalogo: list[Produto]
) -> None:
    resposta = cliente_api.get(
        '/api/v1/produtos/',
        {
            'busca': catalogo[0].nome_comercial.lower()[3:-3],
        },
    )
    assert [item['id'] for item in resposta.data['results']] == [
        produto.pk for produto in catalogo[:2]
    ]


@pytest.mark.parametrize('limites', ['minimo', 'maximo', 'ambos', 'com_busca'])
def test_faixa_preco(
    cliente_api: APIClient, catalogo: list[Produto], limites: str
) -> None:
    filtros = {}
    if limites in ('minimo', 'ambos', 'com_busca'):
        filtros['preco_minimo'] = str(catalogo[1].preco)
    if limites in ('maximo', 'ambos', 'com_busca'):
        filtros['preco_maximo'] = str(catalogo[1].preco)
    if limites == 'com_busca':
        filtros['busca'] = catalogo[0].nome_comercial.lower()
    esperados = {
        'minimo': catalogo[1:],
        'maximo': catalogo[:2],
        'ambos': catalogo[1:2],
        'com_busca': catalogo[1:2],
    }
    resposta = cliente_api.get('/api/v1/produtos/', filtros)
    assert [item['id'] for item in resposta.data['results']] == [
        produto.pk for produto in esperados[limites]
    ]


def test_codigo_exato(cliente_api: APIClient, catalogo: list[Produto]) -> None:
    resposta = cliente_api.get('/api/v1/produtos/', {'codigo': catalogo[1].pk})
    assert resposta.data['count'] == 1
    assert resposta.data['results'][0]['id'] == catalogo[1].pk


def test_detalhe(cliente_api: APIClient, produto: Produto) -> None:
    resposta = cliente_api.get(f'/api/v1/produtos/{produto.pk}/')
    assert resposta.status_code == 200
    assert resposta.data == {
        'id': produto.id,
        'nome_comercial': produto.nome_comercial,
        'descricao': produto.descricao,
        'url_imagem': produto.url_imagem,
        'preco': f'{produto.preco:.2f}',
    }


def test_inexistente(cliente_api: APIClient) -> None:
    assert cliente_api.get('/api/v1/produtos/1/').status_code == 404
    assert cliente_api.get('/api/v1/produtos/', {'codigo': 1}).data['count'] == 0


def test_paginacao(
    cliente_api: APIClient, criar_produto: Callable[..., Produto]
) -> None:
    produtos = [criar_produto() for _ in range(13)]
    primeira = cliente_api.get('/api/v1/produtos/').data
    assert primeira['count'] == 13
    assert len(primeira['results']) == 12
    assert primeira['next'] is not None
    assert primeira['previous'] is None
    segunda = cliente_api.get(primeira['next']).data
    assert [item['id'] for item in segunda['results']] == [produtos[-1].pk]
    assert segunda['next'] is None
    assert segunda['previous'] is not None
    assert cliente_api.get('/api/v1/produtos/', {'page': 3}).status_code == 404


@pytest.mark.parametrize(
    'filtros',
    [
        {'preco_minimo': 'abc'},
        {'preco_minimo': '-1'},
        {'preco_minimo': '10', 'preco_maximo': '1'},
        {'preco_maximo': '1.001'},
        {'codigo': 'abc'},
        {'codigo': '0'},
        {'codigo': '1.5'},
        {'preco_minimo': 'NaN'},
        {'preco_maximo': 'Infinity'},
    ],
)
def test_filtros_invalidos(cliente_api: APIClient, filtros: dict) -> None:
    assert cliente_api.get('/api/v1/produtos/', filtros).status_code == 400


@pytest.mark.parametrize('metodo', ['post', 'put', 'patch', 'delete'])
@pytest.mark.parametrize('detalhe', [True, False])
def test_somente_leitura(
    cliente_api: APIClient, produto: Produto, metodo: str, detalhe: bool
) -> None:
    url = f'/api/v1/produtos/{produto.pk}/' if detalhe else '/api/v1/produtos/'
    assert getattr(cliente_api, metodo)(url, {}, format='json').status_code == 405
    assert Produto.objects.filter(pk=produto.pk).exists()


def test_filtros_vazios(cliente_api: APIClient, produto: Produto) -> None:
    resposta = cliente_api.get(
        '/api/v1/produtos/',
        {
            'busca': '',
            'preco_minimo': '',
            'preco_maximo': '',
            'codigo': '',
        },
    )
    assert resposta.status_code == 200
    assert resposta.data['count'] == 1


def test_sem_resultados(
    cliente_api: APIClient, produto: Produto, gerador: Faker
) -> None:
    resposta = cliente_api.get('/api/v1/produtos/', {'busca': gerador.uuid4()})
    assert resposta.data['results'] == []

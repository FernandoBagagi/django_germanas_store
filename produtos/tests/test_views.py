from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse
from faker import Faker

from produtos.models import Produto

pytestmark = pytest.mark.django_db


def test_inicio(client: Client) -> None:
    resposta = client.get('/')
    assert resposta.status_code == 200
    assert 'Produtos' in resposta.content.decode()
    assert reverse('produtos:listagem') in resposta.content.decode()


def test_listagem(client: Client, produto: Produto) -> None:
    resposta = client.get('/produtos/')
    assert resposta.status_code == 200
    assert list(resposta.context['produtos']) == [produto]
    conteudo = resposta.content.decode()
    assert produto.nome_comercial in conteudo
    assert produto.url_imagem in conteudo
    assert reverse('produtos:detalhe', args=[produto.pk]) in conteudo


def test_busca_nome_ou_descricao(client: Client, catalogo: list[Produto]) -> None:
    termo = catalogo[0].nome_comercial.lower()[3:-3]
    resposta = client.get('/produtos/', {'busca': termo})
    assert list(resposta.context['produtos']) == catalogo[:2]
    assert resposta.context['filtros']['busca'] == termo


@pytest.mark.parametrize('limites', ['minimo', 'maximo', 'ambos', 'com_busca'])
def test_faixa_preco(client: Client, catalogo: list[Produto], limites: str) -> None:
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
    resposta = client.get('/produtos/', filtros)
    assert list(resposta.context['produtos']) == esperados[limites]


def test_detalhe_e_moeda(client: Client, produto: Produto) -> None:
    produto.preco = Decimal('1250.50')
    produto.save()
    resposta = client.get(reverse('produtos:detalhe', args=[produto.pk]))
    assert resposta.status_code == 200
    conteudo = resposta.content.decode().replace('\xa0', ' ')
    assert 'R$ 1.250,50' in conteudo
    assert produto.nome_comercial in conteudo
    assert produto.descricao in conteudo
    assert produto.url_imagem in conteudo


def test_detalhe_inexistente(client: Client) -> None:
    assert client.get('/produtos/1/').status_code == 404


def test_sem_resultados(client: Client, produto: Produto, gerador: Faker) -> None:
    resposta = client.get('/produtos/', {'busca': gerador.uuid4()})
    assert 'Nenhum produto encontrado.' in resposta.content.decode()


@pytest.mark.parametrize(
    'filtros',
    [
        {'preco_minimo': 'abc'},
        {'preco_maximo': '-1'},
        {'preco_minimo': '10', 'preco_maximo': '1'},
        {'preco_minimo': 'NaN'},
        {'preco_maximo': 'Infinity'},
    ],
)
def test_filtros_invalidos(client: Client, filtros: dict) -> None:
    resposta = client.get('/produtos/', filtros)
    assert resposta.status_code == 400
    assert resposta.context['erros']


def test_filtros_vazios(client: Client, produto: Produto) -> None:
    resposta = client.get(
        '/produtos/', {'busca': '', 'preco_minimo': '', 'preco_maximo': ''}
    )
    assert list(resposta.context['produtos']) == [produto]


@pytest.mark.parametrize('valor', ['1.250,50', '1250,50', '1250.50'])
def test_filtro_preco_brasileiro(client: Client, produto: Produto, valor: str) -> None:
    produto.preco = Decimal('1250.50')
    produto.save()
    resposta = client.get(
        '/produtos/',
        {
            'preco_minimo': valor,
            'preco_maximo': valor,
        },
    )
    assert resposta.status_code == 200
    assert list(resposta.context['produtos']) == [produto]
    conteudo = resposta.content.decode().replace('\xa0', ' ')
    assert 'R$ 1.250,50' in conteudo
    assert f'value="{valor}"' in conteudo


@pytest.mark.parametrize('valor', ['1.25,50', '-10,00', '1,001', 'abc,00'])
def test_preco_brasileiro_invalido(client: Client, valor: str) -> None:
    resposta = client.get('/produtos/', {'preco_minimo': valor})
    assert resposta.status_code == 400


def test_faixa_brasileira_invertida(client: Client) -> None:
    resposta = client.get(
        '/produtos/',
        {
            'preco_minimo': '200,00',
            'preco_maximo': '10,00',
        },
    )
    assert resposta.status_code == 400


def test_aviso_nova_loja(client: Client) -> None:
    conteudo = client.get('/').content.decode()
    assert 'Vem novidade por aí' in conteudo
    assert 'Em breve' in conteudo
    assert "Germana's Store" in conteudo
    assert 'de tudo, em um só lugar' in conteudo


def test_controles_listagem(client: Client, produto: Produto) -> None:
    conteudo = client.get('/produtos/').content.decode()
    assert '<h1>Produtos</h1>' not in conteudo
    assert 'type="number"' not in conteudo
    assert conteudo.count('inputmode="numeric"') == 2
    assert 'aria-label="Limpar filtros"' in conteudo
    assert '>Limpar filtros</a>' not in conteudo
    assert 'mascara_precos.js' in conteudo

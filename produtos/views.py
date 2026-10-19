from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from rest_framework.exceptions import ValidationError

from produtos.servicos import ServicoProdutos


def inicio(requisicao: HttpRequest) -> HttpResponse:
    return render(requisicao, 'produtos/inicio.html')


def listagem(requisicao: HttpRequest) -> HttpResponse:
    contexto = {'filtros': requisicao.GET}
    try:
        contexto['produtos'] = ServicoProdutos.listar_web(requisicao.GET)
    except ValidationError as erro:
        contexto['erros'] = erro.detail
        contexto['produtos'] = []
        return render(requisicao, 'produtos/listagem.html', contexto, status=400)
    return render(requisicao, 'produtos/listagem.html', contexto)


def detalhe(requisicao: HttpRequest, id: int) -> HttpResponse:
    return render(
        requisicao, 'produtos/detalhe.html', {'produto': ServicoProdutos.obter(id)}
    )

import re
from collections.abc import Mapping

from django.db.models import Q, QuerySet
from django.shortcuts import get_object_or_404

from produtos.api.serializers import FiltrosProdutoSerializer
from produtos.models import Produto


class ServicoProdutos:
    @staticmethod
    def listar_web(parametros: Mapping[str, str]) -> QuerySet[Produto]:
        filtros = dict(parametros.items())
        for campo in ('preco_minimo', 'preco_maximo'):
            valor = filtros.get(campo, '').strip()
            if re.fullmatch(r'(?:[0-9]+|[0-9]{1,3}(?:\.[0-9]{3})+),[0-9]{2}', valor):
                filtros[campo] = valor.replace('.', '').replace(',', '.')
        return ServicoProdutos.listar(filtros)

    @staticmethod
    def listar(parametros: Mapping[str, str]) -> QuerySet[Produto]:
        filtros = FiltrosProdutoSerializer(
            data={chave: valor for chave, valor in parametros.items() if valor != ''}
        )
        filtros.is_valid(raise_exception=True)
        dados = filtros.validated_data
        produtos = Produto.objects.all()
        if busca := dados.get('busca'):
            produtos = produtos.filter(
                Q(nome_comercial__icontains=busca) | Q(descricao__icontains=busca)
            )
        if 'preco_minimo' in dados:
            produtos = produtos.filter(preco__gte=dados['preco_minimo'])
        if 'preco_maximo' in dados:
            produtos = produtos.filter(preco__lte=dados['preco_maximo'])
        if 'codigo' in dados:
            produtos = produtos.filter(pk=dados['codigo'])
        return produtos

    @staticmethod
    def obter(codigo: int) -> Produto:
        return get_object_or_404(Produto, pk=codigo)

from typing import override

from django.db.models import QuerySet
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.pagination import PageNumberPagination

from produtos.api.serializers import ProdutoSerializer
from produtos.models import Produto
from produtos.servicos import ServicoProdutos


class PaginacaoProdutos(PageNumberPagination):
    page_size = 12


class ListagemProdutos(ListAPIView):
    serializer_class = ProdutoSerializer
    pagination_class = PaginacaoProdutos

    @override
    def get_queryset(self) -> QuerySet[Produto]: # type: ignore[override]
        query_params = getattr(self.request, 'query_params', {})
        return ServicoProdutos.listar(query_params)


class DetalheProduto(RetrieveAPIView):
    serializer_class = ProdutoSerializer

    @override
    def get_object(self) -> Produto: # type: ignore[override]
        produto = ServicoProdutos.obter(self.kwargs['codigo'])
        self.check_object_permissions(self.request, produto)
        return produto

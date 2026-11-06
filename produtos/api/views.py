from typing import override

from django.db.models import QuerySet
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated

from produtos.api.serializers import ProdutoSerializer
from produtos.models import Produto
from produtos.servicos import ServicoProdutos
from usuarios.api.permissoes import PermissaoProdutos


class PaginacaoProdutos(PageNumberPagination):
    page_size = 12


class ListagemProdutos(ListCreateAPIView):
    permission_classes = [IsAuthenticated, PermissaoProdutos]
    serializer_class = ProdutoSerializer
    pagination_class = PaginacaoProdutos

    @override
    def get_queryset(self) -> QuerySet[Produto]:  # type: ignore[override]
        query_params = getattr(self.request, 'query_params', {})
        return ServicoProdutos.listar(query_params)


class DetalheProduto(RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, PermissaoProdutos]
    serializer_class = ProdutoSerializer

    @override
    def get_object(self) -> Produto:  # type: ignore[override]
        produto = ServicoProdutos.obter(self.kwargs['codigo'])
        self.check_object_permissions(self.request, produto)
        return produto

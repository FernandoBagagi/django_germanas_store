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

    def get_queryset(self) -> QuerySet[Produto]:
        return ServicoProdutos.listar(self.request.query_params)


class DetalheProduto(RetrieveAPIView):
    serializer_class = ProdutoSerializer

    def get_object(self) -> Produto:
        produto = ServicoProdutos.obter(self.kwargs['codigo'])
        self.check_object_permissions(self.request, produto)
        return produto

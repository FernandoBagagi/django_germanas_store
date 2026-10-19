from django.urls import path

from produtos.api.views import DetalheProduto, ListagemProdutos

app_name = 'api_produtos'
urlpatterns = [
    path('', ListagemProdutos.as_view(), name='listagem'),
    path('<int:codigo>/', DetalheProduto.as_view(), name='detalhe'),
]

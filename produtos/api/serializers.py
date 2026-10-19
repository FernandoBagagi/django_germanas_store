from rest_framework import serializers

from produtos.models import Produto


class ProdutoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Produto
        fields = ['id', 'nome_comercial', 'descricao', 'url_imagem', 'preco']
        read_only_fields = fields


class FiltrosProdutoSerializer(serializers.Serializer):
    busca = serializers.CharField(required=False, allow_blank=True)
    preco_minimo = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=0, required=False
    )
    preco_maximo = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=0, required=False
    )
    codigo = serializers.IntegerField(min_value=1, required=False)

    def validate(self, dados: dict) -> dict:
        minimo = dados.get('preco_minimo')
        maximo = dados.get('preco_maximo')
        if minimo is not None and maximo is not None and minimo > maximo:
            raise serializers.ValidationError(
                'O preço mínimo não pode ser maior que o preço máximo.'
            )
        return dados

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db.models import (
    BigAutoField,
    CharField,
    CheckConstraint,
    DecimalField,
    Model,
    Q,
    TextField,
    URLField,
)


class Produto(Model):
    id: BigAutoField = BigAutoField('código', primary_key=True)
    nome_comercial: CharField = CharField('nome comercial', max_length=255)
    descricao: TextField = TextField('descrição')
    url_imagem: URLField = URLField('URL da imagem', max_length=2048)
    preco: DecimalField = DecimalField(
        'preço',
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
    )

    class Meta:
        verbose_name = 'produto'
        verbose_name_plural = 'produtos'
        ordering = ['id']
        constraints = [
            CheckConstraint(condition=Q(id__gt=0), name='produto_id_positivo'),
            CheckConstraint(
                condition=Q(preco__gte=0), name='produto_preco_nao_negativo'
            ),
        ]

    def __str__(self) -> str:
        return self.nome_comercial

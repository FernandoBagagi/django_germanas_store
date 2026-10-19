from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


class Produto(models.Model):
    id = models.BigAutoField('código', primary_key=True)
    nome_comercial = models.CharField('nome comercial', max_length=255)
    descricao = models.TextField('descrição')
    url_imagem = models.URLField('URL da imagem', max_length=2048)
    preco = models.DecimalField(
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
            models.CheckConstraint(
                condition=models.Q(id__gt=0), name='produto_id_positivo'
            ),
            models.CheckConstraint(
                condition=models.Q(preco__gte=0), name='produto_preco_nao_negativo'
            ),
        ]

    def __str__(self) -> str:
        return self.nome_comercial

from django.core.exceptions import ValidationError
from rest_framework import serializers

from usuarios.models import Usuario
from usuarios.servicos import CAMPOS, ServicoUsuarios
from usuarios.validadores import validar_formato_data_iso


class DataISOSerializer(serializers.DateField):
    def to_internal_value(self, value):
        if not isinstance(value, str):
            raise serializers.ValidationError('Informe uma data no formato AAAA-MM-DD.')
        try:
            validar_formato_data_iso(value)
        except ValidationError as erro:
            raise serializers.ValidationError(erro.messages) from erro
        return super().to_internal_value(value)


class UsuarioSerializer(serializers.ModelSerializer):
    papel = serializers.CharField(read_only=True)

    class Meta:  # type: ignore[reportIncompatibleVariableOverride]
        model = Usuario
        fields = ['id', *CAMPOS, 'papel', 'is_active']
        read_only_fields = fields


class CadastroSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField(max_length=254)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    data_nascimento = DataISOSerializer(input_formats=['%Y-%m-%d'])
    cpf = serializers.CharField()
    telefone = serializers.CharField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def to_internal_value(self, data):
        ServicoUsuarios.verificar_campos(data)
        return super().to_internal_value(data)


class AtualizacaoSerializer(CadastroSerializer):
    password = serializers.CharField(
        required=False, write_only=True, trim_whitespace=False
    )
    cpf = serializers.CharField(required=False)

from typing import Any

from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)

from usuarios.models import Usuario
from usuarios.validadores import normalizar_cpf

CAMPOS = (
    'username',
    'email',
    'first_name',
    'last_name',
    'data_nascimento',
    'cpf',
    'telefone',
)
PRIVILEGIADOS = {
    'is_staff',
    'is_superuser',
    'is_active',
    'groups',
    'user_permissions',
    'papel',
    'versao_autenticacao',
    'cadastro_pendente',
}


class ServicoUsuarios:
    @staticmethod
    def verificar_campos(dados: dict) -> None:
        if PRIVILEGIADOS.intersection(dados):
            raise PermissionDenied('Não é permitido enviar campos privilegiados.')
        desconhecidos = set(dados) - {*CAMPOS, 'password'}
        if desconhecidos:
            raise ValidationError(dict.fromkeys(desconhecidos, 'Campo não permitido.'))

    @staticmethod
    def autorizar(ator: Usuario, usuario: Usuario) -> None:
        ator.refresh_from_db()
        if not ator.is_active or (ator.pk != usuario.pk and not ator.is_superuser):
            raise PermissionDenied('Você não pode acessar este usuário.')
        if ator.cadastro_pendente and ator.pk != usuario.pk:
            raise PermissionDenied('Complete seu cadastro para continuar.')

    @staticmethod
    def exigir_admin(ator: Usuario) -> None:
        ator.refresh_from_db()
        if not ator.is_active or not ator.is_superuser or ator.cadastro_pendente:
            raise PermissionDenied('Esta operação exige ADMIN com cadastro completo.')

    @staticmethod
    def proteger_admin(usuario: Usuario) -> None:
        if (
            usuario.is_active
            and usuario.is_superuser
            and not Usuario.objects.filter(is_active=True, is_superuser=True)
            .exclude(pk=usuario.pk)
            .exists()
        ):
            raise PermissionDenied('Não é permitido remover o último ADMIN ativo.')

    @staticmethod
    def revogar(usuario: Usuario) -> None:
        usuario.versao_autenticacao += 1
        for token in OutstandingToken.objects.filter(user_id=usuario.pk):
            BlacklistedToken.objects.get_or_create(token=token)

    @staticmethod
    def preencher(usuario: Usuario, dados: dict, novo: bool = False) -> None:
        ServicoUsuarios.verificar_campos(dados)
        for campo in CAMPOS:
            if campo in dados:
                setattr(usuario, campo, dados[campo])
        usuario.cadastro_pendente = False
        usuario.full_clean(exclude=['password'])
        if novo or 'password' in dados:
            senha = dados.get('password')
            if not senha:
                raise ValidationError({'password': 'Informe a senha.'})
            try:
                validate_password(senha, usuario)
            except ValidationError as erro:
                raise ValidationError({'password': erro.messages}) from erro
            usuario.set_password(senha)

    @staticmethod
    @transaction.atomic
    def cadastrar(dados: dict[str, Any]) -> tuple[Usuario, bool]:
        ServicoUsuarios.verificar_campos(dados)
        cpf = normalizar_cpf(dados.get('cpf', ''))
        usuario = Usuario.objects.filter(cpf=cpf).first()
        reativado = usuario is not None
        if usuario and usuario.is_active:
            raise ValidationError({'cpf': 'Este CPF já está cadastrado.'})
        usuario = usuario or Usuario()
        ServicoUsuarios.preencher(usuario, dados, novo=True)
        usuario.is_active = True
        usuario.is_staff = False
        usuario.is_superuser = False
        if reativado:
            ServicoUsuarios.revogar(usuario)
        try:
            usuario.save()
        except IntegrityError as erro:
            raise ValidationError(
                'Já existe usuário com estes identificadores.'
            ) from erro
        grupo, _ = Group.objects.get_or_create(name='CLIENTE')
        usuario.groups.set([grupo])
        usuario.user_permissions.clear()
        return usuario, reativado

    @staticmethod
    @transaction.atomic
    def atualizar(ator: Usuario, codigo: int, dados: dict) -> Usuario:
        usuario = Usuario.objects.get(pk=codigo)
        ServicoUsuarios.autorizar(ator, usuario)
        ServicoUsuarios.preencher(usuario, dados)
        usuario.save()
        return usuario

    @staticmethod
    @transaction.atomic
    def desativar(ator: Usuario, codigo: int) -> None:
        usuario = Usuario.objects.get(pk=codigo)
        ServicoUsuarios.autorizar(ator, usuario)
        ServicoUsuarios.proteger_admin(usuario)
        usuario.is_active = False
        usuario.save()

    @staticmethod
    @transaction.atomic
    def alterar_papel(ator: Usuario, codigo: int, papel: str) -> Usuario:
        ServicoUsuarios.exigir_admin(ator)
        if papel not in ('ADMIN', 'VENDEDOR', 'CLIENTE'):
            raise ValidationError({'papel': 'Papel inválido.'})
        usuario = Usuario.objects.get(pk=codigo)
        if papel != 'ADMIN':
            ServicoUsuarios.proteger_admin(usuario)
        if usuario.cadastro_pendente:
            raise ValidationError('Complete o cadastro antes de alterar o papel.')
        ServicoUsuarios.revogar(usuario)
        usuario.is_superuser = papel == 'ADMIN'
        usuario.is_staff = papel == 'ADMIN'
        usuario.save()
        usuario.groups.clear()
        usuario.user_permissions.clear()
        if papel != 'ADMIN':
            grupo, _ = Group.objects.get_or_create(name=papel)
            usuario.groups.add(grupo)
        return usuario

    @staticmethod
    @transaction.atomic
    def reativar(ator: Usuario, codigo: int, dados: dict) -> Usuario:
        ServicoUsuarios.exigir_admin(ator)
        usuario = Usuario.objects.get(pk=codigo)
        if usuario.is_active:
            raise ValidationError('A conta já está ativa.')
        if normalizar_cpf(dados.get('cpf', '')) != usuario.cpf:
            raise ValidationError({'cpf': 'O CPF não pode ser alterado.'})
        return ServicoUsuarios.cadastrar(dados)[0]

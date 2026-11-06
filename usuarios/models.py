from __future__ import annotations

from datetime import date
from typing import Any

from django.contrib.auth.models import AbstractUser, Group, Permission, UserManager
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models.expressions import Combinable
from django.db.models.functions import Lower

from usuarios.validadores import normalizar_cpf, normalizar_telefone, validar_maioridade


class GerenciadorUsuarios(UserManager):
    def create_user(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        usuario = self.model(username=username, email=email or '', **extra_fields)
        usuario.cadastro_pendente = False
        usuario.full_clean(exclude=['password'])
        if not password:
            raise ValidationError({'password': 'Informe a senha.'})
        validate_password(password, usuario)
        usuario.set_password(password)
        usuario.save(using=self._db)
        if not usuario.is_superuser:
            grupo, _ = Group.objects.get_or_create(name='CLIENTE')
            usuario.groups.add(grupo)
        return usuario

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        if not extra_fields['is_staff'] or not extra_fields['is_superuser']:
            raise ValueError('ADMIN exige is_staff e is_superuser verdadeiros.')
        return self.create_user(username, email, password, **extra_fields)


class Usuario(AbstractUser):
    email: models.EmailField[str | Combinable, str] = models.EmailField(
        'email', blank=False
    )
    first_name: models.CharField[str | int | Combinable, str] = models.CharField(
        'primeiro nome', max_length=150
    )
    last_name: models.CharField[str | int | Combinable, str] = models.CharField(
        'sobrenome', max_length=150
    )
    data_nascimento: models.DateField[date | None, date | None] = models.DateField(
        'data de nascimento', null=True, blank=True
    )
    cpf: models.CharField[str | None, str | None] = models.CharField(
        'CPF', max_length=11, unique=True, null=True, blank=True
    )
    telefone: models.CharField[str, str] = models.CharField(
        'telefone', max_length=11, blank=True
    )
    versao_autenticacao: models.PositiveIntegerField[int, int] = (
        models.PositiveIntegerField(default=1, editable=False)
    )
    cadastro_pendente: models.BooleanField[bool, bool] = models.BooleanField(
        default=False, editable=False
    )
    groups = models.ManyToManyField(
        Group,
        through='VinculoGrupo',
        blank=True,
        related_name='user_set',
        related_query_name='user',
    )
    user_permissions = models.ManyToManyField(
        Permission,
        through='VinculoPermissao',
        blank=True,
        related_name='user_set',
        related_query_name='user',
    )
    objects = GerenciadorUsuarios()
    REQUIRED_FIELDS = [
        'email',
        'first_name',
        'last_name',
        'data_nascimento',
        'cpf',
        'telefone',
    ]

    class Meta:  # type: ignore[reportIncompatibleVariableOverride]
        db_table = 'auth_user'
        swappable = 'AUTH_USER_MODEL'
        verbose_name = 'usuário'
        verbose_name_plural = 'usuários'
        constraints = [
            models.UniqueConstraint(
                Lower('email'),
                condition=~models.Q(email=''),
                name='usuario_email_unico',
            ),
            models.CheckConstraint(
                condition=~models.Q(is_superuser=True) | models.Q(is_staff=True),
                name='usuario_admin_staff',
            ),
        ]

    def __str__(self) -> str:
        return self.username

    @transaction.atomic
    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.pk:
            anterior = type(self).objects.filter(pk=self.pk).first()
            if anterior and (
                self.password != anterior.password
                or self.is_active != anterior.is_active
                or self.is_superuser != anterior.is_superuser
            ):
                from usuarios.servicos import ServicoUsuarios

                if not self.is_active or not self.is_superuser:
                    ServicoUsuarios.proteger_admin(anterior)
                self.versao_autenticacao = max(
                    self.versao_autenticacao,
                    anterior.versao_autenticacao,
                )
                ServicoUsuarios.revogar(self)
                if kwargs.get('update_fields'):
                    kwargs['update_fields'] = {
                        *kwargs['update_fields'],
                        'versao_autenticacao',
                    }
        super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):
        from usuarios.servicos import ServicoUsuarios

        ServicoUsuarios.desativar(self, self.pk)
        return 0, {}

    @property
    def papel(self) -> str:
        if self.is_superuser:
            return 'ADMIN'
        if self.groups.filter(name='VENDEDOR').exists():
            return 'VENDEDOR'
        return 'CLIENTE'

    def clean_fields(self, exclude=None) -> None:
        erros = {}
        for campo, normalizar in (
            ('cpf', normalizar_cpf),
            ('telefone', normalizar_telefone),
        ):
            if getattr(self, campo):
                try:
                    setattr(self, campo, normalizar(getattr(self, campo)))
                except ValidationError as erro:
                    erros[campo] = erro.messages
        if erros:
            raise ValidationError(erros)
        super().clean_fields(exclude=exclude)

    def clean(self) -> None:
        super().clean()
        self.email = self.email.strip().lower()
        erros: dict[str, Any] = {}
        for campo in self.REQUIRED_FIELDS:
            if not getattr(self, campo) and not self.cadastro_pendente:
                erros[campo] = 'Este campo é obrigatório.'
        for campo, funcao in [
            ('cpf', normalizar_cpf),
            ('telefone', normalizar_telefone),
        ]:
            if getattr(self, campo):
                try:
                    setattr(self, campo, funcao(getattr(self, campo)))
                except ValidationError as erro:
                    erros[campo] = erro.messages
        if self.data_nascimento:
            try:
                validar_maioridade(self.data_nascimento)
            except ValidationError as erro:
                erros['data_nascimento'] = erro.messages
        if self.pk:
            anterior = type(self).objects.filter(pk=self.pk).values('cpf').first()
            if anterior and anterior['cpf'] and anterior['cpf'] != self.cpf:
                erros['cpf'] = 'O CPF não pode ser alterado.'
        if erros:
            raise ValidationError(erros)


class VinculoGrupo(models.Model):
    usuario_id: int
    group_id: int
    usuario: models.ForeignKey[Usuario, Usuario] = models.ForeignKey(
        Usuario, db_column='user_id', on_delete=models.CASCADE
    )
    group: models.ForeignKey[Group, Group] = models.ForeignKey(
        Group, on_delete=models.CASCADE
    )

    class Meta:
        db_table = 'auth_user_groups'
        unique_together = [('usuario', 'group')]
        verbose_name = 'vínculo de grupo'
        verbose_name_plural = 'vínculos de grupos'

    def __str__(self) -> str:
        return f'{self.usuario_id}: {self.group_id}'


class VinculoPermissao(models.Model):
    usuario_id: int
    permission_id: int
    usuario: models.ForeignKey[Usuario, Usuario] = models.ForeignKey(
        Usuario, db_column='user_id', on_delete=models.CASCADE
    )
    permission: models.ForeignKey[Permission, Permission] = models.ForeignKey(
        Permission, on_delete=models.CASCADE
    )

    class Meta:
        db_table = 'auth_user_user_permissions'
        unique_together = [('usuario', 'permission')]
        verbose_name = 'vínculo de permissão'
        verbose_name_plural = 'vínculos de permissões'

    def __str__(self) -> str:
        return f'{self.usuario_id}: {self.permission_id}'

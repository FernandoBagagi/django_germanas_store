from typing import cast

from django import forms
from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

from usuarios.models import Usuario
from usuarios.servicos import CAMPOS, PRIVILEGIADOS, ServicoUsuarios


class FormularioAdmin(forms.ModelForm):
    cpf = forms.CharField(label='CPF')
    telefone = forms.CharField(label='Telefone com DDD')
    password = forms.CharField(
        label='Nova senha', required=False, strip=False, widget=forms.PasswordInput
    )

    class Meta:
        model = Usuario
        fields = [*CAMPOS, 'password']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial['password'] = ''
        if not self.instance.pk:
            self.fields['password'].required = True

    def clean(self):
        dados = super().clean() or {}
        if not self.errors:
            entrada = {c: dados[c] for c in CAMPOS if c in dados}
            if self.instance.pk and self.instance.cpf:
                entrada['cpf'] = self.instance.cpf
            if dados.get('password'):
                entrada['password'] = dados['password']
            ServicoUsuarios.preencher(self.instance, entrada, novo=not self.instance.pk)
        # ModelForm não deve sobrescrever o hash validado com senha em texto.
        dados['password'] = self.instance.password
        return dados


@admin.register(Usuario)
class AdminUsuarios(admin.ModelAdmin):
    form = FormularioAdmin
    list_display = ['username', 'email', 'papel', 'is_active']
    search_fields = ['username', 'email', 'cpf']
    list_filter = ['is_active', 'is_superuser']
    actions = [
        'desativar',
        'reativar',
        'tornar_cliente',
        'tornar_vendedor',
        'tornar_admin',
    ]
    fields = [*CAMPOS, 'password']

    def add_view(self, request, form_url='', extra_context=None):
        ServicoUsuarios.exigir_admin(cast(Usuario, request.user))
        return redirect('usuarios:novo')

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        if request.method == 'POST' and PRIVILEGIADOS.intersection(request.POST):
            raise PermissionDenied('Não é permitido enviar campos privilegiados.')
        return super().changeform_view(request, object_id, form_url, extra_context)

    @admin.action(description='Reativar conta com novos dados')
    def reativar(self, request, queryset):
        ServicoUsuarios.exigir_admin(request.user)
        if queryset.count() != 1:
            self.message_user(request, 'Selecione uma única conta.', level='error')
            return None
        return redirect('usuarios:reativar', id=queryset.get().pk)

    def get_readonly_fields(self, request, obj=None):
        return ['cpf'] if obj and obj.cpf else []

    def has_module_permission(self, request):
        usuario = request.user
        return (
            isinstance(usuario, Usuario)
            and usuario.is_superuser
            and not usuario.cadastro_pendente
        )

    def has_view_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_change_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_add_permission(self, request):
        return self.has_module_permission(request)

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        ServicoUsuarios.exigir_admin(cast(Usuario, request.user))
        obj.save()
        if not change:
            from django.contrib.auth.models import Group

            grupo, _ = Group.objects.get_or_create(name='CLIENTE')
            obj.groups.set([grupo])

    @admin.action(description='Desativar contas selecionadas')
    def desativar(self, request, queryset):
        for usuario in queryset:
            ServicoUsuarios.desativar(request.user, usuario.pk)

    def atribuir(self, request, queryset, papel):
        for usuario in queryset:
            ServicoUsuarios.alterar_papel(request.user, usuario.pk, papel)

    @admin.action(description='Definir papel CLIENTE')
    def tornar_cliente(self, request, queryset):
        self.atribuir(request, queryset, 'CLIENTE')

    @admin.action(description='Definir papel VENDEDOR')
    def tornar_vendedor(self, request, queryset):
        self.atribuir(request, queryset, 'VENDEDOR')

    @admin.action(description='Definir papel ADMIN')
    def tornar_admin(self, request, queryset):
        self.atribuir(request, queryset, 'ADMIN')

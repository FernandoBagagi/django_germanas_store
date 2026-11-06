from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordResetConfirmView
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods

from usuarios.formularios import FormularioPapel, FormularioUsuario, verificar_post
from usuarios.models import Usuario
from usuarios.servicos import ServicoUsuarios
from usuarios.tokens import gerador_recuperacao


@require_http_methods(['GET', 'POST'])
def cadastrar(request):
    return editar_formulario(request, titulo='Cadastrar')


def editar_formulario(request, usuario=None, titulo='Editar cadastro', reativar=False):
    formulario = FormularioUsuario(request.POST or None, usuario=usuario)
    if reativar:
        formulario.fields['password'].required = True
    if request.method == 'POST':
        verificar_post(request.POST)
        if formulario.is_valid():
            try:
                if reativar and usuario:
                    ServicoUsuarios.reativar(
                        request.user, usuario.pk, formulario.dados()
                    )
                elif usuario:
                    ServicoUsuarios.atualizar(
                        request.user, usuario.pk, formulario.dados()
                    )
                else:
                    ServicoUsuarios.cadastrar(formulario.dados())
                return redirect(
                    'usuarios:minha_conta'
                    if request.user.is_authenticated
                    else 'usuarios:entrar'
                )
            except ValidationError as erro:
                formulario.registrar_erros(erro)
    return render(
        request, 'usuarios/formulario.html', {'form': formulario, 'titulo': titulo}
    )


@login_required
@require_http_methods(['GET'])
def minha_conta(request):
    return render(request, 'usuarios/conta.html', {'conta': request.user})


@login_required
@require_http_methods(['GET', 'POST'])
def editar_conta(request):
    return editar_formulario(request, request.user)


@login_required
@require_http_methods(['GET', 'POST'])
def desativar_conta(request, id=None):
    conta = get_object_or_404(Usuario, pk=id or request.user.pk)
    ServicoUsuarios.autorizar(request.user, conta)
    if request.method == 'POST':
        ServicoUsuarios.desativar(request.user, conta.pk)
        if conta.pk == request.user.pk:
            logout(request)
            return redirect('/')
        return redirect('usuarios:listagem')
    return render(request, 'usuarios/confirmar.html', {'conta': conta})


@login_required
@require_http_methods(['GET'])
def listar(request):
    ServicoUsuarios.exigir_admin(request.user)
    pagina = Paginator(Usuario.objects.order_by('id'), 12).get_page(
        request.GET.get('page')
    )
    return render(request, 'usuarios/listagem.html', {'pagina': pagina})


@login_required
@require_http_methods(['GET', 'POST'])
def cadastrar_admin(request):
    ServicoUsuarios.exigir_admin(request.user)
    return editar_formulario(request, titulo='Cadastrar usuário')


@login_required
@require_http_methods(['GET', 'POST'])
def editar_usuario(request, id):
    ServicoUsuarios.exigir_admin(request.user)
    return editar_formulario(request, get_object_or_404(Usuario, pk=id))


@login_required
@require_http_methods(['GET', 'POST'])
def reativar_usuario(request, id):
    ServicoUsuarios.exigir_admin(request.user)
    return editar_formulario(
        request,
        get_object_or_404(Usuario, pk=id),
        titulo='Reativar usuário',
        reativar=True,
    )


@login_required
@require_http_methods(['GET', 'POST'])
def alterar_papel(request, id):
    ServicoUsuarios.exigir_admin(request.user)
    conta = get_object_or_404(Usuario, pk=id)
    formulario = FormularioPapel(request.POST or None, initial={'papel': conta.papel})
    if request.method == 'POST' and formulario.is_valid():
        try:
            ServicoUsuarios.alterar_papel(
                request.user, conta.pk, formulario.cleaned_data['papel']
            )
            return redirect('usuarios:listagem')
        except ValidationError as erro:
            formulario.add_error(None, erro)
    return render(
        request,
        'usuarios/formulario.html',
        {'form': formulario, 'titulo': 'Alterar papel'},
    )


@method_decorator(transaction.atomic, name='dispatch')
class ConfirmarSenha(PasswordResetConfirmView):
    token_generator = gerador_recuperacao
    template_name = 'usuarios/formulario.html'
    extra_context = {'titulo': 'Definir nova senha'}

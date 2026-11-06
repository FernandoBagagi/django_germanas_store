from django.contrib.auth import authenticate
from django.contrib.auth.forms import SetPasswordForm
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError

from usuarios.api.autenticacao import emitir_tokens, renovar_tokens
from usuarios.api.serializers import (
    AtualizacaoSerializer,
    CadastroSerializer,
    UsuarioSerializer,
)
from usuarios.formularios import solicitar_recuperacao
from usuarios.models import Usuario
from usuarios.servicos import ServicoUsuarios
from usuarios.tokens import gerador_recuperacao


class Publica(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]


class Cadastro(Publica):
    def post(self, request):
        entrada = CadastroSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        usuario, reativado = ServicoUsuarios.cadastrar(entrada.validated_data)
        return Response(
            UsuarioSerializer(usuario).data, status=200 if reativado else 201
        )


class Login(Publica):
    @transaction.atomic
    def post(self, request):
        if not all(
            isinstance(request.data.get(campo), str)
            for campo in ('username', 'password')
        ):
            raise AuthenticationFailed('Informe login e senha válidos.')
        usuario = authenticate(
            request,
            username=request.data.get('username'),
            password=request.data.get('password'),
        )
        if not isinstance(usuario, Usuario):
            raise AuthenticationFailed('Login ou senha inválidos.')
        return Response(emitir_tokens(usuario))

    def get_authenticate_header(self, request):
        return 'Bearer'


class Renovacao(Login):
    def post(self, request):
        valor = request.data.get('refresh')
        if not isinstance(valor, str) or not valor:
            raise AuthenticationFailed('Informe um refresh token válido.')
        try:
            return Response(renovar_tokens(valor))
        except (TokenError, KeyError) as erro:
            raise AuthenticationFailed('Refresh token inválido ou expirado.') from erro


class Recuperacao(Publica):
    def post(self, request):
        solicitar_recuperacao(request.data.get('email', ''), request)
        return Response(
            {'detail': 'Se a conta estiver disponível, enviaremos um link por email.'}
        )


class ConfirmacaoSenha(Publica):
    @transaction.atomic
    def post(self, request):
        if not all(
            isinstance(request.data.get(campo), str)
            for campo in ('uid', 'token', 'password')
        ):
            raise ValidationError('Informe uid, token e senha válidos.')
        try:
            codigo = force_str(urlsafe_base64_decode(request.data.get('uid', '')))
            usuario = Usuario.objects.get(pk=codigo, is_active=True)
        except (
            ValueError,
            TypeError,
            OverflowError,
            UnicodeDecodeError,
            Usuario.DoesNotExist,
        ):
            raise ValidationError('Link inválido ou expirado.') from None
        if not gerador_recuperacao.check_token(usuario, request.data.get('token', '')):
            raise ValidationError('Link inválido ou expirado.')
        senha = request.data.get('password', '')
        formulario = SetPasswordForm(
            usuario, {'new_password1': senha, 'new_password2': senha}
        )
        if not formulario.is_valid():
            raise ValidationError(
                {'password': [e for erros in formulario.errors.values() for e in erros]}
            )
        formulario.save()
        return Response({'detail': 'Senha redefinida. Entre novamente.'})


class Usuarios(APIView):
    def get(self, request):
        ServicoUsuarios.exigir_admin(request.user)
        paginador = PageNumberPagination()
        paginador.page_size = 12
        pagina = paginador.paginate_queryset(Usuario.objects.order_by('id'), request)
        return paginador.get_paginated_response(
            UsuarioSerializer(pagina, many=True).data
        )

    def post(self, request):
        ServicoUsuarios.exigir_admin(request.user)
        entrada = CadastroSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        usuario, reativado = ServicoUsuarios.cadastrar(entrada.validated_data)
        return Response(
            UsuarioSerializer(usuario).data, status=200 if reativado else 201
        )


class DetalheUsuario(APIView):
    def obter(self, request, id=None):
        usuario = get_object_or_404(Usuario, pk=id or request.user.pk)
        ServicoUsuarios.autorizar(request.user, usuario)
        return usuario

    def get(self, request, id=None):
        return Response(UsuarioSerializer(self.obter(request, id)).data)

    def patch(self, request, id=None):
        return self.atualizar(request, id, parcial=True)

    def put(self, request, id=None):
        return self.atualizar(request, id, parcial=False)

    def atualizar(self, request, id, parcial):
        usuario = self.obter(request, id)
        entrada = AtualizacaoSerializer(data=request.data, partial=parcial)
        entrada.is_valid(raise_exception=True)
        usuario = ServicoUsuarios.atualizar(
            request.user, usuario.pk, entrada.validated_data
        )
        return Response(UsuarioSerializer(usuario).data)

    def delete(self, request, id=None):
        usuario = self.obter(request, id)
        ServicoUsuarios.desativar(request.user, usuario.pk)
        return Response(status=204)


class MinhaConta(DetalheUsuario):
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']


class AlteracaoPapel(APIView):
    def post(self, request, id):
        ServicoUsuarios.exigir_admin(request.user)
        get_object_or_404(Usuario, pk=id)
        if set(request.data) != {'papel'}:
            raise ValidationError('Informe somente o papel.')
        usuario = ServicoUsuarios.alterar_papel(request.user, id, request.data['papel'])
        return Response(UsuarioSerializer(usuario).data)


class Reativacao(APIView):
    def post(self, request, id):
        ServicoUsuarios.exigir_admin(request.user)
        get_object_or_404(Usuario, pk=id)
        entrada = CadastroSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        usuario = ServicoUsuarios.reativar(request.user, id, entrada.validated_data)
        return Response(UsuarioSerializer(usuario).data)

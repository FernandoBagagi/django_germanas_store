import re
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from faker import Faker
from rest_framework.test import APIClient

from usuarios.models import Usuario
from usuarios.servicos import ServicoUsuarios
from usuarios.tokens import gerador_recuperacao

pytestmark = pytest.mark.django_db


def dados_outro(dados):
    fake = Faker('pt_BR')
    return {
        **dados,
        'username': fake.unique.user_name(),
        'email': fake.unique.email(),
        'cpf': fake.cpf(),
    }


def test_web_cadastro_edicao(dados_usuario):
    web = Client()
    assert web.post('/usuarios/cadastrar/', dados_usuario).status_code == 302
    usuario = Usuario.objects.get()
    assert web.login(username=usuario.username, password=dados_usuario['password'])
    novos = {**dados_usuario, 'first_name': Faker('pt_BR').first_name(), 'password': ''}
    assert web.post('/usuarios/minha_conta/editar/', novos).status_code == 302
    usuario.refresh_from_db()
    assert usuario.first_name == novos['first_name']
    assert usuario.check_password(dados_usuario['password'])
    novos['is_staff'] = True
    assert web.post('/usuarios/minha_conta/editar/', novos).status_code == 403


def test_web_admin_fluxos(administrador, dados_usuario):
    web = Client()
    web.force_login(administrador)
    dados = dados_outro(dados_usuario)
    assert web.post('/usuarios/novo/', dados).status_code == 302
    conta = Usuario.objects.get(username=dados['username'])
    assert web.get('/usuarios/').status_code == 200
    assert web.get(f'/usuarios/{conta.pk}/editar/').status_code == 200
    assert (
        web.post(
            f'/usuarios/{conta.pk}/alterar_papel/', {'papel': 'VENDEDOR'}
        ).status_code
        == 302
    )
    conta.refresh_from_db()
    assert conta.papel == 'VENDEDOR'
    assert conta.has_perm('produtos.add_produto')
    assert web.post(f'/usuarios/{conta.pk}/desativar/').status_code == 302
    assert web.post(f'/usuarios/{conta.pk}/reativar/', dados).status_code == 302
    conta.refresh_from_db()
    assert conta.is_active and conta.papel == 'CLIENTE'
    assert conta.has_perm('produtos.view_produto')


def test_admin_edicao_sem_senha_preserva_hash(administrador, dados_usuario):
    web = Client()
    web.force_login(administrador)
    dados = dados_outro(dados_usuario)
    conta = ServicoUsuarios.cadastrar(dados)[0]
    anterior = conta.password
    dados['password'] = ''
    dados['first_name'] = Faker('pt_BR').first_name()
    dados['_save'] = 'Salvar'
    url = reverse('admin:usuarios_usuario_change', args=[conta.pk])
    resposta = web.post(url, dados)
    assert resposta.status_code == 302, resposta.context['adminform'].form.errors
    conta.refresh_from_db()
    assert conta.password == anterior
    assert conta.first_name == dados['first_name']
    dados['is_superuser'] = True
    assert web.post(url, dados).status_code == 403
    assert web.get(reverse('admin:usuarios_usuario_add')).status_code == 302


def test_recuperacao_web(usuario, mailoutbox):
    web = Client()
    assert (
        web.post('/usuarios/redefinir_senha/', {'email': usuario.email}).status_code
        == 302
    )
    correspondencia = re.search(r'https?://[^\s]+', mailoutbox[0].body)
    assert correspondencia is not None
    url = correspondencia.group()
    resposta = web.get(url)
    assert resposta.status_code == 302
    confirmacao = resposta['Location']
    anterior = usuario.password
    assert web.get(confirmacao).status_code == 200
    usuario.refresh_from_db()
    assert usuario.password == anterior
    senha = Faker('pt_BR').password(length=24)
    assert (
        web.post(
            confirmacao, {'new_password1': senha, 'new_password2': senha}
        ).status_code
        == 302
    )
    usuario.refresh_from_db()
    assert usuario.check_password(senha)


def test_recuperacao_expirada(usuario):
    token = gerador_recuperacao.make_token(usuario)
    futuro = timezone.now().replace(tzinfo=None) + timedelta(hours=2)
    with patch.object(gerador_recuperacao, '_now', return_value=futuro):
        assert not gerador_recuperacao.check_token(usuario, token)


def test_falha_email_preserva_senha(usuario):
    api = APIClient()
    api.raise_request_exception = False
    anterior = usuario.password
    with patch(
        'django.contrib.auth.forms.PasswordResetForm.send_mail',
        side_effect=OSError('Falha no envio'),
    ):
        assert (
            api.post(
                '/api/v1/usuarios/redefinir_senha/', {'email': usuario.email}
            ).status_code
            == 500
        )
    usuario.refresh_from_db()
    assert usuario.password == anterior


def test_email_conta_inativa(usuario, mailoutbox):
    ServicoUsuarios.desativar(usuario, usuario.pk)
    assert (
        APIClient()
        .post('/api/v1/usuarios/redefinir_senha/', {'email': usuario.email})
        .status_code
        == 200
    )
    assert len(mailoutbox) == 0


def test_link_antigo_nao_revive(usuario, dados_usuario):
    token = gerador_recuperacao.make_token(usuario)
    ServicoUsuarios.desativar(usuario, usuario.pk)
    conta, _ = ServicoUsuarios.cadastrar(dados_usuario)
    assert not gerador_recuperacao.check_token(conta, token)


def test_logout_preserva_outra_sessao(usuario):
    primeira, segunda = Client(), Client()
    primeira.force_login(usuario)
    segunda.force_login(usuario)
    assert primeira.post('/usuarios/sair/').status_code == 302
    assert segunda.get('/usuarios/minha_conta/').status_code == 200


def test_legado_admin_sem_acesso_admin(administrador):
    Usuario.objects.filter(pk=administrador.pk).update(cadastro_pendente=True)
    administrador.refresh_from_db()
    web = Client()
    web.force_login(administrador)
    assert web.get('/admin/').status_code == 403
    assert web.get('/usuarios/minha_conta/').status_code == 200

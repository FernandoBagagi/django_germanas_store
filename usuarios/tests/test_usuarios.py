from datetime import date, timedelta

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import Client
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from usuarios.api.autenticacao import emitir_tokens
from usuarios.models import Usuario
from usuarios.servicos import CAMPOS, PRIVILEGIADOS, ServicoUsuarios
from usuarios.tokens import gerador_recuperacao
from usuarios.validadores import normalizar_telefone, validar_maioridade

pytestmark = pytest.mark.django_db


def cliente(usuario):
    api = APIClient()
    api.credentials(HTTP_AUTHORIZATION=f'Bearer {emitir_tokens(usuario)["access"]}')
    return api


def test_cadastro_publico_normalizacao(dados_usuario):
    resposta = APIClient().post('/api/v1/usuarios/cadastrar/', dados_usuario)
    assert resposta.status_code == 201, resposta.data
    assert resposta.data['papel'] == 'CLIENTE'
    assert resposta.data['cpf'].isdigit()
    usuario = Usuario.objects.get(pk=resposta.data['id'])
    assert usuario.check_password(dados_usuario['password'])
    assert 'password' not in resposta.data
    assert usuario.password not in str(resposta.data)


@pytest.mark.parametrize('campo', [*CAMPOS, 'password'])
def test_obrigatorios(campo, dados_usuario):
    dados_usuario.pop(campo)
    resposta = APIClient().post('/api/v1/usuarios/cadastrar/', dados_usuario)
    assert resposta.status_code == 400
    assert campo in resposta.data


@pytest.mark.parametrize('campo', sorted(PRIVILEGIADOS))
def test_privilegios_rejeitados(campo, dados_usuario, usuario):
    api = APIClient()
    dados_usuario[campo] = True
    assert api.post('/api/v1/usuarios/cadastrar/', dados_usuario).status_code == 403
    assert (
        cliente(usuario)
        .patch('/api/v1/usuarios/minha_conta/', {campo: True})
        .status_code
        == 403
    )


@pytest.mark.parametrize(
    'campo,valor',
    [
        ('cpf', '11111111111'),
        ('cpf', 'texto'),
        ('telefone', '123'),
        ('telefone', '+1 212 555 1234'),
        ('telefone', '00912345678'),
        ('data_nascimento', '2030-01-01'),
        ('data_nascimento', '01/01/1990'),
        ('password', ''),
        ('password', '12345678'),
    ],
)
def test_dados_invalidos(campo, valor, dados_usuario):
    dados_usuario[campo] = valor
    assert (
        APIClient().post('/api/v1/usuarios/cadastrar/', dados_usuario).status_code
        == 400
    )


def test_idade_fronteiras(monkeypatch):
    monkeypatch.setattr(timezone, 'localdate', lambda **kw: date(2026, 2, 28))
    validar_maioridade(date(2008, 2, 28))
    with pytest.raises(ValidationError):
        validar_maioridade(date(2008, 2, 29))
    monkeypatch.setattr(timezone, 'localdate', lambda **kw: date(2026, 3, 1))
    validar_maioridade(date(2008, 2, 29))


def test_telefone():
    assert normalizar_telefone('+55 (71) 91234-5678') == '71912345678'
    assert normalizar_telefone('(11) 2345-6789') == '1123456789'


def test_login_expiracao_rotacao(usuario, dados_usuario):
    api = APIClient()
    resposta = api.post(
        '/api/v1/usuarios/login/',
        {
            'username': usuario.username,
            'password': dados_usuario['password'],
        },
    )
    assert resposta.status_code == 200
    access = AccessToken(resposta.data['access'])
    refresh = RefreshToken(resposta.data['refresh'])
    assert int(access['exp']) - int(access['iat']) == 1800
    assert int(refresh['exp']) - int(refresh['iat']) == 86400
    assert set(access.payload) == {
        'token_type',
        'exp',
        'iat',
        'jti',
        'user_id',
        'versao_autenticacao',
    }
    nova = api.post('/api/v1/usuarios/renovar/', {'refresh': str(refresh)})
    assert nova.status_code == 200
    assert nova.data['refresh'] != str(refresh)
    assert (
        api.post('/api/v1/usuarios/renovar/', {'refresh': str(refresh)}).status_code
        == 401
    )
    assert (
        api.post(
            '/api/v1/usuarios/login/',
            {'username': usuario.username, 'password': 'errada'},
        ).status_code
        == 401
    )


def test_token_expirado(usuario):
    token = AccessToken(emitir_tokens(usuario)['access'])  # type: ignore[arg-type]
    token.set_exp(lifetime=timedelta(seconds=-1))
    api = APIClient()
    api.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    assert api.get('/api/v1/produtos/').status_code == 401


def test_desativacao_reativacao_revogacao(usuario, dados_usuario):
    api = cliente(usuario)
    refresh = emitir_tokens(usuario)['refresh']
    identificador = usuario.pk
    assert api.delete('/api/v1/usuarios/minha_conta/').status_code == 204
    assert api.get('/api/v1/usuarios/minha_conta/').status_code == 401
    assert (
        APIClient().post('/api/v1/usuarios/renovar/', {'refresh': refresh}).status_code
        == 401
    )
    resposta = APIClient().post('/api/v1/usuarios/cadastrar/', dados_usuario)
    assert resposta.status_code == 200, resposta.data
    assert resposta.data['id'] == identificador
    assert resposta.data['papel'] == 'CLIENTE'
    assert api.get('/api/v1/usuarios/minha_conta/').status_code == 401


def test_atualizacao_senha_e_sessao(usuario, dados_usuario):
    api = cliente(usuario)
    web = Client()
    web.force_login(usuario)
    assert web.get('/usuarios/minha_conta/').status_code == 200
    assert (
        api.patch(
            '/api/v1/usuarios/minha_conta/', {'telefone': '71987654321'}
        ).status_code
        == 200
    )
    usuario.refresh_from_db()
    assert usuario.check_password(dados_usuario['password'])
    refresh = emitir_tokens(usuario)['refresh']
    assert (
        api.patch(
            '/api/v1/usuarios/minha_conta/', {'password': 'Senha-nova-segura!921'}
        ).status_code
        == 200
    )
    assert api.get('/api/v1/usuarios/minha_conta/').status_code == 401
    assert (
        APIClient().post('/api/v1/usuarios/renovar/', {'refresh': refresh}).status_code
        == 401
    )
    assert web.get('/usuarios/minha_conta/').status_code == 302


def test_recuperacao(usuario, dados_usuario, mailoutbox):
    api = APIClient()
    tokens = emitir_tokens(usuario)
    resposta = api.post('/api/v1/usuarios/redefinir_senha/', {'email': usuario.email})
    assert resposta.status_code == 200
    assert len(mailoutbox) == 1
    assert '/usuarios/confirmar_senha/' in mailoutbox[0].body
    assert dados_usuario['password'] not in mailoutbox[0].body
    usuario.refresh_from_db()
    assert usuario.check_password(dados_usuario['password'])
    dados = {
        'uid': urlsafe_base64_encode(force_bytes(usuario.pk)),
        'token': gerador_recuperacao.make_token(usuario),
        'password': 'Nova-senha-segura!385',
    }
    assert api.post('/api/v1/usuarios/confirmar_senha/', dados).status_code == 200
    assert api.post('/api/v1/usuarios/confirmar_senha/', dados).status_code == 400
    assert (
        api.post(
            '/api/v1/usuarios/renovar/', {'refresh': tokens['refresh']}
        ).status_code
        == 401
    )
    assert (
        api.post(
            '/api/v1/usuarios/redefinir_senha/', {'email': 'ausente@example.com'}
        ).data
        == resposta.data
    )


def test_admin_ultimo_e_promocao(administrador, dados_usuario):
    api = cliente(administrador)
    assert api.delete('/api/v1/usuarios/minha_conta/').status_code == 403
    assert (
        api.post(
            f'/api/v1/usuarios/{administrador.pk}/alterar_papel/', {'papel': 'CLIENTE'}
        ).status_code
        == 403
    )
    dados_usuario.update(
        username='outro_admin', email='outro@example.com', cpf='52998224725'
    )
    outro = ServicoUsuarios.cadastrar(dados_usuario)[0]
    assert (
        api.post(
            f'/api/v1/usuarios/{outro.pk}/alterar_papel/', {'papel': 'ADMIN'}
        ).status_code
        == 200
    )
    outro.refresh_from_db()
    assert outro.is_staff and outro.is_superuser
    assert api.delete('/api/v1/usuarios/minha_conta/').status_code == 204


def test_usuario_alheio(usuario, dados_usuario):
    dados_usuario.update(username='outro', email='outro@example.com', cpf='52998224725')
    outro = ServicoUsuarios.cadastrar(dados_usuario)[0]
    api = cliente(usuario)
    for metodo in ('get', 'patch', 'delete'):
        assert getattr(api, metodo)(f'/api/v1/usuarios/{outro.pk}/').status_code == 403
    assert api.get('/api/v1/usuarios/').status_code == 403
    assert api.get('/api/v1/usuarios/999999/').status_code == 404


def test_identificadores_reservados(usuario, dados_usuario):
    ServicoUsuarios.desativar(usuario, usuario.pk)
    dados_usuario['cpf'] = '52998224725'
    assert (
        APIClient().post('/api/v1/usuarios/cadastrar/', dados_usuario).status_code
        == 400
    )
    usuario.refresh_from_db()
    assert not usuario.is_active


def test_email_sem_caixa_e_cpf_imutavel(usuario, dados_usuario):
    dados_usuario.update(
        username='outro', cpf='52998224725', email=usuario.email.upper()
    )
    assert (
        APIClient().post('/api/v1/usuarios/cadastrar/', dados_usuario).status_code
        == 400
    )
    assert (
        cliente(usuario)
        .patch('/api/v1/usuarios/minha_conta/', {'cpf': '52998224725'})
        .status_code
        == 400
    )


def test_legado_regularizacao(usuario, dados_usuario):
    Usuario.objects.filter(pk=usuario.pk).update(
        cpf=None, cadastro_pendente=True, telefone=''
    )
    usuario.refresh_from_db()
    api = cliente(usuario)
    assert api.get('/api/v1/usuarios/minha_conta/').status_code == 200
    assert api.get('/api/v1/produtos/').status_code == 403
    assert (
        api.patch(
            '/api/v1/usuarios/minha_conta/',
            {'cpf': dados_usuario['cpf'], 'telefone': dados_usuario['telefone']},
        ).status_code
        == 200
    )
    assert api.get('/api/v1/produtos/').status_code == 200


def test_web_navegacao_logout_csrf(usuario):
    web = Client(enforce_csrf_checks=True)
    assert 'Cadastrar' in web.get('/').content.decode()
    assert web.post('/usuarios/entrar/', {}).status_code == 403
    web.force_login(usuario)
    pagina = web.get('/usuarios/minha_conta/')
    assert 'Minha conta' in pagina.content.decode()
    assert web.get('/usuarios/sair/').status_code == 405
    assert web.get('/usuarios/minha_conta/desativar/').status_code == 200
    usuario.refresh_from_db()
    assert usuario.is_active
    assert (
        web.post(
            '/usuarios/sair/', {'csrfmiddlewaretoken': web.cookies['csrftoken'].value}
        ).status_code
        == 302
    )


@pytest.mark.parametrize('papel', ['ADMIN', 'VENDEDOR', 'CLIENTE'])
def test_produtos_papeis(administrador, dados_usuario, papel):
    dados_usuario.update(
        username='comprador', email='comprador@example.com', cpf='52998224725'
    )
    usuario = ServicoUsuarios.cadastrar(dados_usuario)[0]
    ServicoUsuarios.alterar_papel(administrador, usuario.pk, papel)
    usuario.refresh_from_db()
    api = cliente(usuario)
    assert api.get('/api/v1/produtos/').status_code == 200
    dados = {
        'nome_comercial': 'Produto de teste',
        'descricao': 'Descrição',
        'url_imagem': 'https://example.com/produto.png',
        'preco': '12.34',
    }
    resposta = api.post('/api/v1/produtos/', dados)
    assert resposta.status_code == (403 if papel == 'CLIENTE' else 201)
    if papel != 'CLIENTE':
        url = f'/api/v1/produtos/{resposta.data["id"]}/'
        assert api.patch(url, {'preco': '-1'}).status_code == 400
        assert api.patch(url, {'preco': '23.45'}).status_code == 200
        assert api.delete(url).status_code == 204
    assert APIClient().get('/api/v1/produtos/').status_code == 401


def test_admin_formulario_hash(administrador):
    web = Client()
    web.force_login(administrador)
    resposta = web.get(f'/admin/usuarios/usuario/{administrador.pk}/change/')
    assert resposta.status_code == 200
    assert administrador.password not in resposta.content.decode()


def test_delete_modelo_soft(usuario):
    usuario.delete()
    usuario.refresh_from_db()
    assert not usuario.is_active


def test_ultimo_admin_modelo(administrador):
    administrador.is_superuser = False
    with pytest.raises(PermissionDenied):
        administrador.save()

from datetime import timedelta
from html.parser import HTMLParser

import pytest
from django.test import Client
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from usuarios.api.autenticacao import emitir_tokens
from usuarios.models import Usuario

pytestmark = pytest.mark.django_db


@pytest.fixture
def api(usuario):
    cliente = APIClient()
    cliente.credentials(HTTP_AUTHORIZATION=f'Bearer {emitir_tokens(usuario)["access"]}')
    return cliente


@pytest.mark.parametrize(
    'valor',
    [
        '1990-4-15',
        '1990-04-5',
        '15/04/1990',
        '1990-02-30',
        '1990-04-15T00:00:00',
        ' 1990-04-15 ',
        '１９９０-０４-１５',
    ],
)
def test_f01_cadastro_rejeita_data_fora_contrato(dados_usuario, valor):
    dados_usuario['data_nascimento'] = valor
    resposta = APIClient().post(
        '/api/v1/usuarios/cadastrar/', dados_usuario, format='json'
    )
    assert resposta.status_code == 400
    assert 'data_nascimento' in resposta.data
    assert not Usuario.objects.exists()


@pytest.mark.parametrize('valor', ['1990-4-15', '1990-04-5', '1990-02-30'])
def test_f01_patch_rejeita_sem_alterar(api, usuario, valor):
    anterior = usuario.data_nascimento
    resposta = api.patch('/api/v1/usuarios/minha_conta/', {'data_nascimento': valor})
    assert resposta.status_code == 400
    usuario.refresh_from_db()
    assert usuario.data_nascimento == anterior


def test_f01_iso_valido_cadastro_e_patch(dados_usuario):
    dados_usuario['data_nascimento'] = '1990-04-15'
    resposta = APIClient().post('/api/v1/usuarios/cadastrar/', dados_usuario)
    assert resposta.status_code == 201
    assert resposta.data['data_nascimento'] == '1990-04-15'
    conta = Usuario.objects.get(pk=resposta.data['id'])
    cliente = APIClient()
    cliente.credentials(HTTP_AUTHORIZATION=f'Bearer {emitir_tokens(conta)["access"]}')
    resposta = cliente.patch(
        '/api/v1/usuarios/minha_conta/', {'data_nascimento': '1990-04-05'}
    )
    assert resposta.status_code == 200
    assert resposta.data['data_nascimento'] == '1990-04-05'


class CamposHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.campos = {}

    def handle_starttag(self, tag, attrs):
        atributos = dict(attrs)
        if tag == 'input' and atributos.get('name'):
            self.campos[atributos['name']] = atributos


@pytest.mark.parametrize('valor', ['16/04/1990', '1990-4-16', '1990-04-6'])
def test_f02_admin_exibe_iso_rejeita_outros(administrador, dados_usuario, valor):
    web = Client()
    web.force_login(administrador)
    url = f'/admin/usuarios/usuario/{administrador.pk}/change/'
    campos = CamposHTML()
    campos.feed(web.get(url).content.decode())
    assert (
        campos.campos['data_nascimento']['value']
        == administrador.data_nascimento.isoformat()
    )
    anterior = administrador.data_nascimento
    dados = {
        **dados_usuario,
        'password': '',
        'data_nascimento': valor,
        '_save': 'Salvar',
    }
    resposta = web.post(url, dados)
    assert resposta.status_code == 200
    assert 'data_nascimento' in resposta.context['adminform'].form.errors
    administrador.refresh_from_db()
    assert administrador.data_nascimento == anterior
    dados['data_nascimento'] = '1990-04-16'
    assert web.post(url, dados).status_code == 302
    administrador.refresh_from_db()
    assert administrador.data_nascimento.isoformat() == '1990-04-16'


def test_f02_web_rejeita_data_sem_zero(dados_usuario):
    dados_usuario['data_nascimento'] = '1990-4-15'
    resposta = Client().post('/usuarios/cadastrar/', dados_usuario)
    assert resposta.status_code == 200
    assert 'data_nascimento' in resposta.context['form'].errors
    assert not Usuario.objects.exists()


@pytest.mark.parametrize('tipo', ['malformado', 'expirado', 'refresh'])
def test_f03_jwt_mensagens_portugues(usuario, tipo):
    tokens = emitir_tokens(usuario)
    valor = 'invalid.jwt.token'
    if tipo == 'expirado':
        token = AccessToken(tokens['access'])  # type: ignore[arg-type]
        token.set_exp(lifetime=timedelta(seconds=-1))
        valor = str(token)
    elif tipo == 'refresh':
        valor = tokens['refresh']
    cliente = APIClient()
    cliente.credentials(HTTP_AUTHORIZATION=f'Bearer {valor}')
    resposta = cliente.get('/api/v1/produtos/')
    assert resposta.status_code == 401
    assert resposta['WWW-Authenticate'].startswith('Bearer')
    assert resposta.data['code'] == 'token_not_valid'
    assert str(resposta.data['detail']) == 'Token inválido ou expirado.'
    for mensagem in resposta.data['messages']:
        assert str(mensagem['message']) == 'Token inválido ou expirado.'
        assert mensagem['token_class'] == 'AccessToken'
        assert mensagem['token_type'] == 'access'
    cliente.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
    assert cliente.get('/api/v1/produtos/').status_code == 200


@pytest.mark.parametrize(
    'campo,valor',
    [
        ('id', 7777777),
        ('last_login', '2026-11-07T00:00:00Z'),
        ('date_joined', '2026-11-07T00:00:00Z'),
    ],
)
def test_f04_controles_internos_403(api, usuario, dados_usuario, campo, valor):
    anterior = (usuario.pk, usuario.last_login, usuario.date_joined)
    assert api.patch('/api/v1/usuarios/minha_conta/', {campo: valor}).status_code == 403
    dados_usuario[campo] = valor
    assert (
        APIClient().post('/api/v1/usuarios/cadastrar/', dados_usuario).status_code
        == 403
    )
    usuario.refresh_from_db()
    assert anterior == (usuario.pk, usuario.last_login, usuario.date_joined)
    assert (
        api.patch(
            '/api/v1/usuarios/minha_conta/', {'campo_inexistente': 'x'}
        ).status_code
        == 400
    )

import pytest
from faker import Faker

from usuarios.servicos import ServicoUsuarios


@pytest.fixture(autouse=True)
def senha_rapida(settings):
    settings.PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']


@pytest.fixture
def dados_usuario():
    gerador = Faker('pt_BR')
    return {
        'username': gerador.unique.user_name(),
        'email': gerador.unique.email(),
        'first_name': gerador.first_name(),
        'last_name': gerador.last_name(),
        'data_nascimento': gerador.date_of_birth(minimum_age=20, maximum_age=80),
        'cpf': gerador.cpf(),
        'telefone': gerador.numerify('719########'),
        'password': gerador.password(length=24),
    }


@pytest.fixture
def usuario(dados_usuario):
    return ServicoUsuarios.cadastrar(dados_usuario)[0]


@pytest.fixture
def administrador(dados_usuario):
    from usuarios.models import Usuario

    return Usuario.objects.create_superuser(**dados_usuario)

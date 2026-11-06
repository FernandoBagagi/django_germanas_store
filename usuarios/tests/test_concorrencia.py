import os

from usuarios.tests.test_migracoes import executar


def test_operacoes_concorrentes(tmp_path):
    ambiente = {
        **os.environ,
        'DJANGO_SETTINGS_MODULE': 'config.settings',
        'GERMANAS_BANCO': str(tmp_path / 'concorrencia.sqlite3'),
    }
    executar(
        """
import django
django.setup()
from django.core.management import call_command
call_command('migrate', verbosity=0)
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from django.db import connections
from django.core.exceptions import PermissionDenied, ValidationError
from faker import Faker
from usuarios.models import Usuario
from usuarios.servicos import ServicoUsuarios
from usuarios.api.autenticacao import emitir_tokens, renovar_tokens
from rest_framework_simplejwt.exceptions import TokenError
fake=Faker('pt_BR')
def dados():
    return dict(username=fake.unique.user_name(), email=fake.unique.email(),
                first_name=fake.first_name(), last_name=fake.last_name(),
                cpf=fake.cpf(), telefone=fake.numerify('719########'),
                data_nascimento=fake.date_of_birth(minimum_age=20, maximum_age=70),
                password=fake.password(length=24))
a=Usuario.objects.create_superuser(**dados())
b=Usuario.objects.create_superuser(**dados())
barreira=Barrier(2)
def desativar(codigo):
    try:
        ator=Usuario.objects.get(pk=codigo)
        barreira.wait()
        ServicoUsuarios.desativar(ator, codigo)
        return True
    except PermissionDenied:
        return False
    finally:
        connections.close_all()
with ThreadPoolExecutor(max_workers=2) as pool:
    assert sorted(pool.map(desativar, [a.pk,b.pk])) == [False,True]
assert Usuario.objects.filter(is_superuser=True,is_active=True).count()==1
u=Usuario.objects.filter(is_superuser=True,is_active=True).get()
refresh=emitir_tokens(u)['refresh']
barreira=Barrier(2)
def renovar(_):
    try:
        barreira.wait()
        renovar_tokens(refresh)
        return True
    except TokenError:
        return False
    finally:
        connections.close_all()
with ThreadPoolExecutor(max_workers=2) as pool:
    assert sorted(pool.map(renovar, range(2))) == [False,True]
dados_cliente=dados()
u,_=ServicoUsuarios.cadastrar(dados_cliente)
ServicoUsuarios.desativar(u,u.pk)
barreira=Barrier(2)
def reativar(_):
    try:
        barreira.wait()
        novo,reativado=ServicoUsuarios.cadastrar(dados_cliente)
        assert novo.pk==u.pk and reativado
        return True
    except ValidationError:
        return False
    finally:
        connections.close_all()
with ThreadPoolExecutor(max_workers=2) as pool:
    assert sorted(pool.map(reativar, range(2))) == [False,True]
""",
        ambiente,
    )

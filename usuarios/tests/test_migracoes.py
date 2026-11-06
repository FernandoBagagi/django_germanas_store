import os
import subprocess
import sys

import pytest


def executar(codigo, ambiente):
    resultado = subprocess.run(
        [sys.executable, '-c', codigo],
        env=ambiente,
        capture_output=True,
        text=True,
        check=False,
    )
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr


@pytest.mark.parametrize('duplicado', [False, True])
def test_migracao_preserva_legado(tmp_path, duplicado):
    ambiente = {**os.environ, 'GERMANAS_BANCO': str(tmp_path / 'legado.sqlite3')}
    ambiente.pop('DJANGO_SETTINGS_MODULE', None)
    ambiente['DUPLICADO'] = '1' if duplicado else '0'
    executar(
        """
import os
from django.conf import settings
settings.configure(
    SECRET_KEY='teste', USE_TZ=True,
    INSTALLED_APPS=['django.contrib.auth', 'django.contrib.contenttypes',
                   'django.contrib.admin', 'django.contrib.sessions', 'produtos'],
    DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3',
                          'NAME': os.environ['GERMANAS_BANCO']}},
)
import django
django.setup()
from django.core.management import call_command
call_command('migrate', verbosity=0, skip_checks=True)
from django.contrib.auth.models import User, Group
from django.contrib.admin.models import LogEntry
from produtos.models import Produto
from faker import Faker
fake=Faker('pt_BR')
u=User.objects.create_superuser(username=fake.user_name(), email=fake.email(),
                               password=fake.password())
grupo=Group.objects.create(name='Legado')
u.groups.add(grupo)
LogEntry.objects.create(user=u, object_repr='preservado', action_flag=1)
Produto.objects.create(nome_comercial=fake.word(), descricao=fake.text(),
                       url_imagem=fake.image_url(), preco='12.34')
if os.environ['DUPLICADO']=='1':
    User.objects.create_user(username=fake.unique.user_name(),email=u.email.upper())
""",
        ambiente,
    )
    ambiente['DJANGO_SETTINGS_MODULE'] = 'config.settings'
    ambiente['GERMANAS_PREPARAR_USUARIOS'] = '1'
    resultado = subprocess.run(
        [
            sys.executable,
            'manage.py',
            'migrate',
            'usuarios',
            '--skip-checks',
            '--noinput',
        ],
        env=ambiente,
        capture_output=True,
        text=True,
        check=False,
    )
    if duplicado:
        assert resultado.returncode != 0
        assert 'emails duplicados' in resultado.stderr
        return
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    ambiente.pop('GERMANAS_PREPARAR_USUARIOS')
    executar(
        """
import django
django.setup()
from django.core.management import call_command
call_command('migrate', verbosity=0)
call_command('check', verbosity=0)
from usuarios.models import Usuario
from django.contrib.admin.models import LogEntry
from produtos.models import Produto
u=Usuario.objects.get(pk=1)
assert u.is_superuser and u.is_staff and u.cadastro_pendente
assert u.password and u.groups.filter(name='Legado').exists()
assert LogEntry.objects.get().user_id==u.id
assert Produto.objects.count()==1
assert u.cpf is None
""",
        ambiente,
    )

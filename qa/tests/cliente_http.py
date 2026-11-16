"""Suporte HTTP reconstruído dos roteiros de 07/11/2026; ver qa/AGENTS.md."""

import http.cookiejar
import json
import os
import re
import secrets
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

from faker import Faker

Resposta = dict[str, Any]
DADOS = Faker('pt_BR')


class SemRedirecionamento(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def sessao() -> urllib.request.OpenerDirector:
    return urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),
        SemRedirecionamento(),
    )


class Roteiro:
    def __init__(self) -> None:
        self.url = os.environ.get('QA_URL', 'http://127.0.0.1:8000').rstrip('/')
        destino = urllib.parse.urlsplit(self.url)
        if destino.hostname not in ('localhost', '127.0.0.1', '::1'):
            raise ValueError('QA_URL deve apontar para um servidor local.')
        pasta = os.environ.get('QA_EXECUCAO')
        if not pasta:
            raise ValueError('Defina QA_EXECUCAO como uma pasta temporária externa.')
        self.pasta = Path(pasta).resolve()
        raiz = Path(__file__).resolve().parents[2]
        if self.pasta == raiz or raiz in self.pasta.parents:
            raise ValueError('QA_EXECUCAO deve ficar fora do repositório.')
        self.pasta.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.falhas = 0
        self.criados: list[dict[str, Any]] = []
        self.produtos: list[int] = []
        self.admin = ''
        self.prefixo = 'qa_' + secrets.token_hex(5) + '_'

    def requisitar(
        self,
        metodo: str,
        caminho: str,
        dados: Any = None,
        token: str = '',
        navegador: Any = None,
        formulario: bool = False,
    ) -> Resposta:
        destino = urllib.parse.urljoin(self.url + '/', caminho)
        if (
            urllib.parse.urlsplit(destino).netloc
            != urllib.parse.urlsplit(self.url).netloc
        ):
            raise ValueError('Redirecionamento para outro destino recusado.')
        cabecalhos = {'Authorization': 'Bearer ' + token} if token else {}
        corpo = None
        if dados is not None:
            cabecalhos['Content-Type'] = (
                'application/x-www-form-urlencoded'
                if formulario
                else 'application/json'
            )
            corpo = (
                urllib.parse.urlencode(dados) if formulario else json.dumps(dados)
            ).encode()
        pedido = urllib.request.Request(
            destino, data=corpo, method=metodo, headers=cabecalhos
        )
        try:
            resposta = (navegador or sessao()).open(pedido, timeout=20)
        except urllib.error.HTTPError as erro:
            resposta = erro
        with resposta:
            texto = resposta.read().decode(errors='replace')
            try:
                resultado = json.loads(texto)
            except ValueError:
                resultado = texto
            return {
                'status': resposta.code,
                'corpo': resultado,
                'cabecalhos': dict(resposta.headers),
            }

    def verificar(
        self,
        nome: str,
        resposta: Resposta,
        esperado: int | tuple[int, ...],
        linha: int,
        condicao: Callable[[Any], bool] | None = None,
        evidencia: str = '',
    ) -> Resposta:
        status = (esperado,) if isinstance(esperado, int) else esperado
        passou = resposta['status'] in status
        if condicao is not None:
            try:
                passou = passou and bool(condicao(resposta['corpo']))
            except KeyError, TypeError, IndexError, ValueError:
                passou = False
        self.falhas += not passou
        print(
            f'{"PASSOU" if passou else "FALHOU"} {nome}: '
            f'esperado={status}, recebido={resposta["status"]}; '
            f'especificação linha {linha}'
        )
        if evidencia:
            print(evidencia)
        return resposta

    def credenciais(self, papel: str) -> tuple[str, str]:
        padroes = {
            'ADMIN': 'super_admin',
            'CLIENTE': 'cliente_01',
            'VENDEDOR': 'vendedor_01',
        }
        senha = os.environ.get(f'QA_SENHA_{papel}') or os.environ.get(
            'QA_SENHA_USUARIOS'
        )
        if not senha:
            raise ValueError(f'Informe QA_SENHA_{papel} ou QA_SENHA_USUARIOS.')
        return os.environ.get(f'QA_USUARIO_{papel}', padroes[papel]), senha

    def login(self, usuario: str, senha: str) -> Resposta:
        return self.requisitar(
            'POST',
            '/api/v1/usuarios/login/',
            {
                'username': usuario,
                'password': senha,
            },
        )

    def autenticar(self, papel: str) -> dict[str, Any]:
        resposta = self.verificar(
            'Login ' + papel, self.login(*self.credenciais(papel)), 200, 120
        )
        if resposta['status'] != 200:
            raise RuntimeError('Login de preparação falhou: ' + papel)
        if papel == 'ADMIN':
            self.admin = resposta['corpo']['access']
        return resposta['corpo']

    def dados(self) -> dict[str, Any]:
        nome = self.prefixo + secrets.token_hex(3)
        return {
            'username': nome,
            'email': nome + '@example.invalid',
            'password': 'Qa!7#' + secrets.token_urlsafe(18),
            'first_name': DADOS.first_name(),
            'last_name': DADOS.last_name(),
            'cpf': DADOS.cpf(),
            'data_nascimento': '1990-04-15',
            'telefone': '+55 (71) 99912-3456',
        }

    def cadastrar(
        self,
        dados: dict[str, Any],
        esperado: int = 201,
        nome: str = 'Cadastro',
        linha: int = 119,
    ) -> Resposta:
        resposta = self.requisitar('POST', '/api/v1/usuarios/cadastrar/', dados)
        corpo = resposta['corpo']
        if (
            resposta['status'] in (200, 201)
            and isinstance(corpo, dict)
            and not any(item['id'] == corpo['id'] for item in self.criados)
        ):
            self.criados.append({'id': corpo['id'], 'dados': dados.copy()})
        return self.verificar(nome, resposta, esperado, linha)

    def criar(self) -> dict[str, Any]:
        dados = self.dados()
        resposta = self.cadastrar(dados)
        if resposta['status'] != 201:
            raise RuntimeError('Não foi possível preparar a fixture de QA.')
        return {'id': resposta['corpo']['id'], 'dados': dados}

    def limpar(self) -> None:
        if not self.admin:
            return
        for produto in self.produtos:
            self.verificar(
                'Limpar produto QA',
                self.requisitar(
                    'DELETE', f'/api/v1/produtos/{produto}/', token=self.admin
                ),
                (204, 404),
                136,
            )
        for item in self.criados:
            caminho = f'/api/v1/usuarios/{item["id"]}/'
            resposta = self.requisitar('GET', caminho, token=self.admin)
            if resposta['status'] != 200:
                self.verificar('Consultar fixture para limpeza', resposta, 200, 45)
                continue
            if not resposta['corpo']['username'].startswith(self.prefixo):
                raise RuntimeError('Fixture não pertence a esta execução.')
            if resposta['corpo']['is_active']:
                self.verificar(
                    'Desativar fixture QA',
                    self.requisitar('DELETE', caminho, token=self.admin),
                    204,
                    133,
                )


def csrf(resposta: Resposta) -> str:
    resultado = re.search(
        r'name="csrfmiddlewaretoken" value="([^"]+)"', resposta['corpo']
    )
    if not resultado:
        raise RuntimeError('Formulário esperado não apresentou token CSRF.')
    return resultado.group(1)


def enviar_formulario(
    roteiro: Roteiro,
    navegador: Any,
    caminho: str,
    dados: dict[str, Any],
) -> Resposta:
    pagina = roteiro.requisitar('GET', caminho, navegador=navegador)
    return roteiro.requisitar(
        'POST',
        caminho,
        dict(dados, csrfmiddlewaretoken=csrf(pagina)),
        navegador=navegador,
        formulario=True,
    )


def login_web(
    roteiro: Roteiro,
    navegador: Any,
    usuario: str,
    senha: str,
) -> Resposta:
    return enviar_formulario(
        roteiro,
        navegador,
        '/usuarios/entrar/',
        {
            'username': usuario,
            'password': senha,
        },
    )


def executar(funcao: Callable[[Roteiro], None]) -> None:
    try:
        roteiro = Roteiro()
    except ValueError as erro:
        print(str(erro))
        sys.exit(2)
    codigo = 0
    try:
        funcao(roteiro)
    except Exception as erro:
        print(f'Execução bloqueada: {type(erro).__name__}. Verifique a preparação.')
        codigo = 2
    finally:
        try:
            roteiro.limpar()
        except Exception as erro:
            print(f'Limpeza pendente: {type(erro).__name__}.')
            codigo = 2
    sys.exit(codigo or int(roteiro.falhas > 0))

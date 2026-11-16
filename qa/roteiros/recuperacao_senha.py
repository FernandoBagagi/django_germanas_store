"""Recuperação em duas fases; links e credenciais ficam fora do repositório."""

import argparse
import getpass
import json
import os
import sys
from urllib.parse import urlsplit

from cliente_http import Roteiro, csrf, sessao

BASE = '/api/v1/usuarios/'


def solicitar(qa: Roteiro) -> None:
    arquivo = qa.pasta / 'recuperacao_privada.json'
    if arquivo.exists():
        raise ValueError('Já existe uma recuperação pendente; confirmar ou limpar.')
    qa.autenticar('ADMIN')
    fixture = qa.criar()
    dados = fixture['dados']
    par = qa.login(dados['username'], dados['password'])['corpo']
    estado = {'fixture': fixture, 'tokens': par, 'prefixo': qa.prefixo, 'url': qa.url}
    descritor = os.open(arquivo, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descritor, 'w', encoding='utf-8') as saida:
        json.dump(estado, saida)
    qa.verificar(
        'Solicitar recuperação',
        qa.requisitar('POST', BASE + 'redefinir_senha/', {'email': dados['email']}),
        200,
        162,
    )
    print('Email da fixture para localizar o link no console:', dados['email'])
    print('Execute confirmar --via api ou confirmar --via web com o link recente.')


def carregar(qa: Roteiro) -> dict:
    estado = json.loads((qa.pasta / 'recuperacao_privada.json').read_text())
    if estado['url'] != qa.url:
        raise ValueError('O estado pertence a outro servidor.')
    qa.prefixo = estado['prefixo']
    qa.criados = [estado['fixture']]
    qa.autenticar('ADMIN')
    return estado


def confirmar(qa: Roteiro, estado: dict, via: str) -> None:
    link = getpass.getpass('Link completo de recuperação (entrada oculta): ').strip()
    destino = urlsplit(link)
    if (destino.scheme, destino.netloc) != (
        urlsplit(qa.url).scheme,
        urlsplit(qa.url).netloc,
    ):
        raise ValueError('O link não pertence ao servidor desta execução.')
    partes = destino.path.strip('/').split('/')
    if len(partes) != 4 or partes[:2] != ['usuarios', 'confirmar_senha']:
        raise ValueError('Formato inesperado do link de recuperação.')
    uid, token = partes[-2:]
    dados = estado['fixture']['dados']
    nova_senha = qa.dados()['password']
    navegador = sessao()
    pagina = qa.requisitar('GET', destino.path, navegador=navegador)
    qa.verificar('Abrir link válido', pagina, 302, 148)
    if pagina['status'] != 302:
        raise ValueError('Link inválido ou expirado; gerar uma nova rodada.')
    caminho = pagina['cabecalhos']['Location']
    pagina = qa.requisitar('GET', caminho, navegador=navegador)
    qa.verificar(
        'Formulário de nova senha',
        pagina,
        200,
        148,
        lambda corpo: 'new_password1' in corpo,
    )
    qa.verificar(
        'GET não altera senha', qa.login(dados['username'], dados['password']), 200, 148
    )
    if via == 'api':
        fraca = {'uid': uid, 'token': token, 'password': '123'}
        qa.verificar(
            'Recuperação rejeita senha fraca',
            qa.requisitar('POST', BASE + 'confirmar_senha/', fraca),
            400,
            40,
        )
        pedido = dict(fraca, password=nova_senha)
        resposta = qa.verificar(
            'Confirmar senha pela API',
            qa.requisitar('POST', BASE + 'confirmar_senha/', pedido),
            200,
            123,
        )
        sucesso = resposta['status'] == 200
    else:
        pedido = {'new_password1': nova_senha, 'new_password2': nova_senha}
        qa.verificar(
            'Recuperação Web exige CSRF',
            qa.requisitar(
                'POST', caminho, pedido, navegador=navegador, formulario=True
            ),
            403,
            147,
        )
        pedido['csrfmiddlewaretoken'] = csrf(pagina)
        qa.verificar(
            'Web rejeita senhas diferentes',
            qa.requisitar(
                'POST',
                caminho,
                dict(pedido, new_password2='Outra!Senha#'),
                navegador=navegador,
                formulario=True,
            ),
            200,
            235,
            lambda corpo: 'errorlist' in corpo,
        )
        qa.verificar(
            'Web rejeita senha fraca',
            qa.requisitar(
                'POST',
                caminho,
                dict(pedido, new_password1='123', new_password2='123'),
                navegador=navegador,
                formulario=True,
            ),
            200,
            40,
            lambda corpo: 'errorlist' in corpo,
        )
        resposta = qa.verificar(
            'Confirmar senha pela Web',
            qa.requisitar(
                'POST', caminho, pedido, navegador=navegador, formulario=True
            ),
            302,
            235,
        )
        sucesso = resposta['status'] == 302
    if not sucesso:
        return
    qa.verificar(
        'Senha antiga rejeitada',
        qa.login(dados['username'], dados['password']),
        401,
        159,
    )
    qa.verificar('Nova senha aceita', qa.login(dados['username'], nova_senha), 200, 235)
    qa.verificar(
        'Recuperação revoga access',
        qa.requisitar('GET', '/api/v1/produtos/', token=estado['tokens']['access']),
        401,
        159,
    )
    qa.verificar(
        'Recuperação revoga refresh',
        qa.requisitar(
            'POST', BASE + 'renovar/', {'refresh': estado['tokens']['refresh']}
        ),
        401,
        159,
    )
    qa.verificar(
        'Link não pode ser reutilizado',
        qa.requisitar(
            'POST',
            BASE + 'confirmar_senha/',
            {'uid': uid, 'token': token, 'password': nova_senha},
        ),
        400,
        235,
    )


def principal() -> int:
    argumentos = argparse.ArgumentParser(description=__doc__)
    argumentos.add_argument('acao', choices=('solicitar', 'confirmar', 'limpar'))
    argumentos.add_argument('--via', choices=('api', 'web'), default='api')
    opcoes = argumentos.parse_args()
    try:
        qa = Roteiro()
    except ValueError as erro:
        print(str(erro))
        return 2
    codigo = 0
    try:
        if opcoes.acao == 'solicitar':
            solicitar(qa)
        else:
            estado = carregar(qa)
            if opcoes.acao == 'confirmar':
                confirmar(qa, estado, opcoes.via)
    except Exception as erro:
        print(f'Etapa bloqueada: {type(erro).__name__}. Confira estado e preparação.')
        codigo = 2
    finally:
        if opcoes.acao != 'solicitar':
            try:
                falhas_antes = qa.falhas
                qa.limpar()
                if qa.admin and qa.falhas == falhas_antes:
                    (qa.pasta / 'recuperacao_privada.json').unlink(missing_ok=True)
            except Exception as erro:
                print(f'Limpeza pendente: {type(erro).__name__}.')
                codigo = 2
    return codigo or int(qa.falhas > 0)


if __name__ == '__main__':
    sys.exit(principal())

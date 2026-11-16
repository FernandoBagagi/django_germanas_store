"""Cenários API reconstruídos; execução HTTP explícita, sem importar a aplicação."""

import base64
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from cliente_http import Roteiro, executar

USUARIOS = '/api/v1/usuarios/'
PRODUTOS = '/api/v1/produtos/'


def testar(qa: Roteiro) -> None:
    pares = {papel: qa.autenticar(papel) for papel in ('ADMIN', 'CLIENTE', 'VENDEDOR')}
    admin = pares['ADMIN']['access']
    cliente = pares['CLIENTE']['access']
    vendedor = pares['VENDEDOR']['access']
    for caminho in ('/', '/produtos/', '/usuarios/entrar/', '/usuarios/cadastrar/'):
        qa.verificar(
            'Página pública ' + caminho, qa.requisitar('GET', caminho), 200, 142
        )
    for caminho in (PRODUTOS, USUARIOS, USUARIOS + 'minha_conta/'):
        qa.verificar('API sem JWT ' + caminho, qa.requisitar('GET', caminho), 401, 135)
    for papel, par in pares.items():
        qa.verificar(
            'Produtos ' + papel,
            qa.requisitar('GET', PRODUTOS, token=par['access']),
            200,
            55,
        )
        qa.verificar(
            'Listar usuários ' + papel,
            qa.requisitar('GET', USUARIOS, token=par['access']),
            200 if papel == 'ADMIN' else 403,
            59,
        )

    for campo in qa.dados():
        for valor in ('ausente', '', None):
            dados = qa.dados()
            if valor == 'ausente':
                dados.pop(campo)
            else:
                dados[campo] = valor
            qa.cadastrar(dados, 400, f'Obrigatoriedade {campo}: {valor!r}', 39)

    hoje = datetime.now(ZoneInfo('America/Bahia')).date()
    # Para 29/02, o aniversário de 18 anos ainda não ocorreu em 28/02.
    try:
        limite = hoje.replace(year=hoje.year - 18)
    except ValueError:
        limite = hoje.replace(year=hoje.year - 18, day=28)
    invalidos = {
        'cpf': ['111.111.111-11', '12345678901', '123', 'abcdef'],
        'telefone': [
            '(00) 99999-1234',
            '(20) 99999-1234',
            '+1 202 555 0100',
            '(71) 3333-1234 ramal 12',
            'abc71999123456',
        ],
        'data_nascimento': [
            (limite + timedelta(days=1)).isoformat(),
            '2035-01-01',
            '1990-02-30',
            '15/04/1990',
        ],
        'email': ['invalido', 'a@'],
        'username': ['com espaco', '<qa>'],
        'password': ['123', '123456789012345'],
    }
    for campo, valores in invalidos.items():
        for indice, valor in enumerate(valores):
            qa.cadastrar(
                dict(qa.dados(), **{campo: valor}),
                400,
                f'Validação {campo} caso {indice + 1}',
                229,
            )
    qa.cadastrar(
        dict(qa.dados(), data_nascimento=limite.isoformat()),
        201,
        'Maioridade exata',
        44,
    )
    qa.cadastrar(dict(qa.dados(), telefone='(71) 3333-1234'), 201, 'Telefone fixo', 43)

    fixture = qa.criar()
    dados = fixture['dados']
    caminho = USUARIOS + str(fixture['id']) + '/'
    par = qa.login(dados['username'], dados['password'])['corpo']
    token = par['access']
    qa.verificar(
        'Normalização e papel CLIENTE',
        qa.requisitar('GET', caminho, token=token),
        200,
        42,
        lambda corpo: (
            corpo['papel'] == 'CLIENTE'
            and corpo['telefone'] == '71999123456'
            and corpo['cpf'].isdigit()
            and 'password' not in corpo
        ),
    )
    for campo in ('username', 'email', 'cpf'):
        valor = dados[campo].upper() if campo == 'email' else dados[campo]
        qa.cadastrar(dict(qa.dados(), **{campo: valor}), 400, 'Unicidade ' + campo, 12)
    for campo in (
        'is_staff',
        'is_superuser',
        'is_active',
        'groups',
        'user_permissions',
        'papel',
        'versao_autenticacao',
        'cadastro_pendente',
    ):
        valor = 'ADMIN' if campo == 'papel' else True
        if campo in ('groups', 'user_permissions'):
            valor = []
        qa.cadastrar(
            dict(qa.dados(), **{campo: valor}),
            403,
            'Cadastro privilegiado ' + campo,
            65,
        )
        for credencial in (token, admin):
            qa.verificar(
                'Editar privilegiado ' + campo,
                qa.requisitar('PATCH', caminho, {campo: valor}, token=credencial),
                403,
                65,
            )
    for campo in ('id', 'last_login', 'date_joined'):
        valor = 7777777 if campo == 'id' else '2026-11-07T00:00:00Z'
        qa.verificar(
            'F04 — controle interno ' + campo,
            qa.requisitar('PATCH', caminho, {campo: valor}, token=token),
            403,
            65,
        )
    for credencial in (cliente, vendedor):
        for metodo, corpo in (
            ('GET', None),
            ('PATCH', {'first_name': 'Indevido'}),
            ('DELETE', None),
        ):
            qa.verificar(
                'Usuário alheio ' + metodo,
                qa.requisitar(metodo, caminho, corpo, token=credencial),
                403,
                64,
            )
        qa.verificar(
            'Promoção sem ADMIN',
            qa.requisitar(
                'POST', caminho + 'alterar_papel/', {'papel': 'ADMIN'}, token=credencial
            ),
            403,
            60,
        )
    for campo, valor in (
        ('password', ''),
        ('password', '123'),
        ('cpf', qa.dados()['cpf']),
        ('first_name', ''),
    ):
        qa.verificar(
            'Atualização inválida ' + campo,
            qa.requisitar('PATCH', caminho, {campo: valor}, token=token),
            400,
            40,
        )
    qa.verificar(
        'PUT incompleto',
        qa.requisitar('PUT', caminho, {'first_name': 'Pessoa QA'}, token=token),
        400,
        132,
    )
    completos = {
        chave: valor
        for chave, valor in dados.items()
        if chave not in ('cpf', 'password')
    }
    qa.verificar(
        'PUT sem senha', qa.requisitar('PUT', caminho, completos, token=token), 200, 132
    )

    qa.cadastrar(
        dict(qa.dados(), data_nascimento='1990-4-15'),
        400,
        'F01 — cadastro data sem zero',
        31,
    )
    for data in ('1990-4-15', '1990-04-5'):
        resposta = qa.requisitar(
            'PATCH', caminho, {'data_nascimento': data}, token=token
        )
        saida = resposta['corpo']
        evidencia = str(saida.get('data_nascimento', 'Rejeitada'))
        qa.verificar(
            'F01 — edição data ' + data, resposta, 400, 31, evidencia=evidencia
        )
    qa.verificar(
        'Restaurar nascimento da fixture',
        qa.requisitar('PATCH', caminho, {'data_nascimento': '1990-04-15'}, token=token),
        200,
        31,
    )
    resposta = qa.requisitar('GET', PRODUTOS, token='invalid.jwt.token')
    qa.verificar(
        'F03 — mensagens JWT em pt-BR',
        resposta,
        401,
        46,
        lambda corpo: (
            'Given token' not in json.dumps(corpo)
            and 'Token is invalid' not in json.dumps(corpo)
        ),
    )

    for tipo, segundos in (('access', 1800), ('refresh', 86400)):
        trecho = par[tipo].split('.')[1]
        claims = json.loads(base64.urlsafe_b64decode(trecho + '=' * (-len(trecho) % 4)))
        qa.verificar(
            'Duração e claims ' + tipo,
            {'status': 200, 'corpo': claims},
            200,
            154,
            lambda corpo, duracao=segundos: (
                corpo['exp'] - corpo['iat'] == duracao
                and 'versao_autenticacao' in corpo
                and not {
                    'password',
                    'hash_password',
                    'email',
                    'cpf',
                    'papel',
                }.intersection(corpo)
            ),
        )
    renovar = USUARIOS + 'renovar/'
    qa.verificar(
        'Rotacionar refresh',
        qa.requisitar('POST', renovar, {'refresh': par['refresh']}),
        200,
        155,
        lambda corpo: corpo['refresh'] != par['refresh'],
    )
    qa.verificar(
        'Replay de refresh',
        qa.requisitar('POST', renovar, {'refresh': par['refresh']}),
        401,
        155,
    )
    par = qa.login(dados['username'], dados['password'])['corpo']
    with ThreadPoolExecutor(max_workers=2) as grupo:
        respostas = list(
            grupo.map(
                lambda _: qa.requisitar('POST', renovar, {'refresh': par['refresh']}),
                range(2),
            )
        )
    codigos = sorted(item['status'] for item in respostas)
    qa.verificar(
        'Refresh concorrente',
        {'status': 200, 'corpo': codigos},
        200,
        158,
        lambda corpo: corpo == [200, 401],
        evidencia=str(codigos),
    )

    produto = {
        'nome_comercial': qa.prefixo + 'produto',
        'descricao': 'Produto fictício de QA',
        'url_imagem': 'https://example.invalid/qa.jpg',
        'preco': '1234.56',
    }
    qa.verificar(
        'CLIENTE não cria produto',
        qa.requisitar('POST', PRODUTOS, produto, token=cliente),
        403,
        56,
    )
    resposta = qa.verificar(
        'VENDEDOR cria produto',
        qa.requisitar('POST', PRODUTOS, produto, token=vendedor),
        201,
        136,
    )
    if resposta['status'] == 201:
        identificador = resposta['corpo']['id']
        qa.produtos.append(identificador)
        detalhe = PRODUTOS + str(identificador) + '/'
        for metodo in ('PUT', 'PATCH', 'DELETE'):
            qa.verificar(
                'CLIENTE não escreve produto ' + metodo,
                qa.requisitar(
                    metodo,
                    detalhe,
                    produto if metodo != 'DELETE' else None,
                    token=cliente,
                ),
                403,
                56,
            )
        qa.verificar(
            'VENDEDOR edita produto',
            qa.requisitar('PATCH', detalhe, {'preco': '123.45'}, token=vendedor),
            200,
            136,
        )
        qa.verificar(
            'ADMIN substitui produto',
            qa.requisitar('PUT', detalhe, produto, token=admin),
            200,
            136,
        )
        qa.verificar(
            'Preço negativo',
            qa.requisitar('PATCH', detalhe, {'preco': '-1'}, token=vendedor),
            400,
            237,
        )
        for consulta in (
            'preco_minimo=-1',
            'preco_minimo=abc',
            'preco_minimo=10&preco_maximo=1',
        ):
            qa.verificar(
                'Filtro inválido ' + consulta,
                qa.requisitar('GET', PRODUTOS + '?' + consulta, token=cliente),
                400,
                237,
            )
        qa.verificar(
            'Detalhe Web em reais',
            qa.requisitar('GET', f'/produtos/{identificador}/'),
            200,
            54,
            lambda corpo: '1.234,56' in corpo,
        )
        qa.verificar(
            'Excluir produto',
            qa.requisitar('DELETE', detalhe, token=vendedor),
            204,
            136,
        )
        qa.verificar(
            'Produto excluído retorna 404',
            qa.requisitar('GET', detalhe, token=cliente),
            404,
            15,
        )

    qa.verificar(
        'Promover VENDEDOR',
        qa.requisitar(
            'POST', caminho + 'alterar_papel/', {'papel': 'VENDEDOR'}, token=admin
        ),
        200,
        127,
    )
    qa.verificar(
        'Papel revoga access', qa.requisitar('GET', PRODUTOS, token=token), 401, 159
    )
    par = qa.login(dados['username'], dados['password'])['corpo']
    qa.verificar(
        'Desativar própria conta',
        qa.requisitar('DELETE', USUARIOS + 'minha_conta/', token=par['access']),
        204,
        124,
    )
    qa.verificar(
        'Inativo não autentica',
        qa.login(dados['username'], dados['password']),
        401,
        157,
    )
    qa.verificar(
        'Desativação revoga access',
        qa.requisitar('GET', PRODUTOS, token=par['access']),
        401,
        159,
    )
    qa.verificar(
        'Desativação revoga refresh',
        qa.requisitar('POST', renovar, {'refresh': par['refresh']}),
        401,
        159,
    )
    for campo in ('email', 'username'):
        qa.cadastrar(
            dict(qa.dados(), **{campo: dados[campo]}),
            400,
            'Identificador reservado ' + campo,
            45,
        )
    novos = dict(qa.dados(), cpf=dados['cpf'])
    resposta = qa.cadastrar(novos, 200, 'Reativação pública', 170)
    qa.verificar(
        'Reativação preserva id e remove privilégios',
        resposta,
        200,
        170,
        lambda corpo: corpo['id'] == fixture['id'] and corpo['papel'] == 'CLIENTE',
    )
    qa.verificar(
        'Reativação não recupera access antigo',
        qa.requisitar('GET', PRODUTOS, token=par['access']),
        401,
        232,
    )
    par = qa.login(novos['username'], novos['password'])['corpo']
    senha = qa.dados()['password']
    qa.verificar(
        'Troca de senha',
        qa.requisitar('PATCH', caminho, {'password': senha}, token=par['access']),
        200,
        40,
    )
    qa.verificar(
        'Troca revoga access',
        qa.requisitar('GET', PRODUTOS, token=par['access']),
        401,
        159,
    )
    qa.verificar(
        'Troca revoga refresh',
        qa.requisitar('POST', renovar, {'refresh': par['refresh']}),
        401,
        159,
    )
    qa.verificar(
        'Senha antiga rejeitada',
        qa.login(novos['username'], novos['password']),
        401,
        159,
    )
    qa.verificar('Nova senha aceita', qa.login(novos['username'], senha), 200, 40)


if __name__ == '__main__':
    executar(testar)

"""Controles HTTP de persistência e mensagens para o fechamento de F01–F04."""

import json
import re

from cliente_http import Roteiro, enviar_formulario, executar, login_web, sessao

BASE = '/api/v1/usuarios/'


def testar(qa: Roteiro) -> None:
    qa.autenticar('ADMIN')
    fixture = qa.criar()
    dados = fixture['dados']
    caminho = BASE + str(fixture['id']) + '/'
    par = qa.login(dados['username'], dados['password'])['corpo']
    token = par['access']

    def consultar() -> dict:
        return qa.requisitar('GET', caminho, token=qa.admin)

    datas = (
        '1990-4-15',
        '1990-04-5',
        '15/04/1990',
        '1990-02-30',
        '1990-04-15T00:00:00Z',
        ' 1990-04-15 ',
        '１９９０-０４-１５',
    )
    for data in datas:
        qa.cadastrar(
            dict(qa.dados(), data_nascimento=data),
            400,
            'F01 cadastro rejeita ' + data,
            31,
        )
        qa.verificar(
            'F01 PATCH rejeita ' + data,
            qa.requisitar('PATCH', caminho, {'data_nascimento': data}, token=token),
            400,
            31,
        )
        resposta = consultar()
        qa.verificar(
            'F01 rejeição preserva nascimento',
            resposta,
            200,
            31,
            lambda corpo: corpo['data_nascimento'] == '1990-04-15',
            evidencia=resposta['corpo'].get('data_nascimento', 'Ausente'),
        )
    qa.verificar(
        'F01 ISO válido persiste',
        qa.requisitar('PATCH', caminho, {'data_nascimento': '1991-05-06'}, token=token),
        200,
        31,
        lambda corpo: corpo['data_nascimento'] == '1991-05-06',
    )
    qa.verificar(
        'F01 restaurar data da fixture',
        qa.requisitar('PATCH', caminho, {'data_nascimento': '1990-04-15'}, token=token),
        200,
        31,
    )

    administrador = sessao()
    qa.verificar(
        'Login Web ADMIN para controle F02',
        login_web(qa, administrador, *qa.credenciais('ADMIN')),
        302,
        147,
    )
    tela_admin = f'/admin/usuarios/usuario/{fixture["id"]}/change/'
    pagina = qa.requisitar('GET', tela_admin, navegador=administrador)
    qa.verificar(
        'F02 HTML com valor ISO literal',
        pagina,
        200,
        31,
        lambda corpo: bool(
            re.search(r'name="data_nascimento"[^>]*value="1990-04-15"', corpo)
        ),
    )
    formulario = {
        chave: valor
        for chave, valor in dados.items()
        if chave not in ('password', 'cpf')
    }
    for data in ('16/04/1990', '1990-4-15', '1990-04-5'):
        qa.verificar(
            'F02 Admin rejeita ' + data,
            enviar_formulario(
                qa,
                administrador,
                tela_admin,
                dict(formulario, data_nascimento=data, _save='Salvar'),
            ),
            200,
            31,
            lambda corpo: 'errorlist' in corpo,
        )
        resposta = consultar()
        qa.verificar(
            'F02 rejeição preserva nascimento',
            resposta,
            200,
            31,
            lambda corpo: corpo['data_nascimento'] == '1990-04-15',
            evidencia=resposta['corpo'].get('data_nascimento', 'Ausente'),
        )
    qa.verificar(
        'F02 Admin salva data ISO',
        enviar_formulario(
            qa,
            administrador,
            tela_admin,
            dict(formulario, data_nascimento='1990-04-16', _save='Salvar'),
        ),
        302,
        31,
    )
    resposta = consultar()
    qa.verificar(
        'F02 persistência confirmada pela API',
        resposta,
        200,
        31,
        lambda corpo: corpo['data_nascimento'] == '1990-04-16',
        evidencia=resposta['corpo'].get('data_nascimento', 'Ausente'),
    )

    for nome, credencial in (
        ('malformado', 'invalid.jwt.token'),
        ('refresh como access', par['refresh']),
    ):
        resposta = qa.requisitar('GET', '/api/v1/produtos/', token=credencial)
        corpo = resposta['corpo']
        resumo = {
            'detail': corpo.get('detail'),
            'code': corpo.get('code'),
            'messages': corpo.get('messages'),
            'WWW-Authenticate': resposta['cabecalhos'].get('WWW-Authenticate'),
        }
        qa.verificar(
            'F03 mensagens exatas e estrutura: ' + nome,
            resposta,
            401,
            46,
            lambda valor: (
                valor['detail'] == 'Token inválido ou expirado.'
                and valor['code'] == 'token_not_valid'
                and bool(valor['messages'])
                and all(
                    item['message'] == 'Token inválido ou expirado.'
                    and item['token_class'] == 'AccessToken'
                    and item['token_type'] == 'access'
                    for item in valor['messages']
                )
            ),
            evidencia=json.dumps(resumo, ensure_ascii=False),
        )
        qa.verificar(
            'F03 mantém desafio Bearer',
            resposta,
            401,
            153,
            lambda _, desafio=resumo['WWW-Authenticate']: (
                bool(desafio) and desafio.startswith('Bearer')
            ),
        )
    qa.verificar(
        'F03 access válido continua aceito',
        qa.requisitar('GET', '/api/v1/produtos/', token=token),
        200,
        55,
    )

    antes = consultar()['corpo']
    for campo in ('id', 'last_login', 'date_joined'):
        valor = 7777777 if campo == 'id' else '2026-11-07T00:00:00Z'
        qa.cadastrar(
            dict(qa.dados(), **{campo: valor}), 403, 'F04 cadastro rejeita ' + campo, 65
        )
        for papel, credencial in (('CLIENTE', token), ('ADMIN', qa.admin)):
            resposta = qa.requisitar('PATCH', caminho, {campo: valor}, token=credencial)
            qa.verificar('F04 PATCH ' + papel + ' rejeita ' + campo, resposta, 403, 65)
            qa.verificar(
                'F04 preserva perfil consultável',
                consultar(),
                200,
                65,
                lambda corpo: corpo == antes,
            )
    qa.verificar(
        'F04 campo desconhecido comum permanece 400',
        qa.requisitar('PATCH', caminho, {'campo_inexistente_qa': 'teste'}, token=token),
        400,
        46,
    )

    qa.limpar()
    for item in qa.criados:
        qa.verificar(
            'Limpeza confirmada por consulta',
            qa.requisitar('GET', BASE + str(item['id']) + '/', token=qa.admin),
            200,
            45,
            lambda corpo: not corpo['is_active'],
            evidencia=f'id={item["id"]}',
        )
    for papel in ('ADMIN', 'CLIENTE', 'VENDEDOR'):
        par_original = qa.autenticar(papel)
        qa.verificar(
            'Conta fornecida permanece ativa: ' + papel,
            qa.requisitar('GET', BASE + 'minha_conta/', token=par_original['access']),
            200,
            13,
            lambda corpo, role=papel: corpo['papel'] == role and corpo['is_active'],
        )


if __name__ == '__main__':
    executar(testar)

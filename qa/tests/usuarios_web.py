"""Formulários Web reconstruídos da rodada histórica; não faz inspeção visual."""

import re

from cliente_http import Roteiro, csrf, enviar_formulario, executar, login_web, sessao


def testar(qa: Roteiro) -> None:
    qa.autenticar('ADMIN')
    navegadores = {}
    for papel in ('ADMIN', 'CLIENTE', 'VENDEDOR'):
        navegador = sessao()
        navegadores[papel] = navegador
        qa.verificar(
            'Login Web ' + papel,
            login_web(qa, navegador, *qa.credenciais(papel)),
            302,
            147,
        )
        qa.verificar(
            'Navegação ' + papel,
            qa.requisitar('GET', '/', navegador=navegador),
            200,
            142,
            lambda corpo, role=papel: (
                'Minha conta' in corpo
                and 'Sair' in corpo
                and (('Usuários' in corpo) == (role == 'ADMIN'))
            ),
        )
        qa.verificar(
            'Django Admin ' + papel,
            qa.requisitar('GET', '/admin/', navegador=navegador),
            200 if papel == 'ADMIN' else (302, 403),
            61,
        )
    cliente = navegadores['CLIENTE']
    qa.verificar(
        'Logout GET rejeitado',
        qa.requisitar('GET', '/usuarios/sair/', navegador=cliente),
        405,
        147,
    )
    qa.verificar(
        'Logout sem CSRF rejeitado',
        qa.requisitar(
            'POST', '/usuarios/sair/', {}, navegador=cliente, formulario=True
        ),
        403,
        147,
    )
    outra = sessao()
    login_web(qa, outra, *qa.credenciais('CLIENTE'))
    pagina = qa.requisitar('GET', '/', navegador=cliente)
    qa.verificar(
        'Logout Web',
        qa.requisitar(
            'POST',
            '/usuarios/sair/',
            {'csrfmiddlewaretoken': csrf(pagina)},
            navegador=cliente,
            formulario=True,
        ),
        302,
        149,
    )
    qa.verificar(
        'Logout preserva outra sessão',
        qa.requisitar('GET', '/', navegador=outra),
        200,
        149,
        lambda corpo: 'Minha conta' in corpo,
    )

    fixture = qa.criar()
    dados = fixture['dados']
    identificador = fixture['id']
    caminho_api = f'/api/v1/usuarios/{identificador}/'
    navegador = sessao()
    login_web(qa, navegador, dados['username'], dados['password'])
    editar = '/usuarios/minha_conta/editar/'
    sem_senha = {chave: valor for chave, valor in dados.items() if chave != 'password'}
    qa.verificar(
        'Editar sem senha',
        enviar_formulario(
            qa, navegador, editar, dict(sem_senha, first_name='Pessoa QA Web')
        ),
        302,
        40,
    )
    qa.verificar(
        'Edição Web persistida',
        qa.requisitar('GET', caminho_api, token=qa.admin),
        200,
        145,
        lambda corpo: corpo['first_name'] == 'Pessoa QA Web',
    )
    qa.verificar(
        'Campo privilegiado Web',
        enviar_formulario(qa, navegador, editar, dict(sem_senha, is_superuser='true')),
        403,
        65,
    )
    qa.verificar(
        'Senha fraca Web',
        enviar_formulario(qa, navegador, editar, dict(sem_senha, password='123')),
        200,
        40,
        lambda corpo: 'errorlist' in corpo,
    )
    for papel in ('CLIENTE', 'VENDEDOR'):
        for caminho in (
            '/usuarios/',
            '/usuarios/novo/',
            f'/usuarios/{identificador}/editar/',
            f'/usuarios/{identificador}/alterar_papel/',
        ):
            qa.verificar(
                'Web usuário alheio ' + papel,
                qa.requisitar(
                    'GET',
                    caminho,
                    navegador=outra if papel == 'CLIENTE' else navegadores[papel],
                ),
                403,
                59,
            )

    admin = navegadores['ADMIN']
    caminho = f'/admin/usuarios/usuario/{identificador}/change/'
    resposta = qa.requisitar('GET', caminho, navegador=admin)
    qa.verificar(
        'F02 — nascimento ISO no Admin',
        resposta,
        200,
        31,
        lambda corpo: bool(
            re.search(r'name="data_nascimento"[^>]*value="1990-04-15"', corpo)
        ),
    )
    qa.verificar(
        'F02 — rejeitar data brasileira no Admin',
        enviar_formulario(
            qa,
            admin,
            caminho,
            dict(sem_senha, data_nascimento='16/04/1990', _save='Salvar'),
        ),
        200,
        31,
        lambda corpo: 'errorlist' in corpo,
    )
    qa.verificar(
        'Restaurar data fixture',
        qa.requisitar(
            'PATCH', caminho_api, {'data_nascimento': '1990-04-15'}, token=qa.admin
        ),
        200,
        31,
    )
    qa.verificar(
        'Admin não expõe hash',
        resposta,
        200,
        41,
        lambda corpo: (
            not re.search(r'(pbkdf2_sha256\$|argon2\$|bcrypt_sha256\$|scrypt\$)', corpo)
        ),
    )

    senha = qa.dados()['password']
    qa.verificar(
        'Trocar senha Web',
        enviar_formulario(qa, navegador, editar, dict(sem_senha, password=senha)),
        302,
        160,
    )
    qa.verificar(
        'Troca encerra sessão atual',
        qa.requisitar('GET', '/usuarios/minha_conta/', navegador=navegador),
        302,
        160,
    )
    login_web(qa, navegador, dados['username'], senha)
    desativar = '/usuarios/minha_conta/desativar/'
    qa.verificar(
        'GET desativação apresenta confirmação',
        qa.requisitar('GET', desativar, navegador=navegador),
        200,
        148,
    )
    qa.verificar(
        'GET preserva conta ativa',
        qa.requisitar('GET', caminho_api, token=qa.admin),
        200,
        148,
        lambda corpo: corpo['is_active'],
    )
    qa.verificar(
        'Desativação Web', enviar_formulario(qa, navegador, desativar, {}), 302, 145
    )
    qa.verificar(
        'Reativação administrativa Web',
        enviar_formulario(qa, admin, f'/usuarios/{identificador}/reativar/', dados),
        302,
        145,
    )
    qa.verificar(
        'Reativação CLIENTE',
        qa.requisitar('GET', caminho_api, token=qa.admin),
        200,
        172,
        lambda corpo: corpo['is_active'] and corpo['papel'] == 'CLIENTE',
    )
    for papel in ('ADMIN', 'CLIENTE'):
        qa.verificar(
            'Alterar papel Web ' + papel,
            enviar_formulario(
                qa, admin, f'/usuarios/{identificador}/alterar_papel/', {'papel': papel}
            ),
            302,
            145,
        )
    qa.verificar(
        'Bloquear exclusão física Admin',
        qa.requisitar(
            'GET', f'/admin/usuarios/usuario/{identificador}/delete/', navegador=admin
        ),
        403,
        69,
    )


if __name__ == '__main__':
    executar(testar)

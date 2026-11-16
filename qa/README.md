# QA funcional

Esta pasta reúne roteiros HTTP, relatórios e rastreabilidade das rodadas de QA.
Os testes internos da aplicação continuam em `usuarios/tests` e `produtos/tests`.

## Organização

```text
qa/
├── README.md
├── novo_relatorio.py          # Reserva o próximo número e cria um rascunho
├── tests/                    # Verificações offline da infraestrutura de QA
├── relatorios/
│   └── relatorio_001.md       # Rodada realizada em 07/11/2026
└── roteiros/
    ├── cliente_http.py        # HTTP, cookies, CSRF, fixtures e evidências
    ├── usuarios_api.py        # Cadastro, roles, produtos, JWT e ciclo de vida
    ├── usuarios_web.py        # Formulários, sessões e Django Admin
    └── recuperacao_senha.py   # Solicitação e confirmação via API/Web
```

## Origem dos roteiros

Em 07/11/2026 foram executados sete arquivos temporários: `qa_usuarios_http.py`,
`qa_usuarios_suite.py`, `qa_usuarios_web.py`, `qa_usuarios_deep.py`,
`qa_usuarios_confirm.py`, `qa_usuarios_finalchecks.py` e `qa_usuarios_finish.py`.
Eles estavam em `/tmp` e já não existiam quando esta pasta foi organizada, em
16/11/2026. O arquivo de evidências JSONL e o estado temporário também não estavam
disponíveis. Não foram inventados logs ou snapshots da execução antiga.

Os roteiros desta pasta foram **reconstruídos e consolidados a partir dos
comandos registrados na conversa**, com nomes em pt-BR, parâmetros reutilizáveis
e sem credenciais embutidas. Não são cópias byte a byte dos originais nem uma
reprodução exata das 350 verificações históricas. O relatório 001 documenta
a execução histórica; resultados novos só podem ser atribuídos a novas rodadas.

| Originais temporários | Roteiros reconstruídos |
|---|---|
| `qa_usuarios_http.py` | `cliente_http.py` e início de `usuarios_api.py` |
| `qa_usuarios_suite.py` | `usuarios_api.py` |
| `qa_usuarios_web.py`, `qa_usuarios_deep.py` | `usuarios_web.py` |
| `qa_usuarios_finalchecks.py` | `usuarios_api.py` e `usuarios_web.py` |
| `qa_usuarios_confirm.py`, `qa_usuarios_finish.py` | `recuperacao_senha.py`, promoção e limpeza nos demais roteiros |

As expectativas que geraram falsos alertas históricos foram corrigidas:
redirecionar o cadastro do Admin é permitido; a palavra `administrador` não é
uma senha obrigatoriamente recusada pelo contrato; não se faz login Web entre
gerar e consumir um link de recuperação. Datas de maioridade usam o dia atual
em America/Bahia em vez de fixar o aniversário de 07/11/2026.

## Relatórios incrementais

1. A próxima rodada começa com `.venv/bin/python qa/novo_relatorio.py`.
   Isso cria `relatorio_002.md`, depois `relatorio_003.md`, e assim por diante.
   O comando cria apenas um rascunho: não executa testes nem declara correções.
2. Preencher ambiente, data, versão testada, roteiro, evidências e limitações.
3. Manter IDs de falhas estáveis. F01–F04 são os IDs da rodada 001; novos
   problemas recebem F05 em diante. Não reutilizar IDs de falhas encerradas.
4. Em cada reteste, classificar cada falha como `Reproduzida`, `Corrigida`,
   `Regrediu` ou `Não retestada`. Só marcar `Corrigida` após verificar o caso
   original e os controles pertinentes. Informar cobertura bloqueada/incompleta.
5. Finalizar e preservar cada relatório. Retestes ficam em outro arquivo;
   relatórios anteriores não devem ser sobrescritos para apagar falhas.

O relatório inicial é [relatorio_001.md](relatorios/relatorio_001.md).
A fonte de requisitos continua em
[PLAN_USUARIOS_ORIGINAL.md](../docs/PLAN_USUARIOS_ORIGINAL.md).
O gerador registra o commit atual, o SHA-256 da especificação e de cada roteiro;
isso identifica os arquivos mesmo quando existem alterações não commitadas.
Para reproduzir integralmente uma rodada, versionar também os roteiros no Git.

Para verificar somente esta infraestrutura, sem iniciar testes contra o servidor:

```bash
.venv/bin/python -m unittest discover -s qa/tests -v
.venv/bin/ruff check qa
.venv/bin/ruff format --check qa
```

## Executar os roteiros

Executar a partir da raiz do projeto, com o servidor já iniciado. Os roteiros
acessam o servidor real por HTTP, criam dados fictícios e exercitam alterações de
senha, papel e desativação nessas fixtures. Não usam ORM nem leem o banco.
O destino padrão é `http://127.0.0.1:8000`; `QA_URL` pode indicar outro destino local.

Fornecer as senhas por ambiente, sem colocá-las em arquivos versionados:

```bash
read -rsp 'Senha das contas de QA: ' QA_SENHA_USUARIOS
export QA_SENHA_USUARIOS
export QA_EXECUCAO="$(mktemp -d /tmp/germanas-qa-XXXXXX)"
.venv/bin/python qa/roteiros/usuarios_api.py
.venv/bin/python qa/roteiros/usuarios_web.py
```

Por padrão, as contas são `super_admin`, `cliente_01` e `vendedor_01`.
É possível configurá-las com `QA_USUARIO_ADMIN`, `QA_USUARIO_CLIENTE` e
`QA_USUARIO_VENDEDOR`. Senhas diferentes podem ser fornecidas em
`QA_SENHA_ADMIN`, `QA_SENHA_CLIENTE` e `QA_SENHA_VENDEDOR`.

Cada processo cria suas próprias fixtures, identifica-as antes da limpeza e
tenta desativá-las em `finally`. As contas fornecidas são usadas para autenticar
e autorizar operações; não são alvos de alteração cadastral. Falha de limpeza
fica registrada para tratamento manual via aplicação.

`QA_EXECUCAO` deve apontar para uma pasta temporária fora do repositório. Recebe
`verificacoes.jsonl` e, na recuperação, um arquivo privado com a fixture e tokens.
Não versionar estado de autenticação, senhas, tokens ou cookies. As evidências
JSONL armazenam status, expectativas e contexto selecionado; não armazenam
corpos HTTP completos, HTML de debug, credenciais ou dados pessoais.

### Recuperação de senha

```bash
.venv/bin/python qa/roteiros/recuperacao_senha.py solicitar
# Copiar o link mais recente do console do servidor.
.venv/bin/python qa/roteiros/recuperacao_senha.py confirmar --via api
# O comando solicita o link de forma oculta, sem colocá-lo no histórico do shell.
```

Para testar a Web, repetir `solicitar` e usar `confirmar --via web`.
Não fazer login Web na fixture depois da solicitação. O estado da recuperação
é salvo antes do envio para permitir limpeza se o servidor falhar.
Se não for possível concluir, usar:

```bash
.venv/bin/python qa/roteiros/recuperacao_senha.py limpar
unset QA_SENHA_USUARIOS QA_SENHA_ADMIN QA_SENHA_CLIENTE QA_SENHA_VENDEDOR
```

Os processos retornam 0 quando as verificações passam, 1 para divergências e 2
para bloqueios/interrupções. A saída e o JSONL precisam de triagem: um erro de
preparação não prova defeito da aplicação. Relatórios não são gerados como
“aprovados” automaticamente a partir dos códigos HTTP.

## Limites

Não cobrem inspeção visual em navegador, SMTP real, migração de banco, legado
incompleto, passagem real do prazo de expiração ou mutação do último ADMIN ativo.
O relatório de cada rodada deve registrar esses limites. Criar esta pasta não
equivale a executar um novo reteste nem a confirmar que F01–F04 continuam abertas.

# Devolutiva DEV — Relatório QA 001

Data: 16/11/2026, America/Bahia.
Referência: [relatorio_001.md](relatorio_001.md), rodada histórica de 07/11/2026.
Commit-base: `fb00e063e8c4489d9bdb246d87ee03f979d67d88`.
As correções desta devolutiva estão no diretório de trabalho, ainda sem commit.

## Resultado e método

F01–F04 foram reproduzidas e corrigidas em reteste automatizado isolado.
Antes das correções, o novo módulo de regressão apresentou **14 falhas e 7
aprovações**; depois, **21 testes passaram**. As falhas abrangem os quatro IDs,
com parametrizações e controles adicionais; não representam 14 defeitos distintos.

Foram usadas requisições pelos clientes de testes do Django e DRF, incluindo
renderização e submissão do Django Admin e confirmação de persistência. Os dados
são fixtures Faker pt_BR em bancos de teste. Esta execução não usou as contas
reais de QA, não acessou o banco real e não executou os roteiros HTTP reconstruídos
contra `http://127.0.0.1:8000/`. Portanto, não constitui uma nova rodada funcional
HTTP equivalente à rodada 001; o reteste no servidor de QA permanece disponível
para confirmação pelo QA.

O relatório original e os dois planos de usuários foram preservados. Não houve
alteração de esquema nem necessidade de migração.

## Correções e evidências por ID

| ID | Estado nesta devolutiva | Correção | Evidência automatizada |
|---|---|---|---|
| F01 | Corrigida em reteste isolado | Validação lexical antes da conversão de data: exatamente quatro dígitos ASCII de ano, dois de mês e dois de dia, separados por hífen. | Cadastro e PATCH rejeitam `1990-4-15` e `1990-04-5` com 400; PATCH preserva nascimento anterior. Cadastro ISO retorna 201 e PATCH ISO retorna 200. |
| F02 | Corrigida em reteste isolado | Campo compartilhado entre Web e Admin, com entrada ISO estrita e widget cujo valor HTML é `AAAA-MM-DD`. | GET da edição administrativa verifica o valor ISO no HTML. POST com `16/04/1990` ou zeros ausentes retorna formulário com erro e preserva o nascimento. POST ISO retorna 302 e persiste a data. |
| F03 | Corrigida em reteste isolado | Tradução das mensagens humanas de token inválido para `Token inválido ou expirado.`, mantendo estrutura e identificadores técnicos do Simple JWT. | JWT malformado, expirado e refresh usado como access retornam 401 com `detail` e `messages[].message` em pt-BR; `token_not_valid`, `AccessToken`, `access` e cabeçalho Bearer são preservados. Access válido continua retornando 200. |
| F04 | Corrigida em reteste isolado | `id`, `last_login` e `date_joined` passam a integrar os controles internos protegidos no serviço compartilhado. | PATCH retorna 403 para cada entrada original, sem alterar valores; cadastro público também retorna 403. Campo desconhecido comum continua retornando 400. |

Arquivo de evidências executáveis:
[usuarios/tests/test_regressoes_qa_001.py](../../usuarios/tests/test_regressoes_qa_001.py).

Reprodução do reteste:

```bash
GERMANAS_BANCO=:memory: .venv/bin/pytest usuarios/tests/test_regressoes_qa_001.py -q --tb=short
```

Os controles adicionais rejeitam datas impossíveis, datas com hora, espaços
externos e dígitos não ASCII. A conversão e a maioridade continuam validadas pelos
mecanismos existentes. O navegador pode localizar visualmente um `input type=date`;
o valor HTML e o contrato recebido pelo servidor permanecem ISO.

## Verificações realizadas

| Comando | Resultado |
|---|---|
| `GERMANAS_BANCO=:memory: .venv/bin/pytest -q --tb=short` | 145 testes passaram, incluindo regressões, testes existentes e cenários sintéticos de migração/concorrência. |
| `.venv/bin/ruff check usuarios` | Aprovado. |
| `.venv/bin/ruff format --check usuarios` | Aprovado após ajuste final dos imports. |
| `.venv/bin/pyright usuarios` | Zero erros e avisos. |
| `.venv/bin/mypy usuarios/` | Aprovado. |
| `GERMANAS_BANCO=:memory: .venv/bin/python manage.py check` | Nenhum problema identificado. |
| `GERMANAS_BANCO=:memory: .venv/bin/python manage.py makemigrations --check --dry-run` | Nenhuma mudança detectada. |

## Devolução ao QA e limitações

Não restaram correções de código bloqueadas entre F01–F04. A confirmação no
servidor de QA deve preservar esses IDs e registrar a versão implantada, conforme
`qa/README.md`, em um novo relatório de rodada.

Continuam fora deste reteste DEV: SMTP real/entrega na caixa postal, instalação de
agendamento diário, avaliação visual em navegador, acessibilidade visual e espera
real pelos prazos de expiração. São limitações de cobertura, não defeitos novos
confirmados. Os testes simulam expiração e verificam HTML, sem comprovar o aspecto
visual ou a infraestrutura de produção. Não há credenciais de QA embutidas nem
logs de tokens, senhas, cookies ou dados pessoais neste documento.

## Rastreabilidade dos arquivos

SHA-256 do relatório de origem e dos arquivos usados nesta correção:

| Arquivo | SHA-256 |
|---|---|
| `qa/relatorios/relatorio_001.md` | `cd8edef8d6236243ebf62f82b44324335cc3c166b4fd49da649ba7bc6e8065c8` |
| `usuarios/admin.py` | `eb38f57d497562f5603d685fc2e3bdf3875d4ec9460c798f9b879597a1f68c96` |
| `usuarios/api/autenticacao.py` | `50eb9a4408c53ec894928699f7da26a55c5e0042e42f91bfca3b99229dd15048` |
| `usuarios/api/serializers.py` | `503fef3e6abf41dc5766336be50bbb86ee4cd2c9d878c2f183be59509c38b5b2` |
| `usuarios/formularios.py` | `3ac07b5277580f0a3e0ba32f7b89a0ff28f81ff9985854e920b3a875a2c19681` |
| `usuarios/servicos.py` | `641f2fa129dbd522aae2367f3ee86da006e00a8462dda80cf045a03acf8fafbd` |
| `usuarios/validadores.py` | `9cb9d62621f7bef10f7518ecfba8c12f1bc4232756d1cf52eedeea198d05ed10` |
| `usuarios/tests/test_regressoes_qa_001.py` | `bf40f6b22a848d999da9f66cebb3000cf40b02151a35188111ccd9be48566900` |

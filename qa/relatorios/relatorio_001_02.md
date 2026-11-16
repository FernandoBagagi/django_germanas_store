# Relatório de QA 001_02 — Usuários

Estado: **Finalizado — aprovado no escopo executado. F01–F04 corrigidas.**

Criado em: 2026-11-16T09:48:03-03:00

Commit no momento da criação: `5c6fb9cd66491bde8fad9458caf171d690a660fa`

## Resultado e execução

Reteste em **16/11/2026**, entre aproximadamente **09:48 e 09:55**, America/Bahia,
contra `http://127.0.0.1:8000/`.

**289 verificações funcionais HTTP aprovadas, zero divergências e zero bloqueios
de execução.** A suíte automatizada isolada também passou: **145 testes em
11,18 segundos**. As contagens são separadas: verificações HTTP incluem preparação,
controles e limpeza, não representam requisitos distintos nem repetem exatamente
as 350 verificações históricas da rodada 001.

Referências:

- [Relatório 001_01](relatorio_001_01.md), evidência histórica de 07/11/2026.
- [Especificação original](../../docs/PLAN_USUARIOS_ORIGINAL.md).

O diretório de trabalho estava limpo no início, no commit identificado acima.
O servidor não expõe um identificador de commit; o hash identifica o workspace
consultado, enquanto a confirmação da correção no servidor decorre dos resultados
HTTP observados. A afirmação da devolutiva DEV de que as correções estavam sem
commit descreve o estado daquela devolutiva, não o estado desta rodada.

Foram executados testes de comportamento; não houve revisão ou correção do código
da aplicação. Além dos roteiros existentes, foi acrescentado
[reteste_qa_001.py](../tests/reteste_qa_001.py) para verificar persistência após
rejeições, controles positivos e mensagens exatas. O README de QA foi atualizado
para documentar sua execução.

| Execução | Verificações | Falhas |
|---|---:|---:|
| `usuarios_api.py` | 151 | 0 |
| `usuarios_web.py` | 42 | 0 |
| `reteste_qa_001.py` | 64 | 0 |
| Recuperação: solicitação e confirmação pela API | 15 | 0 |
| Recuperação: solicitação e confirmação pela Web | 17 | 0 |
| **Total HTTP** | **289** | **0** |
| Suíte pytest isolada — contagem independente | **145 testes** | **0** |

Comandos para reprodução pela `.venv` a partir da raiz (caminhos atualizados):

```bash
GERMANAS_BANCO=:memory: .venv/bin/pytest -q --tb=short
.venv/bin/python qa/tests/usuarios_api.py
.venv/bin/python qa/tests/usuarios_web.py
.venv/bin/python qa/tests/reteste_qa_001.py
.venv/bin/python qa/tests/recuperacao_senha.py solicitar
.venv/bin/python qa/tests/recuperacao_senha.py confirmar --via api
.venv/bin/python qa/tests/recuperacao_senha.py solicitar
.venv/bin/python qa/tests/recuperacao_senha.py confirmar --via web
```

Os roteiros receberam `QA_EXECUCAO` e as credenciais fornecidas anteriormente via
ambiente. A execução principal utilizou `/tmp/germanas-qa-002-1VbJqj`; a recuperação
usou pastas independentes `recuperacao_api` e `recuperacao_web` dentro dela.
Os dois links de email foram fornecidos pelo operador a partir do console do
servidor e digitados na entrada oculta, sem armazenamento no relatório.

## Reteste das falhas

| ID | Situação | Caso executado / evidência |
|---|---|---|
| F01 | **Corrigida** | Cadastro e PATCH rejeitam datas sem zeros com 400. Controles negativos preservam a data anterior; ISO válido é aceito e persiste. |
| F02 | **Corrigida** | HTML do Admin apresenta valor ISO; datas brasileiras/sem zeros são rejeitadas e não persistem. POST ISO retorna 302 e persiste. |
| F03 | **Corrigida** | Mensagens humanas de JWT inválido em pt-BR, com 401 e estrutura/códigos/desafio Bearer preservados. Access válido segue aceito. |
| F04 | **Corrigida** | `id`, `last_login` e `date_joined` retornam 403 no cadastro e na edição por CLIENTE/ADMIN, preservando o perfil consultável. |

### F01 — formato ISO e persistência

Referência: seção 2, linha 31, e critérios de aceite, linha 229, da especificação.

Em `POST /api/v1/usuarios/cadastrar/` e `PATCH /api/v1/usuarios/<id>/`, os valores
`1990-4-15`, `1990-04-5`, `15/04/1990`, `1990-02-30`, `1990-04-15T00:00:00Z`,
` 1990-04-15 ` e `１９９０-０４-１５` retornaram **400**. Após cada PATCH rejeitado,
uma nova consulta confirmou `data_nascimento` igual a `1990-04-15`.

O PATCH válido com `1991-05-06` retornou **200** com essa data. Cadastros ISO
válidos retornaram **201**, inclusive no teste de maioridade exata. Não houve
flexibilização indevida dos demais validadores de cadastro observados.

### F02 — Django Admin

Referência: seção 2, linha 31, da especificação.

GET da edição administrativa retornou **200**, com atributo HTML
`name="data_nascimento"` e `value="1990-04-15"`.

Os POST com `16/04/1990`, `1990-4-15` e `1990-04-5` retornaram **200 com erros
de formulário**. Consultas subsequentes pela API confirmaram que a data não
mudou. O POST ISO com `1990-04-16` retornou **302** e a consulta confirmou
`1990-04-16` persistido. A apresentação visual localizada do navegador não foi
avaliada; a verificação refere-se ao HTML e ao contrato recebido pelo servidor.

### F03 — mensagens JWT

Referência: seção 2, linha 46; falha de autenticação, linha 15; Bearer, linha 153.

Tanto um JWT malformado quanto um refresh enviado como access em
`GET /api/v1/produtos/` retornaram **401**, com:

```json
{
  "detail": "Token inválido ou expirado.",
  "code": "token_not_valid",
  "messages": [
    {
      "token_class": "AccessToken",
      "token_type": "access",
      "message": "Token inválido ou expirado."
    }
  ]
}
```

O cabeçalho foi `WWW-Authenticate: Bearer realm="api"`. Um access válido continuou
retornando **200**. Não se esperou a expiração real de um access nesta rodada HTTP;
o resultado dessa espera não é inferido a partir do texto “ou expirado”.

### F04 — controles internos

Referência: seção 2, linhas 25 e 65, da especificação.

As três entradas originais, enviadas separadamente, foram recusadas com **403**:

```json
{"id": 7777777}
```

```json
{"last_login": "2026-11-07T00:00:00Z"}
```

```json
{"date_joined": "2026-11-07T00:00:00Z"}
```

Foram exercitados cadastro público e PATCH tanto por CLIENTE proprietário quanto
por ADMIN. Após cada PATCH recusado, o perfil exposto pela API permaneceu igual
ao anterior. `last_login` e `date_joined` não são expostos nessa representação;
não foi feita consulta direta ao banco para comparar esses valores internos.
Um campo desconhecido comum, `campo_inexistente_qa`, continuou retornando **400**.

## Novas falhas

Nenhuma nova falha confirmada nos cenários executados. Não há F05 nesta rodada.

## Cobertura, limitações e limpeza

Além dos quatro retestes, passaram os cenários de cadastro obrigatório, CPF,
telefone, maioridade, unicidade, permissões das três roles, acesso a usuário
alheio, campos privilegiados, PUT/PATCH, CRUD de produtos, filtros, navegação,
CSRF, logout, sessões, promoção/rebaixamento, desativação, reativação, reserva de
identificadores, rotação/blacklist e concorrência de refresh.

A recuperação foi concluída pela API e pelo formulário Web, com rejeição de senha
fraca, CSRF obrigatório na Web, senha antiga invalidada, nova senha aceita,
access/refresh anteriores revogados e link reutilizado recusado. GET do link
não alterou a senha. Na Web, senhas de confirmação diferentes foram rejeitadas.

As fixtures de QA foram desativadas pelos roteiros, com respostas **204**;
a fixture do controle complementar foi também consultada após a limpeza,
confirmando `is_active=false`. O produto fictício foi excluído e depois retornou
**404**. Os estados privados de recuperação foram removidos pelos roteiros após
a limpeza. As contas fornecidas continuam autenticando com a senha informada,
ativas e nas roles ADMIN, CLIENTE e VENDEDOR. Os registros de contas fictícias,
tokens, blacklist e auditoria permanecem sujeitos às regras normais da aplicação.

Limites da aprovação:

- Esta execução HTTP não avaliou aparência/responsividade/acessibilidade visual.
- O email foi observado no console; SMTP e entrega em caixa postal real não
  foram testados.
- Não houve espera real de 30 minutos, 24 horas ou uma hora para expiração de
  access, refresh e link. A duração declarada dos JWT foi verificada.
- Não houve mutação do último ADMIN do servidor, migração do banco real,
  regularização de conta legada real ou verificação do agendamento de limpeza.
- A aprovação automatizada isolada é complementar; não transforma essas
  condições de infraestrutura do servidor em verificações realizadas.

## Conclusão

**Aprovado o fechamento de F01, F02, F03 e F04.** As correções foram confirmadas
no servidor em execução, além da suíte isolada. Nenhuma regressão foi encontrada
nos fluxos exercitados. Não restam pendências entre as quatro falhas do relatório
001; as limitações acima permanecem fora da aprovação integral do ambiente.

## Evidências e roteiro complementar

O arquivo auxiliar de evidências e a devolutiva DEV foram removidos por solicitação
do usuário. Os resultados desta execução permanecem neste relatório.

- `qa/tests/reteste_qa_001.py`, SHA-256 da versão executada:
  `6e0b7b14b54ff9ed17152bc84c5e3ecd356c5d6b8f936fac810fc5023abb7ce5`.
- O roteiro complementar recebeu depois apenas formatação Ruff, sem mudança
  de lógica. SHA-256 da versão arquivada:
  `9224eb80f3d1bc111a47c70a5d19e15145f1c107e8d8e9b18a245bcfce5023df`.
- Os demais roteiros foram executados sem alteração, com os hashes abaixo.

## SHA-256 dos arquivos na criação do rascunho

Hashes históricos anteriores à reorganização; os caminhos abaixo foram atualizados.
O cliente HTTP deixou de gravar JSONL após esta execução.

- `docs/PLAN_USUARIOS_ORIGINAL.md`: `9fff7897a979981fd9d8d474e7cdb17d5970b6bab1d8b95f7f966be84e597f0d`
- `qa/tests/cliente_http.py`: `3b4e9f55fb1a8190921a6fc19b035a3441acd639a8e4e2ec9f8e6b305284d4b3`
- `qa/tests/recuperacao_senha.py`: `f20e7b9dfef2e19012faa0367f37f43a25a225f629cc87a5567e96e0e62a055a`
- `qa/tests/usuarios_api.py`: `696b440299ad6a121862f71047d05bc5e9537004cfb0d90116b9e3fed70c34ee`
- `qa/tests/usuarios_web.py`: `e7125b6071b9af22f98b7ec7f5dcec3003888eae62f2e149526b89a17475cb2b`

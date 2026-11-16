# Instruções para agentes — QA

Aplicam-se aos arquivos desta pasta, em complemento ao `AGENTS.md` da raiz.

## Estrutura

- `tests/`: código reutilizável dos testes HTTP de API, Web e recuperação de senha.
- `relatorios/`: resultados e falhas. **O usuário define a numeração**.
- Especificações: ficam na pasta docs(../docs/*.md). O usuário indica qual especificação usar.

## Regras

- Testar o comportamento conforme a especificação; não revisar ou modificar a
  implementação durante o QA, salvo solicitação do usuário.
- Reutilizar e manter os scripts em `tests/` para permitir novas execuções.
- Registrar no relatório falhas com referência à especificação, resultado esperado
  e encontrado. Informar limitações; só aprovar o que foi efetivamente testado.
- Ser o mais breve possível
- Preservar relatórios anteriores e IDs das falhas. Usar a numeração informada
  pelo usuário; não criar geradores de relatórios nem arquivos de evidências JSONL.
- Manter credenciais, tokens e estado privado fora do repositório.
- Alterar somente dados fictícios de QA e fazer limpeza pela aplicação.
- Não executar testes contra o servidor apenas para reorganizar arquivos.

## Executar

Na raiz do projeto, com o servidor em `http://127.0.0.1:8000`:

```bash
read -rsp 'Senha das contas de QA: ' QA_SENHA_USUARIOS
export QA_SENHA_USUARIOS
export QA_EXECUCAO="$(mktemp -d /tmp/germanas-qa-XXXXXX)"
.venv/bin/python qa/tests/usuarios_api.py
.venv/bin/python qa/tests/usuarios_web.py
.venv/bin/python qa/tests/reteste_qa_001.py
```

Usam `super_admin`, `cliente_01` e `vendedor_01`. Criam dados fictícios e fazem
limpeza pela aplicação. Resultados aparecem no terminal; não geram JSONL nem relatórios.

Para recuperação de senha, no mesmo terminal:

```bash
.venv/bin/python qa/tests/recuperacao_senha.py solicitar
.venv/bin/python qa/tests/recuperacao_senha.py confirmar --via api
```

Informe o link do email quando solicitado. Para Web, repita com `--via web`.
Se interromper, execute `recuperacao_senha.py limpar` pelo mesmo caminho.
`QA_EXECUCAO` guarda o estado temporário da recuperação fora do repositório.

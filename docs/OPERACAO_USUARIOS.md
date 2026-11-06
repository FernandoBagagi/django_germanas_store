# Operação do app usuarios

O plano aprovado está em `docs/PLAN_USUARIOS.md` e não foi alterado.

## Dependências e verificações

Simple JWT 5.5.1 e PyJWT 2.15.1 foram validados com as versões fixadas do projeto.
O ensaio executou migrações, emissão, autenticação, renovação e blacklist em
SQLite em memória. As versões já estavam presentes na `.venv`.

```bash
GERMANAS_BANCO=:memory: .venv/bin/pytest
GERMANAS_BANCO=:memory: .venv/bin/python manage.py check
GERMANAS_BANCO=:memory: .venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/ruff check .
.venv/bin/pyright usuarios config produtos/api
.venv/bin/mypy usuarios/
```

## Banco existente

Não executar os passos abaixo antes de autorização para acessar o banco real.
Parar os processos da aplicação durante a transição e produzir backup consistente
do SQLite, incluindo estado WAL quando houver, usando a API de backup SQLite.
Testar a restauração do backup antes de migrar. Não apagar o banco.

A primeira etapa mantém temporariamente `AUTH_USER_MODEL=auth.User` para que
o histórico de migrações administrativas continue consistente. A operação adota
as tabelas existentes, adiciona campos e valida emails exclusivos. IDs, hashes,
grupos, permissões e referências são preservados. As contas antigas ficam
pendentes de regularização; superusuários continuam ADMIN.

```bash
GERMANAS_PREPARAR_USUARIOS=1 .venv/bin/python manage.py migrate usuarios --skip-checks
.venv/bin/python manage.py migrate
.venv/bin/python manage.py check
```

`--skip-checks` é restrito à primeira etapa de transição, quando os dois modelos
coexistem temporariamente. Não usar `--fake`. A migração de adoção não possui
reversão automática: em caso de falha operacional, restaurar o backup junto com
a versão anterior da aplicação, mantendo o serviço parado até validar o estado.

Emails duplicados interrompem a migração antes de modificar dados. Não mesclar
contas nem inventar dados para resolver conflitos. Solicitar decisão do usuário.

Para um banco novo, basta `.venv/bin/python manage.py migrate`.
Para ensaios, `GERMANAS_BANCO` seleciona outro arquivo SQLite; não apontar os
ensaios para o banco real. Os testes automatizados usam bancos temporários.

Após a migração, entrar com um usuário legado e completar os campos faltantes
em `/usuarios/minha_conta/editar/`. O ADMIN pendente também precisa regularizar
seu cadastro antes de acessar a administração.

Criar o primeiro ADMIN de uma instalação limpa com:

```bash
.venv/bin/python manage.py createsuperuser
```

## Email

O padrão de desenvolvimento é o backend de console. Em produção, configurar:

- `GERMANAS_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`
- `GERMANAS_EMAIL_HOST`
- `GERMANAS_EMAIL_PORT` (padrão 587)
- `GERMANAS_EMAIL_USUARIO`
- `GERMANAS_EMAIL_SENHA`
- `GERMANAS_EMAIL_TLS` (`1` por padrão)
- `GERMANAS_EMAIL_REMETENTE`

Não versionar credenciais. Configurar domínio permitido, HTTPS e demais ajustes
de implantação do Django antes de expor o serviço. A recuperação não altera a
senha até a confirmação do link. Verificar o envio real no ambiente de destino.

## Limpeza da blacklist

Executar diariamente pelo agendador do ambiente de implantação:

```bash
.venv/bin/python manage.py flushexpiredtokens
```

Exemplo de entrada cron, usando o caminho deste projeto:

```cron
0 3 * * * cd /home/fernando/Projetos/Python/django_germanas_store && .venv/bin/python manage.py flushexpiredtokens
```

A configuração do agendador do sistema não é feita pelos testes nem pelas
migrações. Monitorar falhas da tarefa e de envio de email no ambiente de destino.

## Autenticação e administração

- Web: `/usuarios/entrar/`, `/usuarios/minha_conta/`, `/usuarios/` (ADMIN).
- API: `POST /api/v1/usuarios/login/` com `username` e `password`.
- Renovação: `POST /api/v1/usuarios/renovar/` com `refresh`.
- Chamadas protegidas: `Authorization: Bearer <access>`.
- Recuperação: `/usuarios/redefinir_senha/` ou API equivalente.
- A edição administrativa de papel é explícita e revoga acessos anteriores.
- Ações do Django Admin desativam contas; não existe exclusão física pela UI.

As páginas de produtos são públicas; a API de produtos exige JWT. Desativar,
reativar, trocar senha ou papel invalida os acessos anteriores. A reativação
pública por CPF foi aprovada sem confirmação de titularidade e sempre remove
privilégios, atribuindo CLIENTE.

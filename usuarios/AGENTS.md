## 1. Escopo

Este arquivo é a fonte de verdade do app `usuarios`. 
Não invalida as diretrizes gerais da raiz. Só deve ser
atualizado quando essas regras ou a estrutura mudarem.

## 2. Convenções de Estrutura de Diretórios

```text
usuarios/
├── AGENTS.md           # Contrato do app
├── api/                # Autenticação JWT, permissões, serializers, exceções, views e URLs
├── migrations/         # Adoção das tabelas legadas e evolução do esquema
├── templates/usuarios/ # Cadastro, conta, administração e recuperação
├── tests/              # Modelo, API, Web/Admin, migração, concorrência e regressões
├── admin.py            # Django Admin integrado às regras dos serviços
├── apps.py             # Configuração do app
├── formularios.py      # Formulários e envio de recuperação
├── middleware.py       # Validação de sessão e restrições do legado
├── migracoes.py        # Operação de adoção das tabelas existentes
├── models.py           # Usuario, gerenciamento e vínculos nativos
├── servicos.py         # Regras compartilhadas e transações
├── tokens.py           # Recuperação vinculada à versão de autenticação
├── validadores.py      # CPF, telefone e maioridade
├── views.py            # Interface Web
└── urls.py             # Rotas Web
```

## 3. Comportamento e regras de negócio

### Usuários

- `id` positivo, automático e permanente. Cadastro exige `username`, `email`,
  `password`, `first_name`, `last_name`, `data_nascimento`, `cpf` e `telefone`,
  inclusive no cadastro administrativo e em `createsuperuser`.
- `username` exclusivo, com regras nativas Django; 
- `email` exclusivo sem distinguir caixa;
- `cpf` exclusivo. `cpf` aceita pontuação, armazena 11 dígitos, valida verificadores e rejeita
  sequências repetidas. É imutável após o primeiro preenchimento.
- Os três identificadores (`username`, `email` e `cpf`) ficam reservados na desativação.
- `telefone` não exclusivo: normalizar para dígitos; aceitar fixo de 10 ou celular
  de 11 dígitos com DDD válido, removendo `+55`. Rejeitar ramais e números estrangeiros.
- `nascimento` recebido e representado literalmente como `AAAA-MM-DD`, com zeros,
  na API, Web e Admin. Rejeitar datas inválidas/futuras e menores de 18 anos.
  Calcular por calendário em `America/Bahia`; aniversário de 29/02 ocorre em
  01/03 nos anos não bissextos.
- Campos obrigatórios não podem ficar vazios em cadastros novos ou regularizados.
  `PATCH` é parcial; `PUT` exige todos os campos cadastrais editáveis.
- Senha opcional em atualizações, mas nunca vazia quando enviada. Validadores
  Django consideram os dados finais do usuário. Senha/hash nunca aparecem em
  respostas, JWT, erros ou telas administrativas. Troca exige novo login,
  inclusive na sessão Web que a realizou.
- Validações e mensagens humanas de JWT em pt-BR; nomes e códigos técnicos nativos
  permanecem em inglês. Respostas usam lista explícita de campos, sem controles
  internos de autenticação.

### Papéis e autorização

| Papel | Usuários | Produtos pela API | Django Admin |
|---|---|---|---|
| ADMIN | Listar, cadastrar, consultar, editar, desativar, reativar e alterar papéis de qualquer conta | Criar, consultar, alterar e excluir | Sim, poderes de superusuário |
| VENDEDOR | Consultar, editar e desativar somente a própria conta | Criar, consultar, alterar e excluir | Não |
| CLIENTE | Consultar, editar e desativar somente a própria conta | Consultar | Não |

- ADMIN equivale a `is_superuser=True` e exige `is_staff=True`; VENDEDOR e CLIENTE
  usam grupos Django e permissões nativas de produtos (`add/change/delete/view`
  e `view`, respectivamente). `papel` é representação controlada, não autoridade
  independente. Aplicar autorização por objeto, além das permissões de modelo.
- Cadastro público é aberto, inclusive a autenticados. Cadastro público e
  administrativo criam CLIENTE; promoção/rebaixamento são operações separadas,
  exclusivas de ADMIN e com efeito imediato.
- Rejeitar atribuição direta de `is_staff`, `is_superuser`, `is_active`, `groups`,
  `user_permissions`, `papel`, `versao_autenticacao`, `cadastro_pendente`, `id`,
  `last_login` e `date_joined` no cadastro/edição comum, inclusive por ADMIN.
  Na API, retornar 403; nunca ignorar silenciosamente.
- ADMIN consulta também inativos; listagem inclui ambos, ordenada por `id`,
  paginada em 12 registros. CLIENTE/VENDEDOR acessando outra conta recebem 403.
- Impedir desativação ou rebaixamento do último ADMIN ativo na API, Web e Admin,
  inclusive por ele próprio, operações em lote e requisições concorrentes.

### Desativação, reativação e legado

- Exclusão significa desativar, preservando dados e relações; nunca excluir
  fisicamente. Conta inativa não autentica nem renova tokens. Revogar acessos.
- CPF ativo duplicado retorna 400. Cadastro com CPF inativo reutiliza o mesmo
  registro e `id`, substitui cadastro/senha, remove privilégios e atribui CLIENTE.
  Reativação administrativa também exige cadastro completo, mantém CPF e começa
  como CLIENTE; promoção posterior é explícita.
- Validar tudo antes de gravar; colisões de username/email com outra conta
  impedem a operação inteira. Reativação é atômica e não restaura acessos antigos.
- Reativação pública exige somente identificação pelo CPF, sem comprovação de
  titularidade ou confirmação do email anterior: assumir a conta e seu histórico
  conhecendo esse CPF é uma consequência expressamente aceita.
- Legado preserva IDs, hashes e relações; superusuários permanecem ADMIN e os
  demais recebem CLIENTE. Não inventar dados ausentes: marcar `cadastro_pendente`.
- Pendentes podem autenticar/renovar, consultar/regularizar/desativar a própria
  conta, sair e recuperar senha. Páginas públicas continuam disponíveis; demais
  operações protegidas, produtos e Django Admin ficam bloqueados, inclusive para
  ADMIN. CPF ausente pode ser preenchido uma única vez.

### Web e recuperação de senha

- Disponibilizar entrar, cadastrar, minha conta, editar, confirmar desativação,
  solicitar recuperação e definir senha; ADMIN também lista/cadastra/edita,
  desativa/reativa usuários e altera papéis.
- Navegação: visitante vê Produtos/Entrar/Cadastrar; autenticado vê Produtos/
  Minha conta/Sair; ADMIN também vê Usuários. Preservar marca, rosa e responsividade.
- GET somente apresenta páginas/formulários. Mutações Web usam POST com CSRF,
  inclusive login/logout. Logout encerra apenas a sessão atual.
- Recuperação Web/API é pública: recebe email e envia link Django válido por uma
  hora para escolher senha, nunca uma senha por email. GET do link não altera nada.
- Confirmar por POST com senha válida; rejeitar token expirado/reutilizado.
  Resposta genérica para email inexistente ou conta inativa; não reativar contas.
  Falha de envio não altera senha; confirmação revoga todos os acessos anteriores.

### API e autenticação

Prefixo `/api/v1/usuarios/`:

| Método e rota relativa | Contrato |
|---|---|
| `POST cadastrar/` | Público; cadastro/reativação como CLIENTE |
| `POST login/` | Público; `username`, `password` → `access`, `refresh` |
| `POST renovar/` | Público; `refresh` → novo par |
| `POST redefinir_senha/` | Público; `email` solicita link |
| `POST confirmar_senha/` | Público; `uid`, `token`, `password` confirmam senha |
| `GET/PATCH/DELETE minha_conta/` | Consultar/editar/desativar própria conta |
| `GET/POST` na raiz | ADMIN lista/cadastra |
| `GET/PUT/PATCH/DELETE <id>/` | Próprio usuário ou ADMIN |
| `POST <id>/alterar_papel/` | ADMIN envia `papel`: ADMIN, VENDEDOR ou CLIENTE |
| `POST <id>/reativar/` | ADMIN envia cadastro completo, preservando CPF |

- JWT e autenticação obrigatórios por padrão; liberar explicitamente apenas as
  cinco operações públicas acima. Sessão Web não autentica a API.
- `Authorization: Bearer <access>`; access de 30 minutos; refresh de 24 horas
  desde cada emissão, inclusive após rotação. Rotacionar e bloquear o anterior;
  consumo atômico impede replay e duas renovações simultâneas bem-sucedidas.
- Cada acesso consulta ativação, versão de autenticação e permissões atuais.
  Renovação verifica assinatura, tipo, expiração, blacklist, ativação e versão.
- Troca/redefinição de senha, papel, desativação e reativação incrementam
  `versao_autenticacao`, revogam refresh anteriores e invalidam access e sessões.
  Sessões guardam a versão e a verificam nas requisições.
- HTTP: 200 consulta/atualização/login/renovação/reativação; 201 cadastro novo;
  204 desativação; 400 validação; 401 autenticação ausente/inválida/expirada/revogada;
  403 permissão/operação proibida; 404 recurso inexistente; 405 método não permitido.
- Produtos: páginas públicas; API exige JWT e cadastro completo. Todas as roles
  consultam; ADMIN/VENDEDOR usam POST na coleção e PUT/PATCH/DELETE no detalhe.
  Preservar filtros/validações/paginação; não inclui novas telas Web de manutenção.

## 4. Implementação, operação e validação

- Usar `Usuario(AbstractUser)`, `AUTH_USER_MODEL='usuarios.Usuario'`; preservar
  atributos, interfaces e métodos nativos Django em inglês, extensões em pt-BR.
  Reutilizar formulários, LoginView/LogoutView, sessões, grupos e recuperação.
  Senhas somente via `set_password()` e mecanismos Django.
- Views, API e Admin chamam serviços compartilhados. Não contornar regras com
  `QuerySet.update/delete` ou ações em lote. Transações protegem reativação,
  mudança de papel e último ADMIN, com concorrência compatível com SQLite;
  não depender somente de `select_for_update()`.
- Usar `JWTAuthentication` com consulta ao usuário, não
  `JWTStatelessUserAuthentication`. JWT sem sessão não significa ignorar o banco.
  Incluir apenas identificadores técnicos necessários (`user_id`, versão);
  não incluir dados cadastrais, permissões congeladas ou hashes/derivados.
  Não usar `CHECK_REVOKE_TOKEN` para inserir derivado da senha.
- Habilitar `rest_framework_simplejwt.token_blacklist` e migrações; agendar
  diariamente `.venv/bin/python manage.py flushexpiredtokens`.
- Operação registra Simple JWT 5.5.1/PyJWT 2.15.1 validados nas versões fixadas.
  Novas versões exigem resolução e ensaio isolado de imports, migrações, emissão,
  acesso, renovação e blacklist; não alterar versões do projeto automaticamente.
- Email: console em desenvolvimento, memória nos testes, SMTP por variáveis de
  ambiente em produção. Não versionar credenciais; verificar entrega real.
- Preservar tabelas `auth_user`, `auth_user_groups`, `auth_user_user_permissions`,
  IDs, hashes, grupos, permissões, produtos e referências. Não reescrever
  migrações antigas, apagar/recriar banco, mesclar contas ou inventar dados.
  Conflitos de email interrompem migração para decisão do usuário.
- Banco real exige autorização, backup consistente/restaurável e ensaio prévio.
  Seguir o procedimento abaixo. Não usar `--fake`; `--skip-checks` somente na
  primeira etapa da transição. Testar também instalação limpa.
- Validar com `GERMANAS_BANCO=:memory: .venv/bin/pytest`, `manage.py check` e
  `makemigrations --check --dry-run` pela `.venv`, além de Ruff e tipos do projeto.
  Usar pytest-django, APIClient e Faker `pt_BR`; bancos sintéticos para migração
  e concorrência. Cobrir validações/fronteiras, matriz de papéis, último ADMIN,
  reativação/colisões, JWT/replay/expiração, CSRF/sessões, recuperação, legado e
  regressões de produtos. Regras de QA funcional: [qa/AGENTS.md](../qa/AGENTS.md).


### Procedimentos operacionais

**Migração de banco existente (somente com autorização):** parar os processos,
fazer backup pela API SQLite incluindo WAL quando houver e testar a restauração.
A primeira etapa mantém temporariamente `AUTH_USER_MODEL=auth.User` para preservar
o histórico administrativo enquanto adota as tabelas e valida emails exclusivos:

```bash
GERMANAS_PREPARAR_USUARIOS=1 .venv/bin/python manage.py migrate usuarios --skip-checks
.venv/bin/python manage.py migrate
.venv/bin/python manage.py check
```

Emails duplicados devem interromper a migração antes de modificar dados. A adoção
não tem reversão automática: em falha operacional, restaurar backup e versão
anterior da aplicação; manter o serviço parado até validar o estado.
Para banco novo, usar `migrate` e `createsuperuser` pela `.venv/bin/python manage.py`.
Para ensaios, `GERMANAS_BANCO` seleciona SQLite separado; nunca usar o banco real.
Após migrar, regularizar legados em `/usuarios/minha_conta/editar/`, inclusive ADMIN.

**Verificações isoladas:**

```bash
GERMANAS_BANCO=:memory: .venv/bin/pytest
GERMANAS_BANCO=:memory: .venv/bin/python manage.py check
GERMANAS_BANCO=:memory: .venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/ruff check .
.venv/bin/pyright usuarios config produtos/api
.venv/bin/mypy usuarios/
```

A validação registrada de Simple JWT/PyJWT usou SQLite em memória para migrações,
emissão, autenticação, renovação e blacklist; as versões já estavam na `.venv`.

**Email em produção:** configurar `GERMANAS_EMAIL_BACKEND` como
`django.core.mail.backends.smtp.EmailBackend`, `GERMANAS_EMAIL_HOST`,
`GERMANAS_EMAIL_PORT` (587), `GERMANAS_EMAIL_USUARIO`, `GERMANAS_EMAIL_SENHA`,
`GERMANAS_EMAIL_TLS` (`1`) e `GERMANAS_EMAIL_REMETENTE`. Configurar domínio permitido,
HTTPS e ajustes de implantação Django antes de expor o serviço.

**Agendamento:** configurar externamente a execução diária de
`.venv/bin/python manage.py flushexpiredtokens`, na raiz do projeto. Testes e
migrações não configuram o agendador. Monitorar falhas dessa tarefa e do envio de email.

**Entradas Web:** `/usuarios/entrar/`, `/usuarios/minha_conta/`, `/usuarios/`
(ADMIN) e `/usuarios/redefinir_senha/` (recuperação).

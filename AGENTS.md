## 1. Contexto e Visão do Projeto

- **Nome do Projeto:** Germana's Store (`django_germanas_store`)
- **Tipo:** Plataforma de e-commerce que inclui views HTML tradicionais do Django e endpoints de API RESTful.
- **Versão do Python:** 3.14
- **Versão do Django:** 6.1.2
- **Django REST Framework (DRF):** 3.18.3
- **Objetivo Principal:** Desenvolvimento incremental de um e-commerce.

---

## 2. Convenções de Estrutura de Diretórios

```text
django_germanas_store/
├── .venv/               # Ambiente virtual (ignorado pelo git)
├── config/              # Módulo de configuração central (settings, urls raiz, wsgi/asgi)
├── produtos/            # Catálogo de produtos: consulta Web e API
│   ├── api/             # Serializers, views de leitura, paginação e URLs da API
│   ├── migrations/      # Migrações do modelo Produto
│   ├── static/produtos/ # Estilos e máscara JavaScript de preços
│   ├── templates/produtos/ # Base, início, listagem e detalhe
│   ├── tests/           # Testes pytest de modelos, páginas e API
│   ├── apps.py          # Configuração da app
│   ├── models.py
│   ├── servicos.py      # Consulta e filtros compartilhados entre Web e API
│   ├── views.py         # Views HTML / Web
│   └── urls.py          # Definições de rotas da aplicação
├── pedidos/             # App (futuro): Carrinho de compras e processamento de pedidos
├── .gitignore           # Modificar somente se o usuário permitir!
├── AGENTS.md            # Diretrizes para Agentes de IA. Modificar sempre houver alguma mudança na estrutura de pastas e da regra de negócio 
├── db.sqlite3           
├── manage.py            # Inicializador do projeto
├── pyproject.toml       # Definição das regras técnicas para as ferramentas CLI
└── requirements.txt     # Dependências fixadas do projeto
```

---

## 3. Arquitetura e Diretrizes de Código

### Catálogo de Produtos
- `Produto` possui código `id` inteiro positivo gerado automaticamente, nome comercial,
  descrição, URL de imagem e preço não negativo com duas casas decimais (até 12 dígitos).
- A página `/` apresenta a navegação; `/produtos/` lista cards e
  `/produtos/<int:id>/` apresenta o detalhe com preço em reais no padrão pt-BR.
- A identidade visual usa rosa. A página inicial anuncia a chegada da loja,
  preservando a navegação com marca e aba Produtos.
- Os cards mostram nome em uma linha com reticências e preço brasileiro abaixo,
  em rosa mais claro para diferenciá-lo do nome.
  Na listagem, busca, preço mínimo, preço máximo, Filtrar e limpar ocupam
  proporções 9:4:4:2:1 em telas largas, com
  adaptação para celular. Os botões Filtrar e limpar ficam na mesma linha dos
  campos em telas largas; a limpeza usa botão vermelho com ícone de lixeira.
- Os preços na Web usam máscara de centavos da direita para a esquerda
  (digitar `123456` exibe `1.234,56`), sem controles de incremento.
  A Web aceita valores brasileiros e links anteriores com ponto decimal;
  a API mantém o formato decimal com ponto.
- A API é somente leitura: `GET /api/v1/produtos/` e
  `GET /api/v1/produtos/<int:codigo>/`. `codigo` corresponde ao `id` do produto.
- Filtros por query string: `busca` procura trecho no nome OU na descrição
  (`icontains`); `preco_minimo` e `preco_maximo` são inclusivos e aceitam valores
  decimais com ponto. A API também permite filtrar por `codigo` exato.
- Filtros combinados são aplicados conjuntamente; campos vazios são ignorados.
  Valores inválidos, negativos ou faixa invertida retornam HTTP 400 com mensagens.
  Produto inexistente retorna HTTP 404.
- A API retorna `count`, `next`, `previous` e `results`, com 12 produtos por página,
  ordenados por `id`. Use `page` para navegar.
- Execute `.venv/bin/pytest` para os testes em `produtos/tests/`, com
  `DJANGO_SETTINGS_MODULE=config.settings` e Faker na localidade `pt_BR`.

### Idioma e Nomenclatura do Código (pt-BR)
- **Convenção de Idioma:** Nomes de apps, modelos, tabelas, funções, métodos, variáveis, endpoints de API, arquivos e pastas devem ser escritos em **Português do Brasil (pt-BR)** (ex: `produtos`, `pedidos`, `calcular_total_pedido`).
- **Formatação de Nomes:**
  - Use **snake_case** para nomes de apps, variáveis, funções, métodos, rotas e arquivos.
  - Use **PascalCase** para nomes de modelos, views baseadas em classes (CBVs), serializers e formulários.

### Estrutura do Projeto e Nomenclatura
- A pasta de configuração raiz do Django chama-se **`config`**.
- As apps do Django devem ser módulos modulares e de responsabilidade única (ex: `produtos`, `pedidos`, `usuarios`).

### Arquitetura de API REST
- Mantenha a lógica de API dentro de uma subpasta `api/` em cada app.
- Use **Django REST Framework (DRF)** para os endpoints da API.
- Agrupe os endpoints da API sob prefixos de rota padrão (ex: `/api/v1/produtos/`).
- Use Serializers para validação e representação de dados.

### Banco de Dados e Modelos
- Escreva atributos `verbose_name` e `verbose_name_plural` explícitos nas classes `Meta` dos modelos.
- Sempre implemente o método `__str__` para todos os modelos.
- Gere as migrações imediatamente após modificar o arquivo `models.py`.

### Estilo e Qualidade de Código
- Siga as diretrizes padrão da PEP 8 para Python.
- Use Type Hints em todos os lugares onde for razoável.
- Mantenha a lógica de negócios em classes de serviço (*service classes*), mantendo as views concisas (*thin views*).

---

## 4. Regras de Fluxo de Trabalho para Agentes de IA

1. **Desenvolvimento Incremental:** Implemente funcionalidades em blocos pequenos e testáveis (ex: Modelo de Produto -> Serializer de Produto -> ViewSet/Rotas de Produto).
2. **Atenção às Migrações:** Ao criar ou atualizar modelos do Django, notifique o usuário ou execute `python manage.py makemigrations`.
3. **Segurança do Ambiente:** Não execute comandos que apaguem o banco de dados sem o consentimento explícito do usuário.

---

## 🛠️ Ambiente de Desenvolvimento e Comandos

- **Sistema Operacional:** Ubuntu 26.04.1 LTS
- **Versão do Python:** Python 3.14 (executado rigorosamente via `.venv`)
- **Interpretador do Projeto:** `.venv/bin/python`
- **Gerenciador de Pacotes:** `.venv/bin/pip`

Ao executar comandos de terminal, **sempre utilize o Python e Pip do ambiente virtual**:
- Rodar servidor: `.venv/bin/python manage.py runserver`
- Criar/Aplicar migrações: `.venv/bin/python manage.py makemigrations` e `.venv/bin/python manage.py migrate`
- Executar testes: `.venv/bin/pytest`
- Executar linter: `.venv/bin/ruff check` e `.venv/bin/ruff format`

---

## Ruff & SonarQube

O projeto utiliza **Ruff** e **SonarQube** como analisadores estáticos. Todo código gerado pela IA deve estar em conformidade com as configurações do `pyproject.toml`

---

## 🧪 Estratégia de Testes e Geração de Dados

A IA deve obrigatoriamente criar testes automatizados para todas as novas funcionalidades (modelos, views e endpoints de API REST).

1. **Framework de Testes:**
   - Utilize o **`pytest`** em conjunto com a extensão **`pytest-django`**.
   - Todos os arquivos de teste devem seguir o prefixo `test_*.py` (ex: `test_models.py`, `test_views.py`, `test_api.py`).
   - Marque os testes que acessam o banco de dados com a fixture `@pytest.mark.django_db`.

2. **Geração de Dados Fictícios:**
   - Utilize a biblioteca **`faker`** (instância `Faker('pt_BR')`) para gerar dados aleatórios realistas nos testes (nomes, e-mails, descrições, preços, etc.), evitando dados estáticos fixos (*hardcoded*).

3. **Testes de API REST:**
   - Utilize o cliente de testes nativo do Django REST Framework (`rest_framework.test.APIClient`) para testar requisições HTTP (GET, POST, PUT, DELETE) nos endpoints da API.

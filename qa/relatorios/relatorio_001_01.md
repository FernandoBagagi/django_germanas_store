# Relatório de QA 001_01 — Usuários

> Rodada de 07/11/2026. Arquivado em `qa/relatorios/` em 16/11/2026.
> Conteúdo histórico preservado; esta organização não representa um reteste.

Data: 07/11/2026, America/Bahia.

Ambiente testado: `http://127.0.0.1:8000/`.

Especificação utilizada: [PLAN_USUARIOS_ORIGINAL.md](../../docs/PLAN_USUARIOS_ORIGINAL.md).
O pedido mencionava `PLAN_USUARIO_ORIGINAL.md`, mas o arquivo existente e aberto
no IDE é `PLAN_USUARIOS_ORIGINAL.md`. As linhas citadas abaixo correspondem ao
arquivo original lido nesta execução. Nenhum plano foi modificado.

## Resultado e método

**Quatro divergências confirmadas em relação à especificação.** Não foram
encontradas falhas de controle de acesso nos cenários efetivamente executados.
Isso não representa aprovação integral: existem requisitos não exercitados,
discriminados ao final.

Foram registradas **350 verificações**, incluindo retestes, verificações de
persistência e limpeza. Esse número não representa 350 requisitos distintos.
Após triagem, nove verificações divergentes correspondem aos quatro problemas
abaixo; quatro outros resultados inicialmente sinalizados foram descartados
por expectativa inadequada ou interferência do próprio roteiro.

Os testes foram de caixa-preta: requisições HTTP à API, submissão de formulários
com cookies e CSRF, inspeção de HTML retornado e confirmação de resultados por
novas requisições. Não houve leitura ou avaliação do código da aplicação, acesso
direto ao banco, execução da suíte interna, análise estática ou correção de código.

As contas `super_admin`, `cliente_01` e `vendedor_01` foram usadas conforme as
roles informadas. Alterações cadastrais, de senha, papel e estado foram aplicadas
somente às contas fictícias criadas nesta execução.

## F01 — API aceita datas fora do formato AAAA-MM-DD

**Severidade:** baixa — divergência de contrato de entrada, sem erro na data
normalizada de saída.

**Local na especificação:** seção 2, “Modelo de usuário”, linha 31:
“Data ISO `AAAA-MM-DD`; idade mínima de 18 anos”. Critério de aceite na linha 229:
validação de datas no cadastro.

**Locais testados:**

- `POST /api/v1/usuarios/cadastrar/`.
- `PATCH /api/v1/usuarios/minha_conta/`.

**Como reproduzir:**

1. Enviar um cadastro válido, com identificadores ainda não utilizados, mas com
   `data_nascimento` igual a `1990-4-15`.
2. Com um usuário autenticado, enviar separadamente os PATCH abaixo:

```json
{"data_nascimento": "1990-4-15"}
```

```json
{"data_nascimento": "1990-04-5"}
```

**Esperado:** rejeição com HTTP 400, pois mês e dia devem ocupar duas posições
no formato estabelecido.

**Encontrado:**

| Operação | Entrada | HTTP recebido | Data retornada |
|---|---|---:|---|
| Cadastro | `1990-4-15` | 201 | `1990-04-15` |
| Atualização | `1990-4-15` | 200 | `1990-04-15` |
| Atualização | `1990-04-5` | 200 | `1990-04-05` |

O cadastro de reprodução recebeu o id 5. As atualizações foram reproduzidas na
conta de QA id 4. A API aceita e normaliza entradas que não obedecem ao formato
literal especificado. Datas brasileiras, impossíveis e com componente de hora
foram rejeitadas nos controles comparativos.

## F02 — Django Admin apresenta e aceita nascimento em DD/MM/AAAA

**Severidade:** baixa — inconsistência do formato de datas entre interfaces.

**Local na especificação:** seção 2, linha 31, determina data ISO `AAAA-MM-DD`;
não estabelece exceção para o Django Admin.

**Local testado:** `/admin/usuarios/usuario/4/change/`, autenticado como ADMIN.

**Como reproduzir:**

1. Abrir a edição administrativa de um usuário cujo nascimento seja `1990-04-15`.
2. Observar o valor do campo de nascimento.
3. Enviar o formulário com os demais dados válidos e nascimento `16/04/1990`.
4. Consultar o usuário pela API.

**Esperado:** apresentação em `1990-04-15` e rejeição de entrada `16/04/1990`,
preservando o padrão ISO exigido.

**Encontrado:** o HTML servido contém um campo de texto com o valor brasileiro:

```html
<input type="text" name="data_nascimento" value="15/04/1990" class="vDateField" ...>
```

O POST com `16/04/1990` retornou **HTTP 302**, e a consulta subsequente à API
confirmou persistência de `"data_nascimento": "1990-04-16"`.

Não se trata de inferência sobre a localização visual de um `input type="date"`:
o próprio HTML retornado usa `type="text"` com valor `15/04/1990`.

## F03 — Erros de validação de JWT são retornados em inglês

**Severidade:** baixa — requisito de localização não atendido.

**Local na especificação:** seção 2, linha 46:
“Mensagens de validação em pt-BR”. O HTTP esperado para falha de autenticação
está na linha 15.

**Local testado:** `GET /api/v1/produtos/`.

**Como reproduzir:** enviar a requisição com:

```http
Authorization: Bearer invalid.jwt.token
```

**Esperado:** HTTP 401 com mensagens destinadas ao usuário em pt-BR.

**Encontrado:** o status 401 está correto, mas duas mensagens vêm em inglês:

```json
{
  "detail": "Given token not valid for any token type",
  "code": "token_not_valid",
  "messages": [
    {
      "token_class": "AccessToken",
      "token_type": "access",
      "message": "Token is invalid"
    }
  ]
}
```

A divergência está nos valores humanos de `detail` e `message`. Não se solicita
traduzir nomes nativos, códigos ou identificadores técnicos, cuja preservação
em inglês é compatível com a especificação.

## F04 — Edição de controles internos retorna 400 em vez de 403

**Severidade:** baixa — status de erro divergente; as alterações foram bloqueadas.

**Local na especificação:** seção 2, “Papéis e permissões”, linha 65:
“Rejeitar com 403 tentativas de enviar campos privilegiados: `is_staff`,
`is_superuser`, `is_active`, `groups`, `user_permissions`, `papel` e controles
internos.” Os atributos nativos `id`, `last_login` e `date_joined` constam da
linha 25 e são controles gerenciados pelo sistema, não dados cadastrais editáveis.

**Local testado:** `PATCH /api/v1/usuarios/minha_conta/`, autenticado como CLIENTE.

**Como reproduzir:** enviar separadamente:

```json
{"id": 7777777}
```

```json
{"last_login": "2026-11-07T00:00:00Z"}
```

```json
{"date_joined": "2026-11-07T00:00:00Z"}
```

**Esperado:** HTTP 403 pela tentativa de editar controles internos.

**Encontrado:** HTTP 400 em todas as três requisições, com os corpos:

```json
{"id": ["Campo não permitido."]}
```

```json
{"last_login": ["Campo não permitido."]}
```

```json
{"date_joined": ["Campo não permitido."]}
```

Os campos privilegiados explicitamente enumerados na linha 65, além de
`versao_autenticacao` e `cadastro_pendente`, retornaram 403 nos controles
comparativos. Não foi observada escalada de privilégio ou alteração do id;
o problema identificado é a classificação HTTP dos demais controles internos.

## Cobertura sem falha observada

Nos casos exercitados, funcionaram:

- Login das três roles, token ausente/inválido, leitura autenticada de produtos
  e manutenção de páginas públicas.
- Obrigatoriedade de campos ausentes, nulos e vazios; CPF inválido/repetido;
  DDD, telefone estrangeiro e ramais; normalização de CPF e telefone.
- Rejeição de menor de idade, data futura e data impossível; aceitação de pessoa
  completando 18 anos em 07/11/2026.
- Unicidade de CPF, username e email sem distinguir caixa; preservação dos
  identificadores durante inatividade; cadastro concorrente do mesmo CPF.
- Bloqueio de edição, exclusão e consulta de outro usuário por CLIENTE/VENDEDOR,
  tanto na API quanto nas páginas Web; rejeição de promoção sem ADMIN.
- Cadastro administrativo como CLIENTE; promoção a VENDEDOR e ADMIN; acesso
  efetivo do ADMIN promovido ao Django Admin; rebaixamento e revogação.
- Validação de campos obrigatórios e senha no Django Admin; ausência de hashes
  nos formulários administrativos inspecionados; bloqueio das rotas de exclusão
  física, com preservação do usuário consultável.
- POST, PUT/PATCH e DELETE de produto fictício por roles autorizadas; bloqueio
  de escrita por CLIENTE; preço negativo, filtros e detalhe público em reais.
- Atualização parcial; PUT completo sem senha; rejeição de PUT incompleto,
  CPF alterado, senha vazia/fraca e senha semelhante aos dados finais.
- Duracões declaradas nos JWT: 1.800 segundos para access e 86.400 para refresh;
  claims técnicos sem dados cadastrais, senha, hashes ou papel congelado.
- Rotação, rejeição de replay de refresh e uso concorrente do mesmo refresh,
  com somente uma renovação bem-sucedida.
- Revogação de access e refresh após troca de senha, mudança de papel e
  desativação; tokens antigos continuaram inválidos após reativação.
- Desativação própria Web/API; reativação pública e administrativa Web/API;
  preservação do id, substituição de dados e retorno a CLIENTE.
- Reativação com email em conflito rejeitada sem alteração parcial; reativação
  administrativa incompleta rejeitada.
- Paginação administrativa com mais de 12 contas, segunda página e presença
  de registros inativos.
- Navegação por role, CSRF, logout apenas por POST, logout mantendo outra sessão
  Web aberta e invalidação de sessões após troca de senha ou mudança de papel.
- GET de desativação sem efeito de negócio; métodos GET rejeitados nas ações
  de API exercitadas.
- Recuperação por email, com links obtidos do console pelo operador; confirmação
  pela API e pelo formulário Web; GET sem troca de senha; senhas fracas ou
  diferentes rejeitadas; senha antiga invalidada; tokens anteriores revogados;
  link reutilizado rejeitado.
- Resposta de recuperação idêntica para conta inativa e email inexistente.

### Resultados descartados durante a triagem

- A aceitação da palavra `administrador` não foi classificada como defeito:
  o plano exige os validadores Django, mas não especifica que essa palavra
  particular faça parte da lista de senhas comuns. Senhas curtas, numéricas e
  semelhantes ao cadastro foram rejeitadas.
- `/admin/usuarios/usuario/add/` retorna 302 para `/usuarios/novo/`. O destino
  apresentou corretamente o formulário de cadastro. O redirecionamento não é
  falha funcional nem evidência de exposição de hash.
- Um link de recuperação foi invalidado após login Web do próprio roteiro.
  O teste foi repetido com novo link e sequência corrigida, concluindo com
  sucesso. Esse resultado não foi atribuído à implementação.

## Limitações — não aprovadas nem classificadas como falhas

- **Último ADMIN ativo:** não foram tentados desativação ou rebaixamento do único
  ADMIN original, nem concorrência que pudesse deixar o ambiente sem ADMIN.
  Promoção/rebaixamento de ADMIN fictício foi testado mantendo o original ativo.
- **Legado incompleto:** não havia fixture de conta legada fornecida e o cadastro
  público corretamente impede criar uma conta incompleta. Sua regularização
  e restrições específicas não foram exercitadas.
- **Migração e compatibilidade:** não foram executadas migrações, instalação
  limpa, preservação de banco antigo, resolução de dependências ou comandos
  administrativos como `createsuperuser`.
- **Tempo real:** foram conferidos os tempos declarados nos tokens, mas não se
  aguardaram 30 minutos, 24 horas ou uma hora para testar expiração real de
  access, refresh e link. O limite de aniversário de 29/02 em ano não bissexto
  não pôde ser exercitado na data atual sem controlar o relógio do servidor.
- **Entrega de email:** os links do backend de console foram confirmados e
  utilizados. SMTP de produção, falha de transporte e entrega em caixa postal
  real não foram testados.
- **Agendamento:** não foi verificada a limpeza diária de tokens expirados.
- **Interface visual:** não havia navegador disponível; aparência rosa,
  responsividade, interação JavaScript e acessibilidade visual não foram
  avaliadas. Os testes Web verificam respostas HTTP e HTML servido.

## Estado do ambiente ao finalizar

- As três contas fornecidas continuam autenticando com a senha original.
  Seus dados cadastrais e roles consultáveis pela API foram comparados com o
  início da execução e permanecem iguais.
- As 11 contas fictícias criadas, ids **4 a 14**, foram desativadas pela API e
  sua inatividade foi confirmada individualmente. Seus identificadores ficam
  reservados conforme a regra de negócio; os registros não foram apagados.
- O produto fictício criado para os testes de CRUD foi excluído e a consulta
  posterior retornou 404.
- Logins, sessões, tokens, blacklist e registros operacionais gerados pelos
  testes podem permanecer no ambiente. Não foi realizada limpeza direta do banco.
- Nenhum código da aplicação ou documento de planejamento foi alterado.
  Este relatório é o único artefato adicionado ao repositório nesta execução.

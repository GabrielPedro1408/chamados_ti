# Deskly — Especificação do Projeto

> Sistema de Chamados de TI — Projeto de aplicação em Python
> Centro Universitário Padre Anchieta (UniAnchieta) · Engenharia de Software · 2º semestre de 2026
> Disciplina: Programação em Python · Prof. Dr. Roger Antunes

Este documento é a fonte de verdade sobre **o que** o sistema deve fazer. Ao implementar qualquer funcionalidade, siga as regras abaixo, principalmente as de banco de dados e o escopo (o que está fora do sistema).

---

## 1. Stack e visão geral

- **Backend:** Python + **Flask**
- **Banco de dados:** **MySQL**
- **Frontend:** interface web
- O sistema tem **dois sistemas interligados**:
  1. **Sistema da empresa**: cadastros (empresa, setores, equipes, funcionários) e dashboard de métricas.
  2. **Sistema de chamados**: com **dois modos de login**, **funcionário** e **técnico**, cada um com sua interface principal.

### 1.1 Interface do Funcionário (padrão)

Simples. O funcionário só pode:

- Abrir um chamado
- Ver sua **posição na fila** de atendimento
- Ver se o chamado está **em andamento**
- **Apagar** um chamado
- Ver **quantos chamados abriu no mês**

### 1.2 Interface do Técnico

- Exibe **todos os chamados pendentes**
- Exibe o **número de chamados que o técnico resolveu no dia**
- Ao clicar em um chamado, abre um **pop-up** com as ações:
  - Assumir atendimento
  - Alterar prioridade
  - Adicionar comentários
  - Registrar solução
  - Finalizar chamado

---

## 2. Banco de dados

Legenda: **PK** = chave primária · **FK** = chave estrangeira.

### Empresa

| Campo | Tipo | Chave | Descrição / Regra |
|---|---|---|---|
| IdEmpresa | int | PK | Identificador único das empresas |
| RazaoSocial | varchar(255) | | Razão social da empresa |
| Cnpj | varchar(14) | | **Salvar apenas os números** do CNPJ. Remover a formatação antes de gravar. Único. |
| SenhaHash | varchar(255) | | Senha de acesso da empresa (login por CNPJ + senha), **salva como hash** |

### Setor

| Campo | Tipo | Chave | Descrição / Regra |
|---|---|---|---|
| IdSetor | int | PK | Identificador único dos setores |
| IdEmpresa | int | FK → Empresa | Relaciona o setor à empresa |
| NomeSetor | varchar(50) | | Nome do setor |

### Usuario

| Campo | Tipo | Chave | Descrição / Regra |
|---|---|---|---|
| IdUsuario | int | PK | Identificador único dos usuários |
| IdEmpresa | int | FK → Empresa | Relaciona o usuário à empresa |
| NomeUsuario | varchar(255) | | Salvar **APENAS caracteres em maiúsculo (UPPERCASE) e sem espaços**. Único (o login não pede a empresa). |
| SenhaHash | varchar(255) | | A senha **deve ser salva como hash**, nunca em texto puro (o hash do werkzeug tem ~162 caracteres) |

### EquipeTecnica

| Campo | Tipo | Chave | Descrição / Regra |
|---|---|---|---|
| IdEquipe | int | PK | Identificador único das equipes técnicas (se houver) |
| IdEmpresa | int | FK → Empresa | Relaciona a equipe à empresa |
| NomeEquipe | varchar(50) | | Nome da equipe |

### FuncionarioTecnico

| Campo | Tipo | Chave | Descrição / Regra |
|---|---|---|---|
| IdTecnico | int | PK | Identificador único dos técnicos |
| IdUsuario | int | FK → Usuario | Relaciona o técnico ao usuário |
| IdEquipe | int **NULL** | FK → EquipeTecnica | Equipe do técnico (opcional) |

### FuncionarioPadrao

| Campo | Tipo | Chave | Descrição / Regra |
|---|---|---|---|
| IdFuncionario | int | PK | Identificador único dos funcionários padrão |
| IdUsuario | int | FK → Usuario | Relaciona o funcionário ao usuário |
| IdSetor | int | FK → Setor | Setor do funcionário |

### Prioridade

| Campo | Tipo | Chave | Descrição / Regra |
|---|---|---|---|
| IdPrioridade | int | PK | Identificador único das prioridades |
| DescricaoPrioridade | varchar | | Descrição da prioridade (tamanho não definido no documento original) |

### Chamado

| Campo | Tipo | Chave | Descrição / Regra |
|---|---|---|---|
| IdChamado | int | PK | Identificador único dos chamados |
| IdEmpresa | int | FK → Empresa | Empresa do chamado |
| IdTecnico | int **NULL** | FK → FuncionarioTecnico | Técnico responsável (NULL até alguém assumir) |
| IdFuncionario | int | FK → FuncionarioPadrao | Funcionário que abriu o chamado |
| Descricao | varchar(500) | | Descrição escrita pelo usuário |
| IdPrioridade | int | FK → Prioridade | Prioridade do chamado (nasce como "Baixa") |
| Previsao | varchar(25) **NULL** | | Previsão de resolução, definida pelo técnico |
| DataHoraAbertura | datetime | | Data/hora de abertura do chamado |
| TempoGasto | int **NULL** | | Minutos da abertura até a finalização |
| Status | varchar(20) | | `aguardando` → `em_andamento` (ao assumir) → `finalizado` |
| Solucao | varchar(1000) **NULL** | | Solução registrada pelo técnico ao finalizar |
| DataHoraFechamento | datetime **NULL** | | Quando o chamado foi finalizado (métricas: resolvidos no dia, tempo médio) |

### Comentario

| Campo | Tipo | Chave | Descrição / Regra |
|---|---|---|---|
| IdComentario | int | PK | Identificador único dos comentários |
| IdChamado | int | FK → Chamado | Chamado comentado (apagado junto com o chamado) |
| IdUsuario | int | FK → Usuario | Autor do comentário |
| Texto | varchar(500) | | Texto do comentário |
| DataHora | datetime | | Quando foi escrito |

### Regras de dados (resumo)

- CNPJ: gravar só dígitos (14 caracteres).
- NomeUsuario: converter para UPPERCASE e remover espaços antes de gravar.
- Senha: sempre gravar hash, nunca texto puro.
- Um `Usuario` é técnico (`FuncionarioTecnico`) ou padrão (`FuncionarioPadrao`). O tipo define a interface que ele vê após o login.
- Técnico pode não ter equipe (`IdEquipe` aceita NULL).
- Fila de atendimento: ordenada por prioridade (Crítica primeiro) e depois por ordem de abertura.
- Funcionário com chamados ligados não pode ser excluído nem mudar de tipo (preserva o histórico e as métricas).
- Script do banco: `database/deskly.sql` (tabela do técnico se chama `funcionariotecnico`).

---

## 3. Funcionalidades essenciais (obrigatórias)

- Cadastro de empresas
- Cadastro de setores
- Cadastro de equipes
- Cadastro de funcionários (técnico e padrão)
- Iniciar um chamado (funcionário padrão)
- **Dashboard (Técnicos):** contém todos os chamados
- **Manipulação de chamados (Técnicos):**
  - Atender
  - Dar previsão de resolução
  - Finalizar
  - Alterar prioridade
- **Dashboard (Empresas):**
  - Quantidade de chamados em aberto e resolvidos
  - Quantos atendimentos cada técnico faz por mês
  - Tempo médio para o técnico resolver o problema
  - Quantos chamados os funcionários abrem no mês

## 4. Funcionalidades desejáveis (opcionais)

- **IA para auxílio na resolução de chamados:** comparar um novo chamado com chamados antigos e sugerir uma possível solução ao técnico, poupando tempo de troubleshooting.
- **Notificações** quando um chamado for aberto.

---

## 5. Análise de requisitos

### 5.1 Objetivo do sistema

Garantir a eficiência dos técnicos de informática ao atender chamados feitos por funcionários de outras áreas, e entregar à empresa métricas de quantidade e tempo.

### 5.2 Requisitos funcionais

- Cadastro de empresas
- Cadastro de entidades: setor e equipe
- Cadastro de funcionários da empresa: técnico e padrão
- Gerenciamento de chamados: criação e atendimento
- Entrega de métricas para a empresa
- Dois sistemas interligados: um só para a empresa e outro com duas opções de login (funcionário e técnico)

### 5.3 Requisitos não funcionais

- **Desempenho:** as operações devem ser rápidas
- **Usabilidade:** interface simples e intuitiva (UX/UI)

### 5.4 Fora do escopo (NÃO implementar)

- Controle de estoque de peças de manutenção
- Controle de custos (por hora)
- Gestão de custos dos funcionários
- **Autocadastro de funcionário**: o funcionário não se cadastra. Quem cadastra é a empresa.

---

## 6. Equipe

| Papel | Integrante(s) |
|---|---|
| Gestor de projetos | Vitor Malevichi |
| Líder técnico | Gabriel dos Santos Pedro |
| Desenvolvedores | Felipe Della Nina Rocha, Raphael Pietro dos Reis Tomaz |
| Qualidade e documentação | José Matheus Bernabe Dantas |
| Produto e comercial | Daniel Henrique Souza Castro, Kaique Vinicius Rinaldi de Oliveira |
| DBA | Vitor Malevichi |

## 7. Declaração de uso de IA

1. Apoio na prototipagem de interfaces
2. Estruturação e organização documental
3. Análise e síntese de requisitos
4. Suporte criativo e comunicacional

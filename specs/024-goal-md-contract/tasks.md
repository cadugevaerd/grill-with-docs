---

description: "Task list for Contrato do goal.md"
---

# Tasks: Contrato do goal.md

**Input**: Design documents from `/specs/024-goal-md-contract/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Nenhuma task de teste automatizado. O validador do contrato é entrega da FASE-003 (ADR-0008); nesta fase o gate é a suíte canônica existente não regredir, coberto por T024.

**Organization**: Tasks agrupadas por user story. Todas escrevem no **mesmo arquivo** — ver aviso de paralelismo abaixo.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependências)
- **[Story]**: A qual user story a task pertence (US1, US2, US3, US4)
- Caminhos de arquivo exatos em cada descrição

## Path Conventions

Entrega única desta fase:

```text
plugin/skills/grill-with-docs/assets/GOAL.template.md
```

Nenhum outro caminho de produto é tocado. `ensure_workflow.py`, `grill_workspace.py` e `tests/` permanecem intactos (plan.md §Structure Decision).

## 🚫 Bloqueio de merge

Esta fase cria arquivo no diretório do plugin e **não** faz o bump SemVer. A
cláusula constitucional **Bump obrigatório do plugin** exige que toda alteração
no diretório do plugin incremente a versão SemVer antes de merge ou push.

Consequência operacional, não sugestão: **nenhum merge ou push pode carregar esta
fase sozinha**. Ela viaja junto com a FASE-003, que faz o bump sincronizado nos
oito lugares travados por `tests/validate_distribution.py`. T031 é a guarda que
verifica isso antes do fechamento.

O bump não foi movido para cá porque é ato único por release: fazê-lo uma vez por
fase publicaria três versões para uma mudança só.

## ⚠️ Execução: um nó, um worker

A Fase 1 (T001–T003) foi executada em duas frentes paralelas e integrada
(`WAVE-CONVERGED`). O restante **não é paralelizável**, e o motivo é estrutural,
não de conveniência: as 28 tarefas restantes escrevem todas o mesmo
`GOAL.template.md`, em sequência, cada uma dependendo do texto que a anterior
deixou.

O modelo de execução pressupõe nós disjuntos em arquivo. Um worktree de worker
nasce do `base_commit` fixado na criação da run, não do estado convergido da
wave anterior — então dois nós que escrevem o mesmo arquivo em fases diferentes
não veem o trabalho um do outro, e o merge cai em conflito fabricado pela base,
não por trabalho concorrente real. `PARTITION-DEGRADED` na primeira emissão já
dizia isso; a degradação era o diagnóstico, não um detalhe cosmético.

Por isso a estrutura abaixo tem **duas fases**: a Fase 1, já entregue em
paralelo, e uma fase única de redação com um nó só. O DAG passa a declarar a
verdade sobre este trabalho em vez de prometer largura que não existe.

---

## Phase 1: Setup

**Purpose**: Criar o arquivo e sua identidade versionada

- [X] T001 (serve FR-006, SC-006) Levantar, a partir de `.specify/memory/constitution.md`, `WORKFLOW.md` e dos códigos de recusa em `plugin/skills/grill-with-docs/scripts/`, a fonte exata de cada ponto de interação listado em `specs/024-goal-md-contract/data-model.md`, e registrar o par ponto→fonte em `specs/024-goal-md-contract/contracts/interaction-points.md`
- [X] T002 [P] Criar `plugin/skills/grill-with-docs/assets/GOAL.template.md` com o marcador `<!-- grill-with-docs-goal:v1 -->` na primeira linha, o título de nível 1 e os cabeçalhos de seção vazios, na ordem definida em `specs/024-goal-md-contract/data-model.md` §Documento
- [X] T003 [P] Definir a tupla de substrings essenciais do documento e registrá-la em `specs/024-goal-md-contract/contracts/essential-substrings.md`, como literal congelado, sem derivar de nenhuma tupla de `WORKFLOW.md` (ADR-0003)

**Checkpoint**: arquivo existe, com identidade e esqueleto; fontes levantadas

---

## Phase 2: Redação do documento (nó único)

**Purpose**: Escrever `plugin/skills/grill-with-docs/assets/GOAL.template.md` por
inteiro, partindo do esqueleto que a Fase 1 deixou.

**Independent Test**: o documento entregue conduz as duas trilhas, para em cada
ponto enumerado e sob a cláusula residual, e satisfaz os 31 requisitos
funcionais.

**Ordem interna obrigatória** — o texto de cada bloco depende do anterior:
contrato de parada e templates primeiro (nada pode citá-los antes de existirem),
depois as duas trilhas, depois a cláusula residual, depois a delegação, e o
fechamento por último.

- [X] T004 Escrever a seção de contrato de parada em `plugin/skills/grill-with-docs/assets/GOAL.template.md`, fixando forma `GOAL-HOLD: <motivo>`, posição de última linha isolada e motivo em uma frase, conforme `specs/024-goal-md-contract/contracts/stop-signal.md`, incluindo a regra de que a resposta termina na sinalização e texto posterior que anuncie continuação viola o contrato (FR-004, FR-030)
- [X] T005 Acrescentar à mesma seção a exigência de que a sinalização cite o identificador estável do ponto que a causou, e definir o esquema de identificadores — código de recusa do núcleo quando existir, `HOLD-<TRILHA>-<NN>` quando não — em `plugin/skills/grill-with-docs/assets/GOAL.template.md` (FR-018, FR-019, SC-008)
- [X] T006 Escrever o Template A (trilha pré-ciclo) em `plugin/skills/grill-with-docs/assets/GOAL.template.md`, literal, incluindo a frase de alternativa de parada, a instrução de orçamento de no máximo cinco turnos com três recomendado, e a origem de cada valor que o operador preenche (FR-002, FR-005, FR-025)
- [X] T007 Escrever o Template B (trilha ciclo v4) em `plugin/skills/grill-with-docs/assets/GOAL.template.md`, literal, com a mesma frase de alternativa de parada, a origem de cada valor preenchido e o teto de quarenta turnos próprio desta trilha (FR-002, FR-025, FR-026)
- [X] T008 Escrever, na seção dos templates, a declaração de que eles são normativos e de que sem eles nada garante a parada, em `plugin/skills/grill-with-docs/assets/GOAL.template.md` (FR-003)
- [X] T009 Escrever a seção de registro de avanço em `plugin/skills/grill-with-docs/assets/GOAL.template.md`, instruindo o laço a deixar o avanço gravado no projeto antes de encerrar cada turno, para que o esgotamento de orçamento não perca trabalho (FR-020, SC-009)
- [X] T010 Escrever a seção da trilha pré-ciclo em `plugin/skills/grill-with-docs/assets/GOAL.template.md`, declarando início, etapas na ordem (`init`, `preflight`, `triage`, gate constitucional, entrevista, `audit`), critério de conclusão, a ordem fixa das duas trilhas e o comportamento quando governança ou contrato de fluxo não estão materializados no destino (FR-001, FR-024, FR-031)
- [X] T011 Escrever a tabela de pontos de interação da trilha pré-ciclo em `plugin/skills/grill-with-docs/assets/GOAL.template.md`, com identificador e fonte por linha, usando o levantamento de `specs/024-goal-md-contract/contracts/interaction-points.md` (FR-006)
- [X] T012 Marcar `PLAN_ONLY_STOP` como parada obrigatória e não configurável na tabela e no texto corrente de `plugin/skills/grill-with-docs/assets/GOAL.template.md`, citando a cláusula constitucional que a sustenta (FR-008)
- [X] T013 Escrever, na seção da trilha pré-ciclo de `plugin/skills/grill-with-docs/assets/GOAL.template.md`, as instruções de retomada: como distinguir decisão já selada de decisão nova, como o laço determina em qual trilha está a partir do estado gravado, e por quais verbos — com os argumentos obrigatórios de cada um — ele descobre onde está (FR-016, FR-024)
- [X] T014 Escrever a seção da trilha ciclo v4 em `plugin/skills/grill-with-docs/assets/GOAL.template.md`, listando as onze etapas na ordem canônica e o critério de conclusão (FR-001)
- [X] T015 Escrever a tabela de pontos de interação da trilha ciclo v4 em `plugin/skills/grill-with-docs/assets/GOAL.template.md`, com identificador e fonte por linha, incluindo os retornos *when blocked* de cada etapa (FR-006)
- [X] T016 Marcar `ship` como parada obrigatória e não configurável em `plugin/skills/grill-with-docs/assets/GOAL.template.md`, citando o trecho do `WORKFLOW.md` que reserva a autorização humana para permitir a invocação (FR-008)
- [X] T017 Escrever, em `plugin/skills/grill-with-docs/assets/GOAL.template.md`, a proibição de reproduzir o resultado de uma etapa por meio próprio e a consequência de fazê-lo (FR-017)
- [X] T018 Escrever a cláusula residual em `plugin/skills/grill-with-docs/assets/GOAL.template.md`, definindo a condição de avanço (próxima ação determinística **e** reversível) com critério aplicável, os gatilhos de parada, e a enumeração do que **não** é ponto de interação, para que a residual não seja lida como "pare sempre que houver dúvida" (FR-007, FR-027)
- [X] T019 Escrever, em `plugin/skills/grill-with-docs/assets/GOAL.template.md`, a distinção explícita entre a cláusula residual e o caminho degradado, para que a ausência do coordenador não seja lida como caso de parada (FR-015, resolve CHK050)
- [X] T020 Escrever a seção de delegação em `plugin/skills/grill-with-docs/assets/GOAL.template.md`, estabelecendo a sessão principal como leader e única Evidence Boundary, e a delegação como interna à etapa, válida em qualquer etapa, com o critério aplicável de decomponibilidade por subdomínio — partição de arquivos disjunta que não escreve evidência de coordenação (FR-010, FR-028)
- [X] T021 Escrever as proibições do worker em `plugin/skills/grill-with-docs/assets/GOAL.template.md`: não declara resultado de etapa, não escreve evidência de coordenação — enumerada de forma fechada por caminho —, não é despachado para ser a etapa (FR-011, FR-029)
- [X] T022 Escrever as regras de tier em `plugin/skills/grill-with-docs/assets/GOAL.template.md`: `--model` sempre, `--effort` quando suportado, conferência do efetivo contra o solicitado com bloqueio na divergência, proibição de reusar terminal, e a exceção em que o modelo é derivado de binding versionado (FR-012, FR-013)
- [X] T023 Escrever o critério determinístico de disponibilidade do coordenador, decidido por saída de comando e nunca por texto livre, e o caminho degradado em `plugin/skills/grill-with-docs/assets/GOAL.template.md`, incluindo o comportamento quando ele fica indisponível no meio de uma etapa já distribuída e a resolução de resultados conflitantes entre workers (FR-014, FR-015, FR-021, FR-022, FR-029)
- [X] T024 Executar a suíte canônica `tests/run_validators.py` e confirmar exit `0` com a baseline corrente de CLAUDE.md, sem regressão
- [X] T025 Percorrer os 31 requisitos funcionais de `specs/024-goal-md-contract/spec.md` e confirmar que cada um tem trecho correspondente em `plugin/skills/grill-with-docs/assets/GOAL.template.md`, sem FR órfão (resolve CHK031)
- [X] T026 Varrer `plugin/skills/grill-with-docs/assets/GOAL.template.md` em busca de dependência de recurso exclusivo de runtime — orçamento próprio, transição de status persistida, armazenamento local — e remover o que houver, preservando apenas a instrução ao operador para declarar o seu (FR-009)
- [X] T027 Conferir que a frase de alternativa de parada aparece literalmente idêntica nos dois templates de `plugin/skills/grill-with-docs/assets/GOAL.template.md` e em `specs/024-goal-md-contract/contracts/goal-objective-templates.md` (resolve CHK020)
- [X] T028 Conferir que a tupla de substrings essenciais registrada em `specs/024-goal-md-contract/contracts/essential-substrings.md` casa byte a byte com o conteúdo de `plugin/skills/grill-with-docs/assets/GOAL.template.md`
- [X] T029 Conferir que `plugin/skills/grill-with-docs/assets/GOAL.template.md` não excede 400 linhas e que a decisão de parar pode ser tomada lendo apenas ele, sem abrir outro arquivo (FR-023, SC-010)
- [X] T030 (gate de aceitação) Percorrer os itens abertos de `specs/024-goal-md-contract/checklists/contract.md` e marcar os que o documento entregue resolve, registrando em nota os que permanecem abertos e por quê
- [X] T031 Registrar em `specs/024-goal-md-contract/tasks.md`, na nota de fechamento, que esta fase alterou o diretório do plugin sem bump e que nenhum merge ou push pode carregá-la sozinha; confirmar que a versão declarada em `plugin/.claude-plugin/plugin.json` permanece a publicada e que o bump está pendente na FASE-003 (cláusula **Bump obrigatório do plugin**)

**Checkpoint**: documento completo, suíte verde, checklist percorrido

## Dependencies

```text
Phase 1 (T001–T003) — ENTREGUE, wave-0001 convergida
        │
        ▼
Phase 2 (T004–T031) — nó único, um worker, ordem interna sequencial
```

Dentro da Fase 2 a ordem é a listada: T004–T009 estabelecem parada e templates,
T010–T017 escrevem as duas trilhas, T018–T019 a cláusula residual, T020–T023 a
delegação, T024–T031 o fechamento.

## Parallel Execution

Nenhuma. Todas as tarefas restantes escrevem o mesmo arquivo. Declarar largura
maior que um seria promessa vazia — ver **Execução: um nó, um worker**.

## Implementation Strategy

Fase única. O documento não tem entrega parcial útil: um `goal.md` com trilhas
mas sem contrato de parada conduziria um laço que não sabe parar, que é pior
que documento nenhum.

---

## Phase 3: Convergence

**Purpose**: Fechar as lacunas que a avaliação de `converge` encontrou entre o
documento entregue e o que spec, plano e contratos exigem. Nenhuma é código
ausente: todas são âncoras que a tupla congelada deixou de fixar, e sem elas o
validador da FASE-003 aprovaria um documento mutilado.

- [X] T032 Acrescentar `## Trilha ciclo v4` à tupla de `specs/024-goal-md-contract/contracts/essential-substrings.md` per FR-023 (partial) — a seção existe no documento e não está fixada; a âncora foi perdida numa tentativa de alinhamento da tupla, não pelo redator
- [X] T033 Acrescentar `## Contrato de parada` à tupla de `specs/024-goal-md-contract/contracts/essential-substrings.md` per FR-004, FR-030 (partial) — a seção que define a parada é o núcleo do documento e hoje não tem âncora estrutural
- [X] T034 Substituir, na tupla de `specs/024-goal-md-contract/contracts/essential-substrings.md`, a âncora `cláusula residual` pelo heading `## Cláusula residual` per FR-007 (partial) — a forma minúscula casa em prosa corrente e não garante que a seção exista
- [X] T035 Acrescentar à tupla de `specs/024-goal-md-contract/contracts/essential-substrings.md` os identificadores obrigatórios e um por classe de fonte das duas tabelas de pontos per FR-006, FR-019 (partial) — hoje só `PLAN_ONLY_STOP` e `HOLD-V4-01` estão fixados, e os outros dezesseis podem sumir sem reprovar
- [X] T036 Justificar em `specs/024-goal-md-contract/plan.md` §Complexity Tracking a alteração de `tests/validate_work_item_v3_contract.py`, ou mover a mudança para a fase que cobre `tests/` per plan: Structure Decision (unrequested) — o plano declara `tests/` intacto nesta fase, e a alteração foi correção de regressão real do bundle migrado para v3
- [X] T037 Reconferir, após T032–T035, que cada substring da tupla aparece literalmente em `plugin/skills/grill-with-docs/assets/GOAL.template.md` e que o arquivo continua dentro de 400 linhas per FR-023, SC-010 (partial)


# Feature Specification: Falso positivo de timeout no status do workspace

**Feature Branch**: `025-status-timeout-false-positive`

**Created**: 2026-08-26

**Status**: Draft

**Input**: User description: "Fonte exclusiva de WHAT/WHY: .grill/work-items/fix-status-timeout-false-positive-79cd99681a234f65a93a092b678e39b3/handoffs/FASE-001-SPECIFY-HANDOFF.md — o comando público status (JSON e Markdown) deixa de bloquear com STATUS-TIMEOUT num workspace real com múltiplos work items/worktrees, mesmo quando a projeção leva mais de 5 segundos, porque o custo por worktree deixa de crescer com o número de work items e o timeout público passa a ter margem sobre o pior caso real."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Diagnóstico completo em workspace real acumulado (Priority: P1)

Qualquer sessão ou automação que invoque o comando público de status num workspace real, com vários work items e vários worktrees acumulados, precisa receber o resultado do diagnóstico sem bloqueio por timeout falso.

**Why this priority**: é o cenário para o qual o comando existe — diagnosticar o workspace exatamente quando ele está mais carregado. Um falso bloqueio aqui torna o próprio comando de diagnóstico inutilizável na hora em que é mais necessário.

**Independent Test**: rodar o comando de status (formato JSON e formato Markdown) num workspace com múltiplos work items espalhados por múltiplos worktrees reais e confirmar que o resultado retorna dentro do timeout público, sem o código `STATUS-TIMEOUT`.

**Acceptance Scenarios**:

1. **Given** um workspace com múltiplos work items em múltiplos worktrees reais (cenário de pior caso medido), **When** o status é executado em formato JSON, **Then** o resultado retorna sem `STATUS-TIMEOUT`, dentro do timeout público configurado.
2. **Given** o mesmo workspace, **When** o status é executado em formato Markdown, **Then** o resultado retorna sem `STATUS-TIMEOUT`, dentro do timeout público configurado.

---

### User Story 2 - Custo não cresce com número de work items no mesmo worktree (Priority: P2)

Uma sessão que roda o status num workspace com vários work items concentrados no mesmo worktree precisa de um custo de diagnóstico que não escale por item.

**Why this priority**: sem essa garantia, workspaces que acumulam work items no mesmo worktree reintroduzem o mesmo falso positivo por outro caminho.

**Independent Test**: rodar o status num workspace com um único worktree contendo múltiplos work items e confirmar que o tempo de execução não cresce proporcionalmente à quantidade de work items.

**Acceptance Scenarios**:

1. **Given** um worktree único com N work items, **When** o status é executado, **Then** o custo de execução é equivalente ao custo de um worktree com um único work item (custo por worktree/repositório, não por item).

---

### User Story 3 - Regressão de custo por item fica travada por teste dedicado (Priority: P3)

Quem mantém o projeto precisa que uma futura mudança não reintroduza custo Git proporcional ao número de work items sem que a suíte de testes acuse a regressão.

**Why this priority**: a correção do falso positivo só é confiável no tempo se uma regressão futura for pega automaticamente, antes de voltar a bloquear workspaces reais.

**Independent Test**: rodar a suíte de testes de status e confirmar que existe um teste que falha caso o custo volte a crescer por work item em vez de por worktree.

**Acceptance Scenarios**:

1. **Given** a suíte de testes de status, **When** o custo de execução é medido por item versus por worktree, **Then** um teste dedicado reprova qualquer regressão que reintroduza custo proporcional ao número de work items.

---

### Edge Cases

- Workspace com um único work item: deve permanecer rápido e sem timeout (caso trivial, usado como baseline).
- Workspace no pior caso já medido (projeção real de 10,56s): deve completar dentro do timeout público, com margem.
- O timeout público não pode ser reduzido abaixo do pior caso medido, sob risco de reintroduzir o mesmo falso positivo por um caminho diferente (timeout insuficiente em vez de custo por item).
- O timeout público também não pode subir sem limite: 30s é o teto deliberado que dá margem sobre o pior caso medido (10,56s) sem mascarar por tempo excessivo um travamento real antes de reportar `STATUS-TIMEOUT` (rationale registrada em `research.md` Decisão 2).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O comando público de status (formato JSON e formato Markdown) MUST completar sem retornar `STATUS-TIMEOUT` num workspace real com múltiplos work items e múltiplos worktrees, mesmo quando a projeção leva mais de 5 segundos.
- **FR-002**: O custo de execução do status MUST NOT crescer proporcionalmente ao número de work items no workspace; o custo Git relevante é por worktree/repositório.
- **FR-003**: O timeout público do status MUST ser fixado em 30 segundos (`STATUS_TIMEOUT_SECONDS = 30`, ver `research.md`, Decisão 2 — as decisões numeradas vivem em `research.md`, não em `plan.md`): esse valor mantém margem sobre o pior caso real medido (projeção de 10,56s), sem cair abaixo desse valor, e é também o teto escolhido para não mascarar um travamento real por tempo excessivo.
- **FR-004**: A suíte de testes MUST incluir um teste de regressão dedicado que trava o escopo do custo por worktree e reprova a reintrodução de custo por work item.
- **FR-005**: O contrato público `grill-status/v1` (schema e formato de saída) MUST permanecer inalterado por esta correção. A preservação MUST ser comprovada explicitamente, não inferida da ausência de diff: `contracts/grill-status-v1.md` enumera o schema e os códigos preservados (`STATUS-TIMEOUT`, `STATUS-INVALID-OUTPUT`, `STATUS-SCHEMA`, `WORK-ITEM-MISSING`), e os casos de contrato de `tests/validate_status_contract.py` os verificam na execução mapeada em `tasks.md` T004.
- **FR-006**: A versão do plugin MUST receber o bump SemVer obrigatório, e os oito locais de distribuição do plugin MUST permanecer coerentes entre si após a correção.
- **FR-007**: O `CHANGELOG.md` MUST receber uma entrada nova para a versão bumpada, descrevendo a correção do falso positivo de timeout. A presença dessa entrada MUST ser travada por gate automatizado, e não apenas por conferência humana: `tests/validate_distribution.py` MUST exigir exatamente uma linha `## {VERSION}` em `CHANGELOG.md`, casando a própria constante `VERSION` do validador.
- **FR-008**: Os dois gates de distribuição — `bump-gate.yml` (`tests/check_version_bump.py`) e `ci.yml` (`tests/run_validators.py` na matriz) — MUST reportar verde para o **mesmo** SHA de topo antes do ship. Falha, ausência de veredito ou divergência entre os dois bloqueia o ship, sem waiver; qualquer alteração posterior invalida a aprovação anterior de ambos e exige reavaliação conjunta sobre o novo SHA. Nesta feature, o veredito `NO-PLUGIN-CHANGE` do gate de bump MUST ser tratado como falha, e não como aprovação: a feature altera `plugin/**` por definição, então esse código só aparece quando a mudança ainda não está commitada no SHA avaliado.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% das execuções de status testadas em workspace real (múltiplos work items, múltiplos worktrees) completam sem falso bloqueio por timeout.
- **SC-002**: O tempo de execução do status num worktree com múltiplos work items é equivalente ao de um worktree com um único work item (sem crescimento proporcional ao número de itens).
- **SC-003**: 100% dos testes automatizados de regressão do workspace passam após a correção, incluindo o teste dedicado que trava o escopo por worktree.
- **SC-004**: A versão do plugin e os oito locais de distribuição ficam coerentes entre si após o bump obrigatório.
- **SC-005**: O `CHANGELOG.md` contém uma entrada `## 5.2.1` antes do ship, e `tests/validate_distribution.py` reprova (exit ≠ 0) a ausência dessa entrada — o critério é verificado por execução do validador, não por leitura manual.
- **SC-006**: Antes do ship, `bump-gate.yml` e `ci.yml` estão ambos verdes sobre o mesmo SHA de topo, com o gate de bump reportando literalmente o código `BUMPED`: 0 execuções aceitas com `NO-PLUGIN-CHANGE`, `MISSING-BUMP`, `VERSION-REGRESSION` ou `VERSION-UNREADABLE`.

## Assumptions

- O workspace real descrito no laudo de evidência (múltiplos work items acumulados em múltiplos worktrees) representa o pior caso a cobrir por esta correção.
- Esta correção não altera o schema, o formato ou os códigos do contrato `grill-status/v1`; qualquer necessidade nesse sentido fica fora de escopo.
- Otimizações de performance além das necessárias para eliminar o falso positivo ficam fora de escopo desta correção.

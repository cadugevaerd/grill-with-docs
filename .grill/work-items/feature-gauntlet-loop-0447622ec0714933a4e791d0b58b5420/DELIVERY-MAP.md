# DELIVERY-MAP

decomposition-schema: v1

## MOD-001 — Ativação e política do Gauntlet
- module-kind: platform
- responsibility: Tornar a execução autônoma opt-in e configurável sem degradar o workflow existente
- boundary: Interface de comando, configuração do projeto, registro de skills e guardas de runtime
- depends-on: none

### DU-001 — Contrato de ativação
- development-type: platform-devops
- phase: FASE-001
- scope-in: Configuração explícita, validação V3/Claude, política de tiers e limite de cinco workers
- scope-out: Dispatch de subagentes e persistência de runs
- depends-on: none
- acceptance: Só um work item V3 com adapter Claude verificado pode iniciar uma run, e V2 permanece manual

## MOD-002 — Controle durável de runs
- module-kind: platform
- responsibility: Manter estado, evidência e isolamento de workers íntegros entre interrupções
- boundary: Project Store, journal, leases, receipts e Git worktrees filhos
- depends-on: MOD-001

### DU-002 — Estado e Evidence Boundary
- development-type: platform-devops
- phase: FASE-002
- scope-in: Estado por run, eventos encadeados, lease, receipt do coordenador, worktrees filhos e cleanup seguro
- scope-out: Seleção de modelo e scheduler de waves
- depends-on: DU-001
- acceptance: Worker não altera Store ou receipts, e uma run pode ser retomada ou bloqueada com diagnóstico verificável

## MOD-003 — Execução cooperativa no Claude Code
- module-kind: cross-cutting
- responsibility: Despachar Canonical Skills por subagentes isolados e avançar somente dependências prontas
- boundary: Adapter Claude Code, Execution DAG, processo de worker e monitoramento de progresso
- depends-on: MOD-001, MOD-002

### DU-003 — Scheduler de waves
- development-type: platform-devops
- phase: FASE-003
- scope-in: Adaptação de tiers, validação do DAG, waves paralelas, stream de progresso, retry transitório e Stall Recovery
- scope-out: Runtime não verificado, resolução de conflito e revisão final
- depends-on: DU-001, DU-002
- acceptance: No máximo cinco nós independentes executam em paralelo, cada um no próprio worktree e com Capability Grant mínimo

## MOD-004 — Fechamento fail-closed
- module-kind: cross-cutting
- responsibility: Integrar resultados aceitos e impedir ship sem evidência e revisão independentes
- boundary: Converge, verify, review, status de execução, distribuição e gates de entrega
- depends-on: MOD-003

### DU-004 — Convergência e revisão
- development-type: platform-devops
- phase: FASE-004
- scope-in: Integração limpa serial, bloqueio de conflito, review grande somente leitura, gate humano e cobertura de contratos
- scope-out: Auto-merge conflitante, auto-reparo pós-review e publicação direta
- depends-on: DU-003
- acceptance: Só mudanças convergidas, verificadas e revisadas chegam a `AWAITING_HUMAN`; a distribuição declara 2.6.0

> IDs are stable within this work item. `module-kind` is one of `domain|platform|cross-cutting`; each DU has exactly one closed development type.

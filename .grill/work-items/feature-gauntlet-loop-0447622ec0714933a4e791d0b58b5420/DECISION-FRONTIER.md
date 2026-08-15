# DECISION FRONTIER

## DQ-0001 — Quais work items e runtimes podem iniciar o Loop?
- phase: FASE-001
- fingerprint: ativacao-v3-claude-sem-fallback
- impact: high
- state: resolved
- context-refs: Gauntlet-Enabled Work Item, Canonical Skill, Gauntlet Configuration
- artifacts: ADR-0004, ADR-0007, ROADMAP#FASE-001
- depends-on: none
- final-ref: ADR-0007

## DQ-0002 — Como o Loop distribui capacidade sem amarrar a política a fornecedor?
- phase: FASE-001
- fingerprint: politica-tier-abstrata-por-etapa
- impact: high
- state: resolved
- context-refs: Model Tier, Canonical Skill
- artifacts: ADR-0001, ROADMAP#FASE-001
- depends-on: DQ-0001
- final-ref: ADR-0001

## DQ-0003 — Como a execução paralela evita corrida de escrita e receipt autoafirmado?
- phase: FASE-002
- fingerprint: isolamento-worktree-e-evidence-boundary
- impact: high
- state: resolved
- context-refs: Worker Worktree, Evidence Boundary, Capability Grant
- artifacts: ADR-0003, ADR-0006, ADR-0010
- depends-on: DQ-0001
- final-ref: ADR-0010

## DQ-0004 — De onde vem a ordem e a paralelização da execução?
- phase: FASE-003
- fingerprint: dag-explicito-e-workflow-canonico
- impact: high
- state: resolved
- context-refs: Execution DAG, Canonical Skill
- artifacts: ADR-0004, ROADMAP#FASE-003
- depends-on: DQ-0001, DQ-0003
- final-ref: ADR-0004

## DQ-0005 — Como a run lida com stall, reinício e nova tentativa?
- phase: FASE-003
- fingerprint: stall-automatico-uma-vez-retry-transitorio
- impact: high
- state: resolved
- context-refs: Stall Recovery, Evidence Boundary
- artifacts: ADR-0005, ROADMAP#FASE-003
- depends-on: DQ-0003
- final-ref: ADR-0005

## DQ-0006 — Que resultado pode chegar ao gate humano de ship?
- phase: FASE-004
- fingerprint: converge-fail-closed-e-review-independente
- impact: high
- state: resolved
- context-refs: Integration Conflict, Independent Review, Review Block
- artifacts: ADR-0002, ADR-0008, ADR-0009, ADR-0011
- depends-on: DQ-0003, DQ-0004
- final-ref: ADR-0008

## DQ-0007 — O cap de workers da ativação é concorrente ou cumulativo por run?
- phase: FASE-003
- fingerprint: cap-worker-concorrente-nao-cumulativo
- impact: high
- state: resolved
- context-refs: Execution Wave, Worker Worktree
- artifacts: ADR-0012, ROADMAP#FASE-003
- depends-on: DQ-0003
- final-ref: ADR-0012

## DQ-0008 — Como o Store representa mais de uma wave por run?
- phase: FASE-003
- fingerprint: wave-lifecycle-append-only-store-extension
- impact: high
- state: resolved
- context-refs: Execution Wave, Execution DAG
- artifacts: ADR-0013, ROADMAP#FASE-003
- depends-on: DQ-0004, DQ-0007
- final-ref: ADR-0013

## DQ-0009 — A FASE-003 gera o Execution DAG ou só consome o que a macroetapa tasks produz?
- phase: FASE-003
- fingerprint: dag-e-output-de-tasks-nao-gerador-dedicado
- impact: high
- state: resolved
- context-refs: Execution DAG, Canonical Skill
- artifacts: ADR-0014, ROADMAP#FASE-003
- depends-on: DQ-0004
- final-ref: ADR-0014

> Estados: open | resolved | deferred | split | blocked | out-of-scope. Não duplique fingerprints abertos.

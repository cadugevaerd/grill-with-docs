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

## DQ-0010 — Orçamento de recovery automático (stall) usa qual contador: run ou lease?
- phase: FASE-003
- fingerprint: recovery-budget-lease-nao-run
- impact: high
- state: resolved
- context-refs: Stall Recovery, Resumable Run
- artifacts: ADR-0015, ROADMAP#FASE-003, precode-foundation.json#MOD-004
- depends-on: DQ-0005
- final-ref: ADR-0015

## DQ-0011 — Quem atesta o checkpoint de um líder de macroetapa despachado por subagente?
- phase: FASE-003
- fingerprint: checkpoint-attestation-reuso-verificador-existente
- impact: high
- state: resolved
- context-refs: Independent Review, Canonical Skill
- artifacts: ADR-0016, ROADMAP#FASE-003, precode-foundation.json#MOD-002,MOD-010
- depends-on: none
- final-ref: ADR-0016

## DQ-0012 — Autoridade de despacho real é fixa numa camada, ou delegável conforme a macroetapa?
- phase: FASE-003
- fingerprint: autoridade-despacho-core-mais-delegacao-corrente
- impact: high
- state: resolved
- context-refs: Autonomous Run, Capability Grant, Execution Wave
- artifacts: ADR-0017, ROADMAP#FASE-003, precode-foundation.json#MOD-001,MOD-003
- depends-on: DQ-0001
- final-ref: ADR-0017

## DQ-0013 — Um nó do Execution DAG pode legitimamente pertencer a outra macroetapa além de agent-execute, ou escrever no ledger de governança do grill?
- phase: FASE-003
- fingerprint: dag-node-evidencia-verify-review-ship-e-ledger-grill-rejeitado-fail-closed
- impact: high
- state: resolved
- context-refs: Execution DAG, Execution Wave
- artifacts: ADR-0018 (regra ii revisada rodada 8, ancorada em segmento .grill), ROADMAP#FASE-003, precode-foundation.json#MOD-011
- depends-on: DQ-0009
- final-ref: ADR-0018

## DQ-0014 — O orçamento de recovery automático é por lease ou por nó do Execution DAG, e quem verifica, correlacionado por quê?
- phase: FASE-003
- fingerprint: orcamento-remediacao-por-no-enforcado-por-worker-id-nao-scope
- impact: high
- state: resolved
- context-refs: Stall Recovery, Execution DAG
- artifacts: ADR-0015 (revisão rodadas 7/8/9), ROADMAP#FASE-003, precode-foundation.json#MOD-012
- depends-on: DQ-0010
- final-ref: ADR-0015

## DQ-0015 — O líder de agent-execute pode deter autoridade coordinator-only pra mintar lease/grant dos workers que despacha?
- phase: FASE-003
- fingerprint: lider-agent-execute-autoridade-delegada-escopada
- impact: high
- state: resolved
- context-refs: Evidence Boundary, Capability Grant, Autonomous Run
- artifacts: ADR-0019, ROADMAP#FASE-003
- depends-on: DQ-0011, DQ-0012
- final-ref: ADR-0019

> Estados: open | resolved | deferred | split | blocked | out-of-scope. Não duplique fingerprints abertos.

# DECISION FRONTIER

## DQ-0001 — A adoção de Workflow V3 substitui ou coexistirá com Workflow V2?
- phase: FASE-002
- fingerprint: workflow-v3-explicito-com-leitura-dupla-v2
- impact: high
- state: resolved
- context-refs: Workflow V2, Workflow V3
- artifacts: ADR-0001, ROADMAP, PLAN-CONTEXT
- depends-on: none
- final-ref: ADR-0001

## DQ-0002 — Uma etapa obrigatória pode ser executada por aproximação sem skill registrada?
- phase: FASE-001
- fingerprint: step-obrigatorio-exige-skill-canonica-pinada
- impact: high
- state: resolved
- context-refs: Managed Workflow, Canonical Skill, Skill Resolution
- artifacts: ADR-0002, ROADMAP, PLAN-CONTEXT
- depends-on: none
- final-ref: ADR-0002

## DQ-0003 — Onde vive a coordenação de work items de worktrees vinculadas?
- phase: FASE-003
- fingerprint: project-store-compartilhado-no-git-common-dir
- impact: high
- state: resolved
- context-refs: Work Item V3, Project Store
- artifacts: ADR-0003, ROADMAP, PLAN-CONTEXT
- depends-on: none
- final-ref: ADR-0003

## DQ-0004 — Quais runtimes podem executar V3 no primeiro recorte?
- phase: FASE-001
- fingerprint: somente-runtime-com-entrypoints-comprovados
- impact: high
- state: resolved
- context-refs: Canonical Skill, Skill Resolution
- artifacts: ADR-0002, ROADMAP, PLAN-CONTEXT
- depends-on: DQ-0002
- final-ref: ADR-0002

## DQ-0005 — A atestação V3 precisa resistir a executor malicioso?
- phase: FASE-004
- fingerprint: atestacao-estrutural-cooperativa-sem-proveniencia-criptografica
- impact: high
- state: resolved
- context-refs: Execution Attestation, Canonical Skill
- artifacts: ADR-0004, ROADMAP, PLAN-CONTEXT
- depends-on: DQ-0002
- final-ref: ADR-0004

> Estados: open | resolved | deferred | split | blocked | out-of-scope. Não duplique fingerprints abertos.

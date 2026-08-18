# DECISION FRONTIER

## DQ-0001 — Quem classifica um problema relatado em rota: o core ou a skill?
- phase: FASE-001
- fingerprint: skill-classifica-core-verifica
- impact: high
- state: resolved
- context-refs: Laudo de Causa Raiz, Rota
- artifacts: ADR-0001, ROADMAP, PLAN-CONTEXT
- depends-on: none
- final-ref: ADR-0001

## DQ-0002 — A decisão de rota vira artefato próprio ou fica embutida no work item?
- phase: FASE-001
- fingerprint: registro-selado-compartilhado-entre-init-e-hotfix
- impact: high
- state: resolved
- context-refs: Registro de Triagem, Selo de Triagem
- artifacts: ADR-0002, ROADMAP, PLAN-CONTEXT
- depends-on: DQ-0001
- final-ref: ADR-0002

## DQ-0003 — O que impede duas rotas de virarem questão de gosto?
- phase: FASE-001
- fingerprint: matriz-de-evidencia-exige-e-proibe-por-rota
- impact: high
- state: resolved
- context-refs: Matriz de Evidência, Rota
- artifacts: ADR-0003, ROADMAP, PLAN-CONTEXT
- depends-on: DQ-0001
- final-ref: ADR-0003

## DQ-0004 — A triagem já nasce obrigatória para `init` e `hotfix`?
- phase: FASE-001
- fingerprint: triagem-consultiva-antes-de-obrigatoria
- impact: high
- state: resolved
- context-refs: Triagem Consultiva, Trilha
- artifacts: ADR-0004, ROADMAP, PLAN-CONTEXT
- depends-on: DQ-0002, DQ-0003
- final-ref: ADR-0004

> Estados: open | resolved | deferred | split | blocked | out-of-scope. Não duplique fingerprints abertos.

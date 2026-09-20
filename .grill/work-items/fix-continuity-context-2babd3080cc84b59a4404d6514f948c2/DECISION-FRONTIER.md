# DECISION FRONTIER

## DQ-0001 — Que evidência autoriza uma sessão nova a assumir um work item cujo líder encerrou?
- phase: FASE-001
- fingerprint: context-takeover-authorization
- impact: high
- state: resolved
- context-refs: contexto de orquestração, observação de líder, dispatch terminal
- artifacts: docs/adr/ADR-0001.md, ROADMAP.md, PLAN-CONTEXT.md
- depends-on: none
- final-ref: ADR-0001

## DQ-0002 — Os campos do checkpoint de continuidade estão com nome errado ou conteúdo errado?
- phase: FASE-001
- fingerprint: continuity-checkpoint-hash-fields
- impact: medium
- state: resolved
- context-refs: checkpoint de continuidade, digest de entradas, metadata do work item
- artifacts: docs/adr/ADR-0002.md
- depends-on: DQ-0001
- final-ref: ADR-0002

## BL-0001 — Passar a comparar os digests reais de WORKFLOW.md e da Constituição na retomada
- phase: FASE-001
- state: resolved
- owner: Carlos Araújo
- resolution: adiado por decisão explícita em R-0002 — fica fora do escopo desta fase, que só renomeia campos sem mudar comportamento (ADR-0002). A comparação nova é mudança de contrato com recusa nova e exige seu próprio ciclo.
- evidence-needed: caso real em que uma emenda constitucional ou mudança de WORKFLOW entre a troca e a retomada passou despercebida
- trigger: primeira retomada em que a autoridade normativa mudou no intervalo

## DQ-0003 — Escopo da FASE-001
- phase: FASE-001
- fingerprint: continuity-phase-scope
- impact: medium
- state: resolved
- context-refs: tomada de contexto, troca preparada, preview do adopt, campos do checkpoint
- artifacts: ROADMAP.md, PLAN-CONTEXT.md, handoffs/FASE-001-SPECIFY-HANDOFF.md
- depends-on: DQ-0001, DQ-0002
- final-ref: R-0003

> Estados: open | resolved | deferred | split | blocked | out-of-scope. Não duplique fingerprints abertos.

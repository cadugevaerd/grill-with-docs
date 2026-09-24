# DECISION FRONTIER

## DQ-0001 — Como o GWD escolhe o modelo Codex mais recente?
- phase: FASE-001
- fingerprint: codex-latest-model-resolution-mechanism
- impact: high
- state: resolved
- context-refs: família de modelo, catálogo local do Codex, slug resolvido
- artifacts: docs/adr/ADR-0001.md, ROADMAP.md, PLAN-CONTEXT.md
- depends-on: none
- final-ref: ADR-0001

## DQ-0002 — Qual família atende o tier medium, sem terra na geração 6?
- phase: FASE-001
- fingerprint: codex-medium-tier-family
- impact: medium
- state: resolved
- context-refs: tier, família de modelo
- artifacts: docs/adr/ADR-0001.md, handoffs/FASE-001-SPECIFY-HANDOFF.md
- depends-on: DQ-0001
- final-ref: ADR-0001

## DQ-0003 — O que acontece quando o catálogo não resolve?
- phase: FASE-001
- fingerprint: codex-catalog-unresolved-behavior
- impact: high
- state: resolved
- context-refs: catálogo local do Codex
- artifacts: docs/adr/ADR-0001.md, handoffs/FASE-001-SPECIFY-HANDOFF.md
- depends-on: DQ-0001
- final-ref: ADR-0001

## DQ-0004 — Autor/revisor Codex entram no escopo?
- phase: FASE-001
- fingerprint: codex-specialist-role-scope
- impact: medium
- state: resolved
- context-refs: papel de especialista, família de modelo
- artifacts: docs/adr/ADR-0001.md, ROADMAP.md, PLAN-CONTEXT.md
- depends-on: DQ-0001
- final-ref: ADR-0001

## DQ-0005 — Qual modelo Claude atende autor/revisor especialista?
- phase: FASE-001
- fingerprint: claude-specialist-pair-model
- impact: high
- state: resolved
- context-refs: papel de especialista, alias de modelo Claude
- artifacts: docs/adr/ADR-0002.md, docs/adr/ADR-0001.md, ROADMAP.md, PLAN-CONTEXT.md, handoffs/FASE-001-SPECIFY-HANDOFF.md, DELIVERY-MAP.md, CONTEXT.md
- depends-on: none
- final-ref: ADR-0002

> Estados: open | resolved | deferred | split | blocked | out-of-scope. Não duplique fingerprints abertos.

# DECISION FRONTIER

## DQ-0001 — O que `state.workflow.version` deve registrar, e como o auditor valida?
- phase: FASE-001
- fingerprint: state-workflow-version-semantica-e-validacao
- impact: high
- state: resolved
- context-refs: campo derivado, campo constante, par writer/reader, marcador de workflow
- artifacts: docs/adr/ADR-0001.md, ROADMAP.md, PLAN-CONTEXT.md
- depends-on: none
- final-ref: docs/adr/ADR-0001.md

## DQ-0002 — `development.workflow_version` entra no mesmo conserto?
- phase: FASE-001
- fingerprint: development-workflow-version-derivado-ou-constante
- impact: high
- state: resolved
- context-refs: campo derivado, campo constante, versão ativa do plugin, marcador de workflow
- artifacts: docs/adr/ADR-0001.md, ROADMAP.md, PLAN-CONTEXT.md
- depends-on: DQ-0001
- final-ref: docs/adr/ADR-0001.md

## DQ-0003 — O que o writer carimba sem exatamente um marcador?
- phase: FASE-001
- fingerprint: writer-marcador-ausente-ou-duplicado
- impact: high
- state: resolved
- context-refs: detector estrito, marcador de workflow, campo derivado
- artifacts: docs/adr/ADR-0002.md, ROADMAP.md, PLAN-CONTEXT.md
- depends-on: DQ-0002
- final-ref: docs/adr/ADR-0002.md

## DQ-0004 — Onde mora o detector estrito?
- phase: FASE-001
- fingerprint: detector-estrito-localizacao-ssot
- impact: medium
- state: resolved
- context-refs: detector estrito, marcador de workflow
- artifacts: docs/adr/ADR-0002.md, PLAN-CONTEXT.md
- depends-on: DQ-0003
- final-ref: docs/adr/ADR-0002.md

## DQ-0005 — O custo aceito na DQ-0001 é decisão adiada ou já tomada?
- phase: FASE-001
- fingerprint: custo-carimbo-obsoleto-bl-ou-consequencia
- impact: medium
- state: resolved
- context-refs: campo derivado, par writer/reader
- artifacts: docs/adr/ADR-0001.md, DECISION-BACKLOG.md, ROADMAP.md, handoffs/FASE-001-SPECIFY-HANDOFF.md
- depends-on: DQ-0001
- final-ref: docs/adr/ADR-0001.md

## DQ-0006 — O que resta do escopo depois da 5.0.0?
- phase: FASE-001
- fingerprint: escopo-restante-apos-renomeacao-workflow-schema
- impact: high
- state: resolved
- context-refs: campo derivado, campo constante, par writer/reader, marcador de workflow
- artifacts: docs/adr/ADR-0003.md, ROADMAP.md, PLAN-CONTEXT.md, handoffs/FASE-001-SPECIFY-HANDOFF.md
- depends-on: DQ-0001, DQ-0002
- final-ref: docs/adr/ADR-0003.md

> Estados: open | resolved | deferred | split | blocked | out-of-scope. Não duplique fingerprints abertos.

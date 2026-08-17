# DECISION FRONTIER

## DQ-0001 — A autoridade do registro de decisão pode viver fora do controle de versão?
- phase: FASE-001
- fingerprint: autoridade-vs-evidencia-commit
- impact: high
- state: resolved
- context-refs: Autoridade de estado, Evidência no commit, Projeção
- artifacts: docs/adr/ADR-0001.md, CONTEXT.md
- depends-on: none
- final-ref: ADR-0001

## DQ-0002 — O gate de auditoria deve consultar o backlog operacional?
- phase: FASE-001
- fingerprint: audit-consulta-autoridade
- impact: high
- state: resolved
- context-refs: Projeção, Autoridade de estado
- artifacts: docs/adr/ADR-0002.md
- depends-on: DQ-0001
- final-ref: ADR-0002

## DQ-0003 — Onde vive o vínculo entre referência de decisão e item de backlog?
- phase: FASE-001
- fingerprint: armazenamento-do-vinculo-bl-item
- impact: medium
- state: resolved
- context-refs: Referência de decisão, Item de backlog
- artifacts: PLAN-CONTEXT.md
- depends-on: DQ-0001
- final-ref: marcadores em description; único shape contract-legal de `item add`

## DQ-0004 — Com init fail-closed, o que acontece com --skip-backlog?
- phase: FASE-001
- fingerprint: escape-hatch-skip-backlog
- impact: medium
- state: resolved
- context-refs: Autoridade de estado
- artifacts: PLAN-CONTEXT.md
- depends-on: DQ-0001
- final-ref: mantida e carimbada no bundle; nunca reportada como OK

## DQ-0005 — Como mapear os estados do BL na FSM do backlogctl?
- phase: FASE-001
- fingerprint: mapa-estados-bl-fsm
- impact: high
- state: resolved
- context-refs: Backlog de decisão, Backlog operacional, Item de backlog
- artifacts: docs/adr/ADR-0003.md
- depends-on: DQ-0001
- final-ref: ADR-0003

## DQ-0006 — Um bundle não migrado bloqueia também os comandos read-only?
- phase: FASE-001
- fingerprint: bloqueio-bundle-nao-migrado
- impact: high
- state: resolved
- context-refs: Projeção, Evidência no commit
- artifacts: ROADMAP.md, PLAN-CONTEXT.md, handoffs/FASE-004-SPECIFY-HANDOFF.md
- depends-on: DQ-0001, DQ-0005
- final-ref: read-only reporta como finding bloqueante; mutação recusa

> Estados: open | resolved | deferred | split | blocked | out-of-scope. Não duplique fingerprints abertos.

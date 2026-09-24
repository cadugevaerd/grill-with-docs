# DECISION FRONTIER

## DQ-0001 — O que o core aceita como prova de `stop adhd mode`?
- phase: FASE-001
- fingerprint: presentation-suspension-proof-source
- impact: high
- state: resolved
- context-refs: suspensão, fonte não-agente da sessão, apresentação local
- artifacts: docs/adr/ADR-0001.md, ROADMAP.md, PLAN-CONTEXT.md
- depends-on: none
- final-ref: ADR-0001

## DQ-0002 — Como a suspensão termina na mesma sessão?
- phase: FASE-001
- fingerprint: presentation-reactivation-token
- impact: medium
- state: resolved
- context-refs: reativação, suspensão
- artifacts: docs/adr/ADR-0002.md
- depends-on: DQ-0001
- final-ref: ADR-0002

## DQ-0003 — Mudança de configuração ou de GWD durante a suspensão exige releitura?
- phase: FASE-001
- fingerprint: presentation-upgrade-while-suspended
- impact: medium
- state: resolved
- context-refs: suspensão, apresentação local
- artifacts: docs/adr/ADR-0003.md
- depends-on: DQ-0001
- final-ref: ADR-0003

> Estados: open | resolved | deferred | split | blocked | out-of-scope. Não duplique fingerprints abertos.

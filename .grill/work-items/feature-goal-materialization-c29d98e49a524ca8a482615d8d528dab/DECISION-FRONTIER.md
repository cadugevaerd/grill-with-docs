# DECISION FRONTIER

## DQ-0101 — Onde vive o código que materializa o goal.md?
- phase: FASE-001
- fingerprint: onde-vive-o-ssot-do-documento
- impact: high
- state: resolved
- context-refs: SSOT de documento, materialização
- artifacts: ADR-0101
- depends-on: none
- final-ref: ADR-0101

## DQ-0102 — O que acontece com documento humano preexistente na raiz?
- phase: FASE-001
- fingerprint: colisao-com-documento-humano
- impact: high
- state: resolved
- context-refs: no-clobber, materialização
- artifacts: ADR-0102
- depends-on: DQ-0101
- final-ref: ADR-0102

> Estados: open | resolved | deferred | split | blocked | out-of-scope. Não duplique fingerprints abertos.

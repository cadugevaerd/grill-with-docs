# DECISION FRONTIER

## DQ-0001 — Qual passa a ser a fonte de verdade para detectar extensões instaladas em `ensure_dependencies.py`?
- phase: FASE-001
- fingerprint: fonte-de-verdade-deteccao-extensoes
- impact: high
- state: resolved
- context-refs: registro de extensões, detecção de extensão, falso negativo, falso positivo
- artifacts: docs/adr/ADR-0001.md
- depends-on: none
- final-ref: ADR-0001

## DQ-0002 — O que o preflight reporta quando `.registry` está ausente ou com `schema_version` desconhecido?
- phase: FASE-001
- fingerprint: registro-ilegivel-vs-extensao-ausente
- impact: high
- state: resolved
- context-refs: registro de extensões, fail-closed, falso negativo, undetermined
- artifacts: docs/adr/ADR-0002.md
- depends-on: DQ-0001
- final-ref: ADR-0002

## DQ-0003 — Uma extensão registrada com `enabled: false` conta como presente?
- phase: FASE-001
- fingerprint: extensao-desabilitada-conta-como-presente
- impact: medium
- state: resolved
- context-refs: registro de extensões, detecção de extensão, remediação
- artifacts: docs/adr/ADR-0003.md
- depends-on: DQ-0001
- final-ref: ADR-0003

## DQ-0004 — Qual incremento SemVer o bump obrigatório exige para esta correção?
- phase: FASE-001
- fingerprint: incremento-semver-do-bump
- impact: medium
- state: resolved
- context-refs: bump obrigatório, contrato de distribuição
- artifacts: docs/adr/ADR-0004.md
- depends-on: DQ-0002
- final-ref: ADR-0004

> Estados: open | resolved | deferred | split | blocked | out-of-scope. Não duplique fingerprints abertos.
> Fronteira vazia: nenhuma DQ material aberta.

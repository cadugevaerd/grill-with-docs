# DECISION FRONTIER

## DQ-0201 — Como atestar etapa que o leader conduz sem worker?
- phase: FASE-001
- fingerprint: forma-de-atestacao-sem-worker
- impact: high
- state: resolved
- context-refs: cadeia de atestação, leader, executor da etapa, lease
- artifacts: ADR-0201
- depends-on: none
- final-ref: ADR-0201

## DQ-0202 — O que o emissor exige como âncora do receipt?
- phase: FASE-001
- fingerprint: ancora-verificavel-do-receipt
- impact: high
- state: resolved
- context-refs: emissor, evidência estrutural, artefato da etapa
- artifacts: ADR-0202
- depends-on: DQ-0201
- final-ref: ADR-0202

## DQ-0203 — Como impedir que "conduzido pelo leader" vire porta dos fundos?
- phase: FASE-001
- fingerprint: delimitacao-do-executor-leader
- impact: high
- state: resolved
- context-refs: executor da etapa, leader
- artifacts: ADR-0203
- depends-on: DQ-0201
- final-ref: ADR-0203

## DQ-0204 — Como fechar as etapas de quem entrega o próprio emissor?
- phase: FASE-001
- fingerprint: bootstrap-da-primeira-entrega
- impact: high
- state: resolved
- context-refs: cadeia de atestação, emissor, artefato da etapa
- artifacts: ADR-0204
- depends-on: DQ-0202
- final-ref: ADR-0204

> Estados: open | resolved | deferred | split | blocked | out-of-scope. Não duplique fingerprints abertos.

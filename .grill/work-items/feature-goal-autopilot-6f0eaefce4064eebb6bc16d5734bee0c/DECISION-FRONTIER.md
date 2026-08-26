# DECISION FRONTIER

## DQ-0001 — Qual runtime de goal loop o goal.md deve mirar?
- phase: FASE-001
- fingerprint: runtime-alvo-do-goal-md
- impact: high
- state: resolved
- context-refs: goal loop, runtime de goal, goal.md
- artifacts: ADR-0001
- depends-on: none
- final-ref: ADR-0001

## DQ-0002 — Qual fatia do ciclo o goal loop conduz sozinho?
- phase: FASE-001
- fingerprint: escopo-de-automacao-do-ciclo
- impact: high
- state: resolved
- context-refs: ciclo v4, GWD, goal.md, ponto de interação
- artifacts: ADR-0002
- depends-on: DQ-0001
- final-ref: ADR-0002

## DQ-0003 — goal.md é artefato distribuído do plugin ou documento local deste repositório?
- phase: FASE-001
- fingerprint: superficie-de-distribuicao-do-goal-md
- impact: high
- state: resolved
- context-refs: goal.md, GWD
- artifacts: ADR-0003
- depends-on: DQ-0002
- final-ref: ADR-0003

## DQ-0004 — Como o loop sinaliza que precisa do humano sem ser confundido com objetivo cumprido?
- phase: FASE-001
- fingerprint: contrato-de-parada-do-goal-loop
- impact: high
- state: resolved
- context-refs: ponto de interação, goal loop, goal.md
- artifacts: ADR-0004, BL-0001
- depends-on: DQ-0001, DQ-0002
- final-ref: ADR-0004

## DQ-0005 — Qual é a lista fechada de pontos de interação que emitem GOAL-HOLD?
- phase: FASE-001
- fingerprint: lista-fechada-de-pontos-de-interacao
- impact: high
- state: resolved
- context-refs: ponto de interação, ciclo v4, GWD
- artifacts: ADR-0005
- depends-on: DQ-0004
- final-ref: ADR-0005

## DQ-0006 — Como goal.md integra o /orchestration do Orca quando ele existe?
- phase: FASE-001
- fingerprint: integracao-condicional-orca-orchestration
- impact: medium
- state: split
- context-refs: goal loop, ciclo v4
- artifacts: ADR-0006
- depends-on: DQ-0005
- final-ref: ADR-0006 (paralelização); DQ-0007 (canal de pergunta)

## DQ-0007 — `orca orchestration ask` substitui GOAL-HOLD nas perguntas evitáveis?
- phase: FASE-001
- fingerprint: canal-de-pergunta-bloqueante-vs-goal-hold
- impact: high
- state: resolved
- context-refs: ponto de interação, goal loop
- artifacts: ADR-0007
- depends-on: DQ-0004, DQ-0006
- final-ref: ADR-0007

## DQ-0008 — Esta feature entrega só o asset e sua materialização, ou também superfície nova no core?
- phase: FASE-001
- fingerprint: escopo-de-entrega-asset-versus-core
- impact: high
- state: resolved
- context-refs: goal.md, GWD
- artifacts: ADR-0008, ROADMAP.md
- depends-on: DQ-0003, DQ-0005
- final-ref: ADR-0008

## DQ-0009 — Qual backstop cobre o juiz que ignora GOAL-HOLD?
- phase: FASE-001
- fingerprint: backstop-para-juiz-que-ignora-goal-hold
- impact: medium
- state: resolved
- context-refs: goal loop, ponto de interação
- artifacts: ADR-0004, BL-0001
- depends-on: DQ-0004
- final-ref: BL-0001

> Estados: open | resolved | deferred | split | blocked | out-of-scope. Não duplique fingerprints abertos.

# ROADMAP

- execution-order: FASE-001, FASE-002, FASE-003

## FASE-001 — Contrato do goal.md
- state: ready-for-specify
- objetivo: Um documento que um goal loop consegue seguir para conduzir as duas trilhas do protocolo, parando por `GOAL-HOLD` em cada ponto de interação enumerado e na cláusula residual.
- scope-in: Texto normativo do documento, os dois templates de objetivo, a lista fechada de pontos de interação por trilha, a cláusula residual, a seção de delegação Orca e a citação nominal dos verbos de orientação existentes.
- scope-out: Materialização, validador, versão, verbo novo de CLI, enforcement.
- context-refs: goal.md, goal loop, ponto de interação, ciclo v4, GWD
- ADRs: ADR-0001, ADR-0002, ADR-0004, ADR-0005, ADR-0006, ADR-0007
- BLs: BL-0001
- depends-on: none
- specify-handoff: handoffs/FASE-001-SPECIFY-HANDOFF.md
- delivery-units: DU-001

## FASE-002 — Materialização pelo init
- state: planned
- objetivo: Todo projeto que roda `init` passa a ter o `goal.md` fixado na raiz, no-clobber, com marcador versionado e hash reportado no bundle.
- scope-in: Template no diretório de assets, fixação pelo `init`, marcador e tupla `ESSENTIAL` próprios, hash em `state.json`, reporte no retorno do `init`, preservação byte-intacta de documento humano incompatível.
- scope-out: Texto normativo do documento, validador, bump de versão.
- context-refs: goal.md, GWD
- ADRs: ADR-0003
- BLs: none
- depends-on: FASE-001
- specify-handoff: handoffs/FASE-002-SPECIFY-HANDOFF.md
- delivery-units: DU-002

## FASE-003 — Validador e distribuição
- state: planned
- objetivo: O contrato do `goal.md` fica travado por teste na suíte canônica e a versão publicada do plugin reflete a mudança em todos os lugares exigidos.
- scope-in: Validador novo em `tests/`, bump SemVer sincronizado nos oito lugares, release ancorada pelo pipeline.
- scope-out: Texto normativo, materialização, verbo novo de CLI.
- context-refs: goal.md
- ADRs: ADR-0003, ADR-0008
- BLs: none
- depends-on: FASE-002
- specify-handoff: handoffs/FASE-003-SPECIFY-HANDOFF.md
- delivery-units: DU-003

> Estados: `planned | ready-for-specify | blocked | complete | superseded`. `complete` e `superseded` são terminais. `execution-order` é explícita, topológica e independente dos números de fase. Cada fase tem um handoff exclusivo; somente a primeira incompleta pode ficar `ready-for-specify`. Se todas forem terminais e não houver BL/DQ material aberto, grave `milestone_status=completed`, `state.status=complete`, `active_phase=null` e `audit_verdict=GO`; a auditoria retorna `MILESTONE-COMPLETE`.

## Delivery First
Feature/fix phases are plan-only. Hotfix-fast incidents are tracked in the work-item HOTFIX.md and reconciled after ship.

# ROADMAP

- execution-order: FASE-001

## FASE-001 — Materialização e validação do goal.md
- state: blocked
- objetivo: Todo projeto que executa `init` passa a ter o `goal.md` fixado na raiz, no-clobber, com marcador versionado e hash reportado; e o contrato desse documento fica travado por teste na suíte canônica.
- scope-in: SSOT do documento em `grill_core`, script fino de materialização, fixação pelo `init` com reporte de estado, preservação byte-intacta de documento humano incompatível, validador novo na suíte, bump SemVer sincronizado.
- scope-out: O texto normativo do `goal.md`, entregue pelo work item `feature-goal-autopilot`.
- context-refs: goal.md, materialização, marcador, tupla ESSENTIAL, SSOT de documento, no-clobber
- ADRs: ADR-0101, ADR-0102
- BLs: BL-0101
- depends-on: none
- specify-handoff: handoffs/FASE-001-SPECIFY-HANDOFF.md
- delivery-units: DU-001

> Estados: `planned | ready-for-specify | blocked | complete | superseded`. `complete` e `superseded` são terminais. `execution-order` é explícita, topológica e independente dos números de fase. Cada fase tem um handoff exclusivo; somente a primeira incompleta pode ficar `ready-for-specify`. Se todas forem terminais e não houver BL/DQ material aberto, grave `milestone_status=completed`, `state.status=complete`, `active_phase=null` e `audit_verdict=GO`; a auditoria retorna `MILESTONE-COMPLETE`.

## Origem

Este work item executa o que o `feature-goal-autopilot` declarava como FASE-002
e FASE-003. Aquelas fases estão `superseded` lá: `ship` publica, o operador
decidiu não publicar nada antes das três entregas, e com entrega única elas
deixaram de ser incrementos daquele work item. O escopo não mudou — mudou o
veículo.

As duas fases foram unidas numa só porque a separação original existia para
permitir entregas sucessivas, e não há mais entregas sucessivas: um validador
sem materialização não trava nada, e uma materialização sem validador não tem
gate.

## Delivery First
Feature/fix phases are plan-only. Hotfix-fast incidents are tracked in the work-item HOTFIX.md and reconciled after ship.

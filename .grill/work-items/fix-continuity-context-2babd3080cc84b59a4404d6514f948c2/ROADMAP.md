# ROADMAP

- execution-order: FASE-001

## FASE-001 — Continuidade de contexto sem líder vivo
- state: complete
- objetivo: uma sessão nova consegue retomar um work item cujo líder está comprovadamente terminal, e a troca ordenada é possível desde o `init`, sem afrouxar o fail-closed
- scope-in: tomada de contexto com prova do adapter; `gauntlet-prepare-switch` sem checkpoint anterior; paridade do preview do `gauntlet-orchestration-adopt` com o apply; renomeação dos campos de hash do checkpoint em schema novo
- scope-out: comparar digests reais de WORKFLOW e Constituição na retomada (BL-0001); observação de compactação e suspensão (work item fix-presentation-suspension); líder que nunca foi dispatch observável
- context-refs: contexto de orquestração, observação de líder, dispatch terminal, tomada de contexto, troca preparada, checkpoint de continuidade
- ADRs: ADR-0001, ADR-0002
- BLs: BL-0001
- depends-on: none
- specify-handoff: handoffs/FASE-001-SPECIFY-HANDOFF.md
- delivery-units: DU-001

> Estados: `planned | ready-for-specify | blocked | complete | superseded`. `complete` e `superseded` são terminais. `execution-order` é explícita, topológica e independente dos números de fase. Cada fase tem um handoff exclusivo; somente a primeira incompleta pode ficar `ready-for-specify`. Se todas forem terminais e não houver BL/DQ material aberto, grave `milestone_status=completed`, `state.status=complete`, `active_phase=null` e `audit_verdict=GO`; a auditoria retorna `MILESTONE-COMPLETE`.

## Delivery First
Feature/fix phases are plan-only. Hotfix-fast incidents are tracked in the work-item HOTFIX.md and reconciled after ship.

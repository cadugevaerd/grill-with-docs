# ROADMAP

- execution-order: FASE-001

## FASE-001 — Observar a instalação Codex do i-have-adhd
- state: ready-for-specify
- objetivo: a entrada GWD no Codex chega a `installation=present` a partir da listagem nativa quando a cópia aprovada está instalada, e continua `undetermined` em qualquer evidência incompleta ou divergente
- scope-in: observer de instalação do runtime Codex; teste offline pelo seam injetável
- scope-out: runtime Claude; demais lacunas do T029 (líder morto, preview do adopt, troca antes do checkpoint, suspensão, campos do checkpoint)
- context-refs: observer de instalação, listagem nativa, layout do cache Codex
- ADRs: ADR-0001
- BLs: none
- depends-on: none
- specify-handoff: handoffs/FASE-001-SPECIFY-HANDOFF.md
- delivery-units: DU-001

> Estados: `planned | ready-for-specify | blocked | complete | superseded`. `complete` e `superseded` são terminais. `execution-order` é explícita, topológica e independente dos números de fase. Cada fase tem um handoff exclusivo; somente a primeira incompleta pode ficar `ready-for-specify`. Se todas forem terminais e não houver BL/DQ material aberto, grave `milestone_status=completed`, `state.status=complete`, `active_phase=null` e `audit_verdict=GO`; a auditoria retorna `MILESTONE-COMPLETE`.

## Delivery First
Feature/fix phases are plan-only. Hotfix-fast incidents are tracked in the work-item HOTFIX.md and reconciled after ship.

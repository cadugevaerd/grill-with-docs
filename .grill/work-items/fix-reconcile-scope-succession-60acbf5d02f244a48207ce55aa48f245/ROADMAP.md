# ROADMAP

- execution-order: FASE-001

## FASE-001 — Sucessão explícita de escopo reconciliado
- state: ready-for-specify
- objetivo: distinguir reutilização sequencial autorizada de sobreposição concorrente sem transformar recibos históricos em ownership perpétuo.
- scope-in: dependência direta que autoriza reutilização de escopo nos reconciliadores completo e targeted; preservação fail-closed dos demais conflitos.
- scope-out: autorização transitiva, liberação por mera conclusão e alteração do schema dos recibos.
- context-refs: recibo histórico, sucessão explícita, sobreposição concorrente, ownership perpétuo
- ADRs: ADR-0001
- BLs: none
- depends-on: none
- specify-handoff: handoffs/FASE-001-SPECIFY-HANDOFF.md
- delivery-units: DU-001

> Estados: `planned | ready-for-specify | blocked | complete | superseded`. `complete` e `superseded` são terminais. `execution-order` é explícita, topológica e independente dos números de fase. Cada fase tem um handoff exclusivo; somente a primeira incompleta pode ficar `ready-for-specify`. Se todas forem terminais e não houver BL/DQ material aberto, grave `milestone_status=completed`, `state.status=complete`, `active_phase=null` e `audit_verdict=GO`; a auditoria retorna `MILESTONE-COMPLETE`.

## Delivery First
Feature/fix phases are plan-only. Hotfix-fast incidents are tracked in the work-item HOTFIX.md and reconciled after ship.

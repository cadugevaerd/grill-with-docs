# ROADMAP

- execution-order: FASE-001

## FASE-001 — Detecção de extensão pelo registro
- state: complete
- objetivo: `preflight` reporta `OK` em ambiente íntegro e, quando não reporta, nomeia a causa observada e a ação que a resolve
- scope-in: `ensure_dependencies.py` (detecção de extensão e remediação), `assets/dependencies.json` (registro como dependência declarada), validadores que enumeram status de dependência, os oito lugares do contrato de distribuição, `CHANGELOG.md`
- scope-out: parser da saída de `specify extension list` (removido, não mantido em paralelo), demais tipos de dependência (`runtime`, `binary`), catálogo de confiança `.specify/extension-catalogs.yml`, hooks, qualquer instalação delegada
- context-refs: registro de extensões, detecção de extensão, falso negativo, falso positivo, present, missing, undetermined, remediação, bump obrigatório
- ADRs: ADR-0001, ADR-0002, ADR-0003, ADR-0004
- BLs: none
- depends-on: none
- specify-handoff: handoffs/FASE-001-SPECIFY-HANDOFF.md
- delivery-units: DU-001

> Estados: `planned | ready-for-specify | blocked | complete | superseded`. `complete` e `superseded` são terminais. `execution-order` é explícita, topológica e independente dos números de fase. Cada fase tem um handoff exclusivo; somente a primeira incompleta pode ficar `ready-for-specify`. Se todas forem terminais e não houver BL/DQ material aberto, grave `milestone_status=completed`, `state.status=complete`, `active_phase=null` e `audit_verdict=GO`; a auditoria retorna `MILESTONE-COMPLETE`.

## Delivery First
Feature/fix phases are plan-only. Hotfix-fast incidents are tracked in the work-item HOTFIX.md and reconciled after ship.

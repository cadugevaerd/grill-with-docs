# ROADMAP

- execution-order: FASE-001

## FASE-001 — Probes Git por worktree e timeout público suficiente
- state: ready-for-specify
- objetivo: Eliminar o falso STATUS-TIMEOUT tornando o custo Git da projeção de status independente do número de work items, com um timeout público dimensionado com margem sobre o pior caso real medido.
- scope-in: probes Git (`live`, branches locais) resolvidos por worktree/repositório e não por item; timeout público do wrapper `status`/`status --format markdown` elevado de 5s para 30s; teste de regressão que trava o escopo por worktree; bump SemVer obrigatório do plugin; atualização dos oito locais de distribuição (manifests, marketplaces, README, CHANGELOG) e revalidação dos gates de distribuição.
- scope-out: mudança de formato ou schema do contrato `grill-status/v1`; novos códigos STATUS-*; otimização de performance dos probes além do necessário para eliminar o falso positivo.
- context-refs: STATUS-TIMEOUT, probe Git por worktree, timeout público suficiente
- ADRs: ADR-0001
- BLs: none
- depends-on: none
- specify-handoff: handoffs/FASE-001-SPECIFY-HANDOFF.md
- delivery-units: DU-001

> Estados: `planned | ready-for-specify | blocked | complete | superseded`. `complete` e `superseded` são terminais. `execution-order` é explícita, topológica e independente dos números de fase. Cada fase tem um handoff exclusivo; somente a primeira incompleta pode ficar `ready-for-specify`. Se todas forem terminais e não houver BL/DQ material aberto, grave `milestone_status=completed`, `state.status=complete`, `active_phase=null` e `audit_verdict=GO`; a auditoria retorna `MILESTONE-COMPLETE`.

## Delivery First
Feature/fix phases are plan-only. Hotfix-fast incidents are tracked in the work-item HOTFIX.md and reconciled after ship.

# ROADMAP

- execution-order: FASE-001

## FASE-001 — Resolver o backlog vinculado de qualquer worktree do repositório
- state: ready-for-specify
- objetivo: `preflight`, `init` e os verbos `backlog-*` executados numa worktree linkada encontram o mesmo backlog `BOUND` que a worktree de controle, sem `--skip-backlog`.
- scope-in: `resolve_backlog` comparando `bound_path` com o conjunto de candidatos; enumeração das worktrees pelo seam de toolchain; worktree de controle como alvo de bind e de `derive_identity`; recusa por ambiguidade; fallback para `{root}`; testes com stub e um caso de git real; bump de versão.
- scope-out: re-apontar caminho vinculado de worktree removida (DQ-0005, condição pré-existente ao fix); mudar a chave do `bound_path` no backlogctl; migrar binds existentes; re-vincular `DTA`/`EEA`/`FLM` para a worktree de controle.
- context-refs: worktree de controle, worktree linkada, caminho vinculado, conjunto de candidatos, resolução do backlog, seam de toolchain, carimbo de escape
- ADRs: ADR-0001, ADR-0002
- BLs: none
- depends-on: none
- specify-handoff: handoffs/FASE-001-SPECIFY-HANDOFF.md
- delivery-units: DU-001

> Estados: `planned | ready-for-specify | blocked | complete | superseded`. `complete` e `superseded` são terminais. `execution-order` é explícita, topológica e independente dos números de fase. Cada fase tem um handoff exclusivo; somente a primeira incompleta pode ficar `ready-for-specify`. Se todas forem terminais e não houver BL/DQ material aberto, grave `milestone_status=completed`, `state.status=complete`, `active_phase=null` e `audit_verdict=GO`; a auditoria retorna `MILESTONE-COMPLETE`.

## Delivery First
Feature/fix phases are plan-only. Hotfix-fast incidents are tracked in the work-item HOTFIX.md and reconciled after ship.

# ROADMAP

- execution-order: FASE-001

## FASE-001 — Children Orca independentes de CLI
- state: ready-for-specify
- objetivo: No Claude Code e no Codex, a sessão líder do GWD inicia todo especialista e worker como child Orca verificável por Dispatch, recusa de forma nomeada sem Orca pronto e registra evidência estrutural auditável
- scope-in: topologia coordenador/child; bloqueio sem Orca; binding único de modelo/esforço; override de CLI carimbado; placement do worker no worktree do gauntlet; evidência por child; Orca como dependência obrigatória; bump MAJOR 7.0.0
- scope-out: mudanças no Orca; worktree criado pelo Orca; cópia de transcript; emenda da Constituição; WORKFLOW/ESSENTIAL/registries v3/v4
- context-refs: sessão líder, coordenador, child, Run, Dispatch, especialista, worker, caminho degradado, candidata 6.0.0
- ADRs: ADR-0001, ADR-0002, ADR-0003, ADR-0004, ADR-0005, ADR-0006
- BLs: BL-0001
- depends-on: none
- specify-handoff: handoffs/FASE-001-SPECIFY-HANDOFF.md
- delivery-units: DU-001

> Estados: `planned | ready-for-specify | blocked | complete | superseded`. `complete` e `superseded` são terminais. `execution-order` é explícita, topológica e independente dos números de fase. Cada fase tem um handoff exclusivo; somente a primeira incompleta pode ficar `ready-for-specify`. Se todas forem terminais e não houver BL/DQ material aberto, grave `milestone_status=completed`, `state.status=complete`, `active_phase=null` e `audit_verdict=GO`; a auditoria retorna `MILESTONE-COMPLETE`.

## Delivery First
Feature/fix phases are plan-only. Hotfix-fast incidents are tracked in the work-item HOTFIX.md and reconciled after ship.

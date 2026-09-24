# ROADMAP

- execution-order: FASE-001

## FASE-001 — Suspensão e reativação da apresentação local no core
- state: ready-for-specify
- objetivo: `stop adhd mode` e `start adhd mode` em mensagem de usuário da própria sessão passam a ter efeito verificável no core, sobrevivendo à compactação e a upgrades, sem exigir a recarga que a suspensão proíbe
- scope-in: produção da suspensão a partir do transcript nativo (ADR-0001); reativação explícita (ADR-0002); upgrade durante a suspensão (ADR-0003); teste do caminho `compact_boundary`/`compacted` até o bloco de compactação
- scope-out: conformidade das respostas do modelo (achado F1); reexecução da matriz T029, que pertence ao work item de origem
- context-refs: apresentação local, suspensão, reativação, fonte não-agente da sessão, bloco de compactação
- ADRs: ADR-0001, ADR-0002, ADR-0003
- BLs: none
- depends-on: none
- specify-handoff: handoffs/FASE-001-SPECIFY-HANDOFF.md
- delivery-units: DU-001

> Estados: `planned | ready-for-specify | blocked | complete | superseded`. `complete` e `superseded` são terminais. `execution-order` é explícita, topológica e independente dos números de fase. Cada fase tem um handoff exclusivo; somente a primeira incompleta pode ficar `ready-for-specify`. Se todas forem terminais e não houver BL/DQ material aberto, grave `milestone_status=completed`, `state.status=complete`, `active_phase=null` e `audit_verdict=GO`; a auditoria retorna `MILESTONE-COMPLETE`.

## Delivery First
Feature/fix phases are plan-only. Hotfix-fast incidents are tracked in the work-item HOTFIX.md and reconciled after ship.

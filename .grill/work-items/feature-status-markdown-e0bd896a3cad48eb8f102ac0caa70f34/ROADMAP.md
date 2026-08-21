# ROADMAP

- execution-order: FASE-001

## FASE-001 — Status humano determinístico
- state: complete
- objetivo: a skill `grill-with-docs status` retorna `all good` somente quando não há pendência e, nos demais casos, uma tabela Markdown estável com item, status e causa
- scope-in: projeção aditiva em `grill_status.py`, opção `status --format markdown` em `grill_workspace.py`, instrução canônica da skill, testes públicos de status e distribuição, documentação, bump e changelog
- scope-out: alteração do JSON padrão para Markdown, remoção de itens fechados do JSON, mudança dos exit codes, reformatação do resumo dos hooks, implementação de `gauntlet-status`, reconciliação como requisito de fechamento
- context-refs: status bruto, status humano, work item coerentemente fechado, pendência operacional, etapa GWD, all good, inicialização pendente, bump obrigatório
- ADRs: ADR-0001, ADR-0002, ADR-0003, ADR-0004
- BLs: none
- depends-on: none
- specify-handoff: handoffs/FASE-001-SPECIFY-HANDOFF.md
- delivery-units: DU-001, DU-002

> Estados: `planned | ready-for-specify | blocked | complete | superseded`. `complete` e `superseded` são terminais. `execution-order` é explícita, topológica e independente dos números de fase. Cada fase tem um handoff exclusivo; somente a primeira incompleta pode ficar `ready-for-specify`. Se todas forem terminais e não houver BL/DQ material aberto, grave `milestone_status=completed`, `state.status=complete`, `active_phase=null` e `audit_verdict=GO`; a auditoria retorna `MILESTONE-COMPLETE`.

## Delivery First
Feature/fix phases are plan-only. Hotfix-fast incidents are tracked in the work-item HOTFIX.md and reconciled after ship.

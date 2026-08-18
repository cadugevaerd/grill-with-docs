# ROADMAP

- execution-order: FASE-001

## FASE-001 — Triagem selada
- state: complete
- objetivo: uma decisão de roteamento só existe quando derivada de um laudo que comprova a causa raiz e satisfaz a evidência exigida pela rota, e fica selada contra edição posterior
- scope-in: leitura fingerprintada do laudo; verificação do status declarado; matriz de evidência por rota; registro selado e imutável; preview-first; idempotência e detecção de divergência
- scope-out: exigir triagem no `init` e no `hotfix`; sequência reduzida da trilha `bugfix`; registro de skills por trilha; contrato documental de trilhas no WORKFLOW.md
- context-refs: Laudo de Causa Raiz, Rota, Matriz de Evidência, Registro de Triagem, Selo de Triagem
- ADRs: ADR-0001, ADR-0002, ADR-0003, ADR-0004
- BLs: none
- depends-on: none
- specify-handoff: handoffs/FASE-001-SPECIFY-HANDOFF.md
- delivery-units: DU-001

> Estados: `planned | ready-for-specify | blocked | complete | superseded`. `complete` e `superseded` são terminais. `execution-order` é explícita, topológica e independente dos números de fase. Cada fase tem um handoff exclusivo; somente a primeira incompleta pode ficar `ready-for-specify`. Se todas forem terminais e não houver BL/DQ material aberto, grave `milestone_status=completed`, `state.status=complete`, `active_phase=null` e `audit_verdict=GO`; a auditoria retorna `MILESTONE-COMPLETE`.

## Delivery First
Feature/fix phases are plan-only. Hotfix-fast incidents are tracked in the work-item HOTFIX.md and reconciled after ship.

## Fora desta milestone

Exigir a triagem, reduzir a trilha `bugfix` e levar tracks ao WORKFLOW.md são trabalhos subsequentes com escopo, risco e superfície de compatibilidade próprios. Eles não entram aqui como fases abertas: uma milestone não se declara terminal carregando fase que não entregou, e transformar trabalho futuro em fase aberta apenas para parecer completo é o waiver implícito que a Constituição proíbe. Cada um deles nasce como work item próprio quando for iniciado.

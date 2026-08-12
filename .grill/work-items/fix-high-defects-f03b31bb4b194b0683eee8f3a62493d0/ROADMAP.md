# ROADMAP

- execution-order: FASE-001, FASE-002, FASE-003

## FASE-001 — Virada de fase auditada
- state: ready-for-specify
- objetivo: um work item com ROADMAP multi-fase consegue iniciar a segunda fase, e cada fase deixa trilha por passo
- scope-in: comando de virada que devolve a matriz de etapas ao início; razão obrigatória; registro da transição na trilha de checkpoint; mensagem de erro da transição inválida apontando o caminho de saída
- scope-out: mudança no schema de `state.json`; migração de bundles existentes; re-pino de identidade
- context-refs: Matriz de etapas, Trilha de checkpoint, Virada de fase
- ADRs: ADR-0001
- BLs: none
- depends-on: none
- specify-handoff: handoffs/FASE-001-SPECIFY-HANDOFF.md
- delivery-units: DU-001

## FASE-002 — Deriva viva precisa
- state: planned
- objetivo: `status` deixa de reprovar todo work item multi-commit e volta a distinguir bloqueio real de deriva esperada
- scope-in: separação das duas comparações do pino; supressão do finding de head; escopo do finding de branch ao work item não terminal
- scope-out: qualquer alteração no pino gravado ou no hash que o protege
- context-refs: Pino de identidade, Deriva viva, Work item terminal
- ADRs: ADR-0002
- BLs: none
- depends-on: FASE-001
- specify-handoff: handoffs/FASE-002-SPECIFY-HANDOFF.md
- delivery-units: DU-002

## FASE-003 — Gate de bump bloqueante
- state: planned
- objetivo: PR que altera o conteúdo distribuído sem subir a versão não consegue ser integrada, e PR que não toca esse conteúdo não fica presa
- scope-in: gate em workflow próprio, sem filtro de paths; verificação de que o check reporta em toda PR, inclusive nas que hoje pulam o workflow
- scope-out: alteração do filtro de paths da matriz de portabilidade; o ato humano de marcar o check como required no branch protection
- context-refs: Gate de bump, Required status check, Filtro de paths
- ADRs: ADR-0003
- BLs: none
- depends-on: FASE-001
- specify-handoff: handoffs/FASE-003-SPECIFY-HANDOFF.md
- delivery-units: DU-003

> Estados: `planned | ready-for-specify | blocked | complete | superseded`. `complete` e `superseded` são terminais. `execution-order` é explícita, topológica e independente dos números de fase. Cada fase tem um handoff exclusivo; somente a primeira incompleta pode ficar `ready-for-specify`. Se todas forem terminais e não houver BL/DQ material aberto, grave `milestone_status=completed`, `state.status=complete`, `active_phase=null` e `audit_verdict=GO`; a auditoria retorna `MILESTONE-COMPLETE`.

## Delivery First
Feature/fix phases are plan-only. Hotfix-fast incidents are tracked in the work-item HOTFIX.md and reconciled after ship.

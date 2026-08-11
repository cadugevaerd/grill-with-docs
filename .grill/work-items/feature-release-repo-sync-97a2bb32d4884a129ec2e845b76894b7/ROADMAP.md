# ROADMAP

- execution-order: FASE-001, FASE-002, FASE-003

## FASE-001 — Gate de bump no CI
- state: complete
- objetivo: um merge que toque `plugin/` sem subir a versão falha no CI, e a versão volta a identificar o conteúdo publicado
- scope-in: verificação de bump no workflow de CI existente; critério de "tocou plugin/"; mensagem de falha acionável
- scope-out: qualquer escrita nos marketplaces; credencial; conteúdo copiado
- context-refs: Repositório canônico, Manifesto do plugin, Publicação
- ADRs: ADR-0002
- BLs: none
- depends-on: none
- specify-handoff: handoffs/FASE-001-SPECIFY-HANDOFF.md
- delivery-units: DU-001

## FASE-002 — Publicação fan-out nos dois marketplaces
- state: ready-for-specify
- objetivo: todo merge na main que toque `plugin/` deixa `claude-skills` e `codex-skills` com a versão e o conteúdo do canônico
- scope-in: workflow de publicação; espelho de `plugin/` + README; atualização de `version` na entrada de marketplace; um job por marketplace; secret com o PAT
- scope-out: reconciliação do drift já existente; qualquer mudança no formato de marketplace
- context-refs: Marketplace, Cópia vendorizada, Entrada de marketplace, Publicação
- ADRs: ADR-0001, ADR-0004, ADR-0005, ADR-0006
- BLs: BL-0001
- depends-on: FASE-001
- specify-handoff: handoffs/FASE-002-SPECIFY-HANDOFF.md
- delivery-units: DU-002

## FASE-003 — Reconciliação do drift existente
- state: planned
- objetivo: `claude-skills` e `codex-skills` deixam de servir 2.4.0 e passam a servir a versão corrente do canônico
- scope-in: gatilho `workflow_dispatch` no workflow de publicação; execução manual única; verificação do resultado nos dois marketplaces
- scope-out: backfill de 2.4.1 ou de qualquer versão histórica
- context-refs: Drift de publicação, Publicação
- ADRs: none
- BLs: none
- depends-on: FASE-002
- specify-handoff: handoffs/FASE-003-SPECIFY-HANDOFF.md
- delivery-units: DU-003

> Estados: `planned | ready-for-specify | blocked | complete | superseded`. `complete` e `superseded` são terminais. `execution-order` é explícita, topológica e independente dos números de fase. Cada fase tem um handoff exclusivo; somente a primeira incompleta pode ficar `ready-for-specify`. Se todas forem terminais e não houver BL/DQ material aberto, grave `milestone_status=completed`, `state.status=complete`, `active_phase=null` e `audit_verdict=GO`; a auditoria retorna `MILESTONE-COMPLETE`.

## Delivery First
Feature/fix phases are plan-only. Hotfix-fast incidents are tracked in the work-item HOTFIX.md and reconciled after ship.

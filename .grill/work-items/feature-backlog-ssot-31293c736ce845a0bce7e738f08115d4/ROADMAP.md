# ROADMAP

- execution-order: FASE-001, FASE-002, FASE-003, FASE-006, FASE-004, FASE-005

## FASE-001 — Destravar a ponte com o backlog operacional
- state: complete
- objetivo: A ponte opera sobre um bundle real, espelha decisão em qualquer estado e nunca duplica item ao reexecutar
- scope-in: Gate de integridade do sync, remoção do filtro open-only, mapa de estados conforme a FSM medida, deduplicação por (work_id, BL)
- scope-out: Geração da projeção, pré-requisito fail-closed, migração
- context-refs: Backlog de decisão, Backlog operacional, Item de backlog, Referência de decisão
- ADRs: ADR-0003
- BLs: none
- depends-on: none
- specify-handoff: handoffs/FASE-001-SPECIFY-HANDOFF.md
- delivery-units: DU-001

## FASE-002 — Projeção versionada e determinística
- state: ready-for-specify
- objetivo: DECISION-BACKLOG.md passa a ser gerado, byte-idêntico em reexecução, e a auditoria o valida sem processo externo
- scope-in: Geração canônica, fingerprint da autoridade, comando explícito de verificação de frescor, auditoria offline
- scope-out: Consulta à autoridade dentro do gate de auditoria
- context-refs: Projeção, Evidência no commit, Autoridade de estado
- ADRs: ADR-0001, ADR-0002
- BLs: none
- depends-on: FASE-001
- specify-handoff: handoffs/FASE-002-SPECIFY-HANDOFF.md
- delivery-units: DU-002

## FASE-003 — Pré-requisito fail-closed
- state: planned
- objetivo: O backlog operacional vira exigência declarada e o init recusa sem vínculo
- scope-in: backlogctl como dependência exigida, bind no init, saída --skip-backlog carimbada no bundle
- scope-out: Remoção da saída explícita, alteração da matriz de CI
- context-refs: Autoridade de estado, Backlog operacional
- ADRs: ADR-0001
- BLs: none
- depends-on: FASE-001
- specify-handoff: handoffs/FASE-003-SPECIFY-HANDOFF.md
- delivery-units: DU-003

## FASE-004 — Migração de bundles legados
- state: planned
- objetivo: Bundle autoral migra uma única vez para o modelo de projeção, sem mutação implícita do backlog operacional
- scope-in: Marcador de modo, comando de migração preview-first idempotente, estados históricos, recusa de mutação em bundle não migrado
- scope-out: Backfill manual, alteração de itens preexistentes
- context-refs: Projeção, Item de backlog, Evidência no commit
- ADRs: ADR-0003
- BLs: none
- depends-on: FASE-002, FASE-003
- specify-handoff: handoffs/FASE-004-SPECIFY-HANDOFF.md
- delivery-units: DU-004

## FASE-006 — Detecção de skill sombreada no preflight
- state: planned
- objetivo: O preflight avisa quando um nome de skill publicado pelo plugin está sombreado no ambiente, e sabe removê-lo sob autorização explícita
- scope-in: Detecção das skills do próprio plugin sombreadas por skill pessoal ou de projeto, relato no preflight e no init, remoção sob flag explícita
- scope-out: Colisão entre skills de terceiros, opinião sobre nomes de outros plugins, remoção automática
- context-refs: Backlog operacional
- ADRs: none
- BLs: none
- depends-on: FASE-003
- specify-handoff: handoffs/FASE-006-SPECIFY-HANDOFF.md
- delivery-units: DU-006

## FASE-005 — Verificação e publicação 3.0.0
- state: planned
- objetivo: Os quatro defeitos ganham regressão e a versão incompatível é publicada de forma consistente
- scope-in: Regressões, backlogctl falso pelo seam resolve_cli, bump nos oito lugares
- scope-out: Registro de required status check na proteção de branch, que é ato humano
- context-refs: Projeção, Backlog operacional
- ADRs: none
- BLs: none
- depends-on: FASE-001, FASE-002, FASE-003, FASE-004, FASE-006
- specify-handoff: handoffs/FASE-005-SPECIFY-HANDOFF.md
- delivery-units: DU-005

> Estados: `planned | ready-for-specify | blocked | complete | superseded`. `complete` e `superseded` são terminais. `execution-order` é explícita, topológica e independente dos números de fase. Cada fase tem um handoff exclusivo; somente a primeira incompleta pode ficar `ready-for-specify`. Se todas forem terminais e não houver BL/DQ material aberto, grave `milestone_status=completed`, `state.status=complete`, `active_phase=null` e `audit_verdict=GO`; a auditoria retorna `MILESTONE-COMPLETE`.

## Delivery First
Feature/fix phases are plan-only. Hotfix-fast incidents are tracked in the work-item HOTFIX.md and reconciled after ship.

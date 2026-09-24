# ROADMAP

- execution-order: FASE-001, FASE-002

## FASE-001 — Fence autorizado de atividade órfã
- state: ready-for-specify
- objetivo: um work item com uma atividade de especialista órfã (`DISPATCHED`, sem resultado) ou de sessão retida (`RESULT_RECORDED`, recurso `CLOSE_PENDING`, terminal retido pelo Orca) — cujo líder terminou **ou** que ainda tem líder vivo (DQ-0008) — volta a admitir `gauntlet-context-takeover` por um verbo preview-first que exige prova terminal Orca do especialista, prova terminal do líder ou pedido do líder corrente exato, e autorização humana exata; o verbo leva a atividade a estado terminal não aceito, fecha o recurso com receipt e deixa o autor ser reexecutado como attempt 2 no contexto sucessor. Observável: no X7, `TAKEOVER-WORK-ACTIVE` some após o fence; no work item fix-continuidade-sem-checkpoint-d62bb2a5380d4409ace677fa741af28d, `interview-author-001` deixa de contar como ativa e o takeover pelo sucessor abre.
- scope-in: verbo novo com preview/apply e `--expected-sha256`; prova terminal do especialista e do líder pela mesma observação do takeover; prova de readiness do solicitante sucessor; `human-authorization/v1` com `scope = work_id + context_id + activity_id`; transição da atividade para `FAILED` com `diagnostic_ref` do receipt; fechamento do recurso de sessão com receipt correlacionado; operação `CONFIRMED` rastreável; os quatro testes negativos de DQ-0006 mais preview sem escrita, hash stale e replay idempotente; documentação do verbo no protocolo de sessão; bump nos oito pontos de distribuição.
- scope-out: SGD-37 (transcript do líder > 16 MiB); SGD-38 (KeyError do prepare-switch com `campaign` preenchido e head nulo); SGD-39 (prepare-switch grava `ACCEPTED` contra o protocolo); prevenção por checkpoint automático (T005 já cobre head nulo); aceitar, transferir ou reaproveitar o resultado gravado; fence de workers de run (já coberto por `gauntlet-run-abandon`); alterações em Constituição, WORKFLOW, `ESSENTIAL`, registries ou no Orca; mudança nas regras de herança do takeover; encerrar o work item de origem (FASE-002).
- context-refs: atividade órfã, sessão retida, fence autorizado, prova terminal Orca, autorização humana exata, takeover, quiescência, attempt 2, resultado não aceito
- ADRs: ADR-0001
- BLs: none
- depends-on: none
- specify-handoff: handoffs/FASE-001-SPECIFY-HANDOFF.md
- delivery-units: DU-001

## FASE-002 — Encerramento do work item de origem por fence autorizado
- state: planned
- objetivo: o work item fix-continuidade-sem-checkpoint-d62bb2a5380d4409ace677fa741af28d fica encerrado como `superseded`: sua atividade `interview-author-001` (sessão retida, dispatch `ctx_2923e0218c89`) é cercada pelo verbo entregue pela FASE-001 e publicado na 6.0.31, com autorização humana exata, sem aceite do resultado retido; o bundle de origem registra o encerramento apontando para este work item. Observável: `audit` do work item de origem devolve `MILESTONE-COMPLETE`; sua quiescência fica vazia; aceite tardio de `interview-author-001` recusa.
- scope-in: prévia e aplicação do fence sobre `interview-author-001` do work item de origem com prova terminal Orca de `ctx_2923e0218c89` e do líder `orca:ctx_ad48e72ddf4c` (ou pedido pelo líder corrente exato, se vivo); autorização exata com escopo daquele work item, daquele contexto e daquela atividade; marcação `superseded` da FASE-001 de origem, fechamento do milestone de origem e `superseded-by` no ADR-0001 de origem.
- scope-out: reexecutar o autor de origem como attempt 2 (as decisões já migraram para este work item); tocar o Store do X7; qualquer alteração de código ou de distribuição (entregue pela FASE-001); aceitar o resultado retido.
- context-refs: sessão retida, fence autorizado, prova terminal Orca, autorização humana exata, takeover, quiescência, resultado não aceito
- ADRs: ADR-0001
- BLs: BL-0001
- depends-on: FASE-001
- specify-handoff: handoffs/FASE-002-SPECIFY-HANDOFF.md
- delivery-units: DU-002

> Estados: `planned | ready-for-specify | blocked | complete | superseded`. `complete` e `superseded` são terminais. `execution-order` é explícita, topológica e independente dos números de fase. Cada fase tem um handoff exclusivo; somente a primeira incompleta pode ficar `ready-for-specify`. Se todas forem terminais e não houver BL/DQ material aberto, grave `milestone_status=completed`, `state.status=complete`, `active_phase=null` e `audit_verdict=GO`; a auditoria retorna `MILESTONE-COMPLETE`.

## Delivery First
Feature/fix phases are plan-only. Hotfix-fast incidents are tracked in the work-item HOTFIX.md and reconciled after ship.

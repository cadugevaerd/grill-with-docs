# ROADMAP

- execution-order: FASE-001

## FASE-001 — Fence autorizado de atividade órfã
- state: ready-for-specify
- objetivo: um work item cujo líder terminou com uma atividade de especialista órfã (`DISPATCHED`, sem resultado) ou de sessão retida (`RESULT_RECORDED`, recurso `CLOSE_PENDING`, terminal retido pelo Orca) volta a admitir `gauntlet-context-takeover` por um verbo preview-first que exige prova terminal Orca do especialista e do líder e autorização humana exata, leva a atividade a estado terminal não aceito, fecha o recurso com receipt e deixa o autor ser reexecutado como attempt 2 no contexto sucessor. Observável: no X7, `TAKEOVER-WORK-ACTIVE` some após o fence; no work item corrente, `interview-author-001` deixa de contar como ativa.
- scope-in: verbo novo com preview/apply e `--expected-sha256`; prova terminal do especialista e do líder pela mesma observação do takeover; `human-authorization/v1` com `scope = work_id + context_id + activity_id`; transição da atividade para `FAILED` com `diagnostic_ref` do receipt; fechamento do recurso de sessão com receipt correlacionado; operação `CONFIRMED` rastreável; os quatro testes negativos de DQ-0006 mais preview sem escrita, hash stale e replay idempotente; documentação do verbo no protocolo de sessão; bump nos oito pontos de distribuição.
- scope-out: SGD-37 (transcript do líder > 16 MiB); SGD-38 (KeyError do prepare-switch com `campaign` preenchido e head nulo); prevenção por checkpoint automático (T005 já cobre head nulo); aceitar, transferir ou reaproveitar o resultado gravado; fence de workers de run (já coberto por `gauntlet-run-abandon`); alterações em Constituição, WORKFLOW, `ESSENTIAL`, registries ou no Orca; mudança nas regras de herança do takeover.
- context-refs: atividade órfã, sessão retida, fence autorizado, prova terminal Orca, autorização humana exata, takeover, quiescência, attempt 2, resultado não aceito
- ADRs: ADR-0001
- BLs: none
- depends-on: none
- specify-handoff: handoffs/FASE-001-SPECIFY-HANDOFF.md
- delivery-units: DU-001

> Estados: `planned | ready-for-specify | blocked | complete | superseded`. `complete` e `superseded` são terminais. `execution-order` é explícita, topológica e independente dos números de fase. Cada fase tem um handoff exclusivo; somente a primeira incompleta pode ficar `ready-for-specify`. Se todas forem terminais e não houver BL/DQ material aberto, grave `milestone_status=completed`, `state.status=complete`, `active_phase=null` e `audit_verdict=GO`; a auditoria retorna `MILESTONE-COMPLETE`.

## Delivery First
Feature/fix phases are plan-only. Hotfix-fast incidents are tracked in the work-item HOTFIX.md and reconciled after ship.

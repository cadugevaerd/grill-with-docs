# ROADMAP

- execution-order: FASE-001

## FASE-001 — Alinhar o gate do Gauntlet e a CLI à frontier ativa
- state: ready-for-specify
- objetivo: `gauntlet-init` aceita o `WORKFLOW.md` da frontier ativa, e a suíte reprova sozinha quando uma frontier nova chegar sem que os pontos de injeção acompanhem.
- scope-in: módulo de gate injetado nos quatro pontos do Gauntlet; `KNOWN_VERSIONS` e `EXECUTABLE_VERSIONS` no SSOT; leitura do SSOT pela CLI em lugar das cópias literais; renome do parâmetro para `workflow_gate`; renome de `state.json:workflow.version` para `workflow.schema` com dual-read; teste ancorado em `ACTIVE_VERSION`.
- scope-out: dispatch do gate por versão do documento (BL-0001); migração de bundle existente; qualquer alteração nas tabelas por versão além da amarração de teste; remoção de `workflow_v3` da árvore.
- context-refs: gate de execução, módulo de gate, ponto de injeção, marcador de workflow, frontier ativa, tabela por versão
- ADRs: ADR-0001, ADR-0002, ADR-0003, ADR-0004, ADR-0005, ADR-0006, ADR-0007, ADR-0008
- BLs: BL-0001
- depends-on: none
- specify-handoff: handoffs/FASE-001-SPECIFY-HANDOFF.md
- delivery-units: DU-001

> Estados: `planned | ready-for-specify | blocked | complete | superseded`. `complete` e `superseded` são terminais. `execution-order` é explícita, topológica e independente dos números de fase. Cada fase tem um handoff exclusivo; somente a primeira incompleta pode ficar `ready-for-specify`. Se todas forem terminais e não houver BL/DQ material aberto, grave `milestone_status=completed`, `state.status=complete`, `active_phase=null` e `audit_verdict=GO`; a auditoria retorna `MILESTONE-COMPLETE`.

## Delivery First
Feature/fix phases are plan-only. Hotfix-fast incidents are tracked in the work-item HOTFIX.md and reconciled after ship.

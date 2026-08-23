# ROADMAP

- execution-order: FASE-001

## FASE-001 — Versão de workflow derivada do documento
- state: ready-for-specify
- objetivo: `init` grava em `state.json` a versão de workflow que o `WORKFLOW.md` do repositório efetivamente declara, e a auditoria aceita esse valor verdadeiro; um documento v3 ou v4 deixa de exigir um carimbo `"v2"` falso para obter GO.
- scope-in: `grill_workspace.py` (carimbo de `state.workflow.version` e de `development.workflow_version` no `init`, recusa fail-closed quando o marcador não resolve); `assets/state.template.json` (o literal `"v4"` deixa de valer como valor final); `ensure_workflow.py` (função nova `sole_managed_version`); `audit_decisions.py` (membership em `ACCEPTED_WORKFLOW_MARKERS` no lugar do literal `"v2"`); testes de contrato cobrindo a matriz de marcadores, a paridade entre os dois detectores e a compatibilidade dos bundles `"v2"` existentes.
- scope-out: comparação do carimbo com o marcador em disco (rejeitada em ADR-0001); migração ou reescrita de bundles já publicados; unificação dos dois detectores num módulo comum (rejeitada em ADR-0002); qualquer mudança na tabela de sequências de `workflow_versions.py`; a `ESSENTIAL` de qualquer versão gerenciada.
- context-refs: marcador de workflow, campo derivado, campo constante, detector estrito, par writer/reader, versão ativa do plugin
- ADRs: ADR-0001, ADR-0002
- BLs: none
- depends-on: none
- specify-handoff: handoffs/FASE-001-SPECIFY-HANDOFF.md
- delivery-units: DU-001

> Estados: `planned | ready-for-specify | blocked | complete | superseded`. `complete` e `superseded` são terminais. `execution-order` é explícita, topológica e independente dos números de fase. Cada fase tem um handoff exclusivo; somente a primeira incompleta pode ficar `ready-for-specify`. Se todas forem terminais e não houver BL/DQ material aberto, grave `milestone_status=completed`, `state.status=complete`, `active_phase=null` e `audit_verdict=GO`; a auditoria retorna `MILESTONE-COMPLETE`.

## Delivery First
Feature/fix phases are plan-only. Hotfix-fast incidents are tracked in the work-item HOTFIX.md and reconciled after ship.

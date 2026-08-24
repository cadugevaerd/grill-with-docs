# ROADMAP

- execution-order: FASE-001

## FASE-001 — Versão de workflow derivada do documento
- state: ready-for-specify
- objetivo: `init` grava em `state.json` a sequência de etapas que o `WORKFLOW.md` do repositório efetivamente declara, em vez do literal congelado no asset; um repositório que preserva um documento v3 deixa de nascer declarando v4 e de ser julgado pela sequência errada. Documento sem declaração única passa a recusar a criação, em vez de produzir bundle condenado.
- scope-in: `grill_workspace.py` (`state_template` deriva `development.workflow_version` do marcador do documento; recusa fail-closed quando o marcador não resolve); `assets/state.template.json` (o literal `"v4"` deixa de valer como valor final); `ensure_workflow.py` (função nova `sole_managed_version`); testes de contrato cobrindo a matriz de marcadores, a paridade entre os dois detectores e a preservação do veredito dos bundles existentes.
- scope-out: o campo `workflow` do registro de estado, que a 5.0.0 renomeou para `schema` e redefiniu como tag de forma do próprio bloco (ADR-0003); a asserção correspondente da auditoria; comparação do carimbo com o marcador em disco (rejeitada em ADR-0001); migração ou reescrita de bundles já publicados; unificação dos dois detectores num módulo comum (rejeitada em ADR-0002); qualquer mudança na tabela de sequências de `workflow_versions.py`; a `ESSENTIAL` de qualquer versão gerenciada; o gate de elegibilidade do Gauntlet, corrigido fora deste work item em 055a886.
- context-refs: marcador de workflow, campo derivado, campo constante, detector estrito, par writer/reader, versão ativa do plugin
- ADRs: ADR-0001, ADR-0002, ADR-0003
- BLs: none
- depends-on: none
- specify-handoff: handoffs/FASE-001-SPECIFY-HANDOFF.md
- delivery-units: DU-001

> Estados: `planned | ready-for-specify | blocked | complete | superseded`. `complete` e `superseded` são terminais. `execution-order` é explícita, topológica e independente dos números de fase. Cada fase tem um handoff exclusivo; somente a primeira incompleta pode ficar `ready-for-specify`. Se todas forem terminais e não houver BL/DQ material aberto, grave `milestone_status=completed`, `state.status=complete`, `active_phase=null` e `audit_verdict=GO`; a auditoria retorna `MILESTONE-COMPLETE`.

## Delivery First
Feature/fix phases are plan-only. Hotfix-fast incidents are tracked in the work-item HOTFIX.md and reconciled after ship.

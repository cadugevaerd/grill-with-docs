# DELIVERY-MAP

decomposition-schema: v1

## MOD-001 — Registro de versão de workflow no work item
- module-kind: platform
- responsibility: Gravar e validar, no `state.json`, qual versão de workflow o repositório efetivamente declara
- boundary: Carimbo do `init` (`grill_workspace.py`, `assets/state.template.json`), resolução de marcador (`ensure_workflow.py`) e asserção de estado da auditoria (`audit_decisions.py`)
- depends-on: none

### DU-001 — Versão derivada e validada por pertencimento
- development-type: platform-devops
- phase: FASE-001
- scope-in: Detector estrito `sole_managed_version`; carimbo de `state.workflow.version` e `development.workflow_version` a partir do marcador resolvido; recusa fail-closed do `init` quando o marcador não resolve; troca do literal `"v2"` por pertencimento a `ACCEPTED_WORKFLOW_MARKERS` em `audit_decisions.py:801`; testes de matriz, de paridade entre detectores e de compatibilidade dos bundles `"v2"` existentes
- scope-out: Comparação do carimbo com o marcador em disco (rejeitada em ADR-0001); reescrita de bundles publicados; unificação dos detectores num módulo comum; tabelas de sequência de `workflow_versions.py`
- depends-on: none
- acceptance: Um bundle criado sobre `WORKFLOW.md` v4 registra `v4` nos dois campos e audita GO sem edição manual; os 9 bundles carimbados `"v2"` deste repositório continuam auditando como antes; `init` sobre documento sem marcador, ou com dois, recusa nomeando o encontrado e o esperado, sem criar bundle; a suíte de validadores fecha em exit 0

> IDs are stable within this work item. `module-kind` is one of `domain|platform|cross-cutting`; each DU has exactly one closed development type.

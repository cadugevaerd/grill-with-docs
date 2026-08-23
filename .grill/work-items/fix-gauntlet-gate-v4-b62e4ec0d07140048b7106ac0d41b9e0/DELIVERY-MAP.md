# DELIVERY-MAP

decomposition-schema: v1

## MOD-001 — Versionamento de workflow
- module-kind: platform
- responsibility: Ser a autoridade tabular sobre quais versões de workflow o runtime executa e quais ele sabe ler
- boundary: `grill_core/workflow_versions.py`
- depends-on: none

### DU-001 — Gate na frontier ativa, SSOT único
- development-type: platform-devops
- phase: FASE-001
- scope-in: módulo de gate injetado; `KNOWN_VERSIONS`/`EXECUTABLE_VERSIONS`; CLI lendo o SSOT; parâmetro `workflow_gate`; `workflow.schema` com dual-read; teste ancorado em `ACTIVE_VERSION`
- scope-out: dispatch por versão do documento; migração de bundle; remoção de `workflow_v3`
- depends-on: none
- acceptance: `gauntlet-init` retorna sucesso contra o `WORKFLOW.md` de `ACTIVE_VERSION`; `python3 tests/run_validators.py` em exit 0; nenhuma tabela por versão perde a chave `"v3"`; nenhum código de erro público muda de string

> IDs are stable within this work item. `module-kind` is one of `domain|platform|cross-cutting`; each DU has exactly one closed development type.

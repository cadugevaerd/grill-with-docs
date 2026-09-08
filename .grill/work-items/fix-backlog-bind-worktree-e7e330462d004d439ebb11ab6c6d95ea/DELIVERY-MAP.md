# DELIVERY-MAP

decomposition-schema: v1

## MOD-001 — Ponte do backlog
- module-kind: platform
- responsibility: Decidir a que backlog um repositório pertence e espelhar decisões nele, falando somente `backlogctl --json`
- boundary: `plugin/skills/grill-with-docs/scripts/backlog_bridge.py`; contrato em `tests/validate_backlog_contract.py`
- depends-on: none

### DU-001 — Resolução por conjunto de worktrees
- development-type: platform-devops
- phase: FASE-001
- scope-in: conjunto de candidatos em `resolve_backlog`; worktree de controle como alvo; ambiguidade fail-closed; fallback; testes stub + git real; bump
- scope-out: re-bind de caminho obsoleto (DQ-0005, out-of-scope); mudança no backlogctl; migração de binds
- depends-on: none
- acceptance: `preflight` numa worktree linkada deste repositório devolve `BOUND` código `SGD`; `python3 tests/run_validators.py` em exit 0; nenhum código de erro público muda de string; nenhum bind existente é re-apontado

> IDs are stable within this work item. `module-kind` is one of `domain|platform|cross-cutting`; each DU has exactly one closed development type.

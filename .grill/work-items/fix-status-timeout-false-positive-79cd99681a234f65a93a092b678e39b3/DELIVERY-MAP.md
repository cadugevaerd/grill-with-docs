# DELIVERY-MAP

decomposition-schema: v1

## MOD-001 — Status timeout correction
- module-kind: cross-cutting
- responsibility: Eliminar o falso STATUS-TIMEOUT do wrapper público de status, escopando probes Git por worktree/repositório e dimensionando o timeout com margem sobre o pior caso medido
- boundary: `plugin/skills/grill-with-docs/scripts/grill_status.py`, `plugin/skills/grill-with-docs/scripts/grill_workspace.py` (entry point público `status`), `tests/validate_status_contract.py`, e os oito locais de distribuição do plugin
- depends-on: none

### DU-001 — Probes Git por worktree e timeout público suficiente
- development-type: backend
- phase: FASE-001
- scope-in: escopo dos probes Git por worktree/repositório, timeout público suficiente, teste de regressão, bump SemVer, atualização dos oito locais de distribuição e revalidação dos gates de distribuição
- scope-out: mudança de schema/formato do contrato `grill-status/v1`; novos códigos STATUS-*
- depends-on: none
- acceptance: `tests/run_validators.py` passa sem STATUS-TIMEOUT falso num workspace real com múltiplos work items/worktrees, com regressão travando o escopo por worktree e a versão/distribuição do plugin coerentes nos oito locais

> IDs are stable within this work item. `module-kind` is one of `domain|platform|cross-cutting`; each DU has exactly one closed development type.

# PLAN-CONTEXT

## FASE-001 — Probes Git por worktree e timeout público suficiente
- phase: FASE-001
- ADRs: ADR-0001
- BLs: none
- delivery-units: DU-001
- development-type: backend

### HOW
- Probes Git de `build_status` em `grill_status.py` resolvem `live()` (branch/head/dirty) uma única vez por worktree percorrido, e a lista de branches locais via `git for-each-ref --format=%(refname:short) refs/heads` uma única vez por repositório — nunca uma vez por work item enumerado, que é o que produzia o custo O(items).
- O wrapper público em `grill_workspace.py` (`status_command` e `status_markdown_command`) eleva `STATUS_TIMEOUT_SECONDS` de 5 para 30, valor com margem sobre os 10,56s reais medidos e os 9,03s do contrafactual isolado registrados na evidência.
- Regressão trava o escopo por worktree, não apenas o valor do timeout: um teste que crie múltiplos work items no mesmo worktree e afirme que o probe de estado vivo é chamado exatamente uma vez por worktree, e não uma vez por item, para que uma reintrodução do custo O(items) seja pega mesmo que o timeout de 30s ainda absorva o caso de teste.
- Bump SemVer do plugin (patch — correção de bug sem mudança de contrato público `grill-status/v1`) propagado nos oito locais exigidos pela distribuição: `plugin/.claude-plugin/plugin.json`, `plugin/.codex-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.agents/plugins/marketplace.json`, constante `VERSION` de `tests/validate_distribution.py`, heading de `plugin/skills/grill-with-docs/SKILL.md`, heading de `plugin/skills/grill-with-docs/references/session-protocol.md` e heading de `README.md`.
- `tests/validate_distribution.py` e `python3 tests/run_validators.py` completos revalidados antes do ship, para que o gate de bump e a suíte inteira (não só `validate_status_contract.py`) cubram a correção.
- Nenhuma mudança de schema: o payload `grill-status/v1`, os códigos `STATUS-TIMEOUT`/`STATUS-INVALID-OUTPUT`/`STATUS-SCHEMA` e a renderização Markdown permanecem os mesmos: só o escopo dos probes e o valor do timeout mudam.

> Mantenha um bloco por fase e referências ADR/BL exatamente equivalentes ao ROADMAP e ao handoff. Nunca registre `selected-handoff` aqui.

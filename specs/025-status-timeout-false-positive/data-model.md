# Data Model: Falso positivo de timeout no status do workspace

Esta correção não introduz entidades de domínio novas nem altera o schema público
`grill-status/v1` (FR-005). As "entidades" relevantes são estruturas internas de execução
já existentes, cujo escopo de resolução muda — não sua forma.

## `LiveState` (interno, não serializado no payload público)

Estado Git resolvido por **worktree** (antes: por work item).

| Campo | Tipo | Origem | Escopo (após correção) |
|---|---|---|---|
| `branch` | `str` | `git rev-parse --abbrev-ref HEAD` (via `live()`) | uma vez por worktree percorrido |
| `head` | `str` | `git rev-parse HEAD` (via `live()`) | uma vez por worktree percorrido |
| `dirty` | `bool` | `git status --porcelain` (via `live()`) | uma vez por worktree percorrido |

**Regra de resolução**: `live_state = live(worktree)` é calculado uma vez no laço externo
de `build_status()`, antes de iterar os work items daquele worktree, e passado por
parâmetro (`live_state=`) para cada chamada de `item_payload()`. Nenhum `item_payload()`
chama `live()` diretamente.

## `LocalBranches` (interno, não serializado no payload público)

Conjunto de nomes de branches locais do **repositório**.

| Campo | Tipo | Origem | Escopo (após correção) |
|---|---|---|---|
| `local_branches` | `set[str]` | `git for-each-ref --format=%(refname:short) refs/heads` | uma vez por repositório (`root`) |

**Regra de resolução**: calculado uma vez em `build_status()` antes do laço de worktrees,
passado por parâmetro (`local_branches=`) para `item_payload()`. A checagem
`branch_alive` deixa de spawnar `git rev-parse --verify` por item e passa a testar
pertencimento em `local_branches` (operação em memória).

## `grill-status/v1` (payload público — schema INALTERADO)

Não há mudança de campo, tipo ou significado. Referenciado aqui apenas para deixar
explícito o que a correção NÃO toca:

- `schema`, `verdict`, `code`, `project_root`, `summary` (`total`/`in_progress`/
  `blocked`/`completed`), `work_items[]`, `next_action` — mesma forma antes e depois.
- Código `STATUS-TIMEOUT`: mesmo significado (bloqueio por timeout do wrapper público),
  apenas o limiar que o produz muda (5s → 30s) e a probabilidade de ocorrência em
  workspace real cai (custo deixa de ser O(items)).
- Renderização Markdown (`status --format markdown`): mesmo formato de tabela, mesma
  linha de fallback em timeout.

## Constante de configuração

| Nome | Local | Valor anterior | Valor novo | Tipo de mudança |
|---|---|---|---|---|
| `STATUS_TIMEOUT_SECONDS` | `plugin/skills/grill-with-docs/scripts/grill_workspace.py` | `5` (hardcoded inline) | `30` (constante de módulo) | correção de configuração interna, não contrato |

## Versão do plugin (distribuição, não schema)

| Campo | Local(is) | Valor anterior | Valor novo |
|---|---|---|---|
| `version` | `plugin/.claude-plugin/plugin.json`, `plugin/.codex-plugin/plugin.json`, `.claude-plugin/marketplace.json` (`plugins[0].version`), `.agents/plugins/marketplace.json` (`plugins[0].version`) | `5.2.0` | `5.2.1` |
| `VERSION` | `tests/validate_distribution.py` | `"5.2.0"` | `"5.2.1"` |
| heading `# Grill with Docs vX.Y.Z` | `plugin/skills/grill-with-docs/SKILL.md` | `v5.2.0` | `v5.2.1` |
| heading `# Protocolo de sessão vX.Y.Z` | `plugin/skills/grill-with-docs/references/session-protocol.md` | `v5.2.0` | `v5.2.1` |
| heading `**vX.Y.Z` | `README.md` | `**v5.2.0` | `**v5.2.1` |

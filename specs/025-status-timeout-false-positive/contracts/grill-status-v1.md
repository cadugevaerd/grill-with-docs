# Contrato: `grill-status/v1` (INALTERADO por esta correção)

Este documento fixa o contrato público que a correção MUST preservar (FR-005). Nenhum
campo, código ou formato muda; o único comportamento observável que muda é: o comando
deixa de retornar `STATUS-TIMEOUT` falso em workspaces reais grandes, porque o custo de
execução deixa de crescer com o número de work items e o timeout público ganha margem
sobre o pior caso medido.

## Superfície pública

- `grill status [--work-id ID] [--format json|markdown]` (via `grill_workspace.py`
  `status_command` / `status_markdown_command`)
- Timeout público: `STATUS_TIMEOUT_SECONDS = 30` (antes: `5`, hardcoded inline)

## Payload JSON (`--format json`, default)

```json
{
  "schema": "grill-status/v1",
  "verdict": "GO | NO-GO | BLOCKED",
  "code": "string | null",
  "project_root": "string",
  "summary": {
    "total": "int",
    "in_progress": "int",
    "blocked": "int",
    "completed": "int"
  },
  "work_items": ["... itens agrupados por work_id ..."],
  "next_action": "string"
}
```

- Em timeout: `{"schema": "grill-status/v1", "verdict": "BLOCKED", "code": "STATUS-TIMEOUT", "next_action": "resolver-bloqueios"}`, exit `EXIT_BLOCKED`.
- Em work item ausente: `{"schema": "grill-status/v1", "verdict": "NO-GO", "code": "WORK-ITEM-MISSING", ...}`, exit `1`.

## Saída Markdown (`--format markdown`)

Tabela `| Item | Status | Pendência |` — em timeout, linha fixa de fallback:
`| workspace | blocked | STATUS-TIMEOUT: resolver bloqueios |`, exit `EXIT_BLOCKED`.

## O que esta correção NÃO altera

- Nomes, tipos e semântica de todos os campos acima.
- Códigos existentes: `STATUS-TIMEOUT`, `STATUS-INVALID-OUTPUT`, `STATUS-SCHEMA`,
  `WORK-ITEM-MISSING`.
- Formato da tabela Markdown e sua linha de fallback em timeout.
- Exit codes por verdict/code.

## O que esta correção altera (não-contratual, interno)

- Escopo de resolução dos probes Git: por worktree/repositório em vez de por work item
  (ver `data-model.md`).
- Valor de `STATUS_TIMEOUT_SECONDS`: `5` → `30`.

## Verificação de conformidade

- `tests/validate_status_contract.py` — schema, códigos, exit codes, Markdown, e o teste
  de regressão dedicado `test_live_git_state_is_resolved_once_per_worktree_not_per_item`
  (trava escopo por worktree, não apenas o valor do timeout).
- `tests/validate_distribution.py` — versão coerente nos 8 locais de distribuição.

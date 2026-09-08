# Contrato: resolução do backlog

**Função**: `resolve_backlog(root, cli, tools, db, requested=None) -> dict` em `backlog_bridge.py`. Seis callers internos (`ensure_bind`, `sync_items`, `project`, `verify`, `migrate`); a CLI expõe o resultado em `preflight.backlog`, `init.dependencies.backlog`, `backlog-adopt.backlog` e nos verbos `backlog-*`.

## Payload (inalterado em forma)

```json
{"status": "BOUND|NEEDS-BIND|NEEDS-CREATE", "code": "SGD", "name": "grill-with-docs", "bound_path": "/abs/path"}
```

| `status` | `bound_path` | `code`/`name` |
|---|---|---|
| `BOUND` | o `bound_path` real do vínculo casado (pode ser worktree linkada) | do vínculo |
| `NEEDS-BIND` | worktree de controle | do backlog declarado ou do `unbound` com nome da controle |
| `NEEDS-CREATE` | worktree de controle | `derive_identity(Path(controle), taken)` |

## Casamento

`bound_path` casa quando `os.path.realpath(bound_path) ∈ set(worktree_candidates(root, tools))`.

## Recusas (`BacklogUnavailable`, CLI → `BACKLOG-UNAVAILABLE` + `detail`)

- Dois ou mais códigos distintos casando: `"<controle> matches more than one backlog: <A> at <p1>, <B> at <p2>"`.
- `requested` diferente do código casado: mensagem atual.
- `requested` já vinculado a caminho fora do conjunto: mensagem atual.

## Invariantes

- Nenhum vínculo é alterado por resolução; só `ensure_bind --apply` muta, e apenas quando `status ≠ BOUND`.
- `backlog bind --path` recebe `resolution["bound_path"]`.
- Códigos públicos `BACKLOG-NOT-BOUND`, `BACKLOG-REQUIRED`, `BACKLOG-UNAVAILABLE`, `BACKLOG-NOT-FOUND` mantêm string e semântica.

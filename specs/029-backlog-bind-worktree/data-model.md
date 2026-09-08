# Data Model: Backlog vinculado de qualquer worktree

## Entidades

### Conjunto de candidatos (`worktree_candidates(root, tools) -> list[str]`)

| Campo | Tipo | Regra |
|---|---|---|
| `[0]` | caminho real | worktree de controle: primeira linha `worktree ` do porcelain; alvo de vínculo novo |
| `[1:]` | caminhos reais | worktrees linkadas, na ordem do git, sem duplicatas |
| invariante | — | `realpath(root)` sempre pertence ao conjunto |
| degradação | — | git com código ≠ 0 ou sem linhas → `[realpath(root)]` |

### Vínculo (item de `backlogctl backlog list`)

| Campo | Tipo | Regra |
|---|---|---|
| `code` | string | único por backlog |
| `name` | string | nome do backlog |
| `bound_path` | string ou `""` | um caminho por código; comparado por `realpath` |

### Resolução (`resolve_backlog(...) -> dict`)

| Campo | Tipo | Regra |
|---|---|---|
| `status` | `BOUND` \| `NEEDS-BIND` \| `NEEDS-CREATE` | inalterado |
| `code` | string | do vínculo casado, do `requested`, ou derivado da worktree de controle |
| `name` | string | idem; em `NEEDS-CREATE` derivado de `Path(target).name` |
| `bound_path` | string | `BOUND`: o `bound_path` real do vínculo; `NEEDS-*`: a worktree de controle |

### Recusa (`BacklogUnavailable`)

| Caso | Mensagem | Estado |
|---|---|---|
| dois códigos no conjunto | `<target> matches more than one backlog: A at p1, B at p2` | nada muta |
| `requested` ≠ código casado | `<bound_path> is already bound to A, not B` | inalterado |
| `requested` vinculado fora do conjunto | `B is already bound to <path>` | inalterado |

## Transições

```text
backlogs, candidates
   │
   ├─ ≥2 códigos com bound_path ∈ candidates ──────────────► BacklogUnavailable
   ├─ 1 código com bound_path ∈ candidates ──► requested? ─┬─ igual ──► BOUND
   │                                                        └─ ≠ ─────► BacklogUnavailable
   └─ 0 ──► requested? ─┬─ declarado e vinculado fora ─────► BacklogUnavailable
                        ├─ declarado sem vínculo ──────────► NEEDS-BIND (target)
                        ├─ não declarado ──────────────────► NEEDS-CREATE (target)
                        └─ ausente ─┬─ unbound com nome do target ► NEEDS-BIND (target)
                                    └─ senão ─────────────► NEEDS-CREATE (derive_identity(target))
```

`ensure_bind --apply` executa `backlog create` (se `NEEDS-CREATE` e `create=True`) e `backlog bind --path <resolution.bound_path>`; reexecuta a resolução e devolve `APPLIED`.

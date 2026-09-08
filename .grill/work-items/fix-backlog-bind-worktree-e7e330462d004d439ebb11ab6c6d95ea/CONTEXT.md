# CONTEXT

## Glossário

| Termo canônico | Definição | Termos a evitar | Evidência |
|---|---|---|---|
| worktree de controle | Primeira entrada de `git worktree list --porcelain`: a checkout que hospeda o `.git` real e o common dir. | "worktree principal", "repo original", "main" | `grill_core/store.py:497-501`; `git worktree list --porcelain` neste repo, entrada 1 = `~/Documentos/Projetos/grill-with-docs` |
| worktree linkada | Qualquer entrada seguinte da mesma lista: toplevel próprio, `.git` é arquivo apontando ao common dir da worktree de controle. Mesmo repositório, caminho diferente. | "cópia do repo", "outro repo", "clone" | `git worktree list --porcelain` neste repo, entradas 2 e 3 sob `~/orca/workspaces/grill-with-docs/` |
| caminho vinculado | Campo `bound_path` de um backlog no backlogctl. Um por código; hoje comparado por igualdade de string com o toplevel passado como `root`. | "root do backlog", "path do projeto" | `backlog_bridge.py:120-122`; `backlogctl --json backlog list` (SGD → `~/Documentos/Projetos/grill-with-docs`) |
| conjunto de candidatos | Caminhos de todas as worktrees registradas do repositório, normalizados por `os.path.realpath`. Um caminho vinculado casa com o repositório se pertence ao conjunto. O primeiro elemento é a worktree de controle. | "lista de paths", "roots" | ADR-0001 |
| resolução do backlog | `resolve_backlog`: única função que decide `BOUND`, `NEEDS-BIND` ou `NEEDS-CREATE`. Seis callers, todos na ponte. | "lookup", "detecção do backlog" | `backlog_bridge.py:114-142`; callers em `156,169,237,473,523,573` |
| seam de toolchain | `Toolchain.run`, objeto injetável que concentra todo subprocesso da ponte; os testes o substituem por `StubToolchain`. | "mock", "subprocess direto" | `ensure_dependencies.py:99-116`; `tests/validate_backlog_contract.py:40-61` |
| carimbo de escape | Campo `backlog_skipped` do `state.json`, gravado por `init --skip-backlog` e limpo por `backlog-adopt`. | "flag de skip" | `grill_workspace.py:1483-1529,1641-1652`; `backlog_adopt_command` em `1382-1403` |

> Somente linguagem ubíqua; decisões e tarefas vivem em ADR/BL/ROADMAP.

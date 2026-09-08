# Contrato: enumeração de worktrees

**Função**: `worktree_candidates(root: Path, tools) -> list[str]` em `backlog_bridge.py`.

## Chamada

```text
tools.run(["git", "worktree", "list", "--porcelain"], cwd=root)
```

- Sempre este `argv`, sem `-C`; o diretório vai em `cwd`.
- Um único subprocesso por resolução.

## Entrada aceita (porcelain)

```text
worktree /abs/path/control
HEAD <sha>
branch refs/heads/main

worktree /abs/path/linked
HEAD <sha>
branch refs/heads/feature
```

## Saída

- Lista de `os.path.realpath(<path>)` para cada linha `worktree <path>`, na ordem, sem duplicatas.
- `realpath(root)` acrescentado ao fim se não estiver presente.
- Código ≠ 0, saída vazia ou sem linhas `worktree ` → `[realpath(root)]`.

## Garantias

- Nunca lança por falha do git; a degradação é o comportamento atual.
- Não escreve, não toca a rede, não lê `.git` diretamente.

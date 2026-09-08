# Research: Backlog vinculado de qualquer worktree

Nenhum `NEEDS CLARIFICATION` na spec; as decisões abaixo consolidam o que a entrevista do work item selou e o que foi verificado em sessão (2026-09-08).

## R1 — Identidade do repositório para o vínculo

- **Decision**: o conjunto dos caminhos de todas as worktrees registradas (`git worktree list --porcelain`), normalizados por `os.path.realpath`; o primeiro elemento é a worktree de controle e o alvo canônico de vínculo novo.
- **Rationale**: no backlog do operador, `DTA`, `EEA` e `FLM` já estão vinculados a worktrees linkadas; uma regra "só controle" os rebaixaria a `NEEDS-CREATE`. O conjunto é superconjunto da regra atual e da regra "só controle".
- **Alternatives considered**: só a worktree de controle (rejeitada pelo owner, R-0001); `git-common-dir` ou `project_id` como chave (exigem mudança no backlogctl, outro repositório). Fonte: ADR-0001.

## R2 — Onde a enumeração roda

- **Decision**: em `backlog_bridge.py`, por `tools.run(["git","worktree","list","--porcelain"], cwd=root)`.
- **Rationale**: `Toolchain.run` já aceita `cwd` (`ensure_dependencies.py:108`) e é o único ponto de side effect da ponte; os testes já o substituem por `StubToolchain`. A ponte não importa `grill_core` (só carrega siblings) e `store._main_worktree` devolve só o primeiro caminho.
- **Alternatives considered**: `subprocess` direto (quebra a seam); reusar `grill_core.store` (import novo numa ponte que não o tem, e API privada). Fonte: `backlog_bridge.py:47-58,83-95`; DQ-0002/R-0002.

## R3 — Ambiguidade e degradação

- **Decision**: dois códigos no conjunto → `BacklogUnavailable` nomeando ambos (a CLI já traduz para `BACKLOG-UNAVAILABLE` com `detail`); enumeração com código ≠ 0 ou sem linhas → `[realpath(root)]`.
- **Rationale**: fail-closed sem código público novo; o fallback reproduz o comportamento atual e é inalcançável pelos callers da CLI, porque `project_root` já recusa `INVALID-ROOT` antes (`grill_workspace.py:257-264`).
- **Alternatives considered**: código público `BACKLOG-AMBIGUOUS` (muda o contrato para um caso raro); falhar quando o git falha (recusa nova onde hoje há resposta). Fonte: ADR-0001; DQ-0003/R-0003.

## R4 — Cobertura de teste

- **Decision**: stub do seam para lógica de conjunto, ambiguidade, fallback e bind; **um** caso com `git init` + `git worktree add` real para provar o parsing contra saída real.
- **Rationale**: todos os casos de `Resolution` hoje usam `bound_path == str(self.root)`, por isso o bug era invisível; fixture derivada do código já escondeu bug de parsing neste repositório.
- **Alternatives considered**: só stub; só git real. Fonte: ADR-0002; `tests/validate_backlog_contract.py:95-145`.

## R5 — Forma da chave do stub para git

- **Decision**: `StubToolchain.run` casa `tuple(argv[1:])` quando `argv[0] == "git"`; para os demais mantém `argv[2:]`.
- **Rationale**: o `argv` do git não tem `cli --json` na frente; a chave natural é `("worktree","list","--porcelain")`. Resposta padrão não porcelain → fallback → casos existentes intactos.
- **Alternatives considered**: passar `git -C <root>` (chave começaria pelo caminho temporário, ilegível no teste). Fonte: `tests/validate_backlog_contract.py:48-56`.

## R6 — Normalização de caminho

- **Decision**: `os.path.realpath` nos dois lados.
- **Rationale**: `bound_path` gravado pelo grill já é `Path.resolve()` (`project_root`), e o git grava caminhos reais no `worktree add`; realpath elimina atalhos e grafias divergentes, inclusive no Windows. Caminho inexistente só é normalizado lexicamente, o que basta para comparação.
- **Alternatives considered**: igualdade de string (o bug atual em outra forma); `Path.samefile` (falha para caminho removido). Fonte: DQ-0006 implícito em ADR-0001.

## R7 — Leitura SemVer

- **Decision**: patch, `5.4.0 → 5.4.1`.
- **Rationale**: corrige comportamento; nenhum código, campo ou string pública muda; nenhuma flag nova.
- **Alternatives considered**: minor (não há capacidade nova exposta). Fonte: DQ-0006/R-0006; `CLAUDE.md#Distribuição`.

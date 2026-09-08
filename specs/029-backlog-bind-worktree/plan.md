# Implementation Plan: Backlog vinculado de qualquer worktree

**Branch**: `cadugevaerd/chore-fix-backlog` | **Date**: 2026-09-08 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/029-backlog-bind-worktree/spec.md`; HOW selado no work item `fix-backlog-bind-worktree-e7e330462d004d439ebb11ab6c6d95ea` (`PLAN-CONTEXT.md`, ADR-0001, ADR-0002).

## Summary

`resolve_backlog` (`backlog_bridge.py:114-142`) passa a comparar o `bound_path` de cada backlog com o **conjunto de candidatos** — os caminhos de todas as worktrees registradas do repositório, lidos de `git worktree list --porcelain` pelo seam `Toolchain.run` e normalizados por `os.path.realpath` — em vez de com `str(root)`. O primeiro candidato (worktree de controle) vira o alvo de `NEEDS-BIND`/`NEEDS-CREATE`, de `backlog bind --path` e de `derive_identity`. Dois códigos no mesmo conjunto recusam com `BacklogUnavailable`; enumeração vazia recai em `[realpath(root)]`. Testes: `StubToolchain` aprende `git`, casos novos em `Resolution`/`BindLifecycle`, um caso com `git worktree add` real. Bump patch `5.4.0 → 5.4.1`.

## Technical Context

**Language/Version**: Python >= 3.10, somente biblioteca padrão (`os.path.realpath`, `pathlib`)

**Primary Dependencies**: nenhuma nova; `backlog_bridge.py` (ponte), `ensure_dependencies.Toolchain` (seam de subprocesso, já aceita `cwd`), `git` (dependência obrigatória já declarada)

**Storage**: nenhum; leitura de `backlogctl --json backlog list` e da saída porcelain do git, ambas via `tools.run`

**Testing**: `python3 tests/run_validators.py` (unittest, glob `validate_*.py`); casos novos em `tests/validate_backlog_contract.py` com `StubToolchain` e um caso com repositório git real em `tempfile`

**Target Platform**: Linux, macOS, Windows (matriz de CI: 3 SOs × Python 3.10/3.13), sem rede, sem `backlogctl` real

**Project Type**: plugin/CLI (scripts do skill grill-with-docs)

**Performance Goals**: um subprocesso `git` por resolução, nunca por item; seis callers, cada um resolve uma vez

**Constraints**: sem `subprocess` direto na ponte (só `tools.run`); sem SQLite direto; nenhum código público novo nem string alterada; nenhum bind existente re-apontado; `project_root` continua exigindo toplevel; bump patch nos oito pontos de `validate_distribution.py`

**Scale/Scope**: 1 helper novo + 3 funções tocadas em `backlog_bridge.py` (~40 linhas), 1 stub estendido + ~7 casos de teste, 8 pontos de versão, 1 entrada de CHANGELOG

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Cláusula | Estado | Evidência |
|---|---|---|
| Evidência antes de afirmação | PASS | Sintoma reproduzido em sessão (`preflight` → `NEEDS-CREATE CFB` com `SGD` vinculado); linhas citadas em ADR-0001/0002; research.md cita fonte por decisão |
| Work item isolado e ownership | PASS | Tudo sob `fix-backlog-bind-worktree-e7e330462d004d439ebb11ab6c6d95ea`, branch `cadugevaerd/chore-fix-backlog` |
| Feature/fix plan-only | PASS | Este plano é artefato da etapa `plan` do ciclo executor; o PLAN_ONLY_STOP da entrevista foi atravessado por ato humano (`/goal`) |
| Sequência obrigatória do desenvolvimento | PASS | `specify` atestada e selada (`.grill/attestations/029-specify.json`); `plan` em andamento |
| Verify/review antes de ship | PASS | Sem ship neste plano; ordem canônica mantida |
| Fail-closed sem waiver | PASS | Ambiguidade recusa nomeando; nenhum re-bind silencioso; fallback mantém o comportamento atual, não abre caminho novo |
| Rastreabilidade | PASS | FR-001..FR-012 ↔ US1..US3 ↔ ADR-0001/0002; cada tarefa citará FR |
| Tier de modelo e esforço do worker Orca | NOT-APPLICABLE ainda | Sem worker até `implement-parallel`; lá o modelo é derivado do binding versionado |
| Bump obrigatório do plugin | PASS | 5.4.0 → 5.4.1 em oito pontos (FR-012) |
| Release obrigatória por versão | PASS | Release é do pipeline no merge; nenhuma tag manual |
| Governance | PASS | Constituição, `WORKFLOW.md` e registry não são tocados |

Sem violações → Complexity Tracking vazio.

## Project Structure

### Documentation (this feature)

```text
specs/029-backlog-bind-worktree/
├── plan.md              # este arquivo
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   ├── backlog-resolution.md      # forma do payload de resolução e das recusas
│   └── worktree-enumeration.md    # argv, parsing e fallback da enumeração
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
plugin/skills/grill-with-docs/
├── scripts/backlog_bridge.py                # + worktree_candidates(); resolve_backlog, ensure_bind, derive_identity via alvo
├── SKILL.md                                 # heading de versão (bump); § Dependências e backlog: uma frase sobre worktree
└── references/session-protocol.md           # heading de versão (bump)
plugin/.claude-plugin/plugin.json            # bump
plugin/.codex-plugin/plugin.json             # bump
.claude-plugin/marketplace.json              # bump
.agents/plugins/marketplace.json             # bump
tests/
├── validate_backlog_contract.py             # StubToolchain aprende git; casos Resolution/BindLifecycle; caso git real
└── validate_distribution.py                 # VERSION = "5.4.1"
README.md                                    # heading de versão
CHANGELOG.md                                 # entrada 5.4.1
CLAUDE.md                                    # § init e dependências: nota de que o bind resolve por worktree
```

**Structure Decision**: mudança pontual na ponte existente; nenhum módulo novo. A enumeração vive em `backlog_bridge.py` porque é o único consumidor e porque a ponte já concentra todo subprocesso em `tools.run`; reaproveitar `grill_core.store._main_worktree` exigiria importar `grill_core` numa ponte que hoje só carrega siblings e devolveria só o primeiro caminho.

## Design

### Enumeração (`worktree_candidates`)

Ver [contracts/worktree-enumeration.md](contracts/worktree-enumeration.md).

- `worktree_candidates(root: Path, tools) -> list[str]`.
- `code, output = tools.run(["git", "worktree", "list", "--porcelain"], cwd=root)`.
- Se `code != 0`: `[os.path.realpath(root)]`.
- Caminhos = `os.path.realpath(line[len("worktree "):])` para cada linha com prefixo `worktree `, na ordem do git, sem duplicatas.
- Lista vazia: `[os.path.realpath(root)]`.
- `root` sempre entra no conjunto mesmo quando o git responde: `realpath(root)` é acrescentado se ausente, para que um `bound_path == str(root)` legado continue casando quando o git relatar grafia diferente.

### Resolução (`resolve_backlog`)

Ver [contracts/backlog-resolution.md](contracts/backlog-resolution.md).

- `candidates = worktree_candidates(root, tools)`; `target = candidates[0]`; `known = set(candidates)`.
- `bound = [b for b in backlogs if b.get("bound_path") and os.path.realpath(b["bound_path"]) in known]`.
- `len({b["code"] for b in bound}) > 1` → `BacklogUnavailable("<target> matches more than one backlog: AAA at <p1>, BBB at <p2>")`.
- Um `bound`: mesma lógica de hoje (`requested` divergente recusa); payload `bound_path` = o caminho vinculado **real** do backlog (não `target`), para que o relatório mostre onde o vínculo está.
- Sem `bound`: `requested` declarado com `bound_path` fora de `known` → recusa como hoje; `NEEDS-BIND`/`NEEDS-CREATE` usam `bound_path = target`, `name`/`code` de `derive_identity(Path(target), taken)` e o casamento `unbound` por `Path(target).name`.

### Bind (`ensure_bind`)

- `backlog bind --path resolution["bound_path"]` em vez de `str(root)`. Como `NEEDS-*` já carrega `target`, o bind novo grava a worktree de controle.

### Testes (`tests/validate_backlog_contract.py`)

- `StubToolchain.run`: se `argv[0] == "git"`, a chave é `tuple(argv[1:])`; resposta padrão para git desconhecido continua `0, envelope([])` (não porcelain → fallback), o que mantém os casos existentes intactos.
- Helper `porcelain(*paths)` que monta a saída `worktree <p>\nHEAD …\nbranch …\n\n` por caminho.
- Casos novos em `Resolution`: bound à controle resolvendo da linkada → `BOUND`; bound à linkada resolvendo da controle → `BOUND` com `bound_path` = linkada; `NEEDS-CREATE` com nome/código da controle; ambiguidade → `BacklogUnavailable`; git falhando (`code=1`) → comportamento atual; `requested` já vinculado fora do conjunto → recusa.
- Caso novo em `BindLifecycle`: `ensure_bind(..., apply=True)` a partir da linkada chama `backlog bind --path <controle>`.
- Caso com git real (`class RealWorktree`): `git init` + commit + `git worktree add` em `tempfile`; `resolve_backlog(linked, CLI, tools_stub_backlogctl_mas_git_real, DB)` → `BOUND`. O toolchain do caso responde backlogctl pelo stub e delega `git` a `subprocess` real.

### Bump e documentação

`5.4.0 → 5.4.1` nos oito pontos de `CLAUDE.md#Distribuição`; `CHANGELOG.md` com entrada `## 5.4.1`; uma frase em `SKILL.md` § Dependências e backlog e em `CLAUDE.md` § init e dependências.

## Constitution Check (pós-design)

Sem alteração: a recusa por ambiguidade e a proibição de re-bind mantêm "Fail-closed sem waiver"; nenhum código público muda (Rastreabilidade para consumidores); a Constituição, o `WORKFLOW.md` e o registry não são tocados.

## Complexity Tracking

Sem violações.

# Relatório de debug

## Status
- causa raiz comprovada

## Sintoma reproduzido
- Cenário 1 (consumidor hermes-k3s, plugin 9.1–9.3, 2026-09-26): `implement-parallel` da run `run-36d38a82957edb29aac4c315` declarou os workers `p02-a`/`p02-b`; o core criou os worktrees em `/home/carlosaraujo/Documentos/Projetos/hermes-k3s/.git/grill/wt-run-36d38a82957edb29aac4c315-p02-{a,b}`; `orca orchestration worker-start --worktree path:<.git/grill/wt-...>` funcionou, mas `worker-show` reportou `terminal.orphaned=true` (orphanReason null).
- Resultado observado 1: `gauntlet-worker-session --phase register` → `RESOURCE-IDENTITY-DIVERGENT / LEADER-AUTHORITY-UNPROVEN`; `gauntlet-converge` → `SESSION-CLOSE-UNPROVEN: worker .../p02-a has no confirmed Orca release`. Nenhum `implement-parallel` sob Orca fecha. Evidência: `hermes-k3s/fix-hermes/.grill/work-items/feature-hermes-telegram-nfs-deadlock-ccd914d870da441abfdb6ec3493eaefe/evidence/20260926-converge-bloqueio-sessao-worker.md`.
- Cenário 2 (probe live, repo grill-with-docs, Orca local, 2026-09-26 ~13:30Z): quatro worktrees do mesmo repo, um terminal por `orca terminal create --worktree path:<P>` e leitura de `orca terminal show`:
  - `<main>/.git/grill/probe-sgd45` (local atual do core) → `orphaned=true`, ausente de `orca worktree list`;
  - `<main>.grill-worktrees/probe-sgd45` (irmão fora de `.git/`, correção candidata original) → `orphaned=true`, ausente de `orca worktree list`;
  - `<main>/.claude/worktrees/probe-sgd45` → `orphaned=false`, presente em `orca worktree list`;
  - controle `~/orca/workspaces/grill-with-docs/hotfix-worker-worktree-orca` (workspace Orca) → `orphaned=false`.
- Cenário 3 (git puro, repo temporário): `git worktree add .claude/worktrees/w` → `git status --porcelain --untracked-files=all` no checkout principal mostra `?? .claude/worktrees/w/`; após `/.claude/worktrees/` em `<git-common-dir>/info/exclude`, status vazio.

## Evidências
| Evidência | Fonte | O que comprova |
|---|---|---|
| `target = store.git_common_dir(root) / "grill" / key` | `grill_core/gauntlet_runs.py:1681` (`_workspace_identity`) | todo worktree de worker nasce em `<git-common-dir>/grill/wt-<run>-<worker>` |
| `terminal.get("worktreePath") != str(self.root) or terminal.get("orphaned") is not False` | `grill_core/agent_runtime.py:820/928/970/1033` | register/release/converge exigem terminal não órfão no worktree exato |
| `orphaned:o` com `o=!Qoa(e,this.ptySurfaceTopology())`; `Qoa` exige `paneKey`/`tabId` montados | bundle do Orca `resources/app.asar` (`buildPtyTerminalSummary`) | órfão = pty sem pane montado na UI |
| `externalWorktreeVisibility: 'hide'` em `orca repo show` de grill-with-docs e hermes-k3s | CLI Orca | repositórios escondem worktrees fora das fontes listadas |
| fontes de visibilidade: built-in `[".claude","worktrees"]` e `[".gsd-workspaces"]`, `worktreeBasePath`, custom; `other` = "Outside listed sources" | bundle do Orca (`WorktreeVisibilitySourceList`, `kAe`) | só worktree sob fonte visível entra no catálogo e recebe aba |
| probe: `.git/grill` e irmão fora de `.git` órfãos; `.claude/worktrees` e workspace Orca não órfãos | Cenário 2 | a variável é a fonte de visibilidade, não o `.git/` em si |
| `orca worktree list` de hermes-k3s lista todos os 17 worktrees fora de `.git/`, incluindo `.claude/worktrees/agent-a3cc…`, e 0 de `.git/grill/wt-*` | CLI Orca | consistente com a fonte built-in `.claude/worktrees` visível |
| nested worktree aparece como `??` no checkout principal sem exclude | Cenário 3 | mover para `.claude/worktrees` exige exclude local para não sujar a árvore |

## Caminho de investigação/Hipóteses eliminadas
1. Hipótese do coordenador: Orca descarta worktrees sob `.git/` → parcialmente falsa. Worktree irmão fora de `.git/` também fica órfão e fora do catálogo (Cenário 2); a correção "mover para diretório irmão" não resolveria.
2. Hipótese de cache/atraso do catálogo → falsificada: após >5 min os probes seguem ausentes e órfãos; o de `.claude/worktrees` entrou no catálogo imediatamente.
3. Hipótese de HEAD destacado → falsificada: `fix-continuity-release` (com branch) também está fora do catálogo; `.claude/worktrees/probe-sgd45` com branch entrou.
4. Leitura do bundle do Orca: `orphaned` deriva de pane não montado; aba só monta para worktree do catálogo; catálogo filtra por fonte de visibilidade com `externalWorktreeVisibility='hide'`.

## Causa raiz
`_workspace_identity` (`grill_core/gauntlet_runs.py:1681`) coloca o worktree de cada worker em `<git-common-dir>/grill/wt-<run>-<worker>`, fora de qualquer fonte de visibilidade do Orca. Com `externalWorktreeVisibility='hide'`, o Orca não cataloga o worktree, não monta a aba do terminal do worker e o reporta `orphaned=true`; `agent_runtime.LeaderBoundary` exige `orphaned is False` e recusa register/release, então `gauntlet-converge` recusa por falta de release confirmado.

## Cadeia causal
`gauntlet-worker-prepare` → `git worktree add <git-common-dir>/grill/wt-…` → Orca catálogo (visibilidade externa `hide`) ignora o path → `worker-start --worktree path:<…>` cria pty sem pane → `worker-show`: `terminal.orphaned=true` → `gauntlet-worker-session register/release` recusa (`LEADER-AUTHORITY-UNPROVEN`) → sessão do worker nunca `CLOSED` → `gauntlet-converge` recusa `SESSION-CLOSE-UNPROVEN` → `implement-parallel` não fecha.

## Arquivos envolvidos
- `plugin/skills/grill-with-docs/scripts/grill_core/gauntlet_runs.py`: `_workspace_identity` (local do worktree) e criação em `gauntlet_worker_prepare` (`git worktree add`).
- `plugin/skills/grill-with-docs/scripts/grill_core/agent_runtime.py`: guard `orphaned is False` (correto; não muda).
- `tests/validate_gauntlet_run_contract.py`, `tests/validate_gauntlet_converge_contract.py`: helpers que fixam o path antigo.

## Limitações/incertezas
- Visibilidade de `.claude/worktrees/*` é a fonte built-in do Orca observada visível nos dois repositórios; preferência do usuário pode escondê-la, caso em que o terminal volta a ficar órfão (diagnóstico continua fail-closed pelo guard existente).
- Runs já declaradas mantêm o path antigo (compatibilidade de retomada/cleanup) e continuam órfãs no Orca; exigem run nova.

Diagnóstico encerrado. Nenhuma correção foi executada.

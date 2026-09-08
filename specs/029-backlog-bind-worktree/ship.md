# Ship Report — 029 backlog vinculado de qualquer worktree

Status: **MERGED**

## Hashes
- source_head (work): `1f51365e26867cec20d8ce770bb445b6f7e30600`
- merge commit em main: `9bdab586b8418d3fcdf1e9d03233bc88c84594c7` (`--no-ff`, worktree de integração isolado a partir de `origin/main` = `44c958f`)
- fingerprint revisada: tree `efc4e7c1a4eb` / work `e3b0c44298fc` / plan `66021123d28c` (Verify e Review r2 idênticos; Converge sobre `d647adc7ec01`, superado só por prosa em CLAUDE.md)
- remote `origin/main` lido de volta: `9bdab586b8418d3fcdf1e9d03233bc88c84594c7` — igual ao merge

## Evidência consumida
- Converge: CONVERGED (zero findings, `tasks.md` inalterado)
- Verify: PASS (28 validadores / 1380 testes exit 0, contrato 110, distribution OK, preflight `BOUND SGD`) — revalidado em `b5613ef`
- Review: APPROVE (0 Critical, 0 Important, 3 minors) — revalidado em `b5613ef`
- Autorização humana: `.grill/work-items/fix-backlog-bind-worktree-e7e330462d004d439ebb11ab6c6d95ea/SHIP-AUTHORIZATION.json` (instrução literal "ship", 2026-09-08)

## Learning gate
- Proposta `0e9ba83a516c` sobre source_head `3eca9d0`; aprovação humana: LRN-001 → `agent-context` (CLAUDE.md § Project Learnings, commit `b5613ef` `docs(ship): capture approved project learnings`); LRN-002 → `memory` (host-write após merge verificado: nota `backlog-bind-nao-segue-worktree` marcada RESOLVIDA); LRN-003, LRN-004 → discard
- Revalidação após aplicar: distribution OK, contrato 110 OK, compile OK; verify/review reatestados (`1f51365`)

## Gates na integração
- `validate_distribution.py` OK, `validate_backlog_contract.py` OK (110), `py_compile` OK; árvore do merge byte-idêntica à árvore do work HEAD (main era ancestral), coberta pela suíte completa

## Rollback
- `git revert -m 1 9bdab586b8418d3fcdf1e9d03233bc88c84594c7` em `main` restaura `44c958f` sem perder histórico.
- A release 5.4.1, se já publicada pelo pipeline, é imutável (tag anotada); rollback funcional exige bump 5.4.2 com o revert, nunca reuso da tag.
- Consumidores: nenhum código público mudou; um bind existente nunca é re-apontado. Regressão possível só se `git` falhar na enumeração, e aí o comportamento é o anterior.

## Monitoramento
- `publish.yml` no push para `main` (toca `plugin/**`): job `release` deve criar a tag `v5.4.1`/release ancorada em `9bdab586`; job `publish` aponta os marketplaces. Conferir: `gh run list --workflow publish.yml`, `gh release view v5.4.1`.
- `ci.yml` (3 SOs × Python 3.10/3.13) no push.
- Após atualizar o plugin no harness: `grill_workspace.py preflight . --runtime claude` numa worktree linkada deve devolver `BOUND` com o código do repositório.

## Cleanup
- Worktree de integração removido; 0 worktrees de worker restantes; `git stash list` vazio.
- Branches `grill/…/run-38e8773207b7f3de7623cff3/*` (integradas) removidas.
- Branch `cadugevaerd/chore-fix-backlog` mantida (worktree Orca em uso).

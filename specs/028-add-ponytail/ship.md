# Ship Report — 028 ponytail na stack oficial

Status: **MERGED**

## Hashes
- source_head (work): `bb084d3160735b09a78a0ea7d08cba2791345ff4`
- merge commit em main: `5a37b4225919d1990dfb09946142e97e0a8de209` (`--no-ff`, worktree de integração isolado a partir de `origin/main` = `a067a7c`)
- fingerprint revisada: tree `ccc4c9746a60` / work `e3b0c44298fc` / plan `7a9332aeedf9` (Converge, Verify e Review idênticos)
- remote `origin/main` lido de volta: `5a37b4225919d1990dfb09946142e97e0a8de209` — igual ao merge

## Evidência consumida
- Converge: CONVERGED (tasks_appended → T015 → sem lacunas)
- Verify: PASS (28 validadores, distribution OK, detecção real nos dois runtimes) — revalidado em `6f02757`
- Review: APPROVE (0 Critical, 0 Important, 3 minors) — revalidado em `6f02757`
- Autorização humana: `.grill/work-items/feature-add-ponytail-494ea379ecc84a38b029d55ec39ffe8f/SHIP-AUTHORIZATION.json` (instrução literal "ship")

## Learning gate
- Proposta sobre source_head `f181708`; aprovação humana: LRN-001, LRN-002, LRN-003 → `agent-context` (CLAUDE.md § Project Learnings), commit `6f02757` `docs(ship): capture approved project learnings`; LRN-004 → discard (issue #10 já cobre)
- Revalidação após aplicar: suíte 28/28 OK, verify/review reatestados (`bb084d3`)
- memory: propose-only, pendente (não requerido)

## Gates na integração
- `validate_distribution.py` OK, `validate_dependencies_contract.py` OK (63), `validate_attestation_emitter_contract.py` OK (55); árvore do merge byte-idêntica à árvore do work HEAD (main era ancestral), coberta pela suíte completa

## Rollback
- `git revert -m 1 5a37b4225919d1990dfb09946142e97e0a8de209` em `main` restaura `a067a7c` sem perder histórico; ou `git push origin a067a7c:main` (recusado pela proteção de branch — usar revert).
- A release 5.4.0, se já publicada pelo pipeline, é imutável (tag anotada); rollback funcional exige bump 5.4.1 com o revert, nunca reuso da tag.
- Consumidores: a entrada `ponytail` é `required: true` mas só bloqueia sob `--require-dependencies`; um consumidor sem ponytail vê `missing` + remediação e segue.

## Monitoramento
- `publish.yml` no push para `main` (toca `plugin/**`): job `release` deve criar a tag `v5.4.0`/release ancorada em `5a37b4225919d1990dfb09946142e97e0a8de209`; job `publish` aponta os marketplaces. Conferir: `gh run list --workflow publish.yml`, `gh release view v5.4.0`.
- `ci.yml` (3 SOs × Python 3.10/3.13) no push.
- Após atualizar o plugin no harness: `grill_workspace.py preflight . --runtime claude` deve listar `ponytail present 4.9.0`.

## Cleanup
- Worktree de integração removido; 0 worktrees de worker restantes.
- Branches `grill/…/run-c51c59be…/*` (integradas) removidas.
- Aviso: branches `grill/…/run-af616cae…/p01-a|p01-b` mantidas — run substituída por grant malformado; commits transportados por cherry-pick, branches preservadas como evidência (não mergeadas).
- Branch `cadugevaerd/chore-add-ponytail` mantida (worktree Orca em uso).

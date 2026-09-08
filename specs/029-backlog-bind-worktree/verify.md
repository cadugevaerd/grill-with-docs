## Verify Report

Verdict: PASS
Source fingerprint: tree efc4e7c1a4eb5a6011afe82594ec0d7d09a4a8adf57dffdc468572ad5c284c0a / work e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 / plan 66021123d28c2a7315ffb78ad5bf88679f160e339569b2498da731510c5e1a00   (gate reports excluded)
Converge: CONVERGED — `/speckit-converge` nesta sessão devolveu `converged` (zero findings; `tasks.md` byte-idêntico, 12/12 marcadas), atestado em `.grill/attestations/029-converge.json` e selado. Feature: `specs/029-backlog-bind-worktree`, branch `cadugevaerd/chore-fix-backlog`, HEAD `b5613ef` (revalidação após `docs(ship): capture approved project learnings`, que só acrescentou 1 bullet a `CLAUDE.md` § Project Learnings; gates reexecutados: distribution OK, contrato 110 OK, compile OK; suíte completa executada sobre a mesma árvore de código), worktree limpo.

### Operational Gates
| Gate | Command | Result | Evidence | Validator |
|---|---|---|---|---|
| tests (suíte canônica) | `python3 tests/run_validators.py` | PASS | 28 validadores (`==>`), 1380 testes, `OK (skipped=1)` (alias macOS `/var`), exit 0; sem rede, sem `backlogctl` real | leader (sequential fallback, read-only) |
| tests (unidade da feature) | `python3 tests/validate_backlog_contract.py` | PASS | `Ran 110 tests`, OK (99 → 110: 11 casos novos, incluindo `RealWorktree` com `git worktree add`) | leader |
| build/distribution | `python3 tests/validate_distribution.py` | PASS | `distribution: OK`; 8 pontos em 5.4.1 (4 manifests, `VERSION`, 3 headings) | leader |
| lint/typecheck | `python3 -m py_compile` nos 3 arquivos Python tocados | PASS | compile ok; projeto não declara linter nem typechecker (SKIPPED com evidência: sem `pyproject`/`ruff`/`mypy`) | leader |
| format | — | SKIPPED | nenhum formatador declarado no repositório | leader |
| security | scan do diff contra `main` por `api_key|secret|token|password|BEGIN RSA|BEGIN OPENSSH` e por `.env`/`credentials` | PASS | zero ocorrências; nenhum arquivo de ambiente no diff | leader |
| quickstart §2 (prova do sintoma) | `grill_workspace.py preflight . --runtime claude` nesta worktree linkada | PASS | `BOUND SGD /home/carlosaraujo/Documentos/Projetos/grill-with-docs` (antes: `NEEDS-CREATE CFB`) | leader |
| quickstart §3 (nenhum vínculo alterado) | `backlogctl --json backlog list` | PASS | 28 backlogs; sem `CFB`; SGD, DTA, EEA, FLM nos caminhos anteriores | leader |
| quickstart §4 (adoção deste work item) | `backlog-adopt --apply` | SKIPPED | pós-ship por contrato (PLAN-CONTEXT); ensaiado por `ensure_bind` em T005 | leader |
| quickstart §5 | `validate_distribution.py` | PASS | idem build/distribution | leader |

### Diff Hygiene
- `git diff main --stat`: 54 arquivos, +4792/−20. Produto: `backlog_bridge.py` (+44/−10), `validate_backlog_contract.py` (+167), 8 pontos de versão, `CHANGELOG.md`, `CLAUDE.md`, `SKILL.md`, `session-protocol.md`. Restante: `specs/029-*` (artefatos do ciclo), `.grill/` (bundle, atestações, gauntlet). Nenhum arquivo gerado ou não relacionado; nenhum `.env`/credencial.
- Worktrees de worker removidos após convergência; `git worktree list` sem `wt-run-*`; `git stash list` vazio.

### Executable Scenarios
- US1 (linkada ↔ controle): `test_bound_from_a_linked_worktree_matches_the_control_bind`, `test_a_bind_made_from_a_linked_worktree_is_not_repointed_from_the_control`, `test_resolve_from_the_real_linked_worktree_is_bound` (git real).
- US2 (alvo de bind): `test_needs_create_from_a_linked_worktree_derives_from_the_control`, `test_unbound_backlog_named_after_the_control_needs_bind_from_a_linked_worktree`, `test_requested_code_bound_outside_the_worktree_set_fails_closed`, `test_apply_from_a_linked_worktree_binds_the_control_path`.
- US3 (fail-closed/degradação): `test_two_backlogs_bound_to_different_worktrees_of_the_same_repo_refuse`, `test_git_failure_falls_back_to_the_bare_root`, `test_git_failure_does_not_match_a_different_path`, `test_porcelain_duplicates_and_unnormalised_paths_collapse_to_one_candidate`.

### Failures / Blockers
- Nenhum.

### Next Action
- PASS: run `/speckit.verify-review-ship.review`

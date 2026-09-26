# HOTFIX-PREPARED

- scope: plugin/skills/grill-with-docs/scripts/grill_core/gauntlet_runs.py,tests/validate_gauntlet_run_contract.py,tests/validate_gauntlet_converge_contract.py,tests/validate_distribution.py,plugin/.claude-plugin/plugin.json,plugin/.codex-plugin/plugin.json,.claude-plugin/marketplace.json,.agents/plugins/marketplace.json,plugin/skills/grill-with-docs/SKILL.md,plugin/skills/grill-with-docs/references/session-protocol.md,README.md,CHANGELOG.md,.grill/triage-evidence/sgd-45-debug-report.md,.grill/triage-evidence/sgd-45-constitution.md,.grill/triage/tri-sgd-45-worker-worktree-orca.json
- reproduction: 38b161d: _workspace_identity cria worker em <git-common-dir>/grill/wt-*; probe live orca terminal create: .git/grill e irmão fora de .git -> orphaned=true; <main>/.claude/worktrees -> orphaned=false; consumidor hermes-k3s run-36d38a82957edb29aac4c315 converge SESSION-CLOSE-UNPROVEN
- evidence: .grill/triage-evidence/sgd-45-debug-report.md; triage tri-sgd-45-worker-worktree-orca; backlog SGD-45
- correction-test: test_prepare_pins_base_and_derives_only_the_declared_branch_and_key exige worktree em <main>/.claude/worktrees, fora do git-common-dir, com status do checkout inalterado; test_worker_worktree_identity_keeps_a_legacy_path_for_resume cobre retomada; ambos reprovam em 38b161d
- rollback: Reverter o commit do hotfix 9.3.1 em main e republicar 9.3.0 pela tag imutável v9.3.0; worktrees criados em .claude/worktrees continuam registrados e são removidos por git worktree remove; a linha /.claude/worktrees/ em info/exclude é inofensiva
- constitution-evidence: {"path": ".grill/triage-evidence/sgd-45-constitution.md", "sha256": "2f60aef641431d66097ef547297c12ac7a08122308f0078987a2513985d6e547"}
- test-command: python3 tests/validate_gauntlet_run_contract.py

## Delivery boundary

HOTFIX-GO requires the separate hotfix-go revalidation step. Reconciliation and full documentary audit are post-ship.

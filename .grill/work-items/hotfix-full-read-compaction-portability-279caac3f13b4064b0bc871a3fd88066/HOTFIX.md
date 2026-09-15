# HOTFIX-PREPARED

- scope: .gitattributes,.github/workflows/ci.yml,plugin/skills/grill-with-docs/scripts/grill_core/agent_runtime.py,tests/validate_agent_orchestration_contract.py,tests/validate_distribution.py,plugin/.claude-plugin/plugin.json,plugin/.codex-plugin/plugin.json,.claude-plugin/marketplace.json,.agents/plugins/marketplace.json,plugin/skills/grill-with-docs/SKILL.md,plugin/skills/grill-with-docs/references/session-protocol.md,README.md,CHANGELOG.md,.grill/triage-evidence/hotfix-6-0-1-debug-report.md,.grill/triage-evidence/hotfix-6-0-1-constitution.md,.grill/triage/tri-hotfix-6-0-1.json
- reproduction: 29c9668: _full_read aceita cat -- anterior a bloco compaction; sessão Claude 064b802e pós /compact deu preflight OK com event_ref 92ae25c6 anterior. TMPDIR symlink reproduz 3 FAIL macOS; fixture SKILL.md em CRLF reproduz FAIL Windows STYLE-CONTENT-INCOMPATIBLE.
- evidence: .grill/triage-evidence/hotfix-6-0-1-debug-report.md; triage tri-hotfix-6-0-1; CI runs 35009700240 e 35018334831
- correction-test: test_exact_native_commands_and_envelope: leitura seguida de compaction -> None, releitura após compaction -> aceita; macOS CI validate_agent_orchestration_contract 32 OK; Windows CI smoke OK
- rollback: Reverter o commit do hotfix 6.0.1 em main e republicar 6.0.0 pela tag imutável v6.0.0; nenhum estado persistente muda de formato
- constitution-evidence: {"path": ".grill/triage-evidence/hotfix-6-0-1-constitution.md", "sha256": "4e0395651f8e447be30e2d563c3b9578d7d5d83c69a0737a643be88fdb3ff0b1"}
- test-command: python3 tests/validate_agent_orchestration_contract.py

## Delivery boundary

HOTFIX-GO requires the separate hotfix-go revalidation step. Reconciliation and full documentary audit are post-ship.

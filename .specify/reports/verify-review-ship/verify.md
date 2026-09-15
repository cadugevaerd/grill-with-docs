## Verify Report

Verdict: BLOCKED
Source fingerprint: tree d2bc46ea86c1cfb3bef33de0acdb37286b4bc3cce9dc2c5eda31e1700ae5fb81 / work e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 / plan 910bd12d2dca46423c22cb0da70192f9c8811819d4dd72e916b2897a755ab6a6
Converge: BLOCKED

### Operational Gates

| Gate | Command | Result | Evidence | Validator |
|---|---|---|---|---|
| full validators | `PYTHONDONTWRITEBYTECODE=1 python3 -B tests/run_validators.py` | PASS | 30 validators, 1476 tests, final `OK (skipped=1)`, `EXIT:0`; `/tmp/gwd-full-validators-ab52268.log` | leader |
| focused orchestration contract | `PYTHONDONTWRITEBYTECODE=1 python3 -B tests/validate_agent_orchestration_contract.py` | PASS | 32 tests, OK | leader |
| distribution | `PYTHONDONTWRITEBYTECODE=1 python3 -B tests/validate_distribution.py` | PASS | `distribution: OK` in canonical suite | leader |
| Claude live style load | supervised Claude session on `ab52268` | PASS for loading axis | `STYLE-LIVE-VALIDATION.md`: second preflight `OK`, `loading=loaded`, `use_ready=true`, `work_ready=true`, approved SHA | Claude worker + independent high review |
| Codex live style matrix | fresh Codex session | BLOCKED | hosted primary `gpt-5.6-luna` hit `usage_limit_exceeded`; Luna Reserve TUI and direct CLI probes completed and loaded GWD+i-have-adhd, then canonical GWD blocked on `LEADER-ADAPTER-UNSUPPORTED`/`BACKLOG-UNAVAILABLE`; supervised Orca Reserve retry and pre-open Luna terminal both failed at `agent_readiness: codex-interactive-prompt` (selection also `agent_prompt_blocked`); local Ollama probe did not run canonical GWD/matrix | Codex runtime |

### Diff Hygiene

Worktree clean at `ab52268` lineage; no secrets or environment files added. Documentation evidence is excluded by the configured fingerprint rules where applicable.

### Executable Scenarios

T028/T029/T030 remain unchecked. Claude evidence covers only automatic loading; Luna Reserve covers a real Codex turn and bootstrap loading, while behavior, compactation, suspension, external control, canonical GWD entry with Orca authority, and the Codex matrix remain unproven.

### Failures / Blockers

- Official Converge cannot return `CONVERGED` while T028/T029/T030 are pending.
- Codex primary hosted capacity is unavailable by external quota. Luna Reserve is usable for a model turn but its canonical GWD attempt lacked Orca authority/backlog, so it does not prove FR-024/SC-008. The local OSS transcript proves only a Codex CLI turn; installed cache presence and offline preflight remain insufficient.

### Next Action

Wait for Codex quota recovery, execute the complete two-runtime quickstart matrix with a fresh supervised Codex session, obtain independent high review, then rerun Converge, Verify, Review, and Ship. Do not publish from this report.

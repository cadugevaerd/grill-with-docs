---
description: "Run post-convergence executable gates and diff hygiene checks"
---

# Verify Gate

Run only after the official `/speckit.converge` reports `Converged`. This command proves the current implementation is executable; it does not decide whether implementation fulfills the feature intent.

## User Input

$ARGUMENTS

## Converge Handoff (Required)

Require evidence from the current host session/history that official `/speckit.converge` ran after the latest `/speckit.implement`.

```text
Outcome: converged | tasks_appended | unavailable
Source fingerprint: reviewed-scope tree hash + uncommitted diff hash + tasks.md hash
Evidence source: official command result in the current session/history
```

- `tasks_appended`: return `VERIFY: BLOCKED`; run `/speckit.implement`, then `/speckit.converge` again.
- `unavailable`, missing, ambiguous, or stale evidence: return `VERIFY: BLOCKED`; run `/speckit.converge` again.
- Capture the current source fingerprint in this report, computed as defined in **Source Fingerprint (Canonical)** below. A changed fingerprint makes the report stale; a report written or committed by these gates MUST NOT change it.

The official Converge command owns spec/plan/tasks-to-code completeness. This command **must not reconstruct the intent inventory** and **must not repeat spec-to-code completeness analysis**. Do not enumerate FRs, acceptance scenarios, plan decisions, or tasks as an independent pass/fail ledger.

## Source Fingerprint (Canonical)

The fingerprint identifies the **reviewed content**, never the commit that recorded a gate
report. It is computed by `scripts/source-fingerprint.sh`, which is the single implementation —
do not restate the algorithm in prose:

```bash
scripts/source-fingerprint.sh <feature-dir> [config.yml]
```

It emits the three components and the combined value:

```text
tree <sha256>          committed and staged content of the reviewed scope
work <sha256>          uncommitted changes AND untracked files in that scope
plan <sha256>          the feature's tasks.md
fingerprint <tree>-<work>-<plan>
```

Report the three components, not only the combined value, so a mismatch says which part moved.

**Exclusions come from `converge.fingerprint_exclude`** in the extension configuration, so the
published setting and the algorithm share one effective set. The script falls back to its
documented defaults only when the key is absent. A project that stores gate reports elsewhere
changes the configuration, not the script; a report path inside the fingerprint reintroduces the
defect below.

**Why `HEAD` is not part of it.** Verify and Review are told to write their reports into the
repository. Committing a report changes `HEAD` without changing anything that was reviewed, so a
`HEAD`-based fingerprint invalidates itself between two gates of the same run and forces
`BLOCKED` on work that never moved.

**Why untracked files are part of it.** `git diff HEAD` does not see a file that was never
added. An implementation delivered as a new, unstaged file would otherwise be invisible to the
fingerprint, letting unreviewed content pass a matching-evidence check.

## Scope Discovery

Resolve repository root, active feature, extension configuration, current diff, CI/task-runner/manifests, quickstart, executable contracts, and available project gates. Missing executable context or a forbidden gate is `BLOCKED`; an absent optional gate is `SKIPPED` with evidence.

## Execution

Discover workers/subagents when supported; otherwise use sequential fallback. Assign at most one read-only validator to each independent executable gate or hygiene item. Validators never edit, stage, commit, deploy, or decide the verdict.

Run safe canonical gates in this order when applicable: tests, build, lint, typecheck, format, security, quickstart/contracts, and required manual gates. Record exact command, result, evidence, and validator.

Inspect diff hygiene: changed/generated/unrelated files, accidental secrets or environment files, and whether executable scenarios have supporting tests. Never stage or commit.

## Report

Write when allowed to `.specify/reports/verify-review-ship/verify.md` and the active feature directory.

```markdown
## Verify Report

Verdict: PASS | FAIL | BLOCKED
Source fingerprint: tree <sha> / work <sha> / plan <sha>   (gate reports excluded)
Converge: CONVERGED | STALE | MISSING | TASKS_APPENDED

### Operational Gates
| Gate | Command | Result | Evidence | Validator |

### Diff Hygiene
### Executable Scenarios
### Failures / Blockers

### Next Action
- PASS: run `/speckit.verify-review-ship.review`
- FAIL/BLOCKED: fix the listed operational issue; if code or Spec Kit artifacts changed, rerun `/speckit.converge` first.
```

## Decision Rules

`PASS` requires fresh `CONVERGED` evidence and every mandatory executable gate passing. Never infer a gate pass from another result. A source change invalidates the report.

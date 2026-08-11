---
description: "Review technical risk after Converge and Verify evidence"
---

# Review Gate

Run after `/speckit.verify-review-ship.verify` with a fresh `PASS` report.

## User Input

$ARGUMENTS

## Boundary with Official Converge

`/speckit.converge` owns whether the current code fulfills `spec.md`, `plan.md`, and `tasks.md`. This review owns technical quality and risk in the current diff.

This command **must not repeat requirement, task, or plan completeness** analysis and **must not perform a Constitution item-by-item audit**. A real technical finding may cite an applicable Constitution rule, but the rule is not independently re-audited here.

## Required Evidence

1. Consume fresh Converge `CONVERGED` and Verify `PASS` evidence with matching source fingerprints, computed per **Source Fingerprint (Canonical)** in `verify`. Gate reports are excluded from the fingerprint, so committing `verify.md` before this command MUST NOT be treated as stale evidence.
2. Inspect current diff, tests, generated artifacts, and explicitly requested PR/branch/commit/files.
3. If evidence is missing or stale, return `BLOCKED` with the safe resume command.

## Review Ledger

Discover review workers when supported; otherwise use sequential fallback unless configuration requires workers. One read-only reviewer per independent item:

- test quality and behavioral coverage;
- runtime correctness: boundaries, errors, concurrency, state transitions, migrations/data changes;
- readability;
- architecture and dependency direction;
- security;
- performance;
- explicitly requested scope not already covered.

Reviewers return exact file:line or gate evidence, severity, and a concrete fix for Critical/Important findings. They never edit, stage, commit, deploy, or decide the verdict.

## Decision Rules

- `Critical` blocks ship.
- `Important` requires a fix before ship.
- A meaningful behavior change without adequate tests defaults to `REQUEST CHANGES`.
- Constitution is cited only when a discovered technical finding conflicts with it; missing Constitution alone does not trigger a duplicate audit.

## Report

```markdown
## Review Report

Verdict: APPROVE | REQUEST CHANGES | BLOCKED
Source fingerprint: tree <sha> / work <sha> / plan <sha>
                    (must match Converge and Verify; computed by scripts/source-fingerprint.sh)

### Test Quality
### Runtime Correctness
### Readability
### Architecture
### Security
### Performance

### Critical Issues
### Important Issues
### Constitution References (only for discovered conflicts)

### Final Recommendation
- APPROVE: run `/speckit.verify-review-ship.ship`
- REQUEST CHANGES: fix, run `/speckit.converge`, then verify and review again
- BLOCKED: supply fresh prerequisite evidence
```

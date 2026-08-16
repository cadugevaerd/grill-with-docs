# Quickstart: Convergência, Revisão e Entrega Verificável (FASE-004)

## Scope of this document

FASE-004 adds `gauntlet-converge` and `gauntlet-run-abandon`, extends `gauntlet-wave-declare` (scope-overlap rejection at declaration, DAG-pin write/revalidation), extends `checkpoint --step ship` (a `CONVERGENCE-INCOMPLETE` gate), and extends `gauntlet-status` (a compact `waves` projection). All implemented, wired into `grill_workspace.py`, and covered by `tests/validate_gauntlet_converge_contract.py`. This document covers the full FASE-001/002/003/004 command surface additively; for the formal per-command contract, see `specs/014-converge-review-ship/contracts/gauntlet-converge-cli.md`.

## Prerequisites

Same as FASE-001/002/003: a current FASE-001 activation, a local Git repository with an immutable base commit, Python 3.10+.

## `review` needs no new command

`review` is one of the eleven macro-steps already dispatched by the unmodified FASE-001/003 mechanism, at `TIER_POLICY["review"] == "large"`. A `blocked` checkpoint on it already halts `ship` via the existing step-sequence gate (`checkpoint_command`) — this phase adds a second, independent reason `ship` can be unreachable (convergence incompleteness), never a replacement for the first.

## `gauntlet-converge` — integrate a wave's successful workers

```bash
python3 plugin/skills/grill-with-docs/scripts/grill_workspace.py \
  gauntlet-converge . --work-id <work-item-id> --run-id <run-id> \
  --dag specs/<feature>/execution-dag.json --wave-id wave-0001
```

Verdicts: `WAVE-CONVERGED` (with the list of `node_id`s merged this call), or `WAVE-CONVERGED-REUSED` for an idempotent replay of an already-converged wave — including the wave whose convergence already completed the run. Named blocks, checked in this fixed order: `RUN-NOT-ELIGIBLE` (run `BLOCKED`, or `COMPLETE` with a `--wave-id` other than the one that completed it), `DAG-PIN-MISSING`/`DAG-CONTENT-MISMATCH`, `EXECUTION-BRANCH-UNSET`/`-MISMATCH`, `EXECUTION-TREE-DIRTY`, `WAVE-CONVERGENCE-OUT-OF-ORDER`, `INTEGRATION_CONFLICT` (reason `scope-overlap` or `content-conflict`, recorded in the wave's `last_conflict`). Only lineage-heads in `state == "TERMINAL"` (success) are ever merged or counted toward a wave's `converged` flag — a permanently `FAILED`/`STALLED` sibling never blocks its wave's other members from converging, but the wave itself never reaches `converged: true` while it remains unresolved (see `gauntlet-run-abandon`, below).

Never resolves a conflict automatically (ADR-0021/ADR-0022) and never pushes or releases (ADR-0002) — resolution is always a human act or a new specification.

## `gauntlet-wave-declare` (FASE-003, extended)

Unchanged inputs/outputs, plus two new fail-closed boundaries: `WAVE-SCOPE-OVERLAP` (the same DAG-`files` overlap check `gauntlet-converge`'s own pre-pass uses, now applied at declaration — the primary defense, making the converge-time check residual and reachable only via direct Store injection); `DAG-PIN-MISSING`/`DAG-CONTENT-MISMATCH` (the run's DAG content hash is pinned on the first real wave and revalidated on every subsequent call).

## The ship gate: `checkpoint --step ship --state complete`

Unchanged entry point (`grill_workspace.py`), one new check inserted after the existing step-sequence gate and before the attestation gate: if any run gauntlet V3 admitted for the work item has `state` outside `{COMPLETE, BLOCKED}`, blocks `CONVERGENCE-INCOMPLETE` naming it. A work item with no admitted run, or only terminal ones, is unaffected (no-op) — this phase never makes a gauntlet run mandatory.

## `gauntlet-run-abandon` — the one human act that can close a permanently-stuck run

```bash
python3 plugin/skills/grill-with-docs/scripts/grill_workspace.py \
  gauntlet-run-abandon . --work-id <work-item-id> --run-id <run-id> \
  --attestation path/to/human-authorization-bundle.json
```

Requires a genuine `human-authorization/v1` bundle — the same 6-key schema `attestation.py` already validates for `ship` (`schema`, `scope` = the target `run_id`, `decision: APPROVED`, `authorized_by`, `receipt_ref`, `content_sha256`) — never free text. This is honestly an **attributional**, not preventive, barrier (`attestation.py` documents this bundle as "accepted but never inspected" by the cryptographic chain that gives `ship`'s own gate its real teeth); the value is a deliberate, attributable act instead of a one-line excuse, and the bundle is recorded verbatim, not just hashed, so it stays recoverable.

Verdicts: `RUN-ABANDONED` (first call), `RUN-ABANDON-REUSED` (byte-identical resubmission against an already-`BLOCKED` run). Blocks: `ABANDON-AUTHORIZATION-INVALID` (missing/malformed/unapproved bundle), `RUN-NOT-ELIGIBLE` (a divergent resubmission, or the run is already `COMPLETE`). Deliberately exempt from the current-activation admission boundary — it derives identity from the *target run's own recorded* `admission`, never the live one, because its entire purpose is unsticking a run from an older generation than the one currently active (ADR-0020).

## `gauntlet-status` (extended)

Gains a `waves` list (`wave_id`, `state`, `converged_count`, `member_count`, excluding the internal bootstrap placeholder) and, if any real wave has an unresolved `last_conflict`, its `node_ids`/`reason` (never fingerprints, never raw `events.jsonl`, never worker diff content) — surfaced from the correct wave even when it isn't the newest one (the exact scenario a newer wave declared while an older one's conflict is still open).

## Compatibility

A work item with no gauntlet run at all, or only `COMPLETE`/`BLOCKED` ones, is unaffected by any new gate — V2 items included. FASE-001/002/003's existing command surface (`gauntlet-init`, `gauntlet-run`, `gauntlet-resume`, `gauntlet-prepare-worker`, `gauntlet-cleanup`, `gauntlet-dag-validate`, `gauntlet-worker-declare`, `gauntlet-progress-record`, `gauntlet-worker-terminal`, `gauntlet-remediate`) keeps its current behavior unchanged.

## Architectural correction landing with this phase (ADR-0023)

`_run_for_worker` (the shared identity guard every mutating gauntlet command calls) now compares only the four planning-identity hashes (`activation_sha256`, `work_item_sha256`, `workflow_sha256`, `config_sha256`) against the run's recorded admission — never `base_commit`. `gauntlet-converge` advances `HEAD` on purpose as it merges; before this correction, the very next `gauntlet-wave-declare` (or any other mutating command) after a successful convergence would have blocked `IDENTITY-STALE`, because `base_commit` is recomputed live from `HEAD` on every call. `base_commit` itself is unchanged as the run's fixed anchor for worktree creation and worker dispatch — this correction only removes it from the *staleness* comparison, restoring the natural declare → execute → converge → declare-the-next-wave flow this phase exists to enable.

# Data Model: Durable Gauntlet Runs

## Gauntlet Run Block

| Field | Type | Validation |
|---|---|---|
| `schema` | string | Exactly `grill-gauntlet-runs/v1`. |
| `runs` | object | Safe run IDs map to closed run records; no unknown keys. |

## Run Record

| Field | Type | Validation |
|---|---|---|
| `admission.activation_sha256` | string | Hash of the current matching activation record. |
| `admission.work_item_sha256` | string | Hash of current V3 work item bytes. |
| `admission.workflow_sha256` | string | Hash of accepted V3 workflow bytes. |
| `admission.config_sha256` | string | Hash of current project Gauntlet configuration. |
| `admission.base_commit` | string | Existing immutable 40-hex Git commit. |
| `state` | enum | `ADMITTED`, `RECOVERY_ELIGIBLE`, `RECOVERY_RECORDED`, `BLOCKED`, or `COMPLETE`. |
| `recovery_count` | integer | Exactly 0 or 1. |
| `waves` | object | Correlation labels only; no scheduler selection or progress execution. |
| `workers` | object | Safe worker IDs map to closed worker records. |
| `last_transition` | object | Existing event sequence and immutable receipt hash. |

## Worker Record

| Field | Type | Validation |
|---|---|---|
| `state` | enum | `DECLARED`, `PREPARING`, `PREPARED`, `CLEANING`, `CLEANED`, `ORPHANED`, `RECOVERY_ELIGIBLE`, `RECOVERY_RECORDED`, `FAILED`, `STALLED`, `BLOCKED`, `CONFLICT`, or `TERMINAL`. |
| `lease` | object/null | Coordinator-owned ID, positive fencing token, timestamps, state, and recovery count at most one. |
| `grant.scope_paths` | array | Unique non-empty project-relative paths; no `..`, absolute, or host path. |
| `grant.capabilities` | array | Exact subset of `git-local`, `workspace-read-write`; no Store, dispatch, network, push, ship, release, or credential authority. |
| `workspace.worktree_key` | string | Safe logical key, not a raw filesystem path. |
| `workspace.branch` | string | Exact derived child branch for its work item/run/worker. |
| `workspace.base_commit` | string | Equals run admission base commit. |
| `workspace.clean` | boolean | Recorded current cleanup predicate. |
| `workspace.converged` | boolean | False until an authorized later phase records it. |
| `workspace.cleanup_eligible` | boolean | False until all authorized conditions are recorded. |

## Transition Correlation

Every material transition contains: `work_id`, `run_id`, `wave_id`, `base_commit`, `receipt_sha256`, `input_sha256`, and `output_sha256` (nullable only for a transition with no output). Worker transitions additionally contain `worker_id`, `lease_id`, and positive `fencing_token`.

## State Transitions

```text
absent -> ADMITTED -> RECOVERY_ELIGIBLE -> RECOVERY_RECORDED
                              |                    |
                              +-> BLOCKED           +-> BLOCKED

worker DECLARED -> PREPARING -> PREPARED -> TERMINAL -> CLEANING -> CLEANED
                    |             |             |             |
                    +-> ORPHANED  +-> FAILED/STALLED/BLOCKED/CONFLICT (preserved)
                                  +-> ORPHANED    +-> ORPHANED
```

`PREPARING` and `CLEANING` are durable intents, not completed Git effects. The matching command may reconcile only the exact derived target after interruption; `ORPHANED` is preserved and never auto-deleted. No transition starts a worker, selects a future wave, performs retry/relaunch, converges changes, or emits approval.

# Gauntlet Scheduler CLI Contract — FASE-003

All commands emit one JSON object. Domain denial returns `{"verdict":"BLOCKED","code":"SCREAMING-KEBAB"}` and leaves authoritative state unchanged unless the command reports a successful recorded transition. Every command below also inherits FASE-002's common admission boundary (`gauntlet_run_admission`): a stale or missing FASE-001 activation blocks `ACTIVATION-REQUIRED`/`IDENTITY-STALE`, a V2 work item blocks `WORKFLOW-INCOMPATIBLE`, and an unavailable Git base commit blocks `BASE-COMMIT-UNAVAILABLE`, before any command-specific logic runs.

## `gauntlet-dag-validate ROOT --work-id ID --run-id ID --dag PATH`

```json
{"verdict":"DAG-VALID","work_id":"ID","run_id":"run-<opaque-id>","max_workers":5,"nodes":[{"id":"T001","depends_on":[],"parallel":true,"tier":"medium"}]}
```

`--dag` is a repo-relative path validated by the same escape-proof rule `_strict_scopes` uses. The command is pure/stateless: it proves the current activation and a real Git base commit, loads and validates the named Execution DAG, and touches no run/wave/worker Store state — `run_id` is accepted and echoed for the caller's own correlation only. It fails closed, in order: `DAG-MALFORMED` (schema/shape, duplicate or unsafe node `id`, a node `id` matching the reserved `-r<digits>` remediation suffix, unknown `depends_on` reference), `DAG-CYCLIC`, `DAG-NODE-OUT-OF-SCOPE` (a node's `files` contains a `.specify/reports/` segment or a `.grill` segment at any depth), or `DAG-NODE-TIER-UNRESOLVED` (a node's declared tier is below the `agent-execute` floor, `medium`, unless its files are exclusively Markdown, floor `small`). Idempotent and safe to re-run; `gauntlet-wave-declare` re-runs this exact check inline rather than trusting a prior call.

## `gauntlet-wave-declare ROOT --work-id ID --run-id ID --dag PATH --node-id ID [--node-id ID ...]`

```json
{"verdict":"WAVE-DECLARED","work_id":"ID","run_id":"run-<opaque-id>","wave_id":"wave-0001"}
```

`--node-id` repeats, one per node the caller wants in this wave. The command re-validates the whole DAG inline (identical to `gauntlet-dag-validate`), re-checks each named node's dependencies against the run's current Store state (must all be terminal), and requires a `parallel:false` node to be the sole name in the request. It allocates the next `wave-XXXX` id only if the run's current wave, if any, is already `COMPLETE`; declaring against an already-`ACTIVE` current wave always blocks `WAVE-PREREQUISITE-INCOMPLETE` — there is no `WAVE-REUSED` fallback for that case; the wave's Store record persists the declared `node_ids`, so a retry with a *different* node set against an in-flight wave is a real, distinguishable conflict, not silently reused. `WAVE-REUSED` (same JSON shape, `"verdict":"WAVE-REUSED"`) fires only from an actual concurrent-transaction race that lands on the same target wave identity with the same `node_ids`. Other blocks: `WAVE-NODES-REQUIRED`/`INVALID-IDENTIFIER` (empty or malformed `--node-id` list), `WAVE-NODE-UNKNOWN` (names a node absent from the DAG), `WAVE-NODE-NOT-PARALLEL`, `WAVE-NODE-NOT-READY` (a named node's dependency is not yet terminal), `WAVE-CAP-EXCEEDED` (existing non-terminal workers plus this request would exceed the effective cap — the lesser of the activation-configured worker cap and the DAG's own `max_workers`), and (Store-level, defensive) rejection of an out-of-sequence or wrongly-initialized `wave_id` if ever reached outside this command's own allocation logic.

**Wave Store record:** `{"state": "DECLARED"|"ACTIVE"|"COMPLETE", "node_ids": [...]}` — `node_ids` is written once at declaration and immutable thereafter (same immutability class as everything else about a superseded wave). `gauntlet-worker-terminal` uses it directly to detect wave completion: every name in `node_ids` must have a worker record whose current lineage-head is terminal. No public command exposes `node_ids` directly; it is not part of `gauntlet-status`'s projection (see below) — only `gauntlet-wave-declare`'s own success/`WAVE-REUSED` response confirms the set that was accepted.

**Breaking change to `gauntlet-prepare-worker` (F1, operator-approved):** that FASE-001/002 command now applies the same `.specify/reports/`- and `.grill`-segment scope rejection this command's own `--files` argument enforces, unconditionally, to its `--scope` argument — see `DECISION-BACKLOG.md` BL-0002. A `--scope` path that previously succeeded and touches either rule now blocks `GRANT-OUT-OF-SCOPE`.

## `gauntlet-worker-declare ROOT --work-id ID --run-id ID --wave-id ID --node-id ID --tier TIER --files PATH [--files PATH ...]`

```json
{"verdict":"WORKER-PREPARED","work_id":"ID","run_id":"run-<opaque-id>","worker_id":"T001","worktree_key":"wt-<run-id>-T001","base_commit":"<40-hex>"}
```

First-dispatch only — remediation dispatch is `gauntlet-remediate`, below, and this command takes no `--remediates`-shaped input at all. `worker_id` is set to `--node-id` verbatim. `--wave-id` must name a wave of this run that is currently `ACTIVE` (`WAVE-NOT-FOUND` otherwise). `--tier` must satisfy FR-006's floor for the declared `--files` (`DAG-NODE-TIER-UNRESOLVED` otherwise); a `--node-id` using the reserved `-r<digits>` remediation suffix blocks `INVALID-IDENTIFIER`. This is a thin named entry over the existing `prepare_worker` intent protocol (`DECLARED → PREPARING → git worktree add → PREPARED`) and inherits that function's exact verdict vocabulary and every one of its boundaries (`WORKER-CONFLICT`, `WORKSPACE-PRESERVED`, `LEASE-INVALID`, `WORKTREE-CREATE-FAILED`, `GIT-UNAVAILABLE`, `GRANT-INVALID`).

**Divergence from `plan.md`'s original design:** plan.md's command-surface table proposed `WORKER-DECLARED`/`WORKER-REUSED` as this command's verdicts. The actual implementation reuses `prepare_worker` verbatim, whose verdicts are `WORKER-PREPARED` (first successful declaration) and `REUSED` (an idempotent repeat of an already-`PREPARED` worker with an identical grant) — the same vocabulary `gauntlet-prepare-worker` (FASE-002) already uses. A `REUSED` response omits `worktree_key`/`base_commit`.

## `gauntlet-progress-record ROOT --work-id ID --run-id ID --worker-id ID`

```json
{"verdict":"PROGRESS-RECORDED","work_id":"ID","run_id":"run-<opaque-id>","worker_id":"T001","expires_at":"<iso8601>"}
```

Requires the named worker in `PREPARED` (`WORKER-NOT-FOUND`/`WORKER-NOT-PREPARED` otherwise) with a valid coordinator lease (`LEASE-INVALID`). Renews `lease.expires_at` to `<record time> + LEASE_DURATION` (the same fixed one-hour grant length as the original lease, FASE-002's `timedelta(hours=1)`, not a new constant) — from now, not from the old expiry — so a worker producing genuine progress past its original lease window is never treated as expired solely because that window elapsed.

## `gauntlet-worker-terminal ROOT --work-id ID --run-id ID --worker-id ID --outcome {completed|failed} [--failure-class {process-timeout|transport-failure}]`

```json
{"verdict":"WORKER-TERMINAL","work_id":"ID","run_id":"run-<opaque-id>","worker_id":"T001","state":"TERMINAL"}
```

A `failed` outcome additionally returns `"state":"FAILED","failure_class":"process-timeout"`. `--failure-class` is required if and only if `--outcome failed` (`INVALID-ARGUMENTS` if supplied for `completed`; `FAILURE-CLASS-REQUIRED` if missing or not in the closed set for `failed`). Requires the worker in `PREPARED` (`WORKER-NOT-FOUND`/`WORKER-NOT-PREPARED` otherwise). Frees the worker's concurrent-cap slot regardless of outcome (neither `TERMINAL` nor `FAILED` is a non-terminal state). The classification is recorded as evidence baked into the transition's own immutable receipt name (Store's event/receipt schemas are closed with no spare field for it) — `gauntlet-status` and `gauntlet-remediate --reason transient-failure` both read it back from there, never from a caller-asserted flag on a later call. In the same transaction, if this was the last of the current wave's member nodes to reach a terminal state, the wave itself transitions to `COMPLETE`.

## `gauntlet-remediate ROOT --work-id ID --run-id ID --worker-id ID --reason {stall|transient-failure}`

```json
{"verdict":"REMEDIATION-RECORDED","work_id":"ID","run_id":"run-<opaque-id>","worker_id":"T001-r1","remediates":"T001","recovery_count":1,"worktree_key":"wt-<run-id>-T001-r1","base_commit":"<40-hex>"}
```

One Store transaction does lookup and mint together — no separate advisory step, closing the TOCTOU gap a split design would leave open. `--reason stall` requires the named worker still `PREPARED` (`WORKER-NOT-PREPARED`) and is Store-verified idle — no progress transition since dispatch or the last recorded one — for at least the run's activation-configured stall window (`STALL-NOT-ELIGIBLE` otherwise; the window itself is not a CLI flag, it is read from the pinned activation record, `limits.stall_minutes`). `--reason transient-failure` requires the named worker already `FAILED` via `gauntlet-worker-terminal` (`WORKER-NOT-FAILED` otherwise) with a classification re-derived from the coordinator's own immutable receipt and re-checked against the closed transient set (`FAILURE-CLASS-NOT-TRANSIENT` if it is not — never a bare caller-asserted flag). Either reason: the same transaction scans the run's workers for any entry sharing this worker's `node_id` lineage with `lease.recovery_count == 1`; if found, it blocks `REMEDIATION-BUDGET-SPENT` and mints nothing, regardless of which reason triggered the call — a node cannot chain remediation by alternating reasons. Otherwise it mints `<node_id>-r<n>` with `recovery_count` already `1` and `remediates` set to the replaced worker, then drives the same `PREPARING → git worktree add → PREPARED` sequence as first dispatch.

## `gauntlet-status ROOT --work-id ID [--run-id ID]` (extended)

```json
{"verdict":"STATUS","work_id":"ID","activation_state":"ACTIVATED","run":{"run_id":"run-<opaque-id>","state":"ADMITTED","workers":[{"worker_id":"T001","state":"PREPARED","lease":{},"grant":{},"failure_class":null}]}}
```

Read-only; unchanged failure modes from FASE-002. The only FASE-003 addition to this projection is `failure_class` on each `run.workers[]` entry — `null` unless that worker is `FAILED` with a classification recovered from its own immutable termination receipt (see `gauntlet-worker-terminal`).

**Divergence from `plan.md`'s original design:** plan.md's command-surface table described this row as gaining "wave/worker/remediation-budget state" broadly. The shipped projection does not add a `waves` collection, and does not add `node_id` or `remediates` to a worker entry — `run_projection`/`project_run` in `gauntlet_runs.py` returns only `run_id`, `state`, `recovery_count`, `base_commit`, `workers` (`worker_id`, `state`, `lease`, `grant`, `failure_class`), and `last_transition`. Wave state, node lineage, and remediation-budget occupancy are not observable through this public command; they are recoverable only from the raw Store snapshot or the journal, which `gauntlet-status` does not expose.

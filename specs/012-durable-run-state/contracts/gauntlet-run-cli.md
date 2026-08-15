# Gauntlet Run CLI Contract — FASE-002

All commands emit one JSON object. Domain denial returns `{"verdict":"BLOCKED","code":"SCREAMING-KEBAB"}` and leaves authoritative state unchanged unless the command reports a successful recorded transition.

## `gauntlet-run ROOT --work-id ID`

```json
{"verdict":"RUN-CREATED","work_id":"ID","run_id":"run-<opaque-id>","base_commit":"<40-hex>"}
```

A repeat with identical current admission returns `RUN-REUSED` with the same `run_id` and no revision, event, or receipt churn. It never creates a worker, worktree, process, dispatch, or skill invocation.

## `gauntlet-status ROOT --work-id ID [--run-id ID]`

```json
{"verdict":"STATUS","work_id":"ID","activation_state":"ACTIVATED","run":{"run_id":"run-<opaque-id>","state":"ADMITTED","workers":[]}}
```

The command is read-only. A status subject failure preserves the FASE-001 top-level/projection distinction; a requested unknown run uses a named reason and never invents a run.

## `gauntlet-resume ROOT --work-id ID --run-id ID`

```json
{"verdict":"RESUME-RECORDED","work_id":"ID","run_id":"run-<opaque-id>","recovery_count":1}
```

Only a current activation and one explicitly eligible recorded lease can produce this result. Equivalent repeat returns `RESUME-REUSED`. The command does not execute, replace, relaunch, retry, or dispatch a worker.

## `gauntlet-prepare-worker ROOT --work-id ID --run-id ID --worker-id ID --scope PATH`

```json
{"verdict":"WORKER-PREPARED","work_id":"ID","run_id":"run-<opaque-id>","worker_id":"worker-a","worktree_key":"wt-<opaque-id>-worker-a","base_commit":"<40-hex>"}
```

The command creates only one isolated derived worktree and a closed passive grant. It rejects path traversal, duplicate/incompatible workers, stale identity, unsafe Store/Git state, and unsupported capabilities before mutation. It never starts a worker.

## `gauntlet-cleanup ROOT --work-id ID --run-id ID --worker-id ID`

```json
{"verdict":"CLEANED","work_id":"ID","run_id":"run-<opaque-id>","worker_id":"worker-a"}
```

Only a clean, terminal, converged, recorded-eligible exact worker may be removed. Failed, stalled, blocked, conflicting, dirty, missing, or mismatched workers return `PRESERVED` or `BLOCKED`; no other workspace may be removed.

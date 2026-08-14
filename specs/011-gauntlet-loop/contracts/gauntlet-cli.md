# Gauntlet CLI Contract — FASE-001

All commands write exactly one JSON object to stdout and no unstructured diagnostic text. Domain failures use the existing CLI exit categories.

## `migrate-v3 ROOT --work-id ID --rebind-workflow [--apply]`

Without `--apply`, the command is a no-write preview:

```json
{"verdict":"PREVIEW","work_id":"ID","operation":"rebind-workflow","from_workflow_sha256":"<sha256>","to_workflow_sha256":"<sha256>"}
```

With `--apply`, it returns `APPLIED` after a current V3 workflow gate, no-follow work-item descriptor, and `WORK-ITEM.json` CAS check. A repeated matching rebind returns `REUSED`. The operation changes only the immutable workflow binding and dependent hashes, preserves unrelated top-level fields and the original file mode, and uses descriptor-relative replacement. V2 workflow, invalid V3 input, stale CAS, unavailable safe descriptors, or mode-restoration failure return `BLOCKED` with a precise kebab-case code and leave the prior document unchanged.

## `gauntlet-init ROOT --work-id ID --max-workers N`

```json
{"verdict":"ACTIVATED","work_id":"ID","config":".grill/gauntlet.yaml","max_workers":3,"stall_minutes":15,"runtime":"claude"}
```

Equivalent repeat returns `REUSED`; a differing selected worker value or immutable identity returns `BLOCKED` with code `ACTIVATION-CONFLICT`. V2, unproven runtime, invalid catalog, invalid V3 workflow, malformed config, symbolic link, and concurrent divergent input return a named block before any configuration write. A successful call may mutate only `.grill/gauntlet.yaml`.

## `gauntlet-status ROOT --work-id ID`

```json
{"verdict":"STATUS","work_id":"ID","activation_state":"ACTIVATED"}
```

`activation_state` is exactly `ELIGIBLE`, `ACTIVATED`, `STALE`, or `BLOCKED`. `STALE` and `BLOCKED` include `reason`. `{"verdict":"STATUS","activation_state":"BLOCKED"}` is a successful read-only projection, not a command failure; command failures instead use `{"verdict":"BLOCKED","code":"..."}`. It never writes.

Invalid arguments, an invalid/non-Git root, missing/invalid work item, or a module-load failure before a valid status subject exists use the top-level `BLOCKED` command form. After the root and work item are valid, workflow, catalog, configuration, safe-path, or binding proof failures use the `STATUS` projection with `activation_state:"BLOCKED"` and `reason`.

## `gauntlet-run ROOT --work-id ID`

```json
{"verdict":"RUN-ADMITTED","work_id":"ID","runtime":"claude"}
```

The command does not create a run, worker, worktree, branch, process, receipt, or dispatch. Missing activation returns `BLOCKED` with `ACTIVATION-REQUIRED`; stale input returns a named block.

## `gauntlet-resume ROOT --work-id ID` and `gauntlet-cleanup ROOT --work-id ID`

```json
{"verdict":"BLOCKED","code":"SCHEDULING-NOT-AVAILABLE","work_id":"ID"}
```

`gauntlet-resume` first returns `BLOCKED` with `ACTIVATION-REQUIRED` when activation is absent or stale. With a current activation it returns the shown `SCHEDULING-NOT-AVAILABLE` response. `gauntlet-cleanup` always returns the shown response. Both are non-mutating in FASE-001 and cannot delete any artifact.

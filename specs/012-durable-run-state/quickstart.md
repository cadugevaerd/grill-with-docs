# Quickstart: Durable Gauntlet Runs

## Prerequisites

- A current FASE-001 activation for an eligible V3 work item.
- A local Git repository with an immutable base commit.
- Python 3.10+ and the repository's safe file/Git worktree controls.

Every command below emits exactly one JSON object. A domain denial is a
`BLOCKED` result with a named code and leaves authoritative state unchanged.
The coordinator remains the only authority for Store, leases, receipts, and
correlated evidence; workers receive no evidence or Store-writing authority.

## Admit or reuse a durable run

```bash
python3 plugin/skills/grill-with-docs/scripts/grill_workspace.py \
  gauntlet-run . --work-id <work-item-id>
```

Expected: `RUN-CREATED` with `run_id` and `base_commit`, or `RUN-REUSED` with
the same run identity for an equivalent admission. Admission records durable
state only: it creates no worker, worktree, process, dispatch, or skill
invocation.

## Inspect correlated run evidence

```bash
python3 plugin/skills/grill-with-docs/scripts/grill_workspace.py \
  gauntlet-status . --work-id <work-item-id> --run-id <run-id>
```

Expected: read-only `STATUS` containing the activation and the requested run's
correlated run/worker state and evidence references. Status never recovers an
interrupted transition and never creates or changes durable state.

## Record one explicit recovery decision

```bash
python3 plugin/skills/grill-with-docs/scripts/grill_workspace.py \
  gauntlet-resume . --work-id <work-item-id> --run-id <run-id>
```

Expected: `RESUME-RECORDED` with `recovery_count: 1` only when the current
activation has one eligible recorded lease; an equivalent request returns
`RESUME-REUSED`. This is an explicit recorded decision, not retry, replacement,
relaunch, dispatch, or worker execution.

## Prepare an isolated worker workspace

```bash
python3 plugin/skills/grill-with-docs/scripts/grill_workspace.py \
  gauntlet-prepare-worker . --work-id <work-item-id> --run-id <run-id> \
  --worker-id <worker-id> --scope <relative-project-path>
```

Expected: `WORKER-PREPARED` with one logical `worktree_key` and the declared
`base_commit`. Preparation creates only the exact isolated derived worktree
and passive grant; it starts no worker and grants no Store, receipt, lease,
dispatch, network, push, ship, release, or arbitrary-command authority.

## Cleanup boundary

```bash
python3 plugin/skills/grill-with-docs/scripts/grill_workspace.py \
  gauntlet-cleanup . --work-id <work-item-id> --run-id <run-id> \
  --worker-id <worker-id>
```

Expected: only an exact worker whose recorded state is clean, terminal,
converged, and `cleanup_eligible: true` can return `CLEANED`. Failed, stalled,
blocked, conflicting, dirty, missing, mismatched, or orphaned workspaces are
preserved (`PRESERVED`) or blocked (`BLOCKED`); cleanup never scans or guesses
and the run's diagnostic record remains after removal. In FASE-002, newly
prepared workspaces normally remain preserved because no later phase records
convergence or cleanup eligibility.

## V2 boundary

The same FASE-002 controls (`gauntlet-run`, `gauntlet-status`,
`gauntlet-resume`, `gauntlet-prepare-worker`, and `gauntlet-cleanup`) are
incompatible with V2 work items: they return `BLOCKED` with
`WORKFLOW-INCOMPATIBLE` and leave workspace, Git, and durable state unchanged.
V2 manual workflow behavior and outputs remain unchanged. Scheduling, parallel
dispatch, automatic retry/relaunch, convergence, review, shipping, publishing,
and external approval remain outside FASE-002.

# Quickstart: Claude Scheduler Waves (FASE-003)

## Scope of this document

FASE-003 adds coordinator-only Store extensions and six new `gauntlet-*`
commands for DAG validation, wave declaration, worker declaration, worker
termination, progress recording, and remediation — all implemented, wired
into `grill_workspace.py`, and covered by
`tests/validate_gauntlet_scheduler_contract.py` (43 tests). This document
covers the full FASE-001/002/003 command surface: the existing durable-run
controls, the fixed-order macro-step dispatch boundary, and the new
scheduler-wave commands. For the formal per-command contract (every success
shape and every named block), see
`specs/013-scheduler-waves/contracts/gauntlet-scheduler-cli.md`.

## Prerequisites

- A current FASE-001 activation for an eligible V3 work item.
- A local Git repository with an immutable base commit.
- Python 3.10+ and the repository's safe file/Git worktree controls.

Every command below emits exactly one JSON object. A domain denial is a
`BLOCKED` result with a named code and leaves authoritative state unchanged.

## The existing FASE-001/002 command surface

```bash
python3 plugin/skills/grill-with-docs/scripts/grill_workspace.py \
  gauntlet-run . --work-id <work-item-id>

python3 plugin/skills/grill-with-docs/scripts/grill_workspace.py \
  gauntlet-status . --work-id <work-item-id> --run-id <run-id>

python3 plugin/skills/grill-with-docs/scripts/grill_workspace.py \
  gauntlet-resume . --work-id <work-item-id> --run-id <run-id>

python3 plugin/skills/grill-with-docs/scripts/grill_workspace.py \
  gauntlet-prepare-worker . --work-id <work-item-id> --run-id <run-id> \
  --worker-id <worker-id> --scope <relative-project-path>

python3 plugin/skills/grill-with-docs/scripts/grill_workspace.py \
  gauntlet-cleanup . --work-id <work-item-id> --run-id <run-id> \
  --worker-id <worker-id>
```

These behave exactly as documented in
`specs/012-durable-run-state/quickstart.md`; FASE-003 does not change any of
them.

## The dispatch boundary: `agent-execute` is not a special case

The Gauntlet Loop dispatches each of the eleven canonical macro-steps
(`specify`, `plan`, `checklist`, `tasks`, `analyze`, `agent-assign`,
`agent-execute`, `converge`, `verify`, `review`, `ship`) to its own Claude
subagent leader, strictly in that order. `agent-execute` is one of the
eleven, not an exception: its leader is dispatched and checkpointed through
the same, unmodified `checkpoint` command every other macro-step already
uses.

```bash
python3 plugin/skills/grill-with-docs/scripts/grill_workspace.py \
  checkpoint . --work-id <work-item-id> --step agent-execute \
  --state complete --evidence <path> --attestation <path>
```

There is no core-side exemption for `agent-execute`: `verify_checkpoint_
attestation` in `grill_workspace.py` gates its completion exactly like
`specify`, `plan`, or any other step — a `complete` transition without a
valid attestation bundle fails `ATTESTATION-REQUIRED` (or `EVIDENCE-REQUIRED`
first, if ordinary evidence is also missing), regardless of which step is
named. `tests/validate_gauntlet_scheduler_contract.py` pins this as a
regression test against the unmodified `grill_workspace.py`/
`grill_core/attestation.py` code, not a new behavior this phase adds.

Within its own dispatch window, the `agent-execute` leader is the actor that
runs the wave loop this phase's later commands implement (dispatching,
observing, and remediating the Execution DAG's worker nodes) before
submitting its own single-invocation checkpoint receipt through this same,
unmodified attestation chain. No worker of any wave ever submits that
receipt, and no dispatched worker gains checkpoint, Store-write, or
attestation authority of its own.

## The scheduler-wave command surface (FASE-003)

Full contract: `specs/013-scheduler-waves/contracts/gauntlet-scheduler-cli.md`.
Every command below requires a durable run already admitted via
`gauntlet-run` (above).

### `gauntlet-dag-validate` — fail-closed Execution DAG check

```bash
python3 plugin/skills/grill-with-docs/scripts/grill_workspace.py \
  gauntlet-dag-validate . --work-id <work-item-id> --run-id <run-id> \
  --dag specs/013-scheduler-waves/execution-dag.json
```

Verdicts: `DAG-VALID` (with `max_workers` and a `nodes` projection), or a
named block — `DAG-MALFORMED`, `DAG-CYCLIC`, `DAG-NODE-OUT-OF-SCOPE`,
`DAG-NODE-TIER-UNRESOLVED`. Pure/stateless: reads only the DAG file and the
activation proof, persists nothing, safe to re-run.

### `gauntlet-wave-declare` — declare the run's next Execution Wave

```bash
python3 plugin/skills/grill-with-docs/scripts/grill_workspace.py \
  gauntlet-wave-declare . --work-id <work-item-id> --run-id <run-id> \
  --dag specs/013-scheduler-waves/execution-dag.json \
  --node-id T001 --node-id T002
```

`--node-id` repeats, one per node in this wave. Verdicts: `WAVE-DECLARED` or
`WAVE-REUSED` (both with `wave_id`), or a named block —
`WAVE-NODES-REQUIRED`, `WAVE-NODE-UNKNOWN`, `WAVE-NODE-NOT-PARALLEL`,
`WAVE-NODE-NOT-READY`, `WAVE-PREREQUISITE-INCOMPLETE` (the run's current
wave is not yet `COMPLETE` — this is the only outcome for a still-`ACTIVE`
wave, never a guessed `WAVE-REUSED`), `WAVE-CAP-EXCEEDED`.

### `gauntlet-worker-declare` — first dispatch of one node's worker

```bash
python3 plugin/skills/grill-with-docs/scripts/grill_workspace.py \
  gauntlet-worker-declare . --work-id <work-item-id> --run-id <run-id> \
  --wave-id wave-0001 --node-id T001 --tier medium \
  --files plugin/skills/grill-with-docs/scripts/grill_core/gauntlet_runs.py
```

`worker_id` is set to `--node-id` verbatim. Verdicts: `WORKER-PREPARED`
(first dispatch, with `worktree_key`/`base_commit`) or `REUSED` (idempotent
repeat) — **not** `WORKER-DECLARED`/`WORKER-REUSED`; this command is a thin
entry over the existing `prepare_worker` intent protocol and inherits its
exact verdict vocabulary. Named blocks: `WAVE-NOT-FOUND` (named wave is not
currently `ACTIVE`), `INVALID-IDENTIFIER` (node id uses the reserved
`-r<digits>` remediation suffix), `DAG-NODE-TIER-UNRESOLVED`, plus
`prepare_worker`'s own boundaries (`WORKER-CONFLICT`, `WORKSPACE-PRESERVED`,
`LEASE-INVALID`, `WORKTREE-CREATE-FAILED`, `GIT-UNAVAILABLE`).

### `gauntlet-progress-record` — renew a worker's lease past its window

```bash
python3 plugin/skills/grill-with-docs/scripts/grill_workspace.py \
  gauntlet-progress-record . --work-id <work-item-id> --run-id <run-id> \
  --worker-id T001
```

Verdict: `PROGRESS-RECORDED` with the renewed `expires_at`. Requires the
worker `PREPARED`; blocks `WORKER-NOT-FOUND`, `WORKER-NOT-PREPARED`,
`LEASE-INVALID`.

### `gauntlet-worker-terminal` — end one worker, success or failure

```bash
python3 plugin/skills/grill-with-docs/scripts/grill_workspace.py \
  gauntlet-worker-terminal . --work-id <work-item-id> --run-id <run-id> \
  --worker-id T001 --outcome completed

python3 plugin/skills/grill-with-docs/scripts/grill_workspace.py \
  gauntlet-worker-terminal . --work-id <work-item-id> --run-id <run-id> \
  --worker-id T001 --outcome failed --failure-class process-timeout
```

`--failure-class` (`{process-timeout,transport-failure}`) is required if and
only if `--outcome failed`. Verdict: `WORKER-TERMINAL` with `state`
(`TERMINAL` or `FAILED`; a failed outcome also returns `failure_class`).
Named blocks: `WORKER-NOT-FOUND`, `WORKER-NOT-PREPARED`, `INVALID-ARGUMENTS`,
`FAILURE-CLASS-REQUIRED`. Frees the worker's concurrent-cap slot regardless
of outcome; completes the wave in the same transaction if this was its last
non-terminal node.

### `gauntlet-remediate` — replace one stalled or transiently-failed worker

```bash
python3 plugin/skills/grill-with-docs/scripts/grill_workspace.py \
  gauntlet-remediate . --work-id <work-item-id> --run-id <run-id> \
  --worker-id T001 --reason stall

python3 plugin/skills/grill-with-docs/scripts/grill_workspace.py \
  gauntlet-remediate . --work-id <work-item-id> --run-id <run-id> \
  --worker-id T001 --reason transient-failure
```

Verdict: `REMEDIATION-RECORDED` with the new `worker_id` (`<node-id>-r<n>`),
`remediates`, `recovery_count: 1`. Named blocks:
`REMEDIATION-BUDGET-SPENT` (this node's shared budget is already spent — a
node cannot chain remediation by alternating reasons), `STALL-NOT-ELIGIBLE`
(`--reason stall`, a progress transition landed inside the configured stall
window), `WORKER-NOT-PREPARED` (`--reason stall`), `WORKER-NOT-FAILED`
(`--reason transient-failure`), `FAILURE-CLASS-NOT-TRANSIENT`
(`--reason transient-failure`, re-derived from the coordinator's own
receipt, never caller-asserted).

### Divergences from `plan.md`'s original design, confirmed against the shipped code

- `gauntlet-worker-declare`'s verdicts are `WORKER-PREPARED`/`REUSED` (reused
  verbatim from `prepare_worker`), not `WORKER-DECLARED`/`WORKER-REUSED`.
- `gauntlet-status`'s projection gains only `failure_class` per worker. It
  does **not** expose wave state, `node_id`, or `remediates` — those stay
  recoverable only from the raw Store or the journal, never through this
  public command.
- (The wave record's `node_ids` field, an early implementation pass had
  substituted for a journal-scan and this doc once described that way, was
  reverted back to matching `plan.md`'s original design — `node_ids` **is**
  a required, immutable-once-set Store field. This bullet is kept only so a
  reader of an older copy of this file knows the journal-scan description
  never reflected the final shipped code.)

### Breaking change to an existing FASE-001/002 command

`gauntlet-prepare-worker --scope` now rejects, `GRANT-OUT-OF-SCOPE`, any
scope path with a `.specify` segment immediately followed by `reports`, or
any `.grill` segment, at any depth — the same FR-004 rule
`gauntlet-worker-declare`/`gauntlet-dag-validate` already enforced. This is
a deliberate, operator-approved change (see
`.grill/work-items/feature-gauntlet-loop-0447622ec0714933a4e791d0b58b5420/DECISION-BACKLOG.md`
BL-0002): a scope request touching those paths previously succeeded and now
blocks, for every caller of `gauntlet-prepare-worker`, not only FASE-003
callers. A scope outside those two rules is unaffected.

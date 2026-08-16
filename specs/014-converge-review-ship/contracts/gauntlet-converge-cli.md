# Gauntlet Converge CLI Contract — FASE-004

All commands emit one JSON object. Domain denial returns `{"verdict":"BLOCKED","code":"SCREAMING-KEBAB"}` and leaves authoritative state unchanged unless the command reports a successful recorded transition. Every command below (except `gauntlet-run-abandon`, see its own section) also inherits FASE-002/003's common admission boundary (`gauntlet_run_admission`): a stale or missing FASE-001 activation blocks `ACTIVATION-REQUIRED`/`IDENTITY-STALE`, a V2 work item blocks `WORKFLOW-INCOMPATIBLE`, and an unavailable Git base commit blocks `BASE-COMMIT-UNAVAILABLE`, before any command-specific logic runs.

## `gauntlet-converge ROOT --work-id ID --run-id ID --dag PATH --wave-id ID`

```json
{"verdict":"WAVE-CONVERGED","work_id":"ID","run_id":"run-<opaque-id>","wave_id":"wave-0001","converged":["T001","T002"],"wave_converged":true,"run_state":"ADMITTED"}
```

Reuse (idempotent replay of an already-converged wave, including the wave whose convergence already completed the run):

```json
{"verdict":"WAVE-CONVERGED-REUSED","work_id":"ID","run_id":"run-<opaque-id>","wave_id":"wave-0001"}
```

Checks run in this fixed order, each a fail-closed boundary named on its own block: (1) the common admission boundary above; (2) `DAG-PIN-MISSING`/`DAG-CONTENT-MISMATCH` — the run must already have a DAG hash pinned (by `gauntlet-wave-declare`'s first real wave), and the supplied `--dag`'s content must match it exactly; (3) run-terminal check — `RUN-NOT-ELIGIBLE` if the run is `BLOCKED`, or `COMPLETE` with a `--wave-id` other than the exact wave that completed it (that exact case short-circuits to `WAVE-CONVERGED-REUSED`); a non-terminal run additionally reconciles any dangling `wave-converged`/`run.completed` transaction an earlier interrupted call left pending, before continuing; (4) `EXECUTION-BRANCH-UNSET`/`EXECUTION-BRANCH-MISMATCH` — the work item's `development.execution_branch` must be set and match the coordinator's own currently checked-out branch (never a detached `HEAD`); `EXECUTION-TREE-DIRTY` — the coordinator's own worktree must have no tracked modifications (untracked files the wave's own workers never touch are tolerated); (5) `WAVE-CONVERGENCE-OUT-OF-ORDER` — the requested wave must be the run's next not-yet-fully-converged wave in declaration order, unless it's already `converged: true` (always accepted, short-circuits to reuse) or it's still `ACTIVE` (a member not yet terminal — blocks the same way an out-of-sequence wave would); (6) the scope pre-pass and merge.

The scope pre-pass runs over every wave member with a recorded `workspace.branch` (a `state == "TERMINAL"` lineage-head — never a `FAILED`/`STALLED`/`ORPHANED`/`CONFLICT` one, and never one still `DECLARED` with no worktree), checking pairwise `files` overlap from the pinned DAG (never `grant.scope_paths`, which is not guaranteed to mirror it — ADR-0021). A hit blocks `INTEGRATION_CONFLICT` for the whole wave (`last_conflict.reason = "scope-overlap"`) before any merge is attempted. Members that pass are merged one at a time, alphabetically by `node_id`, each its own Store transaction; a worker whose branch adds no commits beyond `base_commit` counts as a trivial success. A real Git conflict blocks just that worker (`last_conflict.reason = "content-conflict"`, with `execution_branch_head`/`worker_heads` fingerprints); a reentry with unchanged fingerprints re-blocks without recomputing the merge, a changed fingerprint recomputes fresh; earlier successful merges in the same call are never reverted. `last_conflict` clears on that worker's eventual successful merge.

When every declared `node_id` of a wave has a `TERMINAL`-and-merged lineage-head, the wave's own `converged` flag is set (`gauntlet.converge.wave-converged`); when every `node_id` of the whole pinned DAG does, the run transitions to `COMPLETE` (`gauntlet.run.completed`) — never by counting waves, only by the DAG's own node set (ADR-0020).

## `gauntlet-wave-declare` (FASE-003, extended)

Unchanged success/inputs. Two new named blocks, checked before any worker is prepared: `WAVE-SCOPE-OVERLAP` (the requested `node_ids`' declared `files` overlap pairwise — the primary defense, making `gauntlet-converge`'s own pre-pass residual); `DAG-PIN-MISSING`/`DAG-CONTENT-MISMATCH` (on every call after the run's first real wave, which instead *writes* the pin in the same transaction as its own declaration).

## `checkpoint ROOT --work-id ID --step ship --state complete` (FASE-001, extended)

Unchanged entry point and existing gates (step-sequence, then attestation). One new block, `CONVERGENCE-INCOMPLETE`, inserted between them: fires if any run gauntlet V3 admitted for this work item has `state` outside `{COMPLETE, BLOCKED}` — naming the pending run(s). A work item with no admitted run, or only terminal ones, is unaffected (no-op).

## `gauntlet-run-abandon ROOT --work-id ID --run-id ID --attestation PATH`

```json
{"verdict":"RUN-ABANDONED","work_id":"ID","run_id":"run-<opaque-id>"}
```

Reuse: `{"verdict":"RUN-ABANDON-REUSED", ...}` for a byte-identical bundle resubmitted against an already-`BLOCKED` run.

`--attestation` names a `human-authorization/v1` bundle file — the same 6-key closed schema (`schema`, `scope`, `decision`, `authorized_by`, `receipt_ref`, `content_sha256`) `attestation.py` already validates for `ship`, here with `scope` required to equal the target `--run-id`. Loaded with the same loader `checkpoint` already uses; any load failure (missing file, symlink, malformed JSON) or schema/approval failure (`decision != "APPROVED"`, wrong `scope`) collapses to `ABANDON-AUTHORIZATION-INVALID` — never a bare `--reason` string. `RUN-NOT-ELIGIBLE` if the run is already `COMPLETE`, or already `BLOCKED` with a *different* bundle already on record.

**This command does not inherit the common admission boundary above.** It deliberately derives `base_commit` and planning-identity from the *target run's own already-recorded* `admission` — never the currently active one — and skips the Git base-commit-existence check entirely. This is the one command whose entire purpose is unsticking a run from an older generation than the one currently active (a `phase-turn` since changed `base_commit`); requiring current-generation identity, like every other command in this surface does, would make it useless in exactly the case it exists for (ADR-0020).

## `gauntlet-status ROOT --work-id ID [--run-id ID]` (extended)

```json
{"verdict":"STATUS","work_id":"ID","activation_state":"ACTIVATED","run":{"run_id":"run-<opaque-id>","state":"ADMITTED","workers":[...],"waves":[{"wave_id":"wave-0001","state":"COMPLETE","converged_count":2,"member_count":2}],"last_conflict":{"node_ids":["T003"],"reason":"content-conflict"}}}
```

Read-only; unchanged failure modes. `waves` lists every real (non-bootstrap-placeholder) wave in declaration order. `last_conflict`, present only if some wave has an unresolved one, surfaces from the correct wave — scanned in declaration order, most recent unresolved first, never assumed to be the newest wave overall (the exact scenario a newer wave declared while an older one's conflict is still open). Neither field ever exposes `events.jsonl` raw, worker diff content, or the `execution_branch_head`/`worker_heads` fingerprints `gauntlet-converge` uses internally for reentry.

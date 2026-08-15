# Implementation Plan: Durable Gauntlet Runs

**Branch**: `012-durable-run-state` | **Date**: 2026-08-14 | **Spec**: [spec.md](spec.md)
**Phase**: `FASE-002` | **Delivery Unit**: `DU-002` | **Work Item**: `feature-gauntlet-loop-0447622ec0714933a4e791d0b58b5420`

## Summary

Extend the existing project-scoped Store with a strict optional Gauntlet run block. A current FASE-001 activation may create or reuse one durable run, record coordinator-owned correlated evidence, prepare isolated worker worktrees, expose a read-only run projection, support one explicit recovery decision, and clean only a recorded eligible workspace. This phase never selects a wave, starts a worker, dispatches a skill, retries automatically, converges changes, reviews, ships, publishes, or creates an external authority.

## Technical Context

**Language/Version**: Python 3.10+ (standard library only)

**Primary Dependencies**: Existing `grill_workspace.py`, `grill_core.gauntlet`, `grill_core.store`, V3 eligibility modules, and local Git

**Storage**: Existing common-Git Project Store (`orchestrator.json`, chained `events.jsonl`, receipts), with a strict optional `work_items.<work-id>.gauntlet` block; no database, second store, or untracked authority file

**Testing**: Python `unittest` public-contract validators plus Store invariants through the public CLI

**Target Platform**: POSIX Python CLI with Git worktree support; absent safe descriptor or Git capability returns a single named `BLOCKED` JSON response

**Project Type**: Claude/Codex plugin command-line tool

**Performance Goals**: Admission, status, resume, preparation, and cleanup use bounded local I/O and one Store transaction; no background process or network request

**Constraints**: One JSON object on stdout; current activation proof before every mutable action; CAS/journal/receipt correlation; worker IDs and scope paths validated; maximum five declared workers; no coordinator mutation by workers

**Scale/Scope**: Multiple durable runs may be retained for one activated V3 work item, but a compatible active admission reuses its run. Worker workspaces are explicitly prepared, never scheduled, in this phase.

## Constitution Check

| Clause | Plan evidence | Status |
|---|---|---|
| Evidência antes de afirmação | Every material transition binds run, wave, base revision, input, receipt, and output hash/null; worker and lease bind every worker-scoped transition. Public contracts exercise the correlation. | PASS |
| Work item isolado e ownership | The Store keys all run, worker, grant, lease, and receipt references to one validated `--work-id`. | PASS |
| Feature/fix plan-only | This plan respects the external phase contract: it contains no scheduler, worker execution, convergence, review, ship, or publication. | PASS |
| Sequência obrigatória | Planning follows the completed FASE-002 `specify` checkpoint; checklist, tasks, analysis, assignments, execution, converge, verify, review, and ship remain gated. | PASS |
| Verify/review antes de ship | Public validators and a new independent review remain mandatory gates before any isolated ship transaction. | PASS |
| Fail-closed sem waiver | Invalid activation, Store, run, lease, capability, worktree, Git, identity, and cleanup conditions return named blocks before unsafe state changes. | PASS |
| Rastreabilidade | Snapshot revision, chained journal, immutable receipts, base revision, and public evidence use stable run/worker identities. | PASS |
| Bump obrigatório do plugin | This is an unreleased feature branch. FASE-004 synchronizes every distribution surface to `2.6.0` before any merge, push, tag, or publication. | PASS |

## Research Decisions

| Decision | Rationale | Alternatives rejected |
|---|---|---|
| Extend `work_items.<id>` with strict optional `gauntlet` | The Project Store already supplies CAS, locking, journal anchoring, and common-Git scope. A run belongs to one work item. | New store or top-level unversioned file duplicates authority and recovery rules. |
| Coordinator-only Store helpers | Workers receive passive grants and an isolated workspace, not Store or receipt mutation APIs. | Letting worker processes write coordinator evidence violates ADR-0006 and ADR-0010. |
| One Store transaction per material transition | Semantic event, receipt reference, snapshot revision, and commit anchor must be ordered under the existing global lock. | Calling `transact` then `append_event` has a crash window between visible state and its run event. |
| Explicit worker preparation | A prepared workspace establishes isolation without scheduling or executing a worker. | Implicit creation from `run` obscures authority and crosses into FASE-003 dispatch. |
| Logical worktree keys | Persist `worktree_key`, branch, and base commit; derive the filesystem target under the Store root. | Persisting arbitrary user or host paths permits path escape and weakens cleanup validation. |
| Explicit, recorded recovery decision | `resume` evaluates one persisted lease and may record eligibility/blocked state only. | Timeout watchers, relaunches, and retries are FASE-003 responsibilities. |

## Design

### Public command surface

The existing Gauntlet command family remains the only public boundary and continues to emit exactly one JSON object. Existing V2 commands and `gauntlet-init` behavior remain unchanged.

| Command | Inputs | Success | Fail-closed boundary |
|---|---|---|---|
| `gauntlet-run` | root, `--work-id` | `RUN-CREATED` or `RUN-REUSED`, with `run_id` | Requires current activation and Store integrity; never dispatches or creates a worker/worktree. |
| `gauntlet-status` | root, `--work-id`, optional `--run-id` | `STATUS` plus activation and stable run projection | Read-only; absent/invalid run becomes a named projected block without mutation. |
| `gauntlet-resume` | root, `--work-id`, `--run-id` | `RESUME-RECORDED` or `RESUME-REUSED` | Only an explicit one-time eligible recovery decision; no retry, relaunch, dispatch, or worker execution. |
| `gauntlet-prepare-worker` | root, `--work-id`, `--run-id`, `--worker-id`, repeated scoped path | `WORKER-PREPARED` or `REUSED` | Current run, unique worker, strict grant, safe base revision, and isolated worktree are required. |
| `gauntlet-cleanup` | root, `--work-id`, `--run-id`, `--worker-id` | `CLEANED` or `REUSED` | Only clean, terminal, converged, recorded-eligible worker. Failed/stalled/blocked/conflicting/dirty workers return `PRESERVED` or `BLOCKED` without deletion. |

No command accepts a budget, credentials, raw host path, shell command, model invocation, runtime fallback, external approval, or an arbitrary receipt location.

### Durable Store schema

`grill-orchestrator/v1` retains its closed top-level shape. `work_items.<work-id>` accepts a new optional `gauntlet` object; existing work items without that object remain valid and byte-compatible.

```json
{
  "gauntlet": {
    "schema": "grill-gauntlet-runs/v1",
    "runs": {
      "run-<opaque-id>": {
        "admission": {
          "activation_sha256": "<sha256>",
          "work_item_sha256": "<sha256>",
          "workflow_sha256": "<sha256>",
          "config_sha256": "<sha256>",
          "base_commit": "<40-hex>"
        },
        "state": "ADMITTED|RECOVERY_ELIGIBLE|RECOVERY_RECORDED|BLOCKED|COMPLETE",
        "recovery_count": 0,
        "waves": {"wave-0001": {"state": "DECLARED"}},
        "workers": {"worker-<id>": {"lease": null, "grant": null, "workspace": null, "state": "DECLARED"}},
        "last_transition": {"event_sequence": 0, "receipt_sha256": "<sha256>"}
      }
    }
  }
}
```

The implementation replaces placeholders with closed regular expressions and enums. Runs contain no raw receipt payload, host path, process handle, token, secret, or worker output. `wave-0001` is a correlation label only; wave selection and parallel scheduling are deferred to FASE-003.

### Run transition and evidence boundary

`admit_or_reuse_run`, `record_resume_decision`, `prepare_worker`, and `cleanup_worker` are coordinator-only helpers in `grill_core.gauntlet_runs` (or an equivalently isolated core module). They receive already-verified activation inputs from the public CLI and make all Store changes through a new Store-owned `transact_with_event` operation under the existing global Store lock.

`transact_with_event` uses a Store-owned write-ahead intent, not a naïve event/snapshot pair. Under the global lock it first writes and fsyncs an opaque pending candidate containing the target revision/content hash, semantic event payload, receipt reference, and recovery token. It then writes the strict receipt, validates and appends the domain journal event, appends the matching commit anchor, publishes the snapshot, fsyncs its directory, and removes the pending intent only after re-reading the published snapshot. The receipt and event always contain the same `work_id`, `run_id`, `wave_id`, `base_commit`, input hash, output hash or explicit null, and receipt hash; `worker_id` and `lease_id` are mandatory only for worker-scoped transitions.

`recover_pending_transition` is a separate Store-owned operation, run under the same lock before every mutable FASE-002 command and before normal `_require`/`read_snapshot` validation. It uses a narrow raw reader only for the current snapshot bytes, validated journal, and pending intent; it never calls the normal revision-anchor check until it has either published the exact pending candidate or rejected recovery. It validates the exact pending intent against the receipt and journal before choosing one deterministic outcome: abandon an intent with no semantic event (leaving any pre-commit receipt non-authoritative for diagnosis), append a missing commit anchor for a matching semantic event, or publish the pending candidate when the anchor names its exact revision/content hash. A mismatched, duplicated, malformed, or unverifiable pending intent fails `STORE-RECOVERY-REQUIRED` without rewriting the snapshot. Read-only `gauntlet-status` never recovers; it projects that named block. Fault-injection tests cover interruption after pending intent, receipt, semantic event, commit anchor, snapshot replacement, and pending-intent removal.

The Store validates the new block, event shape, receipt category/name, identifiers, closed state transitions, and correlation before commit. Store-local hash fields remain bare 64-hex values; any later attestation adapter must explicitly convert to its `sha256:<hex>` representation rather than mixing the two formats. Repeated equivalent commands return `REUSED` without revision or receipt churn. Stale admission, CAS conflict, changed activation/base, malformed records, unknown keys, unsafe paths, or a Store/journal inconsistency fail before a new authoritative run transition.

### Lease and explicit recovery

Each worker lease has a closed identifier, positive fencing token, acquired and expiration timestamps, state, and `recovery_count` capped at one. A lease is never acquired or renewed by a worker. `gauntlet-resume` reads the selected run, proves current activation and matching admission identity, and records exactly one explicit recovery outcome:

- `RESUME-RECORDED` changes an eligible interrupted/expired lease to `RECOVERY_RECORDED` without starting it.
- `RESUME-REUSED` returns unchanged evidence for the same decision.
- A second recovery, changed identity, malformed lease, unexpired/ineligible lease, or prior terminal/block state returns `BLOCKED` with a precise reason and no write.

There is no timer, heartbeat, watchdog, worker replacement, relaunch, retry, or wave dispatch in this phase.

### Worker worktrees and capability grants

Preparation derives one target from the Store common directory, work ID, run ID, and worker ID. It validates all components as logical identifiers, resolves the recorded `base_commit` to a commit, and creates a child branch and isolated Git worktree from that immutable base. The coordinator worktree is never a target.

Git effects use an idempotent intent protocol because Git and the Store cannot share one filesystem transaction. `gauntlet-prepare-worker` first commits a `PREPARING` worker intent with the derived target/branch/base; it then performs `git worktree add`; a second Store transition changes it to `PREPARED`. A repeated prepare reconciles `PREPARING` deterministically: an entirely absent derived target, child branch, and Git registration runs the same exact add; an exact target, branch, and base finalizes `PREPARED`; a partial or divergent target/branch/registration becomes `ORPHANED`/`BLOCKED` and is preserved for diagnosis. Cleanup first validates every cleanup predicate and exact Git identity while state is unchanged; only then commits `CLEANING`, revalidates the same target immediately before one exact `git worktree remove`, and finally commits `CLEANED`. An invalid cleanup request therefore writes nothing. A repeat reconciles `CLEANING` only when Git proves the target is absent or still the exact declared target. No operation scans, guesses, or removes an orphan automatically. Fault-injection tests cover a crash before and after each Git effect and Store finalization.

The persisted worker record holds `worktree_key`, child branch, base commit, clean state, convergence flag, cleanup eligibility, and a closed grant:

```json
{
  "worktree_key": "wt-<run-id>-<worker-id>",
  "branch": "grill/<work-id>/<run-id>/<worker-id>",
  "base_commit": "<40-hex>",
  "grant": {
    "scope_paths": ["relative/project/path"],
    "capabilities": ["git-local", "workspace-read-write"]
  }
}
```

Grant values are no more than the exact local allowlist; they exclude Store writes, receipt writes, lease control, dispatch, network, push, ship, release, credential access, and arbitrary command execution. FASE-002 records the grant but does not start a worker process or enforce a runtime sandbox—that execution boundary belongs to FASE-003. Same-UID hostile-process isolation is explicitly out of scope: linked worktrees share a Git common directory, so this phase establishes a coordinator API boundary, not an OS sandbox.

`gauntlet-cleanup` never scans or glob-deletes. It accepts one validated pair, re-derives the unique target, verifies Git's registered worktree, child branch, base commit, clean status, terminal worker state, `converged:true`, and `cleanup_eligible:true`, then removes only that target through the `CLEANING` intent protocol. Failed, stalled, blocked, conflicting, dirty, mismatched, missing, or orphaned targets are preserved. The Store record and evidence remain after a successful removal.

### Phase boundary and compatibility

FASE-002 changes FASE-001's `RUN-ADMITTED` response to durable `RUN-CREATED`/`RUN-REUSED`; it does not execute any canonical skill. FASE-003 owns DAG generation/validation, wave selection, native Claude invocation, up-to-five concurrent workers, heartbeat/stall watchdog, automatic retry/relaunch, and compact status events. FASE-004 owns convergence, conflict handling, independent review, human ship gate, distribution bump, and publication. V2 work items do not load the run module and retain their current output.

## Project Structure

```text
plugin/skills/grill-with-docs/
├── scripts/
│   ├── grill_workspace.py                 # public run/status/resume/prepare/cleanup wiring
│   └── grill_core/
│       ├── store.py                       # strict optional run schema, journal/receipt helpers
│       └── gauntlet_runs.py               # coordinator-only run, lease, grant, worktree logic
└── references/
    └── session-protocol.md                # unchanged protocol authority

tests/
├── validate_orchestrator_store_contract.py
└── validate_gauntlet_run_contract.py

specs/012-durable-run-state/
├── plan.md
├── research.md
├── data-model.md
├── contracts/gauntlet-run-cli.md
└── quickstart.md
```

**Structure Decision**: One dedicated runtime-state core module keeps FASE-002 coordinator authority separate from FASE-001 activation and FASE-003 scheduling. The Store remains the only durable authority.

## Complexity Tracking

| Decision | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Optional strict Store extension | Durable run state needs the Store's lock, CAS, and journal anchors. | A loose sidecar file cannot prove its ordering or recover safely. |
| Transactional event-before-visible transition | Evidence must be readable before a transition is considered authoritative. | Writing an unverifiable state first can expose an approved-looking transition with no receipt. |
| Explicit preparation command | It proves isolation and grants without creating a scheduler. | Automatically preparing workers at admission couples state creation to future dispatch policy. |

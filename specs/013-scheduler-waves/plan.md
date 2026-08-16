# Implementation Plan: Claude Scheduler Waves

**Branch**: `013-scheduler-waves` | **Date**: 2026-08-15 | **Spec**: [spec.md](spec.md)
**Phase**: `FASE-003` | **Delivery Unit**: `DU-003` | **Work Item**: `feature-gauntlet-loop-0447622ec0714933a4e791d0b58b5420`

## Summary

Extend the coordinator's Store schema (per ADR-0012, ADR-0013, ADR-0015) and add coordinator-only primitives (`grill_core.gauntlet_runs`) so that a running FASE-002 admission can validate an Execution DAG fail-closed, declare successive waves, mint node-derived worker leases with a shared per-node remediation budget, record periodic progress with lease-TTL renewal, and remediate exactly one stall or transient failure per node. This phase never invokes a Claude subagent itself — the deterministic core has no subprocess/network capability and cannot — it only produces and validates the state a dispatching actor (the outer orchestrating session for ten macro-steps, or `agent-execute`'s own dispatched leader for the eleventh, per ADR-0017/ADR-0019/FR-016) needs to dispatch safely. Convergence, review, and ship remain FASE-004's responsibility.

## Technical Context

**Language/Version**: Python 3.10+ (standard library only)

**Primary Dependencies**: Existing `grill_workspace.py`, `grill_core.store`, `grill_core.gauntlet_runs` (extended, not replaced), `grill_core.attestation` (consumed unmodified — no schema change), local Git

**Storage**: Existing common-Git Project Store (`orchestrator.json`, chained `events.jsonl`, receipts), extending the FASE-002 `work_items.<id>.gauntlet` block; no new store, database, or untracked authority file

**Testing**: Python `unittest` public-contract validators (new `tests/validate_gauntlet_scheduler_contract.py` plus extensions to `tests/validate_orchestrator_store_contract.py` and `tests/validate_gauntlet_run_contract.py`)

**Target Platform**: POSIX Python CLI with Git worktree support, unchanged from FASE-001/002

**Project Type**: Claude/Codex plugin command-line tool

**Performance Goals**: DAG validation, wave declaration, worker lease minting, progress recording, and remediation each use one bounded Store transaction; no background process, no polling loop in the core (polling, if any, lives in the dispatching session per FR-016's Assumptions note, not in `grill_core`)

**Constraints**: One JSON object on stdout per command; current activation proof before every mutable action; CAS/journal/receipt correlation (FASE-002 pattern, reused); worker IDs derived from Execution DAG node `id` (FR-007); maximum five *concurrently non-terminal* workers per run (ADR-0012); exactly one shared remediation budget per node for its lifetime (ADR-0015), enforced in the Store by `worker_id` lineage (FR-008(e)), never by declared-file/grant-scope equality (empirically refuted against both existing Execution DAGs — see Research Decisions)

**Scale/Scope**: A run may declare multiple successive waves (ADR-0013); a DAG may name more nodes than the concurrent cap, deferring the remainder to later waves; this phase validates and dispatches-against the DAG `tasks` produces, it never generates one (ADR-0014, unchanged from FASE-001 research)

## Constitution Check

| Clause | Plan evidence | Status |
|---|---|---|
| Evidência antes de afirmação | Every wave declaration, worker lease mint, progress record, and remediation binds run/wave/worker/lease identity through a Store transaction before any status reports it. | PASS |
| Work item isolado e ownership | All new Store keys stay under the existing `work_items.<work-id>.gauntlet` block; no cross-work-item read or write. | PASS |
| Feature/fix plan-only (grill-with-docs session boundary) | This plan document authorizes no alteration or publication by itself; it contains no scheduler invocation, no merge, no push. The intent to proceed to `tasks`/`agent-execute` is the same externally-gated sequence FASE-001/002 used, and each downstream step carries its own independent gate. | PASS |
| Sequência obrigatória | Planning follows the FASE-003 `specify` outputs (spec.md, precode, ADR-0015–0019); checklist, tasks, analysis, assignments, execution, converge, verify, and review remain gated in order. | PASS |
| Verify/review antes de ship | Public validators and an independent review remain mandatory before any ship transaction; ship stays out of this phase's scope entirely (FASE-004). | PASS |
| Fail-closed sem waiver | Malformed/cyclic/out-of-scope DAG, over-cap wave, unresolved tier, unspent-budget remediation lease, and out-of-window remediation all return named blocks before unsafe state changes (FR-004, FR-006, FR-008(e), FR-009/FR-010). | PASS |
| Rastreabilidade | Wave, worker, lease, and remediation identities correlate through the same journal/receipt chain FASE-002 established, parameterized by the actual `wave_id` instead of the FASE-002 hardcoded constant (see Complexity Tracking); `worker_id` lineage (FR-007) makes node ownership recoverable from the identifier alone. | PASS |
| Bump obrigatório do plugin | FASE-003 bumps the version to `2.7.0` across all eight distribution surfaces in the same commit that merges, satisfying the constitution directly — no deferral, same precedent FASE-002 (`specs/012-durable-run-state/plan.md` line 41) set. | PASS |

## Research Decisions

| Decision | Rationale | Alternatives rejected |
|---|---|---|
| `agent-execute` gets a real dispatched leader, no exception (ADR-0016) | The existing `checkpoint-attestation/v1` schema models exactly one canonical-skill invocation; a leader that itself runs the wave loop and submits its own single-invocation receipt fits it with zero schema change. | The outer orchestrating session submitting an "aggregated" receipt built from Store transitions — unimplementable: the attestation bundle's `step_output` fields are singular (`worker_lease_id`, `output_sha256`, etc.), there is no way to express N workers in one bundle. |
| Delegated coordinator authority, scoped to the dispatch window (ADR-0017, ADR-0019, FR-016) | The deterministic core cannot invoke a subagent (stdlib-only, no subprocess/network); dispatch authority must live in whichever actor is currently invoking — the outer session for ten macro-steps, `agent-execute`'s own leader for the eleventh. | Fixing dispatch authority permanently in the outer session — breaks the moment `agent-execute` needs to mint leases/grants for workers it dispatches itself. |
| Node identity is `worker_id`, derived from the DAG node's own `id` (FR-007) | Exact, no false positives, no new worker-record field (`SAFE_NAME_RE` already admits it). | Correlating node identity by `grant.scope_paths` equality — empirically refuted: 15/20 nodes of `specs/011-gauntlet-loop/execution-dag.json` and 16/20 of `specs/012-durable-run-state/execution-dag.json` share an identical `files` set with at least one other node (ordinary red-green-refactor decomposition), so scope-equality would reject the large majority of legitimate first dispatches. |
| One shared remediation budget per node, enforced in the Store (ADR-0015, FR-007, FR-008(e)) | `lease.recovery_count` already exists and is bounds-checked `{0,1}`; a remediation lease must be minted already-spent, and the Store — not just the dispatching leader's prompt construction — must reject a fresh-budget mint for a `worker_id` lineage that already has a spent sibling, mirroring how `run.recovery_count` is already CAS-enforced for manual resume. | Trusting the dispatching leader alone to pass the correct value — the same "convention without executable gate" pattern ADR-0018 already rejected for FR-004; a node could otherwise alternate stall (FR-009) and transient-retry (FR-010) remediation indefinitely, never touching `run.recovery_count`, with no effective cap. |
| DAG-scope rejection anchored on the `.grill` path segment, not an enumerated basename list (ADR-0018) | Covers the entire grill governance ledger (all ten `ROOT_FILES`, ADRs, handoffs, `WORK-ITEM.json`) in one rule; a three-name list already proved insufficient once (missed `state.json`, where the attestation chain itself lives). | Enumerating basenames — provably incomplete against `ROOT_FILES` today and would need a new ADR revision for every future ledger file. |
| Lease TTL renewed by every recorded progress transition (FR-008(d)) | A `large`-tier node legitimately running past the original one-hour grant must not be treated as expired just because time passed while it was actively producing recorded progress. | A second, independent TTL-extension command — redundant: progress recording is already the signal that proves the worker is alive, tying renewal to it is the minimal addition. |

## Design

### Public command surface

All new commands share FASE-001/002's boundary: current activation proof before any mutation, one JSON object on stdout, coordinator-only Store authority, never a subagent invocation.

| Command | Inputs | Success | Fail-closed boundary |
|---|---|---|---|
| `gauntlet-dag-validate` | root, `--work-id`, `--run-id`, `--dag <path>` (repo-relative, validated by the same rule class as `_strict_scopes`) | `DAG-VALID` with node/wave-eligibility projection | Malformed/missing/cyclic structure, any node `id` failing `SAFE_NAME_RE` or matching the reserved `-r<digits>` remediation-suffix pattern (see Complexity Tracking), or any node whose `files` matches FR-004's `.specify/reports/` or `.grill` segment rules, returns a named block; never mutates. Stateless and idempotent — callers re-run it as needed; it persists nothing (see Complexity Tracking on why no cross-command precondition exists). |
| `gauntlet-wave-declare` | root, `--work-id`, `--run-id`, `--dag <path>`, `--node-id` (repeated) | `WAVE-DECLARED` or `WAVE-REUSED` with `wave_id` | Re-runs `gauntlet-dag-validate`'s checks inline against the given DAG before accepting any node; all named nodes must be ready (terminal dependencies, `parallel` rules honored per FR-004) and the resulting non-terminal worker count (existing + this wave) must not exceed the effective cap (lesser of activation config and DAG `max_workers`, FR-005, ADR-0012). Declaring `wave-000N+1` requires `wave-000N` (if any) to already be `COMPLETE`. |
| `gauntlet-worker-declare` | root, `--work-id`, `--run-id`, `--wave-id`, `--node-id`, `--tier`, scoped `--files` (repeated) | `WORKER-PREPARED` or `REUSED` (verdict names inherited verbatim from the reused `prepare_worker` primitive, not a distinct `WORKER-DECLARED`/`WORKER-REUSED` pair) with `worker_id`, `lease_id` | First dispatch only (no `--remediates`; remediation dispatch is `gauntlet-remediate`, below). `worker_id` is set to `--node-id` verbatim; tier must satisfy FR-006's floor; drives the full FASE-002 `PREPARING → git worktree add → PREPARED` intent protocol (extends `prepare_worker`, does not duplicate it — see Complexity Tracking). Rejects a `--node-id` that already has any worker record in the run (first dispatch is exactly-once per node). |
| `gauntlet-worker-terminal` | root, `--work-id`, `--run-id`, `--worker-id`, `--outcome {completed\|failed}`, `--failure-class {process-timeout\|transport-failure}` (required iff `--outcome failed`) | `WORKER-TERMINAL` | Requires the worker in `PREPARED`; transitions to `TERMINAL` (`completed`) or `FAILED` (`failed`, with the classification recorded as evidence on the transition — the one caller-asserted fact FR-010 cannot otherwise verify, named explicitly rather than left implicit, see Design). Frees the worker's concurrent-cap slot (ADR-0012) regardless of outcome. |
| `gauntlet-progress-record` | root, `--work-id`, `--run-id`, `--worker-id` | `PROGRESS-RECORDED` | Requires the worker in `PREPARED` (non-terminal); renews the lease's expiration by its original fixed duration (FR-008(d)). |
| `gauntlet-remediate` | root, `--work-id`, `--run-id`, `--worker-id`, `--reason {stall\|transient-failure}` | `REMEDIATION-RECORDED` with the new `worker_id` (`<node-id>-r<n>`), or `BLOCKED` | One Store transaction does lookup and mint together (no separate advisory step, closing the TOCTOU gap a split design would have — see Complexity Tracking). `stall`: Store-verified from the worker's own recorded lease-expiry/progress timestamps against the run's configured stall window — not caller-asserted. `transient-failure`: requires the named worker already `FAILED` via `gauntlet-worker-terminal` with a recorded transient `--failure-class` — not a bare flag on this command. Either reason: the transaction scans the run's `workers` for any entry sharing this `node_id` with `lease.recovery_count == 1`; if found, blocks `REMEDIATION-BUDGET-SPENT` and mints nothing, regardless of which reason was given. |
| `gauntlet-status` (extended) | root, `--work-id`, optional `--run-id` | Existing FASE-002 projection plus per-worker `failure_class` | Read-only; unchanged failure modes. Wave membership, `node_id`, and `remediates` are not projected — recoverable from the raw Store or journal, not exposed as a `gauntlet-status` convenience field (implementation chose journal-derived wave membership over a persisted `node_ids` field, see §Store schema extension note below). |

`checkpoint` (existing, `grill_workspace.py`) is unchanged and unextended: every macro-step leader — including `agent-execute`'s, per ADR-0016/FR-001 — submits its own single-invocation attestation bundle through the same command and verifier every other step already uses. This phase adds no attestation schema change and no second verification layer.

FR-002 (macro-step leader tier) needs no new command: the tier policy (`TIER_POLICY`/`minimum_by_step`) was already pinned at FASE-001 activation and is already readable through the existing config projection; resolving and recording it is the dispatching session's own action when it invokes a leader, not a `grill_core` primitive this phase adds. FR-013 (compact dispatch status events) needs no new command either: every command above already appends a journal event as part of its Store transaction (wave declaration, worker declaration, termination, progress, remediation) — those events, correlated to run/wave/worker/lease identity, are FR-013's "compact dispatch status event"; they are explicitly the low-level per-transition journal entries, distinct from FASE-004's higher-level aggregated Run Status Events, which read from this journal rather than duplicating it.

No command accepts a budget, credentials, raw host path, shell command, model invocation, runtime fallback, external approval, or an arbitrary receipt location — unchanged from FASE-001/002.

### Store schema extension

`grill-gauntlet-runs/v1` (FASE-002) gains, inside an existing run's `waves` and `workers` maps:

```json
{
  "waves": {
    "wave-0001": {"state": "COMPLETE"},
    "wave-0002": {"state": "ACTIVE"}
  },
  "workers": {
    "T003": {
      "state": "DECLARED",
      "lease": {"lease_id": "lease-<run-id>-T003", "recovery_count": 0, "expires_at": "<iso8601>"},
      "grant": {"scope_paths": ["plugin/skills/.../file.py"], "capabilities": ["git-local", "workspace-read-write"]},
      "node_id": "T003",
      "remediates": null
    },
    "T003-r1": {
      "state": "DECLARED",
      "lease": {"lease_id": "lease-<run-id>-T003-r1", "recovery_count": 1, "expires_at": "<iso8601>"},
      "grant": {"scope_paths": ["plugin/skills/.../file.py"], "capabilities": ["git-local", "workspace-read-write"]},
      "node_id": "T003",
      "remediates": "T003"
    }
  }
}
```

`WAVE_STATES` widens from the FASE-002-frozen `{DECLARED}` to `{DECLARED, ACTIVE, COMPLETE}` (ADR-0013). This requires replacing `_validate_gauntlet_state_transitions`' current whole-map immutability check (`store.py:927-928`, `jcs(new_run["waves"]) != jcs(old_run["waves"])` unconditionally fails) with a per-wave edge table: a `wave_id` already present in both old and new MUST either be byte-identical, or transition `DECLARED → ACTIVE → COMPLETE` (never backward, never skip); a `wave_id` may be added (map grows); a `wave_id` present in old but absent in new still fails (removal stays forbidden). Once a `wave_id` other than the newest reaches `COMPLETE`, it becomes immutable again — "superseded" means "not the run's current wave," determined by wave-declaration order, not by state alone. The worker-cap check (`_validate_gauntlet_block`) counts only workers in a non-terminal state — `{DECLARED, PREPARING, PREPARED, RECOVERY_ELIGIBLE, RECOVERY_RECORDED}` — instead of the map's lifetime size (ADR-0012); the remaining `WORKER_STATES` (`TERMINAL, CLEANING, CLEANED, ORPHANED, FAILED, STALLED, BLOCKED, CONFLICT`) free their slot.

`node_id` and `remediates` join `state`, `lease`, `grant`, `workspace` as **required** members of the worker record's closed key set (six keys, not four) — `_closed_object`'s exact-set style, extended, not an optional-key exception to it. `node_id` MUST equal `worker_id` with any trailing `-r<digits>` remediation suffix removed; `remediates`, when non-null, MUST name an existing sibling `worker_id` whose own `node_id` matches, and its presence is exactly what makes `lease.recovery_count` MUST-be-1-at-creation instead of MUST-be-0 (FR-007/FR-008(e)) — the Store rejects a transaction where these two facts disagree. **This is a breaking schema change for any worker record created before this phase's Store code lands**, the same way FASE-002 introducing `workers` at all was breaking relative to FASE-001: a run with a non-terminal FASE-002-shape (four-key) worker record open across the code boundary fails validation on next read, loudly (`STATE-DIVERGENCE`), never silently. This is acceptable because the Store is local, ephemeral, per-checkout state (`<git-common-dir>/grill/`), not a cross-deployment artifact — no in-flight run is expected to straddle a FASE-002-to-FASE-003 code upgrade in practice, and a loud failure is the correct behavior if one somehow does. There is no silent-migration path and none is claimed.

### DAG validation (FR-003, FR-004, FR-014)

`gauntlet-dag-validate` loads the `tasks`-produced Execution DAG (unchanged five-field schema: `id`, `depends_on`, `tier`, `parallel`, `files` — no new field, ADR-0018's rejected alternative), and checks, in order: (1) structural validity (required fields, no duplicate `id`, every `id` matching `SAFE_NAME_RE` and not the reserved `-r<digits>` remediation suffix, no cycle via topological sort); (2) FR-004's two closed rejection rules per node's `files` entries — a `.specify` segment immediately followed by `reports` at any depth, or a `.grill` segment at any depth; (3) FR-006's tier floor per node (`medium`, or `small` for Markdown-only nodes). Any failure returns a single named block (`DAG-MALFORMED`, `DAG-CYCLIC`, `DAG-NODE-OUT-OF-SCOPE`, `DAG-NODE-TIER-UNRESOLVED`) and never creates wave/worker/lease/grant state — matching FR-014's fail-closed requirement exactly. The command is pure/stateless (reads the DAG file, the run's current admission for the activation proof, nothing else) and persists nothing; `gauntlet-wave-declare` re-runs the identical checks itself rather than trusting a separate command's earlier result, so there is no cross-command precondition to keep in sync (see Complexity Tracking).

### Wave lifecycle and worker declaration (FR-004, FR-005, FR-007, FR-008(a-c))

`gauntlet-wave-declare` accepts the caller's chosen ready-node set (ready = terminal dependencies; `parallel:true` nodes may share a wave, a `parallel:false` node must be declared alone), re-validates the whole DAG (not just the named nodes) with the same logic `gauntlet-dag-validate` uses, and re-checks readiness against the DAG rather than trusting the caller's selection blindly. It declares a new wave only if (a) the run's current wave, if any, is already `COMPLETE`, and (b) the named nodes' resulting non-terminal worker count would not exceed the effective cap (lesser of activation config and DAG `max_workers`). **Implementation note (post-build, reconciling this plan with what shipped):** rather than persisting `node_ids` on the wave record as originally proposed here, the shipped implementation recovers wave membership by scanning the run's journal for `gauntlet.worker.declared` events correlated to that `wave_id` (stripping any `-r<n>` remediation suffix to get each member's `node_id`) — this avoids widening the wave record's own closed key set a second time and keeps membership as journal-derived evidence, consistent with this project's evidence-over-assertion bias. The wave record itself stays `{"state": ...}` only. A wave becomes `COMPLETE` when every node recovered this way has its current lineage-head worker record (the one not named by any sibling's `remediates`) in a terminal state — recorded via a state-only follow-up transition, not a separate command, driven by whichever call (`gauntlet-worker-terminal` or `gauntlet-remediate`'s block path) observes the last node reaching terminal. `gauntlet-worker-declare` is called once per node inside a declared wave for that node's *first* dispatch only; it sets `worker_id = node_id` verbatim, mints lease and grant by extending `prepare_worker`'s existing intent protocol (parameterized to accept and persist `node_id`/`remediates=null`, and to thread the worker's actual `wave_id` through `_worker_receipt_event`/`_transition_worker` instead of the FASE-002 hardcoded `WAVE_ID` module constant — every FASE-003 transition's receipt/event must name its real wave), and drives the same `PREPARING → git worktree add → PREPARED` sequence FASE-002 already validated.

### Worker termination, progress, stall, and remediation (FR-008(d), FR-009, FR-010)

`gauntlet-worker-terminal` is the missing piece FASE-002 never needed (it never ran a wave to completion): it transitions a `PREPARED` worker to `TERMINAL` or `FAILED` — both already legal edges in the existing `worker_edges` table (`store.py`, `PREPARED → {..., TERMINAL, FAILED, STALLED, ...}`), just never driven by any command until now. A `failed` outcome requires `--failure-class` from FR-010's closed set and records it as evidence on the transition itself, so FR-010's classification is a Store-recorded fact `gauntlet-remediate` can later verify, not a bare caller-asserted flag on the remediation call. `gauntlet-progress-record` appends a coordinator-only transition correlated to the named worker's active lease and, in the same Store transaction, extends `lease.expires_at` by the lease's original fixed duration (matching FASE-002's existing `timedelta(hours=1)` grant length — this phase does not introduce a second TTL constant).

`gauntlet-remediate` is the single entry point for both User Story 3 (stall) and User Story 4 (transient retry), and does lookup-and-mint in one Store transaction (no separate advisory step): for `--reason stall` it verifies from the worker's own recorded timestamps — no new progress transition since dispatch or the last progress record, for at least the run's configured stall window — that the condition actually holds, independent of the lease's own expiry (FR-009, closing the TTL-vs-stall gap FASE-002 left open); for `--reason transient-failure` it requires the worker already `FAILED` (via `gauntlet-worker-terminal`) with a recorded transient `--failure-class`. Either way, the same transaction scans the run's `workers` for any entry sharing the target's `node_id` with `lease.recovery_count == 1`; if one exists, it blocks `REMEDIATION-BUDGET-SPENT` and mints nothing — regardless of which reason triggered this call, so a node cannot chain remediation by alternating reasons (ADR-0015). Otherwise it mints `<node_id>-r<n>` with `recovery_count` already `1` and `remediates` set to the worker being replaced, in the same transaction that recorded the block-check passed — closing the gap a split lookup/mint design would leave open.

### Phase boundary and compatibility

FASE-003 owns DAG validation, wave declaration, worker-lease minting with node lineage, progress recording with TTL renewal, and the shared per-node remediation budget. It does not own: subagent invocation itself (ADR-0017 — that is session-level, outside `grill_core`), convergence, conflict resolution, independent review, ship, or distribution publication (FASE-004, unchanged). FASE-001/002's existing commands (`gauntlet-init`, `gauntlet-run`, `gauntlet-status`, `gauntlet-resume`, `gauntlet-prepare-worker`, `gauntlet-cleanup`) keep their current behavior for any run that never calls a FASE-003 command; V2 work items are unaffected (unchanged since FASE-001) — **with one deliberate exception**, below.

### Security note: `gauntlet-prepare-worker` now also enforces FR-004's scope rule (F1, operator-approved)

FR-004's two closed rejection rules (a `.specify/reports/` segment at any depth, or a `.grill` segment at any depth) were written for the Execution DAG and enforced on `gauntlet-worker-declare`'s grant from the start of this phase, but two independent code reviews (findings tracked as F1) found that `gauntlet-prepare-worker` — the FASE-002 command `gauntlet-worker-declare` itself extends (see §Wave lifecycle and worker declaration) — never applied the same rule to its own `--scope` argument, even though it mints worker capability grants over the identical Store. A caller could ask `gauntlet-prepare-worker` for write-scope over `.grill/work-items/<id>/state.json` (the attestation chain this very governance ledger lives in) or any `.specify/reports/` path, and it would silently succeed. The operator's explicit decision, recorded here and in `DECISION-BACKLOG.md` BL-0002, is that the previous sentence's "keep their current behavior" promise for FASE-001/002 command surface (FR-015) does not extend to preserving this gap: it is a security invariant that should have applied to `gauntlet-prepare-worker` since FASE-002, only surfaced now because this phase's own spec work (ADR-0018) was the first to articulate the `.grill` self-attestation danger explicitly. `prepare_worker` (`grill_core/gauntlet_runs.py`) now applies `_dag_scope_violation` — the same path-syntactic helper `declare_worker` already used, requiring no DAG document — unconditionally to every `scope_paths`/`--scope` entry, rejecting a violation with `GRANT-OUT-OF-SCOPE` (distinct from `declare_worker`'s `DAG-NODE-OUT-OF-SCOPE`, since a bare `gauntlet-prepare-worker` call has no DAG node to blame). This is a real, intentional behavior change to the existing FASE-002 command: a `--scope` touching `.grill/` or `.specify/reports/` that previously succeeded now blocks. It is not a new required argument and does not affect any legitimate scope outside those two rules.

## Project Structure

```text
plugin/skills/grill-with-docs/
├── scripts/
│   ├── grill_workspace.py                 # + gauntlet-dag-validate/wave-declare/worker-declare/worker-terminal/progress-record/remediate wiring
│   └── grill_core/
│       ├── store.py                       # + WAVE_STATES widened w/ per-wave edge table, non-terminal cap count, node_id/remediates required-key schema + budget-lineage validation
│       └── gauntlet_runs.py               # + DAG validation, wave/worker declaration, worker termination, progress/remediation helpers; wave_id parameterized through _receipt_and_event/_worker_receipt_event/_transition_worker (was hardcoded WAVE_ID)
└── references/
    └── session-protocol.md                # unchanged protocol authority

tests/
├── validate_orchestrator_store_contract.py   # + wave lifecycle, non-terminal cap, node_id/remediates budget-lineage cases
├── validate_gauntlet_run_contract.py         # + FASE-003 command surface public contract cases
└── validate_gauntlet_scheduler_contract.py   # new: DAG validation, wave/worker declaration, progress/remediation end-to-end

specs/013-scheduler-waves/
├── plan.md
├── research.md
├── data-model.md
├── contracts/gauntlet-scheduler-cli.md
└── quickstart.md
```

**Structure Decision**: Extends the existing two-module core (`store.py` for schema/transactions, `gauntlet_runs.py` for coordinator-only logic) rather than adding a third module — FASE-003's primitives are a direct continuation of FASE-002's run/worker/lease/grant model, not a separate authority. No new top-level package.

## Complexity Tracking

| Decision | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| `node_id`/`remediates` as new **required** closed Store fields, with `node_id` derived from `worker_id` by stripping a reserved `-r<digits>` suffix | Node identity must be recoverable from the worker record itself for the Store to enforce the shared remediation budget (FR-008(e)). The suffix-strip parse is unavoidable *somewhere* once `worker_id = node_id` is the naming rule — `gauntlet-dag-validate` closes the one real ambiguity (a `tasks` output declaring both `T003` and `T003-r1` as distinct node ids) by rejecting any DAG node `id` matching the reserved suffix pattern, so the parse is safe at the one point it runs. | An optional-key exception to `_closed_object` (new fields present only on FASE-003-created records) — `_closed_object` has no such idiom today (`store.py:731-734`, exact-set match only); adding one is a bigger, more invasive Store change than accepting the schema-version boundary this plan already names. |
| `gauntlet-worker-terminal` as its own command, separate from `gauntlet-remediate` | FR-010's transient-failure classification needs a durable, Store-recorded fact (not a bare flag) for `gauntlet-remediate` to verify; and FR-005's "a worker that reaches a terminal state frees its slot" needs a transition producer for the *success* case too, which no remediation call would ever exercise. | Folding termination into `gauntlet-remediate` — conflates "this worker is done" (always true eventually, success or failure) with "this node needs replacing" (only true on failure/stall); a successfully completed worker would have no command to record that fact at all. |
| `gauntlet-remediate` does lookup-and-mint in one transaction, for both stall and transient retry | FR-007's shared-budget rule needs one enforcement point regardless of which User Story triggered it, and the check-then-mint must be atomic under the same Store lock (`transact_with_event`, same pattern `record_resume_decision` already uses) or a concurrent second call could pass the same stale lookup. | A separate advisory "check budget" command before a separate "mint" command — the exact TOCTOU gap between the two calls is what let a node chain unbounded remediation in this plan's own first draft; one command closes it. |
| `gauntlet-dag-validate` re-runs its full check inline inside `gauntlet-wave-declare`, rather than `wave-declare` trusting a prior `dag-validate` call's result | A non-mutating command has nowhere durable to leave a "this DAG was already validated" fact for a later command to trust: adding one would mean a stateless validator suddenly needs its own Store field and immutability rule, for a check that is cheap to simply re-run. | A persisted `validated_dag_sha256` on the run — real complexity (a new field, a new immutability rule, a staleness question when `tasks` re-runs) to save re-executing a check that has no side effects and no meaningful cost. |

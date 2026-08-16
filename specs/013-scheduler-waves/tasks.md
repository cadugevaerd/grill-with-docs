# Tasks: Claude Scheduler Waves

**Input**: Design documents from `specs/013-scheduler-waves/`
**Prerequisites**: plan.md, spec.md, checklists/scheduler-requirements.md

## Phase 1: Store Foundation

- [x] T001 [P] Add red per-wave lifecycle (DECLARED→ACTIVE→COMPLETE, superseded-wave immutability, growth-only map), non-terminal worker-cap counting, and `node_id`/`remediates` required-key + budget-lineage cases to `tests/validate_orchestrator_store_contract.py`.
- [x] T002 [P] Create `tests/validate_gauntlet_scheduler_contract.py` with isolated Git fixtures for FASE-003 public controls (`gauntlet-dag-validate`, `gauntlet-wave-declare`, `gauntlet-worker-declare`, `gauntlet-worker-terminal`, `gauntlet-progress-record`, `gauntlet-remediate`) before T004–T009 exist.
- [x] T003 Replace `_validate_gauntlet_state_transitions`' whole-`waves`-map immutability check (`store.py:927-928`) with the per-wave edge table from plan.md §Store schema extension; widen `WAVE_STATES` to `{DECLARED, ACTIVE, COMPLETE}`.
- [x] T004 Extend `_validate_gauntlet_block`'s worker-cap check to count only non-terminal workers (`{DECLARED, PREPARING, PREPARED, RECOVERY_ELIGIBLE, RECOVERY_RECORDED}`) instead of `len(run["workers"])`.
- [x] T005 Extend the worker-record closed key set from `{state, lease, grant, workspace}` to `{state, lease, grant, workspace, node_id, remediates}`; validate `node_id` equals `worker_id` minus a trailing `-r<digits>` suffix, `remediates` (when non-null) names an existing sibling with matching `node_id`, and `lease.recovery_count` agrees with `remediates`' presence (0 iff null, 1 iff set).
- [x] T006 Validate T001–T005 through `tests/validate_orchestrator_store_contract.py` and preserve all existing Store contracts (FASE-001/002 regression).

**Checkpoint**: Store can represent and validate a multi-wave run with node-lineage-tracked workers before any FASE-003 CLI command exists.

## Phase 2: User Story 1 - Dispatch each macro-step to its own subagent leader (Priority: P1) 🎯 MVP

**Goal**: Confirm the existing checkpoint mechanism (unmodified this phase) already satisfies FR-001/FR-002's dispatch-order and tier-floor requirements, and document the `agent-execute`-has-a-real-leader boundary the rest of this phase depends on.

**Independent Test**: A `checkpoint --state blocked` halts `current_step` at that step; a `checkpoint --state complete` advances it; `agent-execute`'s own checkpoint requires the same single-invocation attestation bundle as any other step, with no second verification layer.

- [x] T007 [P] [US1] Add red cases to `tests/validate_gauntlet_scheduler_contract.py` proving `checkpoint --step agent-execute --state complete` requires a real attestation bundle (no core-side exception), and that `current_step` does not advance past a `blocked` step (regression-pins ADR-0016's finding against `grill_workspace.py:2564`).
- [x] T008 [US1] No production code change: this story's requirement is already satisfied by unmodified `checkpoint_command`/`verify_checkpoint_attestation`. Document the boundary in `specs/013-scheduler-waves/quickstart.md` (a macro-step leader, including `agent-execute`'s, is dispatched and checkpointed exactly like FASE-001/002's existing steps).
- [x] T009 [US1] Prove the User Story 1 contract in `tests/validate_gauntlet_scheduler_contract.py`.

**Checkpoint**: The dispatch-order/attestation boundary this whole phase relies on is pinned by a regression test, not just narrative.

## Phase 3: User Story 2 - Dispatch an independent wave of workers inside agent-execute (Priority: P1) 🎯 MVP

**Goal**: Validate an Execution DAG fail-closed, declare successive waves within the effective concurrent cap, and mint node-derived worker leases for first dispatch.

**Independent Test**: A DAG with a `.grill`-scoped or `.specify/reports/`-scoped node is rejected whole, before any wave/worker/lease/grant state exists; a DAG with ready `parallel:true` nodes and a lone `parallel:false` node declares waves matching FR-004's sharing rule and never exceeds the effective cap; two waves in sequence require the first `COMPLETE` before the second declares.

- [x] T010 [P] [US2] Add red cases to `tests/validate_gauntlet_scheduler_contract.py`: DAG structural validity (malformed/cyclic/duplicate-id/reserved-suffix-id), FR-004's two rejection rules against both real corpus nodes (011 T019's `.grill`-nested `ROUND-LOG.jsonl`, 012 T019/T020's `.specify/reports/`), tier-floor rejection, wave declaration readiness/cap/`COMPLETE`-gating, and worker-declare exactly-once-per-node.
- [x] T011 [US2] Implement `validate_execution_dag` in `grill_core/gauntlet_runs.py`: structural checks, FR-004's two path-segment rules, FR-006 tier floor — pure function, no Store I/O beyond the activation proof.
- [x] T012 [US2] Implement `declare_wave` in `grill_core/gauntlet_runs.py`: re-runs `validate_execution_dag`, re-checks node readiness/`parallel` rules, enforces the effective cap and prior-wave-`COMPLETE` gate, commits the wave record (with its fixed `node_ids`) via `transact_with_event`.
- [x] T013 [US2] Implement `declare_worker` in `grill_core/gauntlet_runs.py`: extends `prepare_worker`'s intent protocol to set `worker_id = node_id`, `remediates = None`, `lease.recovery_count = 0`, and thread the real `wave_id` through `_receipt_and_event`/`_worker_receipt_event`/`_transition_worker` (replacing the hardcoded `WAVE_ID` module constant with a required parameter).
- [x] T014 [US2] Wire `gauntlet-dag-validate`, `gauntlet-wave-declare`, `gauntlet-worker-declare` in `grill_workspace.py`, following the existing `gauntlet-*` argparse/handler/`CliFailure` pattern.
- [x] T015 [US2] Prove the User Story 2 contract in `tests/validate_gauntlet_scheduler_contract.py`, including the full corpus-derived rejection cases and multi-wave sequencing.

**Checkpoint**: A DAG can be validated and dispatched into waves of first-time workers, matching the run's effective cap, without any remediation machinery yet.

## Phase 4: User Story 3 - Observe worker progress and recover one stall (Priority: P2)

**Goal**: Record progress with lease-TTL renewal, terminate workers (success and failure), and remediate exactly one stall per node via a Store-verified, atomic lookup-and-mint transaction.

**Independent Test**: A worker's lease is renewed on every recorded progress transition, independent of the original TTL; a worker with no progress transition for the stall window is remediated exactly once via `gauntlet-remediate --reason stall`, and a second stall on the same node blocks `REMEDIATION-BUDGET-SPENT` without minting a new worker.

- [x] T016 [P] [US3] Add red cases to `tests/validate_gauntlet_scheduler_contract.py`: progress recording renews TTL past the original grant, `gauntlet-worker-terminal` drives `PREPARED→TERMINAL`/`PREPARED→FAILED` and frees the cap slot, wave reaches `COMPLETE` when its last node terminates, stall remediation is Store-verified (not caller-asserted) from recorded timestamps, remediation lease is minted already-spent, and a second stall on the same node blocks without a new worker.
- [x] T017 [US3] Implement `record_progress` in `grill_core/gauntlet_runs.py`: appends a coordinator-only transition correlated to the worker's active lease, renews `lease.expires_at` by the original fixed duration, in one transaction.
- [x] T018 [US3] Implement `terminate_worker` in `grill_core/gauntlet_runs.py`: `PREPARED→TERMINAL` (`completed`) or `PREPARED→FAILED` (`failed`, with `--failure-class` recorded as evidence); on the transition that leaves a wave's every `node_ids` member terminal, also commits that wave to `COMPLETE` in the same transaction.
- [x] T019 [US3] Implement `remediate_node` in `grill_core/gauntlet_runs.py` for the `stall` reason: verifies from the worker's own recorded last-progress/dispatch timestamp that the configured stall window elapsed; scans `workers` for a `node_id`-matching entry with `lease.recovery_count == 1` and blocks `REMEDIATION-BUDGET-SPENT` if found; otherwise mints `<node_id>-r<n>` with `recovery_count: 1`, `remediates` set — all in one `transact_with_event` call.
- [x] T020 [US3] Wire `gauntlet-progress-record`, `gauntlet-worker-terminal`, `gauntlet-remediate` (stall path) in `grill_workspace.py`.
- [x] T021 [US3] Prove the User Story 3 contract in `tests/validate_gauntlet_scheduler_contract.py`.

**Checkpoint**: A wave can run to completion end-to-end — dispatch, progress, one bounded stall recovery, wave closure — without transient-retry machinery yet.

## Phase 5: User Story 4 - Retry exactly one classified transient failure (Priority: P3)

**Goal**: Extend `remediate_node` to the `transient-failure` reason, sharing the exact-one-remediation-per-node budget with the stall path.

**Independent Test**: A worker recorded `FAILED` with a transient `--failure-class` is remediated exactly once via `gauntlet-remediate --reason transient-failure`; a node whose budget was already spent by a stall blocks a subsequent transient-failure remediation, and vice versa.

- [x] T022 [P] [US4] Add red cases to `tests/validate_gauntlet_scheduler_contract.py`: transient-failure remediation requires a prior `FAILED` transition with a recorded transient `--failure-class` (not a bare flag); non-transient failure classes are rejected; budget-spent blocks regardless of which reason (stall vs. transient-failure) spent it first, in both orderings.
- [x] T023 [US4] Extend `remediate_node` in `grill_core/gauntlet_runs.py` for the `transient-failure` reason: requires the target worker in `FAILED` state with a recorded transient `failure_class`; reuses the same budget-lineage scan and atomic mint as the `stall` path.
- [x] T024 [US4] Wire the `transient-failure` reason into `gauntlet-remediate` in `grill_workspace.py`.
- [x] T025 [US4] Prove the User Story 4 contract in `tests/validate_gauntlet_scheduler_contract.py`, including both cross-mechanism budget-sharing orderings.

**Checkpoint**: Both remediation mechanisms share one enforced budget per node; no ordering of stall/transient-failure can chain more than one automatic replacement.

## Phase 6: Cross-Cutting Validation and Documentation

- [x] T026 [P] Write `specs/013-scheduler-waves/quickstart.md` with only executable validated commands and FASE-003 boundary expectations (no subagent invocation, no convergence/review/ship).
- [x] T027 [P] Write `specs/013-scheduler-waves/contracts/gauntlet-scheduler-cli.md` documenting the six new commands' inputs/outputs/fail-closed boundaries (mirrors plan.md §Public command surface).
- [x] T028 Run `python3 tests/validate_orchestrator_store_contract.py`, `python3 tests/validate_gauntlet_scheduler_contract.py`, `python3 tests/validate_gauntlet_run_contract.py`, and `python3 tests/run_validators.py`; record reproducible evidence.
- [x] T029 Run independent read-only review of the completed FASE-003 diff and evidence against spec.md/plan.md/ADR-0015–0019; record verdict.

## Dependencies & Execution Order

- T001–T002 may run in parallel; T003 depends on T001; T004 depends on T003; T005 depends on T004; T006 gates all stories.
- T007 → T008 → T009 pins the US1 boundary before US2 builds on it (no code change, regression test only).
- T010 → T011 → T012 → T013 → T014 → T015 delivers the US2 MVP (DAG validation, wave/worker declaration).
- T016 → T017 → T018 → T019 → T020 → T021 depends on T015 (needs a declared wave/worker to observe and remediate).
- T022 → T023 → T024 → T025 depends on T021 (shares `remediate_node`'s budget-lineage scan with the stall path).
- T026–T027 may run after their documented commands are proven (after T025). T028 depends on all implementation tasks. T029 depends on T028.

## Parallel Opportunities

- T001 and T002 have distinct test ownership (Store contract vs. new scheduler contract).
- T026 and T027 are both Markdown-only and follow the final public contract.

## Requirement Traceability

| Requirement | Tasks | Evidence |
|---|---|---|
| FR-001, FR-002, SC-001, SC-004 | T007–T009 | dispatch-order/attestation boundary regression, no new code |
| FR-003, FR-004, FR-006, FR-014, SC-002, SC-009 | T001–T002, T010–T015 | DAG validation, wave declaration, corpus-derived rejection cases |
| FR-005, FR-008(a-c), SC-003 | T001, T003–T004, T012–T013 | wave lifecycle, non-terminal cap, effective-cap enforcement |
| FR-007, FR-008(e), ADR-0015 | T001, T005, T013, T019, T023 | node-lineage schema, shared budget mint/block |
| FR-008(d), SC-010 | T016–T017 | progress recording, TTL renewal |
| FR-009, SC-005, SC-011 | T016, T018–T021 | worker termination, stall remediation, budget enforcement |
| FR-010, SC-006 | T022–T025 | transient-failure classification, shared-budget cross-mechanism block |
| FR-011, FR-012, SC-007 | T011 (scope checks), T029 (independent review) | no non-Claude runtime, no convergence/review/ship path in any new command |
| FR-013 | T017–T020, T023 (journal events each command already commits) | no dedicated command; traced in plan.md §Design |
| FR-015 | T006, T009, T015, T021, T025 (regression sections of each contract proof) | V2/FASE-001/002 command surface unchanged |
| FR-016, SC-012 | T013 (delegated authority exercised, never persisted beyond the dispatch window) | leader authority never becomes a Store-level actor identity — enforced by construction, named in Assumptions |

## Implementation Strategy

1. Build and prove the Store foundation (multi-wave lifecycle, non-terminal cap, node-lineage schema) before any FASE-003 CLI command exists.
2. Pin the US1 attestation/dispatch-order boundary as a regression test — no code, but the foundation every later story assumes.
3. Deliver the US2 MVP: DAG validation and wave/worker declaration for first dispatch only.
4. Add progress/termination/stall remediation (US3), then extend remediation to transient retry (US4) sharing the same budget enforcement.
5. Run the full suite, review independently, and stop at the FASE-003 ship gate. FASE-004 convergence/review/ship and distribution bump remain a separate handoff.

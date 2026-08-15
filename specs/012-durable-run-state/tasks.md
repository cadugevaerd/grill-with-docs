# Tasks: Durable Gauntlet Runs

**Input**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md), [data-model.md](data-model.md), [gauntlet-run-cli.md](contracts/gauntlet-run-cli.md), and [quickstart.md](quickstart.md)

**Tests**: Public contract and Store tests are required by the feature's safety and compatibility criteria.

## Phase 1: Shared Store Foundation

- [X] T001 [P] Extend `tests/validate_orchestrator_store_contract.py` with red schema, fail-closed validation, and fault-injection recovery cases for the optional per-work-item Gauntlet run block and WAL boundaries before T003–T004.
- [X] T002 [P] Create `tests/validate_gauntlet_run_contract.py` with isolated Git fixtures, one-JSON helpers, and root/store/worktree snapshots for FASE-002 public controls.
- [X] T003 Extend `plugin/skills/grill-with-docs/scripts/grill_core/store.py` with strict run/worker/lease/grant/intent schema validation and closed state transitions required by [data-model.md](data-model.md).
- [X] T004 Extend `plugin/skills/grill-with-docs/scripts/grill_core/store.py` with coordinator-only receipt helpers and `transact_with_event` WAL/recovery semantics, including fault boundaries before and after receipt, event, anchor, snapshot, and intent removal.
- [X] T005 Validate T003–T004 through `tests/validate_orchestrator_store_contract.py` and preserve all existing Store contracts.

**Checkpoint**: Store can validate and recover a correlated non-authoritative run transition before any Gauntlet CLI changes.

## Phase 2: User Story 1 - Record Recovery for an Interrupted Run (Priority: P1) 🎯 MVP

**Goal**: Admit/reuse a durable run and record one explicit recovery decision for later scheduling without dispatching work.

**Independent Test**: A current activation creates one run, a repeat reuses it, and an eligible interrupted record gains one recovery decision while stale/ineligible state remains unchanged.

- [X] T006 [P] [US1] Add red admission/reuse/resume/stale/no-write public cases to `tests/validate_gauntlet_run_contract.py`.
- [X] T007 [US1] Create coordinator-only `plugin/skills/grill-with-docs/scripts/grill_core/gauntlet_runs.py` admission, projection, lease, and explicit recovery helpers using the Store transaction protocol.
- [X] T008 [US1] Wire durable `gauntlet-run`, optional-run `gauntlet-status`, and `gauntlet-resume --run-id` in `plugin/skills/grill-with-docs/scripts/grill_workspace.py` after fresh FASE-001 activation proof.
- [X] T009 [US1] Prove the User Story 1 contract in `tests/validate_gauntlet_run_contract.py`, including no spawned process, no scheduler, no retry/relaunch, and V2 output preservation.

## Phase 3: User Story 2 - Diagnose Worker Progress Safely (Priority: P2)

**Goal**: Persist and project coordinator-owned correlated evidence without granting workers Store or receipt authority.

**Independent Test**: A run projection identifies one run/wave/worker/lease/base/receipt correlation; malformed or worker-originated evidence is rejected without mutation.

- [X] T010 [P] [US2] Add correlation, receipt, authority, digest-format, and read-only-status cases to `tests/validate_gauntlet_run_contract.py`.
- [X] T011 [US2] Extend `plugin/skills/grill-with-docs/scripts/grill_core/gauntlet_runs.py` with strict transition-correlation records and coordinator-only evidence references.
- [X] T012 [US2] Extend `plugin/skills/grill-with-docs/scripts/grill_workspace.py` status projection and closed error translation for run evidence states.
- [X] T013 [US2] Prove the User Story 2 contract in `tests/validate_gauntlet_run_contract.py` and retain `tests/validate_attestation_contract.py` as an unwired future-dispatch boundary.

## Phase 4: User Story 3 - Isolate and Clean Up Worker Work (Priority: P3)

**Goal**: Prepare one isolated worker workspace and safely preserve or clean it through explicit intent/reconciliation records.

**Independent Test**: An exact base-pinned derived workspace is prepared without worker execution; only a recorded clean/terminal/converged/eligible fixture removes that workspace, while every failure class is preserved.

- [X] T014 [US3] Add red Git fixture cases for base pinning, branch/worktree derivation, grant validation, PREPARING/CLEANING interruption, orphan preservation, and exact cleanup to `tests/validate_gauntlet_run_contract.py`.
- [X] T015 [US3] Implement worker grant validation, derived workspace intent/reconciliation, and exact Git worktree preparation in `plugin/skills/grill-with-docs/scripts/grill_core/gauntlet_runs.py`.
- [X] T016 [US3] Wire `gauntlet-prepare-worker` and `gauntlet-cleanup --run-id --worker-id` in `plugin/skills/grill-with-docs/scripts/grill_workspace.py` without introducing worker execution, waves, or convergence.
- [X] T017 [US3] Prove preservation/cleanup and V2 compatibility through `tests/validate_gauntlet_run_contract.py` and `tests/validate_workspace_contract.py`.

## Phase 5: Cross-Cutting Validation and Documentation

- [X] T018 [P] Update `specs/012-durable-run-state/quickstart.md` with only executable validated commands and FASE-002 boundary expectations.
- [X] T019 Run `python3 tests/validate_orchestrator_store_contract.py`, `python3 tests/validate_gauntlet_run_contract.py`, and `python3 tests/run_validators.py`; record reproducible evidence in `.specify/reports/verify-review-ship/verify.md`.
- [ ] T020 Run independent read-only review of the completed FASE-002 diff and evidence; record verdict in `.specify/reports/verify-review-ship/review.md`.

## Dependencies & Execution Order

- T001–T002 may run in parallel; T003 depends on T001; T004 depends on T003; T005 gates all stories.
- T006 → T007 → T008 → T009 delivers the MVP durable run/recovery path.
- T010 → T011 → T012 → T013 depends on T009.
- T014 → T015 → T016 → T017 depends on T013 because these tasks share the run validator, coordinator module, and public CLI with US2.
- T018 may run after its documented commands are verified. T019 depends on all implementation tasks. T020 depends on T019.

## Parallel Opportunities

- T001 and T002 have distinct test ownership.
- T018 is Markdown-only and follows the final public contract.

## Requirement Traceability

| Requirement | Tasks | Evidence |
|---|---|---|
| FR-001, FR-003, FR-010, SC-001 | T001–T009 | durable admission/reuse/recovery contract |
| FR-002, FR-004, FR-005, SC-002 | T001–T005, T010–T013 | validated Store/WAL and coordinator-only correlated evidence |
| FR-006, FR-007, SC-004 | T014–T017 | exact derived workspace and closed passive grant |
| FR-008, FR-009, SC-005 | T014–T017 | intent/reconciliation and preservation/cleanup matrix |
| FR-011, SC-003 | T001–T005, T006, T010, T014, T017 | fault-injection, stale/unsafe, and no-write controls |
| FR-012, SC-006 | T009, T013, T017, T019 | V2 and no-scheduler/release regression suite |
| SC-001–SC-006 | T009, T013, T017, T019 | public scenarios and full validator evidence |

## Implementation Strategy

1. Build and prove the Store/WAL foundation before exposing any FASE-002 CLI mutation.
2. Deliver the durable-run/recovery MVP without preparing a worker.
3. Add correlated evidence projection, then isolated worker preparation and cleanup.
4. Run the full suite, review independently, and stop at the FASE-002 ship gate. FASE-003 scheduler and FASE-004 convergence/release remain separate handoffs.

# Tasks: Convergência, Revisão e Entrega Verificável

**Input**: Design documents from `specs/014-converge-review-ship/`
**Prerequisites**: plan.md, spec.md, checklists/converge-requirements.md

## Phase 1: Store Foundation

- [x] T001 [P] Add red cases to `tests/validate_orchestrator_store_contract.py`: `run_edges` gains `ADMITTED→COMPLETE`/`RECOVERY_ELIGIBLE→COMPLETE`; run key-set admits optional write-once `dag_content_sha256`/`abandon_authorization` (absent→present once, any further write rejected regardless of match); wave key-set admits optional `last_conflict`/`converged`; the newest-wave-only mutation guard's narrow exception (only `last_conflict`/`converged` may differ on a superseded wave, `state`/`node_ids` still byte-identical).
- [x] T002 [P] Create `tests/validate_gauntlet_converge_contract.py` with isolated Git fixtures for FASE-004 public controls (`gauntlet-converge`, `gauntlet-run-abandon`, extended `gauntlet-wave-declare`, extended `checkpoint --step ship`, extended `gauntlet-status`) before T007–T020 exist.
- [x] T003 Replace the run's `_closed_object` call (`store.py`) with the `required`/`optional` style `_transition_fields` already uses; add the write-once transition guard for `dag_content_sha256`/`abandon_authorization` (same mechanism that already makes `admission` immutable, applied per-key: absent→present exactly once, any further write rejected).
- [x] T004 Replace the wave's inline exact-match key-set check (`store.py`, `set(wave) != {"state", "node_ids"}`) with `required`/`optional` admitting `last_conflict`/`converged`; validate `last_conflict`'s four keys (`node_ids` non-empty `SAFE_NAME_RE` list, `reason` in `{scope-overlap, content-conflict}`, `execution_branch_head`/`worker_heads` values `HEX40`); validate `converged` as strict boolean.
- [x] T005 Rewrite the newest-wave-only mutation guard (`store.py`, the `wave_id != newest_wave_id` short-circuit): for a non-newest `wave_id` present in both snapshots, require `state`/`node_ids` byte-identical and permit only `last_conflict`/`converged` to differ; the two other existing conditions (state-edge validity, `node_ids` write-once) still apply unconditionally to the newest wave, unchanged.
- [x] T006 Add `ADMITTED→COMPLETE`/`RECOVERY_ELIGIBLE→COMPLETE` to `run_edges` (`store.py`).
- [x] T007 Add write-once immutability for `converged` (absent→`true` exactly once, never `true→absent`) alongside T003's guard, same mechanism.
- [x] T008 Validate T001–T007 through `tests/validate_orchestrator_store_contract.py` and preserve all existing Store contracts (FASE-001/002/003 regression).

**Checkpoint**: The Store can represent and validate a run/wave with a pinned DAG, a durable conflict record, a durable abandonment record, and a real `COMPLETE`/`BLOCKED` terminal lifecycle, before any FASE-004 CLI command exists.

## Phase 2: User Story 1 - Integrar em série apenas mudanças limpas de cada wave concluída (Priority: P1) 🎯 MVP

**Goal**: `gauntlet-converge` integrates a wave's successfully-terminal workers into `execution_branch`, wave by wave, with fail-closed scope/content conflict detection and idempotent replay.

**Independent Test**: A wave with two non-overlapping successful workers converges both into `execution_branch` in one call; a wave with declared-scope overlap blocks `INTEGRATION_CONFLICT` before any merge, converging nothing; a real Git conflict blocks just the offending worker without reverting an earlier successful merge in the same call; replaying an already-converged wave (including the wave that completed the run) returns `WAVE-CONVERGED-REUSED` with no new merge attempt.

- [x] T009 [P] [US1] Add red cases to `tests/validate_gauntlet_converge_contract.py`: `gauntlet-dag-validate`'s hash is computed and returned for pinning; `DAG-PIN-MISSING`/`DAG-CONTENT-MISMATCH` from both `gauntlet-converge` and `gauntlet-wave-declare`; `EXECUTION-BRANCH-UNSET`/`-MISMATCH` (including detached-`HEAD`); `EXECUTION-TREE-DIRTY` (tracked dirt, and the untracked-overwrite pre-check with a `-uall`-only-visible untracked directory); `WAVE-CONVERGENCE-OUT-OF-ORDER` (out-of-sequence wave, and a still-`ACTIVE` wave); clean multi-wave integration; scope-overlap block via direct Store injection (unreachable via CLI once T012 ships); real Git content-conflict block, its fingerprint-based reentry (unchanged heads re-blocks without recompute, changed head recomputes), and its clearing on eventual success; idempotent replay of a converged wave, both non-terminal and `COMPLETE`-run cases; a permanently `FAILED` sibling never reaching `converged` while its wave's other members still merge.
- [x] T010 [US1] Add DAG-content-hash computation to the DAG-loading path in `grill_core/gauntlet_runs.py` (`store.jcs_sha256` of the parsed document) and return it from `gauntlet-dag-validate`'s projection.
- [x] T011 [US1] Implement the DAG-pin write in `declare_wave` (`grill_core/gauntlet_runs.py`): reinforce `expect_placeholder` with `node_ids == WAVE_PENDING_NODE_IDS`; write `dag_content_sha256` in the same transaction as the first real wave's declaration; revalidate `--dag` against an existing pin on every subsequent call, blocking `DAG-CONTENT-MISMATCH`/`DAG-PIN-MISSING` per plan.md §Store schema extension #2.
- [x] T012 [US1] Implement the scope pre-pass as a declare-time rejection in `declare_wave` (`grill_core/gauntlet_runs.py`): checks pairwise `files` overlap among the wave's requested `node_ids` (from the pinned/validated DAG), blocking `WAVE-SCOPE-OVERLAP` before any worker is prepared (FR-004b).
- [x] T013 [US1] Add `include_untracked: bool = True` keyword to `_exact_worktree_is_clean` (`grill_core/gauntlet_runs.py`), default preserving `cleanup_worker`'s existing two call sites.
- [x] T014 [US1] Implement `converge_wave` in `grill_core/gauntlet_runs.py` per plan.md §Convergence's six ordered steps: admission boundary; DAG pin check; terminal-run check (`BLOCKED`→`RUN-NOT-ELIGIBLE`, `COMPLETE`→`WAVE-CONVERGED-REUSED` fast path) then non-terminal reconciliation (mint any pending `wave-converged`/`run.completed`); `execution_branch`/tree state (live branch check, `-uall` untracked capture, `EXECUTION-TREE-DIRTY`); wave order (with the already-converged carve-out and the `wave.state == "COMPLETE"` precondition); scope pre-pass and merge-set definition (`state == "TERMINAL"` lineage-heads only); the merge loop itself (one Store transaction per successful worker, fingerprint-based conflict reentry, atomic per-worker revert, `last_conflict` clearing on eventual success); the closing chain (`wave-converged` then `run.completed`, inline in the same call when reached).
- [x] T015 [US1] Wire `gauntlet-converge` in `grill_workspace.py`, following the existing `gauntlet-*` argparse/handler/`CliFailure` pattern; wire the DAG-pin/scope-overlap blocks into `gauntlet-wave-declare`'s existing handler.
- [x] T016 [US1] Prove the User Story 1 contract in `tests/validate_gauntlet_converge_contract.py`.

**Checkpoint**: A wave's successful workers converge into `execution_branch` deterministically, fail-closed on scope/content conflict, idempotent on replay — independent of the ship gate or abandonment machinery.

## Phase 3: User Story 2 - Revisão independente antes do gate humano de ship (Priority: P1)

**Goal**: Confirm `review` needs no new mechanism — it is already one of the eleven macro-steps dispatched identically — and pin that boundary as a regression test.

**Independent Test**: `review`'s checkpoint dispatches at tier `large`, exactly like any other macro-step; a `blocked` checkpoint on it already halts `ship` via the existing step-sequence gate, with no new code path.

- [x] T017 [US2] Add a red case to `tests/validate_gauntlet_converge_contract.py` proving `review` dispatches at `TIER_POLICY["review"] == "large"` and that a `blocked` `review` checkpoint already prevents `checkpoint --step ship` from being accepted (regression-pins the "no new mechanism" claim against `grill_workspace.py`).
- [x] T018 [US2] No production code change: this story's requirement is already satisfied by the unmodified FASE-001/003 dispatch mechanism. Document the boundary in `specs/014-converge-review-ship/quickstart.md`.

**Checkpoint**: The `review` boundary this phase's ship gate builds on top of is pinned by a regression test, not just narrative.

## Phase 4: User Story 3 - Ship nunca despacha sobre convergência incompleta (Priority: P2)

**Goal**: `checkpoint --step ship --state complete` blocks `CONVERGENCE-INCOMPLETE` unless every admitted run for the work item is terminal (`COMPLETE`/`BLOCKED`); `gauntlet-run-abandon` is the one human act that can make a permanently-stuck run terminal.

**Independent Test**: A work item with any non-terminal admitted run blocks `ship`'s `--state complete` transition, citing the pending run, before attestation; a work item with only terminal runs (or none) is unaffected; `gauntlet-run-abandon` with a valid `human-authorization/v1` bundle marks a stale run `BLOCKED`, after which `ship` becomes reachable if nothing else is pending.

- [x] T019 [P] [US3] Add red cases to `tests/validate_gauntlet_converge_contract.py`: `checkpoint --step ship --state complete` blocked `CONVERGENCE-INCOMPLETE` by a non-terminal run (including a DAG-partially-despachado run with zero pending workers to name), by the non-"default-selected" run among several admitted, and released once every run is terminal; the gate as a no-op for V2/no-Store/no-run work items; `gauntlet-run-abandon` success, `RUN-ABANDON-REUSED` on an identical resubmission, `RUN-NOT-ELIGIBLE` on a divergent resubmission or an already-`COMPLETE` run, `ABANDON-AUTHORIZATION-INVALID` on a missing/malformed/unapproved bundle; abandonment succeeding on a run whose `base_commit` no longer resolves in Git.
- [x] T020 [US3] Implement `list_run_states` in `grill_core/gauntlet_runs.py`: `store.store_exists(root)` guard first (empty list if absent), then `_read_runs(..., absent_ok=True)`, returning `{run_id, state}` per admitted run.
- [x] T021 [US3] Implement `abandon_run` in `grill_core/gauntlet_runs.py`: derives `base_commit`/identity from the target run's own recorded `admission` (never the current activation), skips `_require_base_commit`, applies the write-once `abandon_authorization` guard (T003/T007), flips `state` to `BLOCKED` in the same transaction, mints `gauntlet.run.abandoned`.
- [x] T022 [US3] Wire `gauntlet-run-abandon` in `grill_workspace.py`: loads `--attestation <path>` via the existing `load_checkpoint_attestation`, translates any `CliFailure` it raises to `ABANDON-AUTHORIZATION-INVALID`; validates the loaded bundle with `attestation._validate_human_authorization(bundle, run_id)` standalone, translating any `AttestationError` to the same code; calls `gauntlet_runs.abandon_run`.
- [x] T023 [US3] Add the `CONVERGENCE-INCOMPLETE` check to `checkpoint_command` (`grill_workspace.py`): call `list_run_states`, block if any entry's `state` is outside `{COMPLETE, BLOCKED}`, inserted after the existing step-sequence gate and before `verify_checkpoint_attestation`.
- [x] T024 [US3] Prove the User Story 3 contract in `tests/validate_gauntlet_converge_contract.py`.

**Checkpoint**: `ship` is unreachable while any run genuinely has unconverged work, and a human has one clean, attributable way to unstick a run that never will converge.

## Phase 5: User Story 4 - Observabilidade compacta de wave e bloqueio via `gauntlet-status` (Priority: P3)

**Goal**: `gauntlet-status` projects wave state and the most recent unresolved `last_conflict`, without exposing raw Store internals.

**Independent Test**: A run with waves in distinct states returns a `waves` list with correct `wave_id`/`state`/`converged_count`/`member_count`, excluding the bootstrap placeholder; a run with an `INTEGRATION_CONFLICT` on a superseded (non-newest) wave still surfaces that wave's `last_conflict`.

- [x] T025 [P] [US4] Add red cases to `tests/validate_gauntlet_converge_contract.py`: `waves` list excludes the placeholder, orders by declaration, reports correct counts; `last_conflict` surfaces from the correct (possibly non-newest) wave when present, absent when resolved.
- [x] T026 [US4] Extend `run_projection` in `grill_core/gauntlet_runs.py`: add the `waves` list (excluding the placeholder via the same `expect_placeholder`-derived check T011 uses) and the reverse-scan `last_conflict` lookup.
- [x] T027 [US4] Prove the User Story 4 contract in `tests/validate_gauntlet_converge_contract.py`.

**Checkpoint**: Wave and conflict state are observable through the public command surface alone, without reading the Store directly.

## Phase 6: Cross-Cutting Validation, Documentation, and Distribution

- [x] T028 [P] Write `specs/014-converge-review-ship/quickstart.md` with only executable validated commands and FASE-004 boundary expectations (no conflict auto-resolution, no push/release, `review` unchanged).
- [x] T029 [P] Write `specs/014-converge-review-ship/contracts/gauntlet-converge-cli.md` documenting the new/extended commands' inputs/outputs/fail-closed boundaries (mirrors plan.md §Public command surface).
- [x] T030 Bump the plugin version 2.7.0 → 2.8.0 across all eight distribution surfaces (`plugin/.claude-plugin/plugin.json`, `plugin/.codex-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.agents/plugins/marketplace.json`, `tests/validate_distribution.py`, `plugin/skills/grill-with-docs/SKILL.md`, `plugin/skills/grill-with-docs/references/session-protocol.md`, `README.md`), per FR-013/SC-007.
- [x] T031 Run `python3 tests/validate_orchestrator_store_contract.py`, `python3 tests/validate_gauntlet_converge_contract.py`, `python3 tests/validate_gauntlet_scheduler_contract.py`, `python3 tests/validate_gauntlet_run_contract.py`, `python3 tests/validate_distribution.py`, and `python3 tests/run_validators.py`; record reproducible evidence.
- [x] T032 Run independent read-only review of the completed FASE-004 diff and evidence against spec.md/plan.md/ADR-0020–0023; record verdict.

## Dependencies & Execution Order

- T001–T002 may run in parallel; T003 depends on T001; T004–T005 depend on T003; T006–T007 depend on T004/T005; T008 gates all stories.
- T009 → T010 → T011 → T012 → T013 → T014 → T015 → T016 delivers the US1 MVP (convergence itself). T014 depends on T011–T013 (pin, scope, tree helpers) all existing first.
- T017 → T018 has no dependency on Phase 2 (pure regression + documentation of already-shipped behavior) but is sequenced after US1 since it references convergence in its own documentation.
- T019 → T020 → T021 → T022 → T023 → T024 depends on T008 (Store terminal-lifecycle foundation) and T014 (a run must be able to reach `COMPLETE` for the gate to have a real positive case) but not on T017–T018.
- T025 → T026 → T027 depends on T014 (needs real wave/conflict state to project).
- T028–T029 may run after their documented commands are proven (after T024/T027). T030 is independent, may run any time before T031. T031 depends on all implementation tasks. T032 depends on T031.

## Parallel Opportunities

- T001 and T002 have distinct test ownership (Store contract vs. new converge contract).
- T009, T019, T025 (red cases for three independent user stories) may be drafted in parallel once T002 exists, though each story's own implementation sequence (T010+, T020+, T026+) stays serial.
- T028, T029, T030 are independent artifacts with no shared file.

## Requirement Traceability

| Requirement | Tasks | Evidence |
|---|---|---|
| FR-001, FR-004, FR-005, SC-001, SC-003 | T006–T008, T010, T014, T016 | run terminal lifecycle, DAG-pin gate, wave-order/reuse, merge-set success-only predicate |
| FR-002, FR-004b, SC-002 | T004–T005, T012, T014, T016 | scope pre-pass at declare (primary) and converge (residual, Store-injection-only) |
| FR-003, SC-003 | T014, T016 | content-conflict fingerprint reentry, atomic per-worker revert |
| FR-004c, ADR-0021 | T003, T010–T011 | DAG-pin write-once field, `expect_placeholder` reinforcement, mismatch/missing blocks |
| FR-006 | T005 | `INTEGRATION_CONFLICT` never automatically resolved — enforced by omission (no auto-resolution code path exists) |
| FR-007, FR-008, SC-004 | T019–T024 | ship gate scans every admitted run, no-op for V2/no-run |
| FR-009 | T021–T022 | no push/release path in `abandon_run`/its CLI wiring |
| FR-010 | T014, T021 | event minting for all five new categories, receipt naming/category |
| FR-011, SC-005 | T025–T027 | `waves`/`last_conflict` projection |
| FR-012 | T015, T022 | `gauntlet_run_admission` fronteira on `gauntlet-converge`; explicit exemption, documented, on `gauntlet-run-abandon` |
| FR-013, SC-007 | T030–T031 | version bump, `validate_distribution.py` |
| FR-014, ADR-0020 | T003, T007, T020–T022, T024 | abandonment write-once bundle, identity-derivation exemption, reuse/divergence verdicts |
| User Story 2 (`review`) | T017–T018 | regression pin, no new code |

## Implementation Strategy

1. Build and prove the Store foundation (terminal lifecycle, DAG-pin field, `last_conflict`/`converged` fields, guard exceptions) before any FASE-004 CLI command exists.
2. Deliver the US1 MVP: `gauntlet-converge` itself, plus the two `gauntlet-wave-declare` extensions (scope pre-pass, DAG pin) it structurally depends on.
3. Pin the US2 `review` boundary as a regression test — no code, but the fact the ship gate (US3) builds on.
4. Add the ship-completeness gate and `gauntlet-run-abandon` (US3), which depend on the Store foundation and on convergence being able to reach `COMPLETE` for a real positive test case.
5. Extend `gauntlet-status`'s projection (US4), which depends on real wave/conflict state existing.
6. Run the full suite, bump the version, review independently, and stop at the FASE-004 ship gate.

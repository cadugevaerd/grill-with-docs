# Tasks: Gauntlet Loop Activation

**Input**: `specs/011-gauntlet-loop/{spec.md,plan.md,research.md,data-model.md,contracts/gauntlet-cli.md,quickstart.md}`
**Work item**: `feature-gauntlet-loop-0447622ec0714933a4e791d0b58b5420`
**Execution DAG**: [`execution-dag.json`](execution-dag.json) (`grill-gauntlet-execution-dag/v1`)

**Tests**: Contract-first tests are required by the feature contract. Run the new
validator through the public CLI and then run the full validator suite.

## Phase 1: Setup

**Purpose**: Package the immutable Claude catalog and establish the validator
fixtures without changing existing V2 behavior.

- [X] T001 [P] Add the immutable shipped Claude catalog, copied from the verified fixture and with no test-time dependency, at `plugin/skills/grill-with-docs/assets/claude-code-local-skills.catalog.json`.
- [X] T002 [P] Add failing rebind and mode-preservation cases for preview, apply, idempotency, stale CAS, interruption, and `fchmod` failure to `tests/validate_work_item_v3_contract.py`.

---

## Phase 2: Foundational safety primitives

**Purpose**: Complete the shared safe-write and explicit-rebind boundary before any Gauntlet activation path exists.

- [X] T003 Update descriptor-relative replacement so an `os.fchmod` failure raises `MODE-PRESERVATION-FAILED` before data write or rename in `plugin/skills/grill-with-docs/scripts/grill_core/work_item_v3.py` (depends on T002).
- [X] T004 Extend the public `migrate-v3` parser and handler with preview-first `--rebind-workflow`, V3 gate, work-item lock, CAS, unrelated-field preservation, and exact JSON outcomes in `plugin/skills/grill-with-docs/scripts/grill_workspace.py` (depends on T003).
- [X] T005 Run `python3 tests/validate_work_item_v3_contract.py` and resolve only the rebind/mode-preservation failures in `tests/validate_work_item_v3_contract.py` (depends on T004).

**Checkpoint**: A legacy V3 work item can be explicitly rebound without a
weaker path write, implicit activation, or mode loss.

---

## Phase 3: User Story 1 — Activate a verified Gauntlet work item (Priority: P1) 🎯 MVP

**Goal**: Create one strict, durable activation record only when all V3 and
Claude capability proofs match.

**Independent Test**: Activate an eligible V3 work item, inspect the exact
record, repeat it for `REUSED`, and submit a different worker limit for
`ACTIVATION-CONFLICT`.

- [X] T006 [US1] Write failing public-CLI contract cases for `gauntlet-init`, record schema, selected workers 1–5, fixed fifteen-minute stall limit, exact tier policy, `ACTIVATED`, `REUSED`, and `ACTIVATION-CONFLICT` in `tests/validate_gauntlet_activation_contract.py` (depends on T001, T005).
- [X] T007 [US1] Implement strict `grill-gauntlet/v1` parsing, immutable identity derivation, Claude-only eleven-step proof, tier-policy construction, and descriptor-safe global configuration transaction/lock in `plugin/skills/grill-with-docs/scripts/grill_core/gauntlet.py` (depends on T001, T006).
- [X] T008 [US1] Add `gauntlet-init ROOT --work-id ID --max-workers N` and its one-JSON public error boundary in `plugin/skills/grill-with-docs/scripts/grill_workspace.py` (depends on T007).
- [X] T009 [US1] Run `python3 tests/validate_gauntlet_activation_contract.py` and make the User Story 1 cases pass without changing existing V2 command output in `tests/validate_gauntlet_activation_contract.py` (depends on T008).

---

## Phase 4: User Story 2 — Prevent unsafe or unsupported activation (Priority: P1)

**Goal**: Fail closed before any configuration mutation for unsupported,
altered, malformed, concurrent, or unsafe inputs.

**Independent Test**: Exercise V2, unproven Codex/Hermes, stale/tampered
catalog, malformed configuration, lock contention, safe-path failure, and
every error-code mapping; each leaves no activation or run state.

- [X] T010 [US2] Extend `tests/validate_gauntlet_activation_contract.py` with failing no-mutation and one-JSON cases for all closed skill/catalog error mappings, fallback mapping, V2, unproven runtimes, malformed input/configuration, symlinks, contention, and unavailable safe descriptors (depends on T009).
- [X] T011 [US2] Add closed kebab-case error translation, trusted-asset/catalog verification, `SAFE-PATH-UNAVAILABLE` handling, duplicate-key schema rejection, CAS/replacement interruption handling, and lock cleanup/ordering in `plugin/skills/grill-with-docs/scripts/grill_core/gauntlet.py` (depends on T010).
- [X] T012 [US2] Preserve one-JSON top-level `BLOCKED` responses and map only valid status-subject proof failures through the Gauntlet boundary in `plugin/skills/grill-with-docs/scripts/grill_workspace.py` (depends on T011).
- [X] T013 [US2] Run `python3 tests/validate_gauntlet_activation_contract.py` and make every unsafe-activation case leave `.grill/gauntlet.yaml` absent or byte-identical in `tests/validate_gauntlet_activation_contract.py` (depends on T012).

---

## Phase 5: User Story 3 — Admit a run and inspect controls safely (Priority: P2)

**Goal**: Provide read-only status plus admission-only run/resume/cleanup
controls, without introducing a scheduler or worker state.

**Independent Test**: Read each closed status state, receive
`RUN-ADMITTED` for a current activation, and receive the specified blocked
responses for resume/cleanup with no worker, worktree, branch, or run record.

- [X] T014 [US3] Extend `tests/validate_gauntlet_activation_contract.py` with failing public-CLI cases for status precedence, stale identity, top-level versus status-projected blocks, admission-only run, and non-mutating resume/cleanup (depends on T013).
- [X] T015 [US3] Implement read-only status projection and current-identity revalidation for run/resume/cleanup, including `ACTIVATION-REQUIRED`, `RUN-ADMITTED`, and `SCHEDULING-NOT-AVAILABLE`, in `plugin/skills/grill-with-docs/scripts/grill_core/gauntlet.py` (depends on T014).
- [X] T016 [US3] Add `gauntlet-status`, `gauntlet-run`, `gauntlet-resume`, and `gauntlet-cleanup` parsers/handlers with exactly one JSON object on stdout in `plugin/skills/grill-with-docs/scripts/grill_workspace.py` (depends on T015).
- [X] T017 [US3] Run `python3 tests/validate_gauntlet_activation_contract.py` and make the User Story 3 cases pass while proving no scheduler, worker, worktree, branch, or durable run record is created in `tests/validate_gauntlet_activation_contract.py` (depends on T016).

---

## Phase 6: Polish and cross-cutting validation

**Purpose**: Verify distribution-safe documentation and all existing contracts.

- [X] T018 [P] Reconcile the commands, non-scheduler boundary, rebind prerequisite, and validator instructions with the implemented output in `specs/011-gauntlet-loop/quickstart.md` (depends on T017).
- [X] T019 Run `python3 tests/validate_gauntlet_activation_contract.py`, `python3 tests/validate_work_item_v3_contract.py`, `python3 tests/validate_step_skill_registry_contract.py`, and `python3 tests/run_validators.py`; record only reproducible validation evidence in `.grill/work-items/feature-gauntlet-loop-0447622ec0714933a4e791d0b58b5420/ROUND-LOG.jsonl` (depends on T005, T017, T018).
- [X] T020 Run `git diff --check` for the implementation files and confirm either synchronized distribution versions remain unchanged while this delivery stays aggregated, or every distribution surface is bumped before an independent FASE-001 ship, starting at `plugin/.claude-plugin/plugin.json` (depends on T019).

---

## Dependencies & Execution Order

The authoritative dependency graph is [`execution-dag.json`](execution-dag.json).
Its wave order is `T001/T002` → `T003` → `T004` → `T005` → `T006` →
`T007` → `T008` → `T009` → `T010` → `T011` → `T012` → `T013` → `T014` →
`T015` → `T016` → `T017` → `T018` → `T019` → `T020`. `T001` and `T002`
are the only implementation tasks intentionally parallel: they change distinct
files and do not rely on one another. All later same-file work is serialized.

## Model-tier assignment

The DAG encodes `small` only for Markdown reconciliation, `medium` for tests
and code execution, and `large` for later plan/review gates. It never exceeds
five worker slots; FASE-001 itself has no worker dispatch or scheduler.

## Implementation Strategy

1. Finish the rebind primitive and test it before exposing activation.
2. Deliver User Story 1 as the MVP: strict activation only.
3. Harden every failure path in User Story 2.
4. Add admission-only controls in User Story 3.
5. Run the full validation gate; human ship remains outside this phase.

## Format validation

All 20 tasks use the required checkbox, sequential ID, optional `[P]`,
story label where applicable, and explicit file path format.

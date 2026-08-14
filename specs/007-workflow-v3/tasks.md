# Tasks: Canonical Step Skills

**Input**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/skill-resolution.md`
**Tests**: required contract matrix in `tests/validate_step_skill_registry_contract.py`.

## Phase 1: Foundation

- [x] T001 Define the exact ordered registry and runtime capability schema in `plugin/skills/grill-with-docs/assets/workflow-step-skills.json`.
- [x] T002 [P] Define the immutable trusted catalog pin in `plugin/skills/grill-with-docs/assets/workflow-trusted-catalogs.json`.
- [x] T003 [P] Capture the observed Claude native catalog fixture in `tests/fixtures/workflow-step-skills/claude-catalog.json`.

## Phase 2: User Story 1 — Resolve a required step safely (P1)

**Independent test**: all eleven supported-runtime steps resolve to distinct canonical identities with stable hashes.

- [x] T004 [US1] Implement strict registry/catalog parsing and byte-level SHA-256 pins in `plugin/skills/grill-with-docs/scripts/grill_core/step_skills.py`.
- [x] T005 [US1] Implement `skill-resolution/v1` creation and digest verification in `plugin/skills/grill-with-docs/scripts/grill_core/step_skills.py`.
- [x] T006 [US1] Add the successful-resolution and repeatability contract cases in `tests/validate_step_skill_registry_contract.py`.

## Phase 3: User Story 2 — Reject an unproven capability (P1)

**Independent test**: each altered registry/catalog/version/entrypoint/runtime fact blocks before a resolution is returned.

- [x] T007 [US2] Reject unresolved runtimes, catalog mismatch and untrusted pins in `plugin/skills/grill-with-docs/scripts/grill_core/step_skills.py`.
- [x] T008 [US2] Validate invocation context and recompute the canonical resolution before accepting a receipt in `plugin/skills/grill-with-docs/scripts/grill_core/step_skills.py`.
- [x] T009 [US2] Add adversarial mutation cases, including self-authorization and direct/emulated/best-effort rejection, in `tests/validate_step_skill_registry_contract.py`.

## Phase 4: Cross-cutting Validation

- [x] T010 Run `python3 tests/validate_step_skill_registry_contract.py` and record the result in `specs/007-workflow-v3/quickstart.md`.
- [x] T011 Recheck requirements quality against `specs/007-workflow-v3/checklists/canonical-skills.md`.

## Dependencies

`T001–T003 → T004–T006 → T007–T009 → T010–T011`. The two user stories share the registry foundation; User Story 2 is the fail-closed validation of User Story 1's output.

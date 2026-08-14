# Feature Specification: Explicit Workflow V3 Migration

**Phase**: FASE-002
**Source handoff**: `.grill/work-items/feature-workflow-v3-7dc283c84fb54e6b8f10a9c4546cd473/handoffs/FASE-002-SPECIFY-HANDOFF.md`

## User Story 1 — Inspect then apply a V3 workflow (Priority: P1)

An operator previews a V2-to-V3 migration, then applies exactly the version they inspected.

**Acceptance scenarios**:

1. Given a valid V2 workflow, `migrate` returns a no-write preview with the target hash.
2. Given that preview identity, `migrate --apply` writes a V3 document with the live registry pin.
3. Given changed workflow bytes after preview, apply blocks rather than overwriting them.

## User Story 2 — Preserve V2 and reject unsafe V3 (Priority: P1)

Existing V2 projects remain valid; an incomplete, forged, reordered, or unpinned V3 workflow never becomes execution-ready.

**Acceptance scenarios**:

1. V2 compatibility stays independent from V3 markers and essentials.
2. V3 rejects a placeholder or divergent registry pin and any non-canonical external-step order.
3. `ensure_workflow --hook` remains read-only and emits one structured response if its V3 dependency fails to load.

## Requirements

- **FR-001**: The system MUST materialize V3 only through a preview-and-identity-confirmed apply.
- **FR-002**: A materialized V3 workflow MUST pin the exact SHA-256 of the shipped canonical registry.
- **FR-003**: V3 execution readiness MUST require the ordered eleven-step external cycle and the current registry pin.
- **FR-004**: V2 reading and bootstrap MUST remain compatible and independent of V3 readiness.
- **FR-005**: A migration and hook failure MUST fail closed with one structured response and no direct write.

## Success Criteria

- **SC-001**: `tests/validate_workflow_v3_contract.py` passes its complete migration/order matrix.
- **SC-002**: `tests/validate_v3_wiring_contract.py` passes V2/V3 wiring and hook behavior.
- **SC-003**: A V3 workflow with a forged pin or reordered cycle is blocked before execution.

## Scope

In: `workflow_v3.py`, V3 template, `ensure_workflow.py` wiring and their contract tests.
Out: work-item migration, project store, and acceptance of step outputs.

# Feature Specification: Work Item V3 and Project Store

**Phase**: FASE-003
**Source handoff**: `.grill/work-items/feature-workflow-v3-7dc283c84fb54e6b8f10a9c4546cd473/handoffs/FASE-003-SPECIFY-HANDOFF.md`

## User Story 1 — Migrate a work item safely (Priority: P1)

An operator can preview and apply an atomic V2-to-V3 work-item migration without writes escaping its pinned bundle.

**Acceptance scenarios**:

1. Preview never mutates and apply requires V3 production-reader support.
2. Directory-FD operations reject final or ancestor symlinks, including a swap while the lock is held.
3. Concurrent or changed input ends in named divergence/blocking rather than partial mutation.

## User Story 2 — Keep a durable project identity and store (Priority: P1)

Linked worktrees share one logical project identity and a guarded journal/store without allowing stale, divergent or untrusted state to overwrite it.

**Acceptance scenarios**:

1. Project identity remains stable across valid worktrees.
2. Lock/CAS/journal integrity failures block with stable outcomes.
3. V2 readers retain their prior behavior.

## Requirements

- **FR-001**: V2/V3 work items MUST dual-read and V3 migration MUST be preview-first.
- **FR-002**: Migration writes MUST remain relative to a no-follow pinned directory descriptor.
- **FR-003**: V3 immutable metadata and worktree identity MUST be validated before use.
- **FR-004**: Store transitions MUST protect project identity, version, lock and journal integrity.
- **FR-005**: Public CLI errors MUST be structured and V2-compatible.

## Success Criteria

- **SC-001**: `tests/validate_work_item_v3_contract.py` passes its migration and adversarial filesystem matrix.
- **SC-002**: `tests/validate_orchestrator_store_contract.py` passes its identity/store matrix.
- **SC-003**: `tests/validate_v3_wiring_contract.py` proves no redirection occurs during a symlink swap.

## Scope

In: `work_item_v3.py`, `store.py`, public migration wiring, and their contract suites.
Out: canonical-skill selection and public checkpoint attestation.

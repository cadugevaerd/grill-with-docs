# Feature Specification: Cooperative Execution Attestation

**Phase**: FASE-004
**Source handoff**: `.grill/work-items/feature-workflow-v3-7dc283c84fb54e6b8f10a9c4546cd473/handoffs/FASE-004-SPECIFY-HANDOFF.md`

## User Story 1 — Require correlated checkpoint evidence (Priority: P1)

An operator cannot advance a V3 checkpoint with files or green tests alone. The coordinating agent or subagent supplies the correlated receipt for the run.

**Acceptance scenarios**:

1. Missing receipt blocks with `ATTESTATION-REQUIRED`.
2. A complete, current and correlated chain advances the intended V3 checkpoint.
3. Direct, replayed, stale, diverged or non-terminal structural receipts are rejected.

## User Story 2 — Coordinate with a subagent (Priority: P1)

When a task starts, its coordinator can assign a subagent to assemble and review the receipt. The public checkpoint validates the receipt's structural correlation and advances only in canonical order.

**Acceptance scenarios**:

1. The subagent's receipt binds resolution, dispatch, invocation and output to one campaign.
2. The public boundary validates that receipt before recording campaign/output state.
3. Missing, stale, replayed or structurally invalid receipts block.

## Requirements

- **FR-001**: Structural attestation data MUST correlate resolution, dispatch, invocation and output to the current campaign.
- **FR-002**: A receipt MUST be treated as cooperative structural evidence, never as cryptographic provenance or a defense against a malicious executor.
- **FR-003**: Public V3 checkpoint completion MUST require a complete structural receipt from the coordinating workflow or its assigned subagent.
- **FR-004**: Missing, replayed, stale, diverged, direct or non-terminal receipts MUST fail closed and preserve state.
- **FR-005**: Runtime-loader failures MUST yield exactly one structured response without import noise or traceback.

## Success Criteria

- **SC-001**: `tests/validate_attestation_contract.py` and `tests/validate_v3_wiring_contract.py` pass all structural and fail-closed cases.
- **SC-002**: A complete cooperative receipt advances one V3 checkpoint only after structural correlation.

## Scope

In: structural chain validation, checkpoint wiring, subagent coordination and JSON loader behavior.
Out: cryptographic provenance, hostile-agent defense, runtime keys and external services.

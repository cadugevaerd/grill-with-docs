# Feature Specification: Canonical Step Skills

**Feature Branch**: `feat/v3-gauntlet`
**Created**: 2026-08-14
**Status**: Ready for planning
**Input**: Handoff `FASE-001 — Catálogo de skills canônicas`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Resolve a required step safely (Priority: P1)

An operator can determine the one authorized capability for any required development step in the supported runtime before starting that step.

**Why this priority**: Operators need a reliable answer to "what may perform this step?" instead of an agent's approximation.

**Independent Test**: Resolve every required step with a supported catalog and verify each result names exactly one distinct registered capability.

**Acceptance Scenarios**:

1. **Given** a valid registered capability catalog, **When** an operator resolves one required workflow step, **Then** the system returns the unique canonical skill identity for that step.
2. **Given** the ship step, **When** it is resolved, **Then** the resolution states that human authorization is additionally required.

---

### User Story 2 - Reject an unproven capability (Priority: P1)

An operator is prevented from treating an unavailable, ambiguous, stale, or untrusted capability as a valid workflow step.

**Why this priority**: A completion claim is unsafe when it can be produced by a substitute or a changed capability.

**Independent Test**: Alter one registry, catalog, version, entrypoint, or runtime fact at a time and verify resolution blocks before producing an authorization.

**Acceptance Scenarios**:

1. **Given** a runtime without a proven entrypoint, **When** an operator resolves a required step, **Then** the operation blocks with a structured explanation.
2. **Given** a catalog whose trusted identity, version, content, or entrypoint has changed, **When** an operator resolves a required step, **Then** the operation blocks without a fallback.

### Edge Cases

- The registry is byte-different while its parsed shape is otherwise equivalent.
- Two capabilities claim the same entrypoint or a single capability is listed for multiple required steps.
- A capability catalog is internally consistent but its trust declaration was constructed by the same caller.
- An invocation references a skill resolution for another step, runtime, or project context.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST retain exactly the eleven required development steps in their established order.
- **FR-002**: The system MUST associate every required step with one unique canonical skill identity for each declared runtime.
- **FR-003**: The system MUST expose a canonical skill only when its registry, trusted catalog, version, content, source, and entrypoint are mutually consistent.
- **FR-004**: The system MUST block a required step when its runtime lacks a proven native entrypoint.
- **FR-005**: The system MUST reject direct, emulated, best-effort, ambiguous, or stale substitutes for a required step.
- **FR-006**: The system MUST mark only the ship step as requiring additional human authorization, while never allowing that authorization to replace the canonical skill.
- **FR-007**: The system MUST return structured, traceable failures for invalid or untrusted capability data without downloading or discovering a substitute.

### Key Entities

- **Canonical Skill**: The only authorized capability for one required workflow step.
- **Skill Resolution**: The pinned identity of a Canonical Skill for a step and runtime.
- **Trusted Catalog**: The approved source of capability identities for a runtime.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of the eleven required steps resolve to one distinct Canonical Skill in the supported runtime.
- **SC-002**: 100% of malformed, stale, ambiguous, untrusted, or unproven-capability cases in the acceptance matrix block before producing a resolution.
- **SC-003**: 100% of successful resolutions contain the same pinned identity when the same inputs are used again.

## Assumptions

- Claude is the only runtime with all required entrypoints proven in this phase; other declared runtimes remain blocked until independently proven.
- Workflow V2 migration, work item migration, and execution attestation are handled by subsequent phases.
- The system operates offline and never treats capability discovery as authorization.

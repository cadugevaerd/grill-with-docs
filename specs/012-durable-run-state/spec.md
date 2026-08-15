# Feature Specification: Durable Gauntlet Runs

**Feature Branch**: `012-durable-run-state`

**Created**: 2026-08-14

**Status**: Draft

**Input**: User description: "Implement FASE-002 durable Gauntlet run state, evidence boundary, recovery, and isolated worker worktrees."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Record recovery for an interrupted run (Priority: P1)

An operator can inspect a previously admitted Gauntlet run and record one validated recovery decision after an interruption, without creating a second run for the same request or starting work.

**Why this priority**: Recovery is the value that makes autonomous work auditable and safe after interruptions.

**Independent Test**: An admitted run is interrupted, then inspected and given one explicit recovery decision; the same run identity and its prior evidence remain available without worker execution.

**Acceptance Scenarios**:

1. **Given** an admitted run with a recorded recovery-eligible state, **When** the operator requests recovery, **Then** the same run records one recovery decision, retains its prior evidence, and remains ready for later scheduling.
2. **Given** a run whose recorded identity no longer matches the active work item, **When** the operator requests a resume, **Then** the request is blocked and no new run state is created.

---

### User Story 2 - Diagnose worker progress safely (Priority: P2)

An operator can inspect correlated run and worker progress, including a stalled or failed worker, while the coordinator retains authority over the evidence used to make that diagnosis.

**Why this priority**: Operators need actionable diagnosis without allowing workers to self-approve or alter the coordination record.

**Independent Test**: A run records worker progress and a failure; inspection identifies the same run, worker, and evidence correlation without granting workers authority to change receipts.

**Acceptance Scenarios**:

1. **Given** an active worker with recorded progress, **When** the operator inspects the run, **Then** the worker state and correlated evidence are visible under the run identity.
2. **Given** a worker that has failed or stalled, **When** the operator inspects the run, **Then** the diagnostic state is retained for recovery or explicit cleanup.

---

### User Story 3 - Isolate and clean up worker work (Priority: P3)

An operator can create work for an eligible worker in an isolated workspace and later request its cleanup only when its recorded state permits removal.

**Why this priority**: Isolation protects the coordinator and preserves failed work for diagnosis.

**Independent Test**: A worker receives an isolated workspace from the declared base revision; only a clean, terminal, converged, and recorded-eligible worker can be removed, while a failed or blocked worker remains available.

**Acceptance Scenarios**:

1. **Given** an eligible worker, **When** it is prepared for a run, **Then** its workspace is isolated from the coordinator and tied to the declared base revision.
2. **Given** a failed, blocked, or conflicting worker, **When** cleanup is requested, **Then** its artifacts are preserved and the request explains why removal is denied.
3. **Given** a clean, terminal, converged, and recorded-eligible worker, **When** validated cleanup is requested, **Then** only its eligible workspace is removed and the diagnostic record remains available.

### Edge Cases

- A repeated admission or resume request must reuse the correlated run rather than duplicate state or evidence.
- A stale work item, altered workflow, or invalid configuration must block before any run or worker state is written.
- A lease interrupted by expiration must expose a deterministic recovery decision for an explicit resume request or become diagnostically blocked.
- A malformed, unsafe, or externally replaced run record must be rejected without changing unrelated run records.
- A V2 work item must retain its existing manual workflow behavior.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST create a durable run record only for an eligible, explicitly activated V3 work item and bind it to the work item, workflow, configuration, and declared base revision used at admission.
- **FR-002**: The system MUST expose a stable run projection that identifies the run, each worker, its recovery state, and the evidence correlated with that run.
- **FR-003**: The system MUST reuse an existing compatible run for an identical admission or resume request and MUST reject an incompatible or stale request without creating duplicate state.
- **FR-004**: The system MUST record each material run transition with its run, wave, declared base revision, input, and receipt correlation; its output correlation is a hash or an explicit null, and worker and lease correlation are required only for worker-scoped transitions.
- **FR-005**: The coordinator MUST be the only authority that accepts and records evidence used for run progress or approval; workers MUST NOT alter run receipts, leases, or coordinator state.
- **FR-006**: The system MUST prepare each worker in an isolated workspace associated with the run's declared base revision and MUST prevent worker changes from mutating coordinator state directly.
- **FR-007**: The system MUST grant each worker only its declared local work scope and approved capabilities; store access, lease control, dispatch control, ship, push, release, and undeclared network authority are denied.
- **FR-008**: The system MUST retain failed, stalled, blocked, or conflicting worker artifacts until an explicit cleanup request satisfies the recorded cleanup conditions.
- **FR-009**: The system MUST allow a clean, terminal, and converged worker workspace to be removed only by an explicit validated cleanup request after recorded cleanup eligibility is established, while preserving the run's diagnostic record.
- **FR-010**: The system MUST make recovery decisions deterministic for an explicit resume request: an expired or interrupted lease is eligible for one recorded recovery decision when its recorded conditions permit; otherwise the run is blocked with a diagnostic reason. Automatic replacement, relaunch, and retry are out of scope.
- **FR-011**: The system MUST fail closed on malformed, unsafe, stale, or unsupported run, worker, identity, or capability input, leaving existing durable state unchanged.
- **FR-012**: The system MUST preserve the behavior and outputs of V2 work items and MUST NOT introduce scheduling, parallel dispatch, convergence, review, shipping, publishing, or external approval authority in this phase.

### Key Entities *(include if feature involves data)*

- **Resumable Run**: The durable record of one admitted unit of Gauntlet work, its identity bindings, progress, recovery state, and correlated evidence.
- **Worker Lease**: The bounded recovery claim for one worker within a run.
- **Evidence Boundary**: The coordinator-owned authority that accepts, validates, and records evidence and receipts.
- **Worker Workspace**: The isolated workspace assigned to a worker and associated with the run's declared base revision.
- **Capability Grant**: The declared, bounded local authority available to a worker for its assigned work.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In every supported interruption scenario, an operator can identify the affected run and its recovery state from one stable run projection without creating a second run.
- **SC-002**: One hundred percent of recorded material run transitions are correlated to one run, wave, declared base revision, input, and receipt; output is a hash or explicit null, and every worker-scoped transition additionally identifies one worker and lease.
- **SC-003**: In all supported invalid or stale admission, resume, and cleanup cases, the request leaves durable state byte-for-byte unchanged and returns one diagnostic outcome.
- **SC-004**: Every worker workspace is attributable to one run and declared base revision; no worker scenario mutates coordinator state or evidence directly.
- **SC-005**: Failed, stalled, blocked, and conflicting worker scenarios retain their artifacts until a validated cleanup condition is met; only clean, terminal, converged, and recorded-eligible scenarios remove the eligible workspace.
- **SC-006**: Existing V2 workflow scenarios retain their documented results while the FASE-002 controls reject unsupported scheduling and release actions.

## Assumptions

- The activated V3 configuration and the FASE-001 public control boundary are available and valid before a run is admitted.
- This phase owns durable state, recovery evidence, and workspace isolation only; scheduling, automatic retry or relaunch, parallel dispatch, convergence execution, review, and publication remain subsequent phases.
- The coordinator remains local to the project and does not require a new external approval authority.
- The existing project journal and safe mutation controls remain the authoritative source for durable lifecycle records.

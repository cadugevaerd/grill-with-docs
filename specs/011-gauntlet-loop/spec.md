# Feature Specification: Gauntlet Loop Activation

**Feature Branch**: `011-gauntlet-loop`
**Created**: 2026-08-14
**Status**: Draft
**Input**: User description: "Implementar o gauntled automatizado de acordo com o plano."
**Work Item**: `feature-gauntlet-loop-0447622ec0714933a4e791d0b58b5420`
**Phase / Delivery Unit**: `FASE-001` / `DU-001`
**Source Handoff**: [FASE-001-SPECIFY-HANDOFF.md](../../.grill/work-items/feature-gauntlet-loop-0447622ec0714933a4e791d0b58b5420/handoffs/FASE-001-SPECIFY-HANDOFF.md)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Activate a verified Gauntlet work item (Priority: P1)

An operator explicitly enables Gauntlet Loop for an eligible work item and receives one durable, readable activation record. The record makes the selected worker limit, fixed stall threshold, and required capability tier policy visible before any work starts.

**Why this priority**: Explicit activation is the safety boundary that prevents a manual or incompatible work item from being scheduled without proven capability.

**Independent Test**: Activate an eligible V3 work item with a verified Claude Code capability catalog, then inspect the activation status without starting a run.

**Acceptance Scenarios**:

1. **Given** an eligible V3 workflow, work item, and verified Claude Code capability catalog, **When** an operator activates Gauntlet Loop, **Then** one activation record is created with the selected worker limit, not exceeding five, the stall limit, and the published Model Tier policy.
2. **Given** an equivalent existing activation record, **When** the operator repeats activation, **Then** the result verdict is `REUSED` and preserves the original record unchanged.
3. **Given** an activation record that conflicts with current verified inputs, **When** an operator requests activation, **Then** the result is `BLOCKED` with `ACTIVATION-CONFLICT`, includes a remediation, and replaces no record.

---

### User Story 2 - Prevent unsafe or unsupported activation (Priority: P1)

An operator receives a clear, non-destructive refusal when the selected workflow, work item, runtime, or capability proof is not eligible for Gauntlet Loop.

**Why this priority**: The first release must never infer activation, substitute a runtime, or degrade a V3 work item into the existing V2 manual path.

**Independent Test**: Attempt activation for V2, malformed V3, unverified, Codex, and Hermes cases; confirm each attempt leaves no activation record or run state.

**Acceptance Scenarios**:

1. **Given** a V2 workflow or V2 work item, **When** activation is requested, **Then** it is `BLOCKED` with `WORKFLOW-INCOMPATIBLE` or `WORK-ITEM-V3-REQUIRED`, without changing the existing manual workflow behavior.
2. **Given** a runtime lacking proven canonical entrypoints for every required stage, **When** activation is requested, **Then** it is `BLOCKED` with `RUNTIME-ENTRYPOINT-UNPROVEN`, without fallback or substitution.
3. **Given** a capability catalog with a missing, stale, ambiguous, or tampered entry, **When** activation is requested, **Then** it is `BLOCKED` with the precise kebab-case catalog or capability code before any mutable state is created.

---

### User Story 3 - Start an admitted run and inspect controls safely (Priority: P2)

After explicit activation, an operator can initiate an admitted Gauntlet run and inspect the activation without modifying the project. Controls that require durable scheduling state report their phase boundary explicitly.

**Why this priority**: Operators need to start only an eligible run while retaining a predictable boundary between admission in this phase and durable scheduling in later phases.

**Independent Test**: Initiate a run for an activated eligible item and obtain `RUN-ADMITTED`; inspect activated and non-activated work items, then request resume and cleanup before scheduling is available; verify that planning artifacts and unrelated project state remain unchanged.

**Acceptance Scenarios**:

1. **Given** any work item, **When** an operator requests Gauntlet status, **Then** the response is `STATUS`, contains exactly one activation state (`ELIGIBLE`, `ACTIVATED`, `STALE`, or `BLOCKED`) and a reason when it is not eligible, and does not modify files, branches, worktrees, or existing status output.
2. **Given** an explicitly activated eligible work item, **When** an operator requests run, **Then** the response verdict is `RUN-ADMITTED` and no stage, worker, worktree, or durable scheduling record is dispatched by this phase.
3. **Given** a work item without explicit activation, **When** an operator requests run or resume, **Then** the response is `BLOCKED` with `ACTIVATION-REQUIRED` and does not create activation or run state.
4. **Given** this activation and admission release, **When** an operator requests resume or cleanup before durable scheduling exists, **Then** the response is `BLOCKED` with `SCHEDULING-NOT-AVAILABLE` and makes no broad deletion or unrelated mutation.

### Edge Cases

- Activation input contains unknown fields, duplicate fields, malformed text, or values outside the worker and stall limits.
- A verified workflow or capability catalog changes after activation.
- Concurrent equivalent activation requests occur for the same work item.
- A path presented as a work item or activation record resolves through a symbolic link or outside the project boundary.
- A domain failure occurs while loading an activation dependency.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST require an explicit activation action before a work item can be considered Gauntlet-enabled.
- **FR-002**: The system MUST activate only an eligible V3 workflow and V3 work item. Eligibility means the current workflow declares the canonical eleven-stage order and current registry identity, and the work item identity remains bound to those current project inputs.
- **FR-003**: The system MUST accept only a Claude Code capability proof that resolves every canonical stage against the current catalog identity. A proof is stale or altered when its recorded workflow, registry, catalog, or work-item identity differs from the current verified identity.
- **FR-004**: The system MUST refuse Codex, Hermes, and every other runtime that lacks the same complete verified capability proof, without emulation, fallback, or runtime substitution.
- **FR-005**: The activation record MUST use a closed, versioned schema and record the V3 work-item immutable identity, workflow and registry identities, catalog ID and catalog/trusted-asset identities, worker limit, stall limit, and Model Tier policy without credentials, host paths, process identifiers, or mutable external authority.
- **FR-006**: The worker limit MUST be configurable only from one through five inclusive; five workers is the maximum.
- **FR-007**: The stall threshold MUST be exactly fifteen minutes and use explicit units.
- **FR-008**: The Model Tier policy MUST require small capability for checklist and Markdown-only maintenance; medium for tasks, agent-execute, converge, and verify; and large for specify, plan, analyze, agent-assign, review, and ship. A requested tier may only be promoted and the promotion MUST be recorded before dispatch.
- **FR-009**: Repeating equivalent activation MUST return `REUSED` without changing the existing activation record; conflicting activation MUST return `BLOCKED` with `ACTIVATION-CONFLICT` without replacing it. A first valid activation MUST return `ACTIVATED`.
- **FR-010**: Status MUST be deterministic and read-only. It MUST return `STATUS` with exactly one activation state, in this precedence order: `STALE` when an activation exists but one recorded identity no longer matches; otherwise `BLOCKED` when eligibility cannot be determined or does not pass; otherwise `ACTIVATED` when a current matching activation exists; otherwise `ELIGIBLE`. `STALE` and `BLOCKED` MUST include a reason. Existing V2 commands and their output contracts MUST remain unchanged.
- **FR-011**: Run MUST require an eligible explicit activation and return `RUN-ADMITTED` only after it revalidates current eligibility. This phase MUST not dispatch a canonical stage, worker, worktree, or durable scheduling record. Resume without a current activation MUST return `BLOCKED` with `ACTIVATION-REQUIRED`; resume with a current activation and cleanup MUST neither infer activation nor create durable scheduling state and MUST return `BLOCKED` with `SCHEDULING-NOT-AVAILABLE` until that state exists.
- **FR-012**: Invalid, unsupported, malformed, stale, concurrent, symbolic-link, or interrupted activation attempts MUST fail closed without partial activation state, worker artifacts, branches, worktrees, or mutation. The sole authorized project-scoped mutation after a successful activation is `.grill/gauntlet.yaml`.
- **FR-013**: Each command outcome MUST be exactly one structured response. Successful verdicts are `ACTIVATED`, `REUSED`, `RUN-ADMITTED`, or `STATUS`; `STATUS` may successfully project activation state `BLOCKED` with a reason, which is distinct from a command denial. Domain denials use verdict `BLOCKED` with one kebab-case code: `ACTIVATION-REQUIRED`, `ACTIVATION-CONFLICT`, `SCHEDULING-NOT-AVAILABLE`, or a precise eligibility failure. No diagnostic noise may be mixed into the response.
- **FR-014**: A legacy work item whose immutable workflow identity differs from the current accepted V3 workflow MUST remain blocked until an operator runs an explicit preview-first rebind through `migrate-v3`. The rebind MUST update the immutable binding only with `--apply`, CAS protection, and current V3 workflow evidence; activation MUST never rebind it implicitly.

### Key Entities *(include if feature involves data)*

- **Gauntlet Activation**: The immutable, versioned record authorizing a single eligible work item for future Gauntlet scheduling.
- **Capability Proof**: The current verified catalog evidence that every required workflow stage can be dispatched by the selected runtime.
- **Model Tier Policy**: The declared minimum capability tier for each canonical stage and each recorded pre-dispatch promotion.
- **Activation Status**: A read-only projection of whether a named work item is eligible, activated, stale, or blocked and why.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator can activate an eligible work item and read its status in two commands or fewer, with no manual file editing.
- **SC-002**: 100% of the defined invalid V2, unverified-runtime, altered-proof, malformed-input, and unsafe-path acceptance cases leave no activation or run state behind.
- **SC-003**: 100% of the eleven canonical stages have a recorded minimum Model Tier and a verified Claude Code capability before activation succeeds.
- **SC-004**: Repeated equivalent activation leaves the visible activation record unchanged and returns `REUSED` every time.
- **SC-005**: Operators of existing V2 work items receive the same documented manual command outcomes after Gauntlet activation becomes available.
- **SC-006**: An operator with an eligible activated work item receives `RUN-ADMITTED` from one run request without dispatching a stage or worker.

## Decision Sources

- The operator can activate and initiate a run only with verified Claude Code capability: FASE-001 handoff and [ROADMAP](../../.grill/work-items/feature-gauntlet-loop-0447622ec0714933a4e791d0b58b5420/ROADMAP.md#fase-001--ativação-explícita-e-contrato-de-configuração).
- The limit of five workers, fifteen-minute stall threshold, and exact Model Tier policy are decided in [PLAN-CONTEXT](../../.grill/work-items/feature-gauntlet-loop-0447622ec0714933a4e791d0b58b5420/PLAN-CONTEXT.md) and [ADR-0001](../../.grill/work-items/feature-gauntlet-loop-0447622ec0714933a4e791d0b58b5420/docs/adr/ADR-0001.md).
- Explicit V3 activation, no runtime fallback, and unchanged V2 behavior are decided in [ADR-0007](../../.grill/work-items/feature-gauntlet-loop-0447622ec0714933a4e791d0b58b5420/docs/adr/ADR-0007.md).

## Assumptions

- This phase admits a run after activation but does not dispatch its stages. Durable scheduling, worker leases, receipts, and worktree lifecycle are delivered by later phases.
- The project retains its existing manual V2 workflow unchanged unless an operator explicitly uses an eligible V3 work item for Gauntlet activation.
- The Claude Code capability catalog is the only runtime proof accepted in the first release; support for other runtimes is deferred until the same proof exists.
- No execution cost or budget cap is part of the Gauntlet configuration or admission policy.

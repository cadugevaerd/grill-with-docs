# Feature Specification: Claude Scheduler Waves

**Feature Branch**: `013-scheduler-waves`

**Created**: 2026-08-15

**Status**: Draft

**Input**: User description: "Implement FASE-003 Claude-native scheduler: dispatch each of the eleven canonical macro-steps to a Claude subagent leader in fixed order, and within agent-execute, dispatch independent Execution DAG nodes to up to five concurrent worker waves, observing progress and recovering a limited stall automatically."

**Work item**: feature-gauntlet-loop-0447622ec0714933a4e791d0b58b5420 · **ADRs**: ADR-0001, ADR-0004, ADR-0005, ADR-0007, ADR-0012, ADR-0013, ADR-0014 · **DU**: DU-003

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Dispatch each macro-step to its own subagent leader, in fixed order (Priority: P1)

A coordinator dispatches each of the eleven canonical macro-steps (specify, plan, checklist, tasks, analyze, agent-assign, agent-execute, converge, verify, review, ship) to one Claude subagent leader, strictly in that order, never starting a macro-step before the previous one is terminal and never running two macro-steps concurrently.

**Why this priority**: This is the baseline capability the handoff names first ("Cada macroetapa usa um subagente Claude") and everything else in this phase happens inside one macro-step's dispatch (`agent-execute`); without fixed-order single-leader dispatch there is no scheduler to wave-parallelize inside.

**Independent Test**: Given a run ready to advance, dispatching the next macro-step creates exactly one subagent leader for that macro-step, at the tier the existing tier policy declares for it, and the following macro-step is never dispatched until the current one reaches a terminal state.

**Acceptance Scenarios**:

1. **Given** a run whose current macro-step is `checklist`, **When** the coordinator dispatches, **Then** exactly one subagent leader is created for `checklist`, invoked at the tier policy's `small` floor, and no other macro-step's leader is concurrently active.
2. **Given** a macro-step leader that has not yet reached a terminal state, **When** the coordinator evaluates the run, **Then** the next macro-step is never dispatched.
3. **Given** the `tasks` macro-step's leader completes, **When** the coordinator inspects its output, **Then** the produced Execution DAG becomes the versioned artifact this phase validates and later dispatches waves against; no separate DAG-generation step runs.

---

### User Story 2 - Dispatch an independent wave of workers inside agent-execute (Priority: P1)

While the `agent-execute` macro-step is the current step, a coordinator dispatches a wave of Claude subagent workers to exactly the Execution DAG nodes that are both marked parallel-eligible and whose declared dependencies are already terminal, each at the tier its node declares, without exceeding the run's configured concurrent worker cap.

**Why this priority**: Parallel dispatch bounded by the declared DAG, its `parallel` flag, and the tier policy is the specific value this phase adds inside `agent-execute`; every other behavior in this story exists to keep that dispatch safe.

**Independent Test**: Given an `agent-execute` macro-step with an Execution DAG containing ready nodes, dependency-pending nodes, and a `parallel:false` node with terminal dependencies, dispatching a wave creates workers only for the ready `parallel:true` nodes plus, alone, any single ready `parallel:false` node, each at its declared tier, and never exceeds the run's configured concurrent worker cap (1-5).

**Acceptance Scenarios**:

1. **Given** an Execution DAG where two `parallel:true` nodes have no pending dependencies and three nodes depend on them, **When** the coordinator dispatches a wave, **Then** exactly the two independent `parallel:true` nodes receive workers and the three dependent nodes remain undispatched.
2. **Given** a ready node marked `parallel:false`, **When** the coordinator dispatches a wave containing it, **Then** that node is dispatched alone in its own wave, with no other node concurrently active in that same run.
3. **Given** a run configured with a worker cap of three and five independent `parallel:true` nodes ready in the same wave, **When** the coordinator dispatches, **Then** exactly three workers are created and the remaining ready nodes wait for a later wave; the cap counts concurrently active workers, so a node that finishes frees its slot for the next wave.
4. **Given** a node whose declared `tier` is `large`, **When** its worker is dispatched, **Then** it is invoked at that tier, the canonical skill and registry hash pinned at FASE-001 activation are resolved and used, and the tier decision is recorded before dispatch.
5. **Given** an Execution DAG whose declared `max_workers` exceeds the run's activation-configured worker cap, **When** the coordinator evaluates the run for dispatch, **Then** the activation-configured cap governs and the excess is never dispatched; if the DAG's declared cap is below the activation cap, the DAG's lower value governs instead.
6. **Given** more independent ready nodes than fit in one wave, **When** the first wave's workers all reach a terminal state, **Then** the coordinator declares a new, distinctly identified wave for the next eligible nodes, and the prior wave's record remains unchanged.

---

### User Story 3 - Observe worker progress and recover one stall (Priority: P2)

A coordinator observes each dispatched worker's coordinator-recorded lease transitions and, when a worker's lease shows no new transition for the run's configured stall window, performs exactly one recovery action (replace the worker or relaunch the run) through the existing FASE-002 lease-recovery mechanism, extended to trigger automatically; a second stall on the same run after that recovery blocks with a diagnostic instead of recovering again.

**Why this priority**: Silent abandonment of an apparently autonomous run is the specific failure the Gauntlet Loop exists to prevent; recovery must be bounded, observable through evidence the coordinator already owns, and never a second authority alongside FASE-002's existing lease-recovery gate.

**Independent Test**: A dispatched worker's lease records no new coordinator transition for the configured stall window; the coordinator performs one recovery action through the existing lease-recovery mechanism and records it. Simulating a second stall on the same run after that recovery yields a block with a diagnostic reason, not a second automatic recovery.

**Acceptance Scenarios**:

1. **Given** a worker whose lease has recorded no new transition for the configured stall window, **When** the coordinator evaluates it, **Then** the coordinator automatically records the recovery-eligible condition FASE-002's manual resume already recognizes, performs exactly one recovery action, and records a compact status event correlated to the run, wave, worker, and lease.
2. **Given** a run that has already used its one recovery action, **When** a second stall is observed on that same run, **Then** the run blocks with a diagnostic reason and no further automatic recovery is attempted.
3. **Given** a worker actively producing new recorded lease transitions, **When** the coordinator evaluates it before the stall window elapses, **Then** it is never classified as stalled.

---

### User Story 4 - Retry exactly one classified transient failure (Priority: P3)

A coordinator classifies a failed worker's outcome against the declared closed transient-failure classification; only a failure matching it receives exactly one automatic retry, counted against the same concurrency cap as any other active worker, and every other failure blocks for diagnosis without retrying.

**Why this priority**: Bounded, classified retry keeps the Loop autonomous for genuinely transient conditions while refusing to mask real defects behind unlimited retries or an uncapped burst of replacement workers.

**Independent Test**: A worker fails with a condition matching the declared transient classification; the coordinator retries it exactly once, without exceeding the run's worker cap. A worker fails with a non-transient condition, or fails a second time after its one retry, and the coordinator blocks instead of retrying again.

**Acceptance Scenarios**:

1. **Given** a worker failure whose recorded outcome is a process-level timeout or a transport-level dispatch failure (the declared transient set; see FR-011), **When** the coordinator observes it, **Then** exactly one automatic retry is dispatched, recorded, and counted against the run's worker cap alongside every other concurrently active worker.
2. **Given** a worker failure whose recorded outcome is a validator, gate, or contract rejection (not in the declared transient set), **When** the coordinator observes it, **Then** the run blocks with a diagnostic reason and no retry is dispatched.
3. **Given** a worker that fails a second time after its one recorded retry, **When** the coordinator observes it, **Then** the run blocks and no further retry is dispatched.

### Edge Cases

- A malformed, missing, or cyclic Execution DAG must block dispatch of `agent-execute` waves before any worker is created; it must not block the `tasks` macro-step leader that produced it.
- A wave request that would exceed the run's configured concurrent worker cap must dispatch only up to the cap and leave the remainder pending, never silently drop or silently exceed it; a stall-triggered replacement worker or a transient-failure retry counts against that same concurrent cap.
- A node whose declared `tier` is below the applicable policy floor for `agent-execute`, or that mixes Markdown and non-Markdown declared files without an explicit tier, must block that node's dispatch rather than dispatch at an unresolved tier.
- A macro-step leader must never be dispatched while a previous macro-step's leader has not yet reached a terminal state; the eleven canonical macro-steps are never reordered or run concurrently by this phase.
- A worker dispatch must never be able to create, resume, or reuse Store, receipt, lease, or grant state outside the existing FASE-002 coordinator-only primitives and this phase's own wave-lifecycle and concurrent-cap extensions to that Store schema.
- A capability grant scoped wider than the dispatched node's declared `files` must be rejected before the worker starts.
- Dispatch, observation, and recovery must never invoke a non-Claude runtime, perform convergence, resolve a conflict automatically, run independent review, or ship; when every Execution DAG node reaches a terminal state, `agent-execute` itself becomes terminal and the coordinator advances to `converge` as an ordinary macro-step dispatch under User Story 1, never performing convergence logic itself.
- A V2 work item, or a V3 work item without an admitted FASE-002 run, must reject a dispatch request without creating any wave, worker, or recovery state.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST dispatch each of the eleven canonical macro-steps (specify, plan, checklist, tasks, analyze, agent-assign, agent-execute, converge, verify, review, ship) to exactly one Claude subagent leader, in that fixed order, and MUST NOT dispatch a macro-step until the previous one has reached a terminal state; this phase never reorders, skips, or parallelizes macro-steps.
- **FR-002**: The system MUST invoke each macro-step's leader at the tier the existing tier policy (`minimum_by_step`, recorded at FASE-001 activation) declares for that macro-step, resolving the exact canonical skill and registry hash pinned at activation, and MUST record the tier decision before dispatch without silently downgrading.
- **FR-003**: The system MUST treat the Execution DAG produced by the `tasks` macro-step's own leader as the versioned artifact this phase validates and dispatches against; this phase MUST NOT generate or algorithmically derive a DAG through any other means.
- **FR-004**: While `agent-execute` is the current macro-step, the system MUST dispatch a worker only to an Execution DAG node whose declared dependencies are already terminal; a node declared `parallel:true` MAY share a wave with other eligible `parallel:true` nodes, and a node declared `parallel:false` MUST dispatch alone, with no other node of that run concurrently active. Parallelism MUST NOT be inferred beyond what the DAG explicitly declares.
- **FR-005**: The system MUST NOT dispatch more workers concurrently for one run than its worker cap, where the effective cap is the lesser of the run's activation-configured cap and the Execution DAG's own declared `max_workers`. A stall-triggered replacement worker and a transient-failure retry each count against this same concurrent cap; a worker that reaches a terminal state frees its slot for a later wave.
- **FR-006**: The system MUST invoke each dispatched `agent-execute` worker as a native Claude subagent at the tier its Execution DAG node declares; that declared tier MUST be at or above the existing tier policy's `agent-execute` floor (`medium`) in the tier order `small < medium < large`, except a node whose declared files are exclusively Markdown MAY use the existing markdown-maintenance supplemental floor (`small`). Dispatch MUST block a node whose declared tier does not satisfy the applicable floor.
- **FR-007**: The system MUST create each `agent-execute` worker's lease and capability grant using the existing FASE-002 coordinator-only run/worker/lease/grant primitives before invoking it; the grant's scope MUST be exactly the dispatched node's declared `files` and MUST NOT be broader.
- **FR-008**: The system MUST extend the coordinator's own Store schema, per ADR-0012 and ADR-0013, so that: (a) the worker-cap check counts only workers in a non-terminal state rather than the lifetime total of worker records; (b) a run can declare more than one wave over its lifetime, each with a distinct identity; (c) a wave already superseded by a later wave remains immutable, while the current wave may record its own state transitions. This extension is coordinator-owned and MUST NOT grant a worker any new authority beyond what FASE-002 already denies it.
- **FR-009**: The system MUST define worker progress as any new coordinator-recorded transition correlated to that worker's active lease since dispatch or since its previous recorded transition. The system MUST treat a worker whose lease has recorded no such transition for the run's configured stall window (fifteen minutes, as recorded at FASE-001 activation) as stalled and MUST automatically record the same recovery-eligible condition FASE-002's manual resume already requires, then perform exactly one recovery action for that run — replacing the worker once or relaunching the run once — before any further automatic recovery on that same run is blocked with a diagnostic reason.
- **FR-010**: The system MUST classify a failed worker's outcome against a declared, closed transient-failure classification limited to a process-level timeout or a transport-level dispatch failure that never reached the worker's Claude subagent; every other failure classification (including any validator, gate, or contract rejection) MUST NOT be treated as transient. The system MUST dispatch exactly one automatic retry only for a failure matching that classification; every non-transient failure, and any failure recurring after its one retry, MUST block with a diagnostic reason instead of retrying.
- **FR-011**: The system MUST NOT invoke a non-Claude runtime (Codex, Hermes, or any other) as a dispatch target for any macro-step leader or `agent-execute` worker.
- **FR-012**: The system MUST NOT perform convergence, automatic conflict resolution, independent review, or ship actions from dispatch, observation, or recovery logic; when every Execution DAG node reaches a terminal state, `agent-execute` itself becomes terminal and the coordinator's next action is the ordinary FR-001 dispatch of `converge` as the next macro-step, never a convergence action performed by this phase.
- **FR-013**: The system MUST record one compact dispatch status event — distinct from FASE-004's later Run Status Events — for each macro-step dispatch, each `agent-execute` worker dispatch, completion, stall, recovery action, and retry, correlated to the existing FASE-002 run and wave identities plus the affected worker and lease where applicable.
- **FR-014**: The system MUST fail closed — blocking dispatch before creating any wave, worker, lease, or grant state — on a malformed, missing, or cyclic Execution DAG, an over-cap wave request, or a node with no honorable declared tier.
- **FR-015**: The system MUST preserve the current behavior of V2 work items and of the existing FASE-001/FASE-002 command surface; dispatch MUST be available only to an activated V3 work item with an admitted FASE-002 run, and every `agent-execute` worker MUST target only a Worker Worktree already prepared through the existing FASE-002 worker-preparation primitive.

### Key Entities *(include if feature involves data)*

- **Macro-Step Dispatch**: The single-leader, fixed-order invocation of one of the eleven canonical macro-steps; the unit User Story 1 governs.
- **Execution Wave**: One `agent-execute` dispatch round's bounded set of workers, identified distinctly from any prior wave of the same run, limited to the run's effective concurrent worker cap and to Execution DAG nodes whose dependencies are terminal and whose `parallel` declaration permits sharing that round.
- **Model Tier Decision**: The recorded tier a dispatched macro-step leader or `agent-execute` worker is invoked at, taken from the existing tier policy (for a macro-step leader) or the Execution DAG node's own declared tier (for a worker), and validated against the applicable floor.
- **Stall Recovery**: The coordinator's evaluation, against the run's configured stall window, of whether a worker's lease has recorded new progress; a positive stall finding automatically records FASE-002's recovery-eligible condition and triggers exactly one bounded recovery action per run.
- **Retry Classification**: The declared, closed set of failure conditions (process-level timeout, transport-level dispatch failure) eligible for exactly one automatic retry, counted against the same worker cap as any other active worker.
- **Dispatch Status Event**: The compact, coordinator-recorded event for a macro-step dispatch, worker dispatch, completion, stall, recovery, or retry, correlated to run/wave/worker/lease identity where applicable; distinct from FASE-004's Run Status Events.
- **Autonomous Run**: A run that advances through successive macro-step dispatches and, within `agent-execute`, successive waves, without human confirmation between them, bounded entirely by the FRs above; it never advances past `agent-execute`'s dispatch into convergence, review, or ship logic performed by this phase.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In every supported run, macro-steps dispatch in the fixed eleven-step order with zero scenarios where a macro-step starts before the previous one is terminal or where two macro-steps are concurrently active.
- **SC-002**: In every supported `agent-execute` wave, zero workers are dispatched to a node with a non-terminal dependency or with `parallel:false` alongside another concurrently active node of the same run; one hundred percent of dispatched nodes have all declared dependencies terminal at dispatch time.
- **SC-003**: In every supported run, the total number of concurrently active `agent-execute` workers — original dispatch, stall replacement, and transient retry combined — never exceeds the run's effective concurrent worker cap (1-5, the lesser of activation config and DAG declaration), and zero scenarios undercount a stall-replacement or retry worker against that cap.
- **SC-004**: One hundred percent of dispatched macro-step leaders and `agent-execute` workers run at their applicable declared tier, at or above the applicable policy floor, using the canonical skill and registry hash pinned at FASE-001 activation; zero silent downgrades or unpinned invocations occur in any supported scenario.
- **SC-005**: Every run that stalls receives exactly one recovery action through the existing FASE-002 lease-recovery mechanism, triggered automatically; one hundred percent of second-stall scenarios on the same run block with a diagnostic instead of a second automatic recovery.
- **SC-006**: Only failures matching the declared transient classification (process-level timeout, transport-level dispatch failure) receive an automatic retry, and each receives exactly one; zero retries occur for non-transient or recurring failures.
- **SC-007**: Zero dispatch, observation, or recovery code path invokes a non-Claude runtime, convergence, automatic conflict resolution, independent review, or ship in any supported scenario, including when every Execution DAG node reaches a terminal state and `agent-execute` hands off to the ordinary dispatch of `converge`.
- **SC-008**: One hundred percent of dispatched `agent-execute` worker capability grants are scoped to exactly their node's declared `files`, with zero scenarios where a grant exceeds that declared scope.

## Assumptions

- The FASE-001 activation boundary and the FASE-002 durable run/worker/lease/grant primitives are available and remain the sole authority for coordinator state; this phase adds macro-step dispatch, wave lifecycle, concurrent-cap accounting, observation, and bounded recovery as coordinator-owned extensions on top of them (ADR-0012, ADR-0013).
- The Execution DAG's node graph, `tier`, `parallel`, `files`, and `max_workers` fields are produced by the `tasks` macro-step's own leader dispatch, not by a separate generator this phase writes (ADR-0014); this phase validates and consumes that DAG within `agent-execute`.
- Convergence, conflict resolution, independent review, and ship remain FASE-004's responsibility and are out of scope here even when every `agent-execute` wave of a run completes cleanly; this phase's only action at that point is the ordinary FR-001 dispatch of `converge`.
- The run's stall window is the value recorded at FASE-001 activation (currently fixed at fifteen minutes); this phase reads that configured value rather than declaring a second constant.
- The transient-failure classification is closed to conditions the coordinator can observe without trusting worker-reported content: a process-level timeout or a transport-level dispatch failure that never reached the invoked Claude subagent. Any failure the subagent itself reports (validator, gate, or contract rejection) is never transient.

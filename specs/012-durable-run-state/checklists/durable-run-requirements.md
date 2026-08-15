# Durable Run Requirements Checklist

**Purpose**: Validate completeness, clarity, consistency, and safety of FASE-002 requirements before task generation.

**Created**: 2026-08-14

**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 Are the current activation, work item, workflow, configuration, and base revision bindings all specified for every new run? [Completeness, Spec FR-001]
- [x] CHK002 Are run, wave, base revision, input, receipt, and output-or-null correlations required for every material transition, with worker and lease required for worker-scoped transitions? [Completeness, Spec FR-004]
- [x] CHK003 Are run and worker state sets closed, including interrupted, failed, blocked, orphaned, and terminal cases? [Completeness, Spec FR-002, FR-008, Data Model]
- [x] CHK004 Are one-time explicit recovery eligibility, reuse, and terminal denial requirements distinguished? [Completeness, Spec FR-003, FR-010]
- [x] CHK005 Are workspace derivation, child-branch provenance, and coordinator-worktree exclusion specified without accepting raw paths? [Completeness, Spec FR-006, Data Model]

## Safety and Authority

- [x] CHK006 Are the coordinator-only receipt, lease, Store, and evidence authorities explicit and non-delegable? [Completeness, Spec FR-005]
- [x] CHK007 Are allowed worker capabilities closed and are Store, dispatch, network, push, ship, release, credentials, and arbitrary execution explicitly excluded? [Completeness, Spec FR-007]
- [x] CHK008 Are invalid, stale, malformed, unsafe, and unsupported inputs required to leave durable state unchanged? [Clarity, Spec FR-011, SC-003]
- [x] CHK009 Is the boundary between logical workspace keys and derived local filesystem targets unambiguous? [Clarity, Data Model, Plan §Worker worktrees]
- [x] CHK010 Are Store-local digest representation and any future attestation representation kept distinct? [Consistency, Plan §Run transition]

## Atomicity and Recovery

- [x] CHK011 Does the plan require one recoverable protocol across pending intent, receipt, semantic event, commit anchor, snapshot publication, and intent removal? [Completeness, Plan §Run transition]
- [x] CHK012 Are read-only status behavior and mutable-command recovery behavior distinguished when a pending Store transition exists? [Clarity, Plan §Run transition]
- [x] CHK013 Are PREPARING and CLEANING intent states, crash boundaries, reconciliation outcomes, and orphan preservation fully specified? [Completeness, Plan §Worker worktrees, Data Model]
- [x] CHK014 Does cleanup validate all predicates before mutation and revalidate the exact target immediately before removal? [Consistency, Spec FR-009, Plan §Worker worktrees]
- [x] CHK015 Are failed, stalled, blocked, conflicting, dirty, missing, and orphaned workspace behaviors specified as preservation rather than deletion? [Coverage, Spec FR-008, FR-009]

## Scope and Compatibility

- [x] CHK016 Are scheduler, wave selection, worker execution, automatic retry/relaunch, convergence, review, shipping, publication, and external approval all explicitly excluded? [Scope, Spec FR-010, FR-012]
- [x] CHK017 Is the same-UID hostile-process limitation accurately bounded as outside this phase rather than silently claimed as a sandbox? [Assumption, Plan §Worker worktrees]
- [x] CHK018 Are V2 behavior/output preservation and one-JSON public error expectations specified for every new control? [Compatibility, Spec FR-012, Contract]

## Notes

- All items pass against the FASE-002 handoff, ROADMAP, PLAN-CONTEXT, ADR-0003, ADR-0005, ADR-0006, ADR-0010, and the reviewed plan.

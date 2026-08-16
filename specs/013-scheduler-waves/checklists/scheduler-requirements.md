# Scheduler Requirements Checklist

**Purpose**: Validate completeness, clarity, consistency, and safety of FASE-003 requirements before task generation.

**Created**: 2026-08-15

**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 Is dispatch of all eleven canonical macro-steps, in fixed order, with no exception for `agent-execute`, fully specified? [Completeness, Spec FR-001]
- [x] CHK002 Is the `blocked`-vs-`complete` halt/advance distinction for a macro-step checkpoint fully specified, including which one is a real terminal state? [Completeness, Spec FR-001, ADR-0016]
- [x] CHK003 Are readiness (terminal dependencies), `parallel` sharing, and the effective concurrent cap (activation config vs. DAG `max_workers`) all specified for wave dispatch? [Completeness, Spec FR-004, FR-005]
- [x] CHK004 Is the DAG-node scope rejection specified with exact, non-basename-list path-matching semantics for both closed rules? [Completeness, Spec FR-004, ADR-0018]
- [x] CHK005 Is worker lease/grant creation bound to the existing FASE-002 coordinator-only primitives, with grant scope exactly the node's `files`? [Completeness, Spec FR-007]

## Safety and Authority

- [x] CHK006 Is the `agent-execute` leader's delegated coordinator authority scoped to its own dispatch window, non-transferable to workers, and distinct from worker authority? [Completeness, Spec FR-016, ADR-0019]
- [x] CHK007 Is the shared per-node remediation budget specified as Store-enforced (not caller-construction-only), covering both stall and transient-retry mechanisms? [Completeness, Spec FR-007, FR-008(e), ADR-0015]
- [x] CHK008 Is node-identity correlation specified precisely enough to rule out the empirically-refuted grant-scope-equality approach? [Consistency, Spec FR-007, Plan §Research Decisions]
- [x] CHK009 Is lease TTL renewal on recorded progress specified as distinct from, and not gated by, stall detection? [Clarity, Spec FR-008(d), FR-009]
- [x] CHK010 Is the transient-failure classification closed to coordinator-observable conditions, and is the one caller-asserted fact (which failure occurred) named rather than left implicit? [Clarity, Spec FR-010, Plan §Design]

## Atomicity and Recovery

- [x] CHK011 Is the wave lifecycle's per-wave (not whole-map) immutability rule fully specified, including what "superseded" means? [Completeness, Plan §Store schema extension]
- [x] CHK012 Is the worker-cap non-terminal/terminal state partition fully enumerated? [Completeness, Plan §Store schema extension]
- [x] CHK013 Is remediation's lookup-then-mint specified as one atomic transaction, closing the TOCTOU a split design would leave? [Consistency, Plan §Design, Complexity Tracking]
- [x] CHK014 Is worker termination (success and failure) specified as a producer of the terminal states FR-005's cap-freeing and FR-009's second-stall detection both depend on? [Completeness, Plan §Design]

## Scope and Compatibility

- [x] CHK015 Are subagent invocation, convergence, conflict resolution, independent review, ship, and publication all explicitly excluded from this phase's core? [Scope, Spec FR-011, FR-012]
- [x] CHK016 Is the DAG-generation exclusion (this phase validates and dispatches against `tasks`'s output, never generates one) unambiguous? [Scope, Spec FR-003, ADR-0014]
- [x] CHK017 Are V2 work-item behavior and the existing FASE-001/002 command surface preserved unchanged for any run that never calls a FASE-003 command? [Compatibility, Spec FR-015]
- [x] CHK018 Is the attestation-contract boundary (`checkpoint-attestation/v1` unmodified, no second verification layer) explicit? [Compatibility, Spec Assumptions, ADR-0016]

## Notes

All eighteen items pass against the current `spec.md` + `plan.md` pair after the plan's independent-review repair pass (Store schema mechanics, wave lifecycle, worker termination, and the atomic remediation transaction). No item required a spec change; all were closeable in `plan.md`.

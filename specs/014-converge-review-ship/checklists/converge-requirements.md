# Converge Requirements Checklist

**Purpose**: Validate completeness, clarity, consistency, and safety of FASE-004 requirements before task generation.

**Created**: 2026-08-16

**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 Is the wave-by-wave, alphabetical-by-`node_id` integration order fully specified, including the pre-merge scope check and the merge-eligibility predicate (`state == "TERMINAL"`, success only)? [Completeness, Spec FR-001, FR-002, Plan §Convergence]
- [x] CHK002 Is the DAG-pin lifecycle (when it's written, what predicate decides "first real wave," what blocks a mismatch) fully specified for both `gauntlet-wave-declare` and `gauntlet-converge`? [Completeness, Spec FR-004c, ADR-0021]
- [x] CHK003 Is the run's terminal-lifecycle closing condition specified precisely as "every `node_id` of the pinned DAG," never "every wave" or "no wave pending in the Store"? [Completeness, Spec FR-001, ADR-0020]
- [x] CHK004 Is `gauntlet-run-abandon`'s authorization mechanism specified as a full `human-authorization/v1` bundle, not free text, with its idempotency (`RUN-ABANDON-REUSED` vs. `RUN-NOT-ELIGIBLE`) enumerated? [Completeness, Spec FR-014]
- [x] CHK005 Is the ship gate's run-enumeration specified as scanning every admitted run (not a single "most recent" selection), with the fail-open this closes named explicitly? [Completeness, Spec FR-007, Plan §Research Decisions]

## Safety and Authority

- [x] CHK006 Is `gauntlet-run-abandon`'s deliberate exemption from the current-activation admission boundary (FR-012) justified and scoped narrowly (identity from the target run's own recorded `admission`, not the current one)? [Completeness, Spec FR-014, Plan §Research Decisions]
- [x] CHK007 Is the honesty of `human-authorization/v1` reuse — an attributional barrier, not a cryptographically preventive one — stated explicitly rather than implied as equivalent to `ship`'s attestation chain? [Clarity, Plan §Research Decisions, §Design]
- [x] CHK008 Is `INTEGRATION_CONFLICT` specified as never reusing the Store's existing but unreachable `CONFLICT` worker state, and never carrying node/reason identity in an event or receipt? [Consistency, Spec Key Entities, ADR-0022]
- [x] CHK009 Is the scope-overlap detection source (Execution DAG's `files`) specified as distinct from, and never `grant.scope_paths`, with the empirical refutation cited? [Consistency, Spec FR-002, ADR-0021]

## Atomicity and Recovery

- [x] CHK010 Is the multi-transaction shape of one wave's convergence (one transaction per merged worker, plus closing transactions) specified, including what closes a gap left by an interrupted call? [Completeness, Plan §Convergence, §Transaction shape]
- [x] CHK011 Is the wave-level `converged` flag specified as distinct from `wave.state` (which FASE-003's `terminate_worker` already drives to `COMPLETE` independent of convergence outcome)? [Consistency, Plan §Store schema extension]
- [x] CHK012 Is reentry behavior for both conflict reasons (`scope-overlap` always re-blocks; `content-conflict` compares fingerprints before recomputing) fully specified? [Completeness, Spec FR-002, FR-003, Edge Cases]
- [x] CHK013 Is the newest-wave-only mutation guard's narrow exception (only `last_conflict`/`converged` may differ on a superseded wave) specified precisely enough to rule out reopening general wave mutability? [Clarity, Plan §Store schema extension, Complexity Tracking]
- [x] CHK014 Is the untracked-file collision (a real Git failure class distinct from a content conflict) specified with a deterministic pre-check, not exit-code or locale-dependent message parsing? [Completeness, Plan §Convergence]

## Scope and Compatibility

- [x] CHK015 Are subagent invocation, DAG generation, and any push/release action explicitly excluded from this phase's core? [Scope, Spec FR-009, Plan §Phase boundary]
- [x] CHK016 Is compatibility preserved for a work item with no gauntlet run, or only terminal ones, with no new gate applying? [Compatibility, Spec FR-008, AC US3-3]
- [x] CHK017 Is `review`'s reuse of the unmodified eleven-macro-step dispatch mechanism (no new command, no new verdict) explicit, distinguishing it from FR-007's independent convergence-based gate? [Compatibility, Spec User Story 2, Plan §Design]
- [x] CHK018 Is the constitutional version-bump obligation (2.7.0 → 2.8.0) named with its eight distribution surfaces? [Compatibility, Spec FR-013, SC-007]

## Notes

All eighteen items pass against the current `spec.md` (approved after 10 rounds of independent adversarial review) + `plan.md` pair (approved after 7 rounds, fixing real defects each round: run-completion premature-closure risk, DAG-pin persistence location, `last_conflict` schema/guard mechanics, `human-authorization/v1` reuse honesty, merge-set success-only predicate). No item required a further spec change; all were closeable in `plan.md`.

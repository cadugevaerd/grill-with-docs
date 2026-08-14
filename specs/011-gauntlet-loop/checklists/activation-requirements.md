# Activation Requirements Checklist: Gauntlet Loop

**Purpose**: Validate completeness, clarity, consistency, and traceability of the FASE-001 activation requirements before task decomposition.
**Created**: 2026-08-14
**Feature**: [spec.md](../spec.md)
**Focus**: Security/trust boundary, V2 compatibility, safe recovery, and public CLI contract.
**Audience**: Reviewer before implementation.

## Requirement Completeness

- [x] CHK001 Are explicit activation, V3 eligibility, and the no-fallback runtime boundary specified separately? [Completeness, Spec §FR-001–FR-004]
- [x] CHK002 Does the specification define all identities that an activation record must retain, including work-item document, workflow, registry, catalog, and trust asset identities? [Completeness, Spec §FR-005]
- [x] CHK003 Are the selected worker range, maximum, stall unit/value, and no-budget boundary stated without an implied default? [Completeness, Spec §FR-006–FR-007, Assumptions]
- [x] CHK004 Is every canonical stage represented once in the tier policy, while Markdown maintenance is explicitly not a twelfth workflow stage? [Completeness, Spec §FR-008; Plan §Versioned configuration]
- [x] CHK005 Is the explicit legacy workflow rebind prerequisite specified as preview-first, applied only on confirmation, and separate from activation? [Completeness, Spec §FR-014]

## Requirement Clarity

- [x] CHK006 Is the distinction between successful verdicts and `BLOCKED` command codes unambiguous for every Gauntlet control? [Clarity, Spec §FR-013; Contract]
- [x] CHK007 Is the successful `STATUS` projection with activation state `BLOCKED` explicitly distinguished from a top-level command failure? [Clarity, Spec §FR-010, FR-013; Contract §gauntlet-status]
- [x] CHK008 Are `STALE`, `BLOCKED`, `ACTIVATED`, and `ELIGIBLE` mutually exclusive through a documented precedence order? [Clarity, Spec §FR-010]
- [x] CHK009 Is `RUN-ADMITTED` bounded so it cannot be read as worker dispatch, a durable run, or a scheduling transition? [Clarity, Spec §FR-011; Assumptions]
- [x] CHK010 Are the conditions under which resume reports `ACTIVATION-REQUIRED` versus `SCHEDULING-NOT-AVAILABLE` specified? [Clarity, Spec §FR-011; Contract §gauntlet-resume]

## Requirement Consistency

- [x] CHK011 Does the allowed successful project mutation (`.grill/gauntlet.yaml`) align with the prohibition on mutations after failed admission? [Consistency, Spec §FR-012; Plan §Versioned configuration]
- [x] CHK012 Do activation scenarios, functional requirements, and success criteria use the same vocabulary for `RUN-ADMITTED`, `ACTIVATION-CONFLICT`, and V2 denial? [Consistency, Spec §User Story 1–3, FR-009–FR-013]
- [x] CHK013 Does the current-workflow binding requirement agree with the explicit rebind flow for legacy V3-migrated work items? [Consistency, Spec §FR-002, FR-014; Quickstart]
- [x] CHK014 Does the Model Tier policy remain consistent with the selected Claude adapter and the prohibition on silent downgrade? [Consistency, Spec §FR-008; Plan §Versioned configuration]

## Scenario and Edge-Case Coverage

- [x] CHK015 Are requirements specified for equivalent activation, conflicting activation, absent activation, stale activation, and unsupported runtime cases? [Coverage, Spec §User Story 1–3]
- [x] CHK016 Are malformed configuration, duplicate key, unknown field, wrong primitive type, symbolic-link, concurrent update, and interrupted update cases explicitly addressed? [Coverage, Spec §Edge Cases, FR-012; Plan §Versioned configuration]
- [x] CHK017 Are the safe-path-unavailable and mode-restoration-failure cases given named, fail-closed outcomes? [Coverage, Plan §Eligibility and proof, §Explicit legacy workflow rebind]
- [x] CHK018 Are catalog absent, malformed, untrusted, stale, ambiguous, and resolver-fallback reasons given deterministic public code treatment? [Coverage, Spec §User Story 2; Plan §Eligibility and proof]

## Acceptance-Criteria Quality

- [x] CHK019 Are the success criteria measurable as operator-visible outcomes without depending on an implementation-specific test suite? [Measurability, Spec §SC-001–SC-006]
- [x] CHK020 Does each denial requirement define both preservation of state and a named remediation or public code? [Measurability, Spec §FR-009–FR-014]
- [x] CHK021 Is the independent-release SemVer condition distinguished from the planned 2.6.0 aggregate release? [Traceability, Plan §Constitution Check]

## Notes

- Revalidation closed the two gaps below against the final plan and contract. This checklist validates requirement quality only; runtime contract verification belongs to later `verify`.

## Revalidation Gaps

- [x] CHK022 Are ownership, scope, ordering, contention, and failure requirements specified separately for the configuration-wide activation lock and the existing work-item rebind lock? [Gap resolved, Plan §Versioned configuration, §Explicit legacy workflow rebind]
- [x] CHK023 Are loader, root, and argument failure requirements assigned stable top-level `BLOCKED` treatment and distinguished from status-projectable proof failures? [Gap resolved, Plan §Public command surface, §Versioned configuration]

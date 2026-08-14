# Canonical Skills Requirements Checklist

**Purpose**: Reviewer checklist for the quality of FASE-001 requirements.
**Created**: 2026-08-14
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 Are all eleven required `step_id`s explicitly identified as an ordered closed set? [Completeness, Spec §FR-001]
- [x] CHK002 Is the identity that must be unique for every step and declared runtime defined without relying on an agent's equivalence judgment? [Clarity, Spec §FR-002]
- [x] CHK003 Are registry, trusted catalog, version, source, content and entrypoint all named as simultaneous authorization conditions? [Completeness, Spec §FR-003]
- [x] CHK004 Is the unproven-runtime outcome stated as a block rather than a degraded result? [Clarity, Spec §FR-004]

## Consistency and Boundaries

- [x] CHK005 Are direct, emulated, best-effort, ambiguous and stale substitutes consistently excluded across requirements and scenarios? [Consistency, Spec §FR-005]
- [x] CHK006 Is human authorization limited to `ship` and explicitly unable to replace its canonical skill? [Consistency, Spec §FR-006]
- [x] CHK007 Is offline operation compatible with the prohibition on discovery or download of a substitute? [Consistency, Spec §FR-007]
- [x] CHK008 Are workflow migration, work-item migration and output attestation explicitly deferred to later handoffs? [Scope, Spec §Assumptions]

## Acceptance Quality

- [x] CHK009 Can each successful resolution be evaluated by one deterministic identity and repeatability criterion? [Measurability, Spec §SC-001, SC-003]
- [x] CHK010 Are malformed, stale, ambiguous, untrusted and unproven cases distinguished enough to produce a structured failure matrix? [Coverage, Spec §US2]
- [x] CHK011 Do edge cases cover byte identity, duplicate claims, self-authorized trust and cross-context invocation? [Coverage, Spec §Edge Cases]

# Orchestration Requirements Checklist: Latest model by family

**Purpose**: Review the completeness and clarity of model selection, historical continuity, and release requirements before tasks are written.
**Created**: 2026-09-24
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [ ] CHK001 Are selection requirements defined for each Codex worker tier and specialist role? [Completeness, Spec §FR-001, §FR-003]
- [ ] CHK002 Are all unusable catalog conditions and their required refusal details specified? [Completeness, Spec §FR-005]
- [ ] CHK003 Is the durable association between a selected model and each worker or specialist observation specified? [Completeness, Spec §FR-004]
- [ ] CHK004 Are the requirements for verifying previously sealed contexts stated without assuming a current catalog or rewritten evidence? [Completeness, Spec §FR-009]
- [ ] CHK005 Are the version, CHANGELOG, tag, and Release obligations all stated for delivery? [Completeness, Spec §FR-012]

## Requirement Clarity and Consistency

- [ ] CHK006 Is "lowest numeric priority" defined sufficiently to decide ties, invalid numbers, and hidden members without relying on catalog order? [Clarity, Spec §FR-001, §SC-002]
- [ ] CHK007 Are Luna, Terra, Sol, and Astra roles consistent across the worker and specialist requirements? [Consistency, Spec §FR-002, §FR-003]
- [ ] CHK008 Is the frontier worker refusal ordered clearly against model resolution and dispatch effects? [Clarity, Spec §FR-006]
- [ ] CHK009 Are the Claude `opus` pairs and `fable` refusal consistent between behavior and public guidance? [Consistency, Spec §FR-007, §FR-011]
- [ ] CHK010 Are historical policy verification and new policy selection distinguished clearly enough to avoid changing sealed work items? [Clarity, Spec §FR-009]
- [ ] CHK011 Does the plan specify how this v1 campaign continues after candidate v2 behavior without weakening the Claude refusal? [Consistency, Spec §FR-007, §FR-009]

## Acceptance Criteria Quality

- [ ] CHK012 Can each of the eight handoff outcomes be judged from an expected model or named refusal? [Measurability, Spec §SC-001]
- [ ] CHK013 Is the no-effects condition measurable for worktrees, leases, and technical payloads across every unresolved case? [Measurability, Spec §SC-003]
- [ ] CHK014 Is historical context verification objectively defined independently of a new catalog lookup? [Measurability, Spec §SC-004]
- [ ] CHK015 Are the eight version locations and immutable tag/Release relationship specific enough for an objective delivery decision? [Measurability, Spec §SC-005, §SC-007]
- [ ] CHK016 Is offline validation bounded by explicit fixture provenance and forbidden runtime/network dependencies? [Measurability, Spec §FR-010, §FR-013, §SC-008]

## Scenario and Edge Case Coverage

- [ ] CHK017 Are absent, unreadable, malformed, ambiguous, and family-empty catalogs addressed as distinct failure conditions or an explicitly shared refusal? [Coverage, Spec §FR-005]
- [ ] CHK018 Are retries after a catalog change and new attempts after remediation distinguished in the requirements? [Coverage, Spec §FR-004, §FR-005]
- [ ] CHK019 Are predecessor contexts without a campaign and predecessor contexts requiring a bridge both covered for historical continuity? [Coverage, Spec §FR-009]
- [ ] CHK020 Are recovery requirements stated for a failed continuity check before further specialist or release effects? [Coverage, Spec §FR-009, §FR-012]
- [ ] CHK021 Is the requirement for preserving Claude worker aliases and leader recommendations explicit while specialist aliases change? [Coverage, Spec §FR-007, §FR-008]

## Dependencies and Assumptions

- [ ] CHK022 Is the local catalog dependency described without implying a download, freshness guarantee, or provider availability? [Assumption, Spec §FR-001, §FR-005]
- [ ] CHK023 Is the preserved v1 coordination bundle and its verification evidence identified before candidate changes are allowed? [Dependency, Spec §FR-009]

## Notes

- These questions assess requirements quality. The later verify step tests implementation behavior.

# Feature Specification: Latest model by family

**Feature Branch**: `cadugevaerd/fix-latest-models`

**Created**: 2026-09-24

**Status**: Draft

**Input**: `.grill/work-items/feature-latest-models-codex-ab7615f7e67f4e2c9d2b94f507c921ec/handoffs/FASE-001-SPECIFY-HANDOFF.md`

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Select the preferred model within a Codex family (Priority: P1)

A GWD leader dispatches a Codex worker for a declared tier. The worker uses the locally listed model with the highest preference within that tier's family, and the selected model is recorded. A new generation is selected only when the local catalog ranks it ahead of the current generation.

**Why this priority**: Generation pins become stale and silently dispatch older models.

**Independent Test**: Present two listed generations of the same family in both priority orders and observe the dispatch choice and durable record.

**Acceptance Scenarios**:

1. **Given** listed Luna models with `gpt-6-luna` at priority 0 and `gpt-5.6-luna` at priority 10, **When** a small worker is declared, **Then** it uses and records `gpt-6-luna`.
2. **Given** the same entries with reversed priorities, **When** a small worker is declared, **Then** it uses and records `gpt-5.6-luna`.
3. **Given** no generation 6 Terra and `gpt-5.6-terra` is the preferred listed Terra, **When** a medium worker is declared, **Then** it uses and records `gpt-5.6-terra`.
4. **Given** a newer listed Terra with a lower priority value, **When** a medium worker is declared, **Then** it uses and records the newer Terra.

---

### User Story 2 - Fail closed when model choice is unproven (Priority: P1)

A GWD leader receives a named refusal before dispatch if the local Codex catalog cannot establish a listed model in the required family. A frontier family remains forbidden for a worker.

**Why this priority**: Silent fallback would recreate the defect, while frontier dispatch would breach the worker floor.

**Independent Test**: Attempt declarations with missing, unreadable and family-empty catalogs, then with a frontier worker tier; observe refusal before any worktree, lease or payload.

**Acceptance Scenarios**:

1. **Given** an absent or unreadable catalog, **When** a Codex worker or specialist is prepared, **Then** `TIER-MODEL-UNRESOLVED` identifies the runtime, tier or role, family and catalog path before any dispatch effect.
2. **Given** a catalog without a listed member of the required family, **When** a Codex worker or specialist is prepared, **Then** the same named refusal occurs.
3. **Given** a frontier worker tier, **When** a worker is declared, **Then** `FRONTIER-MODEL-FORBIDDEN` occurs before any worktree or lease.

---

### User Story 3 - Use the current specialist family (Priority: P2)

A Codex author or reviewer uses the preferred listed Astra and is checked against the observed effective model. A Claude author or reviewer uses the `opus` alias with the required effort. Existing sealed work items remain verifiable.

**Why this priority**: Specialist judgment must use the approved family without pinning a generation or accepting a divergent effective model.

**Independent Test**: Prepare both specialist roles with preferred and nonpreferred catalog orders; check requested and effective model acceptance, Claude role pairs, and a previously sealed context.

**Acceptance Scenarios**:

1. **Given** multiple listed Astra generations, **When** a Codex author or reviewer is prepared, **Then** the lowest priority Astra is requested, the observed effective slug is checked, and the resolved slug is recorded.
2. **Given** a Claude author, **When** the role is prepared, **Then** the required pair is `opus` with `xhigh`; for a reviewer it is `opus` with `high`.
3. **Given** a Claude specialist requested or observed as `fable`, **When** its role is checked, **Then** the pair is refused as divergent.
4. **Given** an existing context sealed with the prior orchestration policy, **When** its historical evidence is checked, **Then** it remains verifiable without rewriting the sealed policy.

### Edge Cases

- A catalog entry that is hidden rather than listed does not qualify as a model choice.
- A newer generation listed with a worse priority does not displace the preferred older one.
- A missing, malformed or unreadable catalog cannot trigger a last known model fallback.
- Equal or invalid priorities require a deterministic, fail-closed outcome rather than an arbitrary selection.
- Claude worker tiers and the leader model recommendation retain their current behavior.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: For each Codex worker tier, GWD MUST bind a model family and select the listed member with the lowest numeric priority in the local catalog.
- **FR-002**: The medium Codex worker tier MUST remain in the Terra family; the small tier MUST remain Luna; the large tier MUST remain Sol and forbidden to workers.
- **FR-003**: Codex author and reviewer roles MUST select the preferred listed Astra and compare the observed effective model with the selected slug.
- **FR-004**: GWD MUST record each resolved Codex model slug with the corresponding worker or specialist observation.
- **FR-005**: A missing, unreadable or unusable Codex catalog, or a family without a listed member, MUST refuse with `TIER-MODEL-UNRESOLVED` and identify the runtime, tier or role, family and catalog path before worktree, lease or payload effects.
- **FR-006**: A frontier family requested for a worker MUST continue to refuse with `FRONTIER-MODEL-FORBIDDEN` before dispatch effects.
- **FR-007**: The Claude specialist author pair MUST be `opus`/`xhigh` and the reviewer pair MUST be `opus`/`high`; `fable` MUST be refused for either role.
- **FR-008**: Claude worker aliases and the leader recommendation MUST retain their existing behavior.
- **FR-009**: Previously sealed work items and contexts MUST remain verifiable without rewriting historical policy or receipts.
- **FR-010**: The behavior MUST be verifiable offline without installing a runtime or contacting a network service.
- **FR-011**: Public role guidance MUST present Claude specialist author as `opus`/`xhigh` and reviewer as `opus`/`high`, without requiring `fable`.
- **FR-012**: Delivery MUST increment the plugin SemVer in all eight required distribution locations and include the corresponding CHANGELOG entry. A published version MUST have an immutable tag and a release anchored to the same commit through the release pipeline.
- **FR-013**: Offline validation MUST use a fixture derived from the Codex 0.155.1 catalog without requiring real `codex`, `claude`, `node` or network access. Dispatch expectations MUST follow the supplied catalog priority rather than a hard-coded generation slug.

### Key Entities

- **Catalog model**: A locally listed model with a slug, family and preference priority.
- **Worker tier**: A size and frontier classification that determines the eligible family.
- **Specialist role**: Author or reviewer, with model family or alias and required effort.
- **Model resolution record**: The selected slug bound to a worker or specialist observation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All eight handoff scenarios produce the specified model or named refusal in offline checks.
- **SC-002**: In 100% of tested catalog order changes, the lowest priority listed member of the required family is selected, regardless of generation number.
- **SC-003**: In 100% of tested unresolved cases, no worktree, lease or technical payload is created.
- **SC-004**: Existing sealed contexts remain verifiable after the change.
- **SC-005**: The full offline validator suite exits successfully, and distribution version metadata is consistent at all required locations.
- **SC-006**: Public role guidance requires `opus`/`xhigh` and `opus`/`high` for Claude specialists and nowhere requires `fable` for those roles.
- **SC-007**: The delivered plugin has a higher SemVer across all eight required locations, a matching CHANGELOG entry, and, if published, a pipeline-created Release at the immutable tag commit.
- **SC-008**: Offline checks cover all eight handoff scenarios using a Codex 0.155.1-derived fixture, require no real `codex`, `claude`, `node` or network, and include a newer generation that is listed but not preferred.
- **SC-009**: `git diff --check` reports no errors for the delivery.

## Assumptions

- The Codex local catalog provides listed model slugs and numeric priorities; its absence or incompatible format is a refusal.
- Priority is the catalog's preference order, not a generation comparison.
- This phase does not change the user's Codex configuration, Claude worker tiers, the leader recommendation or network/install behavior.
- The handoff, ADR-0001 and ADR-0002 are the approved scope and decision sources.

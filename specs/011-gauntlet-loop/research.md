# Research: Gauntlet Loop Activation

## Decision: keep V3 admission in existing guard modules

**Rationale**: `workflow_v3.execution_gate()` proves the pinned V3 workflow and ordered eleven-stage cycle; `work_item_v3.require_v3()` is the public V3 work-item guard; `step_skills.resolve_workflow_skill(step, "claude", registry_sha256, registry=registry_bytes, catalog=claude_catalog)` validates a native runtime resolution against the shipped trusted catalog. Reimplementing any of these checks would let Gauntlet acceptance drift from V3 acceptance.

**Alternatives considered**:

- Inspect a runtime name or `resolved: true` registry field only — rejected because it does not prove every step or catalog trust.
- Add a Gauntlet-specific parallel validator — rejected because registry pin and catalog trust could diverge.

## Decision: config is a project-versioned, strict JSON-compatible YAML document

**Rationale**: The requested `.grill/gauntlet.yaml` is visible in the project and can be reviewed with other source changes. JSON syntax is valid YAML and is parsed by the standard library with a duplicate-key hook, allowing exact schema, type, and canonical-write checks without a new dependency.

**Alternatives considered**:

- Store policy under Git common directory — rejected because it is not project-versioned and does not satisfy explicit activation visibility.
- General YAML syntax — rejected because a parser dependency and its ambiguous features conflict with the standard-library-only, fail-closed plugin contract.
- Put fields in `orchestrator.json` — rejected because its top-level schema is closed and already has compatibility tests.

## Decision: activation map is keyed by immutable work-item identity

**Rationale**: One project can prepare multiple isolated V3 work items without one item's configuration overwriting another. Every command still requires one exact `--work-id`, and a record includes that same identity redundantly for corruption detection.

**Alternatives considered**:

- One unkeyed active configuration — rejected because the next activation would silently replace another work item.
- Per-work-item mutable config outside the project — rejected because it hides the decision and complicates review.

## Decision: package the Claude catalog and persist complete identities

**Rationale**: The resolver requires a catalog document in addition to the shipped trust pin. The existing test fixture has the catalog content but a production activation cannot depend on test bytes. FASE-001 adds an immutable asset with that catalog and verifies it against `workflow-trusted-catalogs.json`. Each activation records its catalog ID/digest, trusted-pin asset digest, workflow/registry digests, and V3 `WORK-ITEM.json` digest so status detects every material drift.

**Alternatives considered**:

- Caller-supplied catalog or trust mapping — rejected because it permits self-authorization.
- Rely on a work-item ID alone — rejected because identity does not detect changed immutable metadata.

## Decision: config transaction is global, not per work item

**Rationale**: A shared activation map needs one config-wide no-follow lock and expected-byte compare-before-replace. Per-work-item locks cannot prevent two different work items from overwriting each other's map changes.

**Alternatives considered**:

- Per-work-item lock only — rejected because concurrent activation of different items races.
- Best-effort atomic replacement — rejected because atomic replacement alone does not preserve both concurrent updates or prove safe path ownership.

## Decision: rebind legacy work items only through explicit migration

**Rationale**: V3 migration preserves a legacy work item's historic workflow hash. Activation must compare that immutable hash with the current V3 workflow and fail rather than silently replacing it. `migrate-v3 --rebind-workflow` therefore offers a preview-first, CAS-protected rebind after the V3 workflow gate passes.

**Alternatives considered**:

- Let activation update the binding — rejected because admission would silently rewrite immutable authority.
- Ignore the old binding — rejected because a V3 work item would not be provably tied to the active workflow.

## Decision: phase-one run is admission only

**Rationale**: The FASE-001 handoff requires starting a run, while the roadmap reserves durable runs, leases, evidence, and worktrees for FASE-002. `RUN-ADMITTED` is observable and revalidates eligibility but cannot dispatch a stage or create scheduling state.

**Alternatives considered**:

- Reject run until FASE-003 — rejected because it contradicts the handoff.
- Create partial durable run state now — rejected because it would duplicate FASE-002 authority and require unsafe cleanup/resume semantics.

## Decision: Claude Code only until another runtime has equivalent proof

**Rationale**: The registry currently resolves the required canonical entrypoints for `claude`; other runtimes lack the full proven entrypoint contract. The feature must fail closed instead of interpreting comparable commands as equivalent.

**Alternatives considered**:

- Codex or Hermes fallback — rejected because missing entrypoints and catalog proof make it unsafe.
- User-provided runtime mapping — rejected because activation must not delegate capability authority to mutable local input.

## Decision: no budget policy

**Rationale**: The operator explicitly removed budget from this project. The config contains no cost ceiling, spend state, or automatic financial stop condition. Runtime capability and named safety blocks remain independent of cost.

**Alternatives considered**:

- Optional budget field — rejected because an unused authority expands the closed schema and implies an unsupported stop condition.

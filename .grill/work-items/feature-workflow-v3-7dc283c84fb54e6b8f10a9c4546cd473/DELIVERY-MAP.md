# DELIVERY-MAP

decomposition-schema: v1

## MOD-001 — Canonical skill governance
- module-kind: cross-cutting
- responsibility: Define the authorized capability for every required workflow step
- boundary: Registry, trust evidence, and resolution
- depends-on: none

### DU-001 — Canonical step registry
- development-type: platform-devops
- phase: FASE-001
- scope-in: Ordered registry, trusted catalog, canonical resolution
- scope-out: Workflow document migration and step output acceptance
- depends-on: none
- acceptance: Every required step resolves uniquely or blocks with evidence

## MOD-002 — Workflow adoption
- module-kind: cross-cutting
- responsibility: Preserve V2 while enabling explicit V3 adoption
- boundary: Managed workflow document and read-only status projection
- depends-on: MOD-001

### DU-002 — Workflow V3 migration
- development-type: platform-devops
- phase: FASE-002
- scope-in: Preview, explicit apply, V2/V3 dual read, read-only hook
- scope-out: Work item migration and execution attestation
- depends-on: DU-001
- acceptance: Valid V2 remains intact; approved V3 adoption is atomic and reusable

## MOD-003 — Work item coordination
- module-kind: platform
- responsibility: Keep work item identity and lifecycle coherent across worktrees
- boundary: Work item metadata and Project Store
- depends-on: none

### DU-003 — Work Item V3 and Project Store
- development-type: platform-devops
- phase: FASE-003
- scope-in: Dual read, explicit migration, identity, shared history, lock and CAS behavior
- scope-out: Canonical skill authorization and global reconciliation
- depends-on: none
- acceptance: Concurrent linked worktrees retain one integrity-checked work item history

## MOD-004 — Attested execution
- module-kind: cross-cutting
- responsibility: Accept only outputs produced by authorized canonical skills
- boundary: Dispatch, invocation, terminal receipts, outputs, and public diagnostics
- depends-on: MOD-001, MOD-002, MOD-003

### DU-004 — Cooperative execution attestation and wiring
- development-type: platform-devops
- phase: FASE-004
- scope-in: Full cooperative attestation chain, replay defense, compatibility wiring, diagnostic translation
- scope-out: Direct execution substitutes and cryptographic runtime provenance
- depends-on: DU-001, DU-002, DU-003
- acceptance: Only a complete, correlated canonical-skill chain can advance a V3 step

> IDs are stable within this work item. `module-kind` is one of `domain|platform|cross-cutting`; each DU has exactly one closed development type.

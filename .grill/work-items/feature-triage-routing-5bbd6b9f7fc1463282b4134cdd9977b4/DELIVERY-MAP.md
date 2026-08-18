# DELIVERY-MAP

decomposition-schema: v1

## MOD-001 — Triage routing
- module-kind: cross-cutting
- responsibility: Turn a proven root-cause report into a verifiable, sealed routing decision
- boundary: Report parsing, per-route evidence matrix, sealed triage record
- depends-on: none

### DU-001 — Sealed triage record
- development-type: platform-devops
- phase: FASE-001
- scope-in: Fingerprinted report read, declared-status verification, per-route evidence matrix, sealed and immutable record, preview-first apply, idempotence and divergence detection
- scope-out: Requiring triage in init and hotfix, reduced bugfix track, per-track skill registry, workflow document contract for tracks
- depends-on: none
- acceptance: A route opens only from a report proving the root cause with the evidence that route demands, and the recorded decision is tamper-evident

> IDs are stable within this work item. `module-kind` is one of `domain|platform|cross-cutting`; each DU has exactly one closed development type.

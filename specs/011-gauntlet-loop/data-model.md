# Data Model: Gauntlet Loop Activation

## Gauntlet Configuration

| Field | Type | Validation |
|---|---|---|
| `schema` | string | Exactly `grill-gauntlet/v1`. |
| `activations` | object | Non-empty string work-item IDs map to activation records; no unknown top-level field. |

## Activation Record

| Field | Type | Validation |
|---|---|---|
| `work_item_id` | string | Equals its map key and passes the existing immutable work-item identifier validation. |
| `work_item.document_sha256` | string | SHA-256 of the current V3 `WORK-ITEM.json` bytes. |
| `workflow.version` | string | Exactly `v3`. |
| `workflow.sha256` | string | SHA-256 of the current accepted workflow bytes. |
| `workflow.registry_sha256` | string | SHA-256 of the current registry bytes accepted by the workflow gate. |
| `runtime.id` | string | Exactly `claude` in this release. |
| `runtime.adapter` | string | Exact approved native adapter identity from resolved entries. |
| `catalog.id` | string | Exact catalog ID expected by every resolved Claude entrypoint. |
| `catalog.document_sha256` | string | SHA-256 of the immutable Claude catalog file bytes. |
| `catalog.resolution_sha256` | string | Declared JCS SHA-256 of catalog entries; must match the shipped trust pin for `catalog.id`. |
| `catalog.trusted_asset_document_sha256` | string | SHA-256 of the shipped trusted-catalog pin asset bytes that authorized `catalog.id`. |
| `limits.max_workers` | integer | Selected inclusive range 1–5; booleans, floats, strings, zero, negatives, and values above five are rejected. |
| `limits.stall_minutes` | integer | Exactly 15. |
| `tier_policy.adapter` | string | Exact native Claude adapter identity. |
| `tier_policy.minimum_by_step` | object | Exact canonical eleven-stage map to `small`, `medium`, or `large`. |
| `tier_policy.supplemental` | object | Exactly `markdown-maintenance: small`; it is not a twelfth canonical stage. |
| `tier_policy.promotions` | array | Closed, auditable pre-dispatch promotion records; empty on FASE-001 activation. |

The record contains neither credentials nor host paths, process IDs, run IDs, worker data, budget fields, or user-controlled trust locations.

## Activation State Projection

| State | Predicate | Required reason |
|---|---|---|
| `STALE` | A record exists and its recorded workflow, registry, catalog, or work-item identity differs from current verified identity. | Yes |
| `BLOCKED` | No stale record takes precedence and the current V3/work-item/runtime proof cannot be determined or fails. | Yes |
| `ACTIVATED` | Current eligibility succeeds and a matching record exists. | No |
| `ELIGIBLE` | Current eligibility succeeds and no record exists. | No |

Exactly one state is emitted by `gauntlet-status` in the listed precedence order.

## Command Outcomes

| Outcome | Transition |
|---|---|
| `ACTIVATED` | Valid absent activation becomes a complete activation record. |
| `REUSED` | Equivalent activation remains unchanged. |
| `BLOCKED` + `ACTIVATION-CONFLICT` | A conflicting activation remains unchanged. |
| `RUN-ADMITTED` | A matching current activation is revalidated; no durable run transition occurs. |
| `BLOCKED` + `ACTIVATION-REQUIRED` | Run/resume has no valid activation; no state changes. |
| `BLOCKED` + `SCHEDULING-NOT-AVAILABLE` | Resume/cleanup are deferred safely; no state changes. |
| `BLOCKED` + precise code | Eligibility, parsing, trust, path, or loading failure; no partial state. |

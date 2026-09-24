# Data model: model selection

This design reuses existing Store and observation entities. The catalog is an external read-only input; no new database, global state or model registry service is introduced.

## 1. Codex catalog input

Source: `<Codex home>/models_cache.json`, where Codex home follows the existing nonempty `CODEX_HOME` override or `Path.home() / '.codex'` convention. Tests inject an absolute catalog path.

| Field | Type and rule |
|---|---|
| Root | JSON object; duplicate keys and non-finite JSON constants refused. |
| `models` | Required array of objects; absence/wrong type is unresolved. |
| `models[].slug` | Required nonempty string; use the full-string family grammar to determine membership. Generic valid strings can be unrelated entries. |
| `models[].visibility` | Required string; only exact `list` is eligible. |
| `models[].priority` | Finite number, excluding boolean, required for every listed member of the requested family. |
| Other fields | Allowed and ignored for selection, including `upgrade`, model instructions, client metadata and reasoning capabilities. |

Family is derived, not trusted from an optional external field. Allowed current families are `luna`, `terra`, `sol`, `astra`. Read/parse/selection failures produce `TIER-MODEL-UNRESOLVED`; they do not generate a selection record. A minimum-priority tie or duplicate relevant slug is a failure, not an order-dependent choice.

`fetched_at`, `etag`, `client_version` and `identity` describe the cache; none ranks a model. The feature adds no age expiry policy. Raw account identity and model instruction bodies are not copied to errors or worker records.

## 2. Current worker binding asset

Keep filename `assets/workflow-tier-models.json`; advance schema to `workflow-tier-models/v2` and `binding_version` to `2`. Preserve workflow version, tier order, actor classes, adapters and unresolved-runtime handling.

| Runtime | Tier entry shape | Values |
|---|---|---|
| Codex | Exactly `family`, `frontier` | small: Luna/false; medium: Terra/false; large: Sol/true. |
| Claude | Exactly `model`, `frontier` | small: haiku/false; medium: sonnet/false; large: opus/true. |

Reject ambiguous entries containing both `model` and `family`, unknown keys/families, non-boolean flags and unsupported schemas. Worker frontier admission precedes catalog I/O. A permitted leader resolution of a frontier family remains possible; leader recommendation text is unchanged.

## 3. Worker model binding in the Store

Add one field, `model_binding`, to the existing worker object. Use `_required_optional_object` for backward-compatible reading instead of changing historical payloads. Every new worker producer must supply it before mint; structural validation and replay still accept historical rows/events without it, rather than enforcing a new required key retroactively. Historical workers remain readable/cleanable with model unknown.

The nested object is the existing resolver result, with exactly these keys:

| Field | Rule |
|---|---|
| `runtime` | `codex` or `claude`; the producer checks the validated activation runtime whose hash is pinned in admission. The admission itself contains hashes, not a runtime field. |
| `tier` | Validated tier, matching the DAG declaration or the derived passive-preparation floor. |
| `actor_class` | Exact `worker`. |
| `adapter` | Existing adapter belonging to that runtime. |
| `model` | Resolved Codex slug or existing Claude worker alias; nonempty, no placeholder. |
| `frontier` | Exact boolean `false` for a worker. |

The current asset establishes family eligibility before mint. Store replay validates this saved shape and worker safety without reading the live catalog or reinterpreting the historical slug against a changed policy asset. Runtime/tier and the full binding are immutable for the lifetime of the worker; transitions must refuse removal, alteration or retroactive addition to an already historical record. A newly created replacement has its own binding and points to the prior worker through `remediates`.

The `DECLARED` mint records the binding atomically with the worker identity and first lease. The resolution is complete before mint; missing catalog must leave no lease, grant, worktree or replacement state mutation. Subsequent `PREPARING`, `PREPARED`, terminal and cleanup transitions retain the same binding.

Public projections keep existing fields `model`, `model_frontier`, `model_runtime`, deriving them from the stored binding. A retry must return that binding; it cannot return a fresh selection for an already existing worktree. Historical projections report an unknown/missing binding honestly, without backfilling a guessed generation.

## 4. Specialist activity and observation

No new activity fields are required. Existing fields carry the chosen model:

| Field | Binding point and meaning |
|---|---|
| `policy_sha256` | Immutable policy selected by the owning context. |
| `runtime`, `requested_model`, `requested_effort` | Set during first preparation, immutable in the Store. Codex model is the selected Astra slug; current Claude model is `opus`. |
| `effective_model`, `effective_effort` | First-bound from the correlated native runtime observation, before technical payload. |
| `resolved_model_id` | First-bound observed identifier. Exact Codex slug; literal `opus` for the currently evidenced Orca format. It is not proof of a hidden full provider slug. |
| `launch_observation_ref`, session identity/resource | Existing source hash/identity correlation; preserved through return and close. |

State flow remains `DECLARED → BOOTSTRAPPING → VERIFIED → DISPATCHED → RESULT_RECORDED → ACCEPTED`, with existing BLOCKED/FAILED alternatives. The constructor's transient unbound activity is not persisted: first successful prepare supplies the resolved pair before recording BOOTSTRAPPING.

After first preparation, comparison uses the immutable request, not the current cache. At verification, the native requested pair must match the activity; provider, effective model/effort and resolved ID must agree. On return, the same identity and first-bound effective facts must remain intact. Review independence and close evidence are unchanged.

A catalog refresh is not a state transition. A new activity may select another slug; an existing activity is never retargeted. Deterministic-check activities retain null model/runtime slots and do not read the catalog.

## 5. Versioned orchestration policy

| Entity | Current creation | Historical reading |
|---|---|---|
| Policy asset | `assets/agent-orchestration.v2.json`; schema `grill-agent-orchestration-policy/v2`, version `2`. | v1 file and bytes preserved. |
| Codex roles | Exactly `family='astra'`, `reasoning_effort='xhigh'` or `high`. | v1 literal request interpreted only under v1. |
| Claude roles | Exactly `model='opus'`, effort `xhigh` or `high`. | Existing v1 records remain evidence of what was requested/observed then. |
| Work item/context | New init/adopt pins current v2 ref/hash. | Existing ref/hash remains immutable through resume/takeover and replay. |
| Activities/checkpoints | Retain their owning policy hash. | Never rewritten or automatically resealed. |

The loader has a closed allowlist of shipped policy references and verifies bytes against the stored hash before use. Unknown reference, changed bytes, unknown schema/version or contradictory context/activity hash refuses `ORCHESTRATION-POLICY-STALE`.

No Store orchestration schema change or mutable policy-version pointer is required. No new fable payload is released from a historical prepared activity; terminal evidence/cleanup remain available. Fresh preparation on a v1 item under the candidate refuses `ORCHESTRATION-MIGRATION-REQUIRED`; historical verification, result completion and cleanup remain available. This feature does not migrate existing campaign seals.

The current campaign's operational continuity record is the existing work-item `continuity-bundle-proof.json` (schema `grill-continuity-bundle-proof/v1`, SHA-256 `89f6ede5fd321c1fe901271386458ba6fda452661a3758db4d2cedea0b4817fc`), not a new Store field or policy pointer. It fixes `/home/carlosaraujo/orca/workspaces/grill-with-docs/continuity-5544829`, revision `5544829185c2e5d1d75e52736364aa00bede9323`, and tree `d5cc959f9c02a98ddc3a5adfd958d729b62807ce` at `plugin/skills/grill-with-docs`; its `files` entries bind five paths, SHA-256 values and sizes. The coordinator freezes these bytes before candidate changes and uses the absolute CLI recorded in [plan.md](plan.md), section 4, while candidate validation stays isolated.

That bundle contains the pre-campaign successor fix and preserves v1 Codex preparation. Revalidation compares the manifest to actual Git/files, validates the current Store and keeps the existing policy/context/campaign/registry/catalog pins unchanged; ordinary canonical progress may append new records, never rewrite old receipts or bridges. Pure preparation evidence does not create an activity in Store or prove a launch. Every real author/reviewer retains the existing bootstrap, observed-pair, independence and close lifecycle through ship. The bundle cannot authorize a new Claude fable activity or reinterpret v1 as Opus; use Codex, or a separately justified safe Claude route, otherwise nominal hold. Any failed revalidation stops dependent work for authorized deterministic coordinator recovery or `GOAL-HOLD`.

## 6. Failure record

Public catalog failure remains a BLOCKED CLI response with exit 2 and code `TIER-MODEL-UNRESOLVED`. It includes `runtime`, exactly one context identifier (`tier` or `role`), `family`, `catalog_path` and `reason`, plus existing work/activity identifiers where available. Reasons distinguish missing/unreadable file, invalid shape, no listed family, invalid priority, duplicate relevant slug and ambiguous minimum. The failure record exposes no catalog bodies or user configuration.

Catalog failure occurs before a new resolution can be persisted. Existing historical evidence remains untouched. An argparse exit 2 without the named JSON payload is not this contract's refusal.

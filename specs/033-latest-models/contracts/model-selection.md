# Contract: model selection and historical policy

Applies to the current policy introduced by spec 033. This is a design contract for existing Python/CLI interfaces, not a new HTTP API. Normative sources are spec FR-001–FR-013 and work-item ADR-0001/ADR-0002.

## 1. Resolution boundary

`grill_core.tier_models` owns Codex family-to-slug selection. Its worker entry remains `resolve_model(runtime, tier, *, actor_class, binding=..., catalog_path=...)`; the optional catalog path is a Python test seam, not a new user configuration or CLI flag. A shared family resolver is also called by specialist preparation at the existing CLI boundary. `agent_orchestration` remains pure and receives the selected pair and policy as values.

| Actor | Runtime | Selector | Required effort |
|---|---|---|---|
| Worker small | codex | family `luna` | Existing worker effort policy, unchanged. |
| Worker medium | codex | family `terra` | Existing worker effort policy, unchanged. |
| Worker large | codex | family `sol`, frontier | Forbidden for workers. |
| Author | codex | family `astra` | `xhigh` |
| Reviewer | codex | family `astra` | `high` |
| Author | claude | alias `opus` | `xhigh` |
| Reviewer | claude | alias `opus` | `high` |

Claude worker aliases and frontier flags stay `haiku`/false, `sonnet`/false, `opus`/true. The leader recommendation remains `Sol` in Codex and `Opus` in Claude. No caller gains a worker model override.

Resolution order:

1. Validate runtime, actor class, tier/role and binding/policy shape. Keep existing UNKNOWN/UNRESOLVED errors for invalid runtime/tier/actor or malformed assets.
2. Reject a frontier family for actor `worker` with `FRONTIER-MODEL-FORBIDDEN`, before catalog access or effects.
3. For an allowed Codex actor, locate/read/parse the local catalog. For Claude aliases, no catalog is read.
4. Select a unique listed minimum within the declared family, or return the named catalog refusal.
5. Persist the selection with the new worker/activity before dependent preparation/bootstrap/payload effects.

## 2. Local catalog input

Default path is `<nonempty CODEX_HOME or Path.home()/.codex>/models_cache.json`. Normalize the resulting path to an absolute path for the existing safe reader and diagnostics; do not resolve symlinks to bypass that reader's checks. Failure to determine home is unresolved with the attempted source identified, never a default model.

The existing bounded regular-file reader is reused; missing, unreadable, symlinked/non-regular, oversized or racing input is refused. Its default limit is 16 MiB. Bytes are UTF-8 JSON with an object root and a `models` array. Reject duplicate JSON keys and non-finite JSON constants. Allow extra fields without treating their contents as instructions or running them.

Each model row must be an object with a nonempty string `slug` and string `visibility`. A candidate must satisfy all of:

- `visibility == 'list'` exactly.
- Slug full-matches `gpt-[0-9]+(?:\.[0-9]+)*-(luna|terra|sol|astra)`.
- The suffix after the final hyphen equals the required family.
- `priority` is a finite `int` or `float`, excluding `bool`.

Rows with another family or nonmatching slug are unrelated; hidden rows are ineligible. Their priority is not part of this family's comparison. An invalid priority on any listed matching candidate is unresolved, because it cannot be ranked safely. A duplicate matching listed slug is unresolved even when repeated rows agree. A unique minimum wins; ties for the minimum refuse. Array order and numeric generation do not break ties. Ties only among worse-priority candidates do not change a unique winner.

`gpt-reserve` and `codex-auto-review` are excluded. `gpt-5.5` is not a family slug; its `upgrade` field cannot redirect selection. Freshness timestamps, model instructions and service tiers do not alter the ranking. An old but structurally valid catalog is used as observed; no remote-availability claim follows from this read.

## 3. Successful worker result and durable state

The Python resolver retains the existing result keys:

```text
runtime, tier, actor_class, adapter, model, frontier
```

`model` is the chosen concrete Codex slug or unchanged Claude alias. Persist that exact object as `worker.model_binding` in the first worker-declared Store transaction, before the worktree intent. A new worker producer must not mint a record without resolution. The Store's structural reader accepts historical records lacking the field and validates/immutably protects it whenever present; it must not reject replay of pre-feature journal entries merely because the field was absent then.

Existing CLI success fields remain `model`, `model_frontier`, `model_runtime`, projected from the saved binding. The caller uses the recorded model for the actual worker start and still verifies requested/effective model and supported effort through the runtime contract. Selection evidence does not itself prove execution.

A recorded worker ID/attempt is immutable. Repeating declaration/preparation returns its saved model with the existing reuse behavior, even if the catalog later changes or disappears. Reuse never creates a new dispatch attempt implicitly. Missing binding on a historical prepared record cannot be repaired by choosing from today's cache; refuse the effect with `WORKER-MODEL-UNPROVEN`, identifying the worker/run and missing binding proof; require a fresh admitted attempt.

All producers are covered:

- `declare_worker`: explicit validated DAG tier and validated activation runtime; resolve before `prepare_worker` and before a new lease/worktree.
- `gauntlet-prepare-worker`: no arbitrary model/tier inference. Derive the passive worker's minimum tier from the current activation's executor/markdown floor and grant classification, and its runtime from the validated activation record returned by `gauntlet_run_admission` (`record["runtime"]["id"]`), whose hash is pinned in admission; pass a validated binding to the same preparation path.
- `_mint_remediation_worker`: resolve a new attempt from the original bound runtime/tier before spending remediation budget, changing the original state or minting a lease. Preserve the existing concurrent cap and one-remediation budget. If a historical binding cannot be proven from its sealed DAG and matching activation, refuse `WORKER-MODEL-UNPROVEN` before effects rather than using a default.

## 4. Specialist lifecycle

A fresh specialist preparation resolves the current policy's pair before writing BOOTSTRAPPING or returning neutral bootstrap instructions. Codex resolution uses the same catalog routine as workers. Deterministic activities keep null runtime/model fields and skip resolution.

Save the selected Codex slug in `activity.requested_model`; save the specified effort in `requested_effort`. These fields are immutable. Repeated preparation of the same activity does not reselect. The lifecycle keeps its existing identity/fence/input-manifest requirements.

Before releasing technical payload and again on result acceptance:

1. Resolve the activity's recorded policy by its sealed reference/hash, without reading the catalog.
2. Check runtime/role/effort and that the saved request belongs to the policy's family or exact alias; validate the native observation's requested model/effort against that saved request.
3. Require provider, effective model/effort and `resolved_model_id` to agree with the saved request. For Codex, accepting another Astra generation is a divergence.
4. Preserve current incarnation/dispatch/worktree identity, reviewer independence, presentation readiness and resource-close requirements.
5. Preserve the first observed effective fields on return; no model change is accepted because a later catalog prefers it.

This rule is shared by verification, session registration, acceptance, visual-author/reviewer validation and task-files review. A change to `specialist_pair` alone is insufficient.

For Claude, the observed current transport reports `opus` in both requested and effective fields. Exact alias equality is the only newly authorized form; no conversion to a full provider slug is fabricated. `resolved_model_id='opus'` records the available identifier. A future transport reporting a different identifier requires evidence and an explicit compatible adapter change; this feature refuses it. `fable` requested or effective is refused for current roles.

## 5. Named refusals

| Condition | Public code | Required behavior |
|---|---|---|
| Missing/unreadable/unsafe/invalid catalog, family empty, invalid relevant priority, duplicate relevant slug, ambiguous minimum | `TIER-MODEL-UNRESOLVED` | Exit 2, BLOCKED JSON; include runtime, tier or role, family, catalog path and reason. No new worker lease/worktree, specialist bootstrap or technical payload. |
| Frontier worker tier | `FRONTIER-MODEL-FORBIDDEN` | Before any catalog read or new worker effects, including when cache is absent. |
| Historical worker lacks a provable runtime/tier/model binding for a requested new effect | `WORKER-MODEL-UNPROVEN` | Identify the run/worker; keep historical reading/cleanup available and refuse the new effect without retroactive backfill. |
| Observed model differs from recorded selected model | `SPECIALIST-MODEL-DIVERGENT` | No payload/acceptance; preserve recorded attempt. |
| Observed effort differs | `SPECIALIST-EFFORT-DIVERGENT` | Existing refusal, without lowering effort or changing model. |
| Uncorrelated/missing native request or resolved identity | `SPECIALIST-CAPABILITY-UNPROVEN` | No alias guessing or leader substitution. |
| Unknown policy ref/version, changed bytes or mismatched seal | `ORCHESTRATION-POLICY-STALE` | Preserve state and diagnose the exact policy. |
| Fresh specialist preparation under historical v1 on the new binary | `ORCHESTRATION-MIGRATION-REQUIRED` | Refuse before bootstrap; historical verification/cleanup remain available. |

Preserve these codes through `TierModelError` → core error → `CliFailure`; do not wrap every specialist failure as capability-unproven or drop catalog metadata. An example shape, with a nonexistent synthetic source rather than a real failure:

```json
{
  "verdict": "BLOCKED",
  "code": "TIER-MODEL-UNRESOLVED",
  "runtime": "codex",
  "tier": "medium",
  "family": "terra",
  "catalog_path": "/tmp/catalog-case/models_cache.json",
  "reason": "no-listed-family"
}
```

For a specialist, replace `tier` with `role='author'` or `role='reviewer'`. Existing message/work-item/activity metadata may accompany the response. Do not print config files, account identity or model instruction bodies.

## 6. Versioned policy contract

Create `assets/agent-orchestration.v2.json` with schema `grill-agent-orchestration-policy/v2` and `policy_version='2'`. Codex role entries have `family` and `reasoning_effort`; Claude role entries have `model` and `reasoning_effort`. Keep activity matrix, efforts, independence, presentation and worker-frontier policy unchanged.

The v1 file stays byte-identical with SHA-256 `c30b3cecf9c5cc4949c8c3d14eca050608d773f4ffa690fc2c9e72e7a95a3553`. Its referenced supplement and task template also stay byte-identical. A single allowlisted loader validates reference, content hash and declared schema/version; never interpret unknown versions as current or try versions until one passes.

New init/adopt chooses v2. Existing items/contexts/activities/checkpoints keep v1, including successor contexts under the existing sealed item. Their verification and already-recorded activity completion use their original policy and saved facts, without live catalog I/O. No automatic reseal, mass migration, new mutable pointer or historical receipt rewrite is introduced.

Historical fable records remain readable/cleanable, but no new fable payload is released, even from an old prepared activity. Fresh v1 specialist preparation on the candidate refuses explicitly. New v2 work items use the new behavior; starting one does not complete the existing campaign.

For this campaign, the coordinator MUST freeze and verify `/home/carlosaraujo/orca/workspaces/grill-with-docs/continuity-5544829` at `5544829185c2e5d1d75e52736364aa00bede9323` before candidate code changes. Use `/home/carlosaraujo/orca/workspaces/grill-with-docs/continuity-5544829/plugin/skills/grill-with-docs/scripts/grill_workspace.py` for live v1 coordinator gates through ship, passing the active campaign root as `ROOT`; use the candidate checkout only for implementation and isolated candidate validation. The installed 6.0.30 cache lacks `f1475f4` and is not an admissible fallback.

The work-item `continuity-bundle-proof.json` is pinned at SHA-256 `89f6ede5fd321c1fe901271386458ba6fda452661a3758db4d2cedea0b4817fc`. Verify detached HEAD, clean status, fix ancestry, `HEAD:plugin/skills/grill-with-docs=d5cc959f9c02a98ddc3a5adfd958d729b62807ce`, all five file hashes/sizes, current Store validation and the campaign's unchanged historical policy/activation/entrypoint/registry/catalog pins before candidate changes, every resume/session switch and each remaining step. No policy/cache/bundle edit, reseal, receipt rewrite or invented bridge is permitted. The exact procedure is [quickstart.md](../quickstart.md), section 0.

Preserved v1 Codex author/reviewer pairs are `gpt-6-astra/xhigh` and `gpt-6-astra/high`; pure preparation and adopt preview are bounded checks, not proof of an end-to-end specialist session. Each real new specialist MUST satisfy current presentation bootstrap, correlated requested/effective/resolved identity, effort, independent review, input/fence checks and confirmed close after durable result/diagnostic, including later converge/review/ship judgment. V1 still requests Claude `fable`: this bundle MUST NOT launch a new Claude specialist or send a new fable payload, and MUST NOT claim Opus admission under that seal. Claude requires a separately justified safe route or nominal hold.

Any refusal MUST stop dependent work. The coordinator may apply an already authorized deterministic recovery and revalidate; otherwise it records the nominal diagnosis and emits `GOAL-HOLD` (residual clause if no core code applies). No fallback to a different CLI, model or policy may bypass the failed gate. Keep the preserved bundle until ship and cleanup are confirmed; candidate policy changes remain confined to isolated validation.

## 7. Compatibility invariants

Worker aliases on Claude, the leader recommendation, canonical eleven-step sequence, worker-required classification, tier floors, read-only hooks, presentation bootstrap, immutable releases and v3/v4 registry/catalog pins remain unchanged. Store historical shapes remain readable; new records carry the added worker binding. Unknown historical model is not reported as a selected current model.

The release must cover both this feature and pre-campaign successor commit `f1475f4f9523fcd7063e32b547aa6fd8bc364528`, preserve that regression's negative bridge check, synchronize all eight version locations and use the existing pipeline for a tag/Release with one anchor.

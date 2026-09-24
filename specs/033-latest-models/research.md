# Research: latest models

Date: 2026-09-24. Scope: technical authorship for `specs/033-latest-models`, under accepted ADR-0001/ADR-0002. Research used local files and existing runtime evidence only; it did not query the network or launch an agent.

## R1 — Catalog shape and preference

**Decision.** Use the local cache object and its `models` array. Select the unique lowest finite numeric `priority` among entries with `visibility == 'list'` and the requested family. Generation is part of an opaque model slug, never a ranking input. Ignore `upgrade` for selection.

**Observed evidence.** `/home/carlosaraujo/.codex/models_cache.json`, read in this session, reports `client_version='0.155.1'`; the final captured read reports `fetched_at='2026-09-24T15:19:31.255515319Z'`, SHA-256 `fb54aa00ed0854df9429c86cae7b0e21a51bf500d8e8e226490163a0f582da4f`. Its top-level keys are `fetched_at`, `etag`, `client_version`, `identity`, `models`.

| Slug in that observation | Visibility | Priority |
|---|---|---:|
| `gpt-6-astra` | list | 1 |
| `gpt-6-sol` | list | 2 |
| `gpt-6-luna` | list | 3 |
| `gpt-reserve` | hide | 3 |
| `gpt-5.6-sol` | list | 4 |
| `gpt-5.6-terra` | list | 7 |
| `gpt-5.6-luna` | list | 8 |
| `gpt-5.5` | list | 12 |
| `codex-auto-review` | hide | 43 |

The `gpt-5.5` entry contains an `upgrade` object with `model`, `migration_markdown` and `retirement_at`; other entries have `upgrade: null`. Entries also carry fields such as `display_name`, `default_reasoning_level`, `supported_reasoning_levels`, `service_tiers` and `model_messages`. Rejecting unknown fields would reject the real source. The identity value and model-message bodies are not required for selection and must not be copied into diagnostic output.

**Rationale.** This implements the approved catalog preference rule, including the medium Terra family staying on its currently preferred listed generation. It does not interpret an API alias or conflate availability with preference.

**Alternatives rejected.** Highest generation; first array element; globally preferred model; following `upgrade`; an API alias; last-known fallback; refreshing/installing Codex. All either change the approved rule or add unauthorized runtime/network effects.

**Fixture decision.** Add a deterministic projection of this real cache under `tests/fixtures/orchestration/codex-models-cache-0.155.1.json`. Preserve the top-level object, all nine entries, actual slug/visibility/priority values, `upgrade` shapes and representative extra fields. Sanitize account/host identity only; document the source version/date/hash in a fixture provenance field. Generate scenario variants from a deep copy: invert priorities, add a later numeric generation, hide a family, corrupt a relevant priority and duplicate a slug. Positive assertions calculate expected preference from the supplied fixture independently; current generation literals are fixture facts, not dispatch policy.

## R2 — Family grammar and ambiguous catalogs

**Decision.** Recognize `gpt-[0-9]+(?:\.[0-9]+)*-(luna|terra|sol|astra)` with full-string matching, then extract the suffix after the final hyphen. The generation grammar identifies candidates but never sorts them. An entry that does not match this grammar is not a family member; the real generic `gpt-5.5`, `gpt-reserve` and `codex-auto-review` entries therefore cannot become dispatch candidates.

Reject a listed candidate of the selected family if its priority is absent, boolean, string, null or non-finite. Accept finite integer/float priorities, including zero and negative values; the contract does not impose a generation-dependent or positivity rule. A duplicate relevant slug is ambiguous even if its other fields agree. Multiple distinct candidates tied for minimum refuse; equal lower-ranked priorities do not affect a unique minimum. Unknown string visibility is simply not listed. Malformed entry shape/slug/visibility that prevents classification refuses the catalog rather than silently skipping a potentially preferred entry.

**Rationale.** Fail closed on information necessary to choose, while tolerating real unrelated models and metadata. A missing family and an incompatible future family grammar have the same safe outcome: a named refusal with source path.

**Alternatives rejected.** Lexical tie-breaking or array-order tie-breaking would hide ambiguity; accepting `true` as priority 1 is a Python numeric-type trap; substring family matching would admit another model line.

## R3 — Read boundary, home and errors

**Decision.** Follow the existing `CODEX_HOME` or `Path.home() / '.codex'` convention observed in `agent_runtime.py`, consistent with `ensure_dependencies.plugin_registry_state`. Inject the final catalog path in tests. Reuse the existing bounded regular-file reader `agent_runtime._native_bytes` and its anti-symlink/racing-read checks; translate its exceptions to `TIER-MODEL-UNRESOLVED`. Parse strict UTF-8 JSON with duplicate-key and non-finite-constant rejection. No cache timestamp TTL is added.

**Rationale.** The existing reader already checks regular files, bounds and file identity. A missing/unreadable/malformed cache is the approved refusal, not an instruction to mutate user state. A stale but structurally valid cache remains the source of truth for this feature; it cannot prove remote availability.

**Finding.** `TierModelError` supports `extra`, but `_resolve_worker_model` currently calls `_fail(error.code, error.message)`, losing metadata; CLI worker handlers also rebuild `extra` with only `work_id`. The implementation must preserve runtime, tier or role, family, catalog path and a stable reason through both boundaries. A nested `SPECIALIST-CAPABILITY-UNPROVEN` wrapper must not hide a catalog-resolution refusal.

**Alternatives rejected.** A new environment flag, a second home resolver service, user config editing, subprocess probing and automatic cache repair.

## R4 — Durable worker fact and complete caller coverage

**Decision.** Add `model_binding` to new worker records using the existing resolver result keys: `runtime`, `tier`, `actor_class`, `adapter`, `model`, `frontier`. The field is optional only for historical records and immutable once recorded. Persist it with the first worker declaration before its lease/worktree effects; response fields project the stored value.

**Observed evidence.** `gauntlet_runs.declare_worker` resolves a model before `prepare_worker`, but its final comment explicitly says the value is reported, not stored. `store._validate_gauntlet_worker` currently allows exactly six keys and no model field. The worker-floor ADR and tier-model module docstring claim durability more strongly than the implementation provides. FR-004 requires closing that gap, not merely changing the asset.

`prepare_worker` is also called by `_mint_remediation_worker` and `grill_workspace.gauntlet_prepare_worker_command`. A repair only in `declare_worker` would leave sibling paths with no resolution or durable model. The public passive-preparation path derives its tier from the existing activation floors and grant classification, and runtime from the validated activation record (`record["runtime"]["id"]`); the admission only contains hashes, not a runtime field; normal DAG declaration retains its explicit validated tier. Remediation must select before its atomic budget/state mutation. Historical records without a binding never gain a guessed model during replay.

**Rationale.** One stored value makes retries and observed dispatch checks stable after the cache changes. The implementation already has a Store transaction and worker result fields; no extra journal or sidecar service is needed.

**Alternatives rejected.** Stdout-only reporting; reselecting on every retry; copying a prior attempt's model into a new attempt as a fallback; modifying historical receipts; changing `--model` into a user override.

## R5 — Specialists and catalog changes after preparation

**Decision.** Resolve at the CLI boundary, then pass the approved pair into pure `prepare_activity`. New Codex preparation requires a usable catalog. The activity's existing `requested_model` is the selected slug and becomes immutable with its initial record. Revalidation compares to that saved request, not to the latest catalog.

**Observed evidence.** `agent_orchestration.py` deliberately keeps pure validation separate from Store I/O. Its `prepare_activity`, `verify_specialist`, visual checks and task-files review currently call the static `specialist_pair`; `record_verified_activity`, `session_resource` and `accept_activity` call verification transitively. `validate_transition` makes the requested pair write-once and observed fields first-bound. The plan updates all these consumers rather than making `specialist_pair` secretly read the filesystem during historical validation.

**Rationale.** A catalog can refresh between preparation, neutral bootstrap, payload and close. Changing the expected model mid-attempt would reject correct work or admit the wrong session. A fresh activity may choose another slug; the current one may not.

**Alternatives rejected.** Resolve on every gate; accept any Astra effective slug; substitute the leader; loosen reviewer independence or close proof.

## R6 — Actual Claude Opus observation

**Decision.** Keep exact alias equality. New author/reviewer requirements are `opus`/`xhigh` and `opus`/`high`. Do not add alias-to-slug matching without evidence of such an observation format.

**Observed evidence.** Coordinator-provided, read-only file `.grill/work-items/feature-latest-models-codex-ab7615f7e67f4e2c9d2b94f507c921ec/opus-alias-launch-evidence.json`, verified SHA-256 `657e761d31b2be862cc6a2fd445fa52b7419e67c7d2aebf3e5f6d01f263fe343`, contains native worker-show envelopes for dispatches `ctx_ffb2d08c15de` and `ctx_a96d57fcf5e9`. In each, the dispatch/worker IDs correlate and `worker.startOptions.launch` contains:

```json
{
  "requested": {"agent": "claude", "model": "opus", "effort": "high"},
  "effective": {"agent": "claude", "model": "opus", "effort": "high"}
}
```

The coordinator identifies the capture as Orca `1.4.205`, from real dispatches launched on 2026-09-23. This author verified the stored native fields and hash; it did not relaunch those dispatches. The artifact proves the recorded alias shape, not a full provider slug or a new live `xhigh` author run. Future runtime admission still checks the actual requested effort and correlated live observation for each role.

`agent_runtime._orca_observation` already records `resolved_model_id=effective_model` when requested and effective agree. Thus it records `opus` here. That identifier must not be relabeled as proof of `claude-opus-5-5` or any generation. `RuntimeBoundary.verified`, revalidation and close keep exact model/effort/identity comparisons. `fable`, another alias and an unproven full-slug substitution remain refused.

**Alternatives rejected.** Broad `startswith('claude-opus')`; assuming the requested alias reveals a provider generation; pinning `claude-opus-5-5`; running fable while waiting for rollout.

## R7 — Immutable policy and historical verification

**Decision.** Add orchestration policy v2 alongside v1; preserve v1 bytes and its hash `c30b3cecf9c5cc4949c8c3d14eca050608d773f4ffa690fc2c9e72e7a95a3553`. V2 changes Codex role selectors to Astra family and Claude pairs to Opus; the activity matrix, independent-review requirement, worker floor, presentation settings and recommendations are unchanged.

A closed loader accepts only the shipped v1/v2 reference/hash combinations and validates by the document's own schema/version. New init/adopt uses v2. Existing adopted items, contexts, activities, checkpoints and resumes retain their pinned version. Historical validation never consults the current catalog or mutates evidence. Fresh specialist preparation on v1 under the new binary refuses `ORCHESTRATION-MIGRATION-REQUIRED`; already recorded v1 activities can still be verified/accepted/cleaned according to their original pair. Historical fable evidence can be read/completed as evidence, but no new fable payload is released, including an old BOOTSTRAPPING activity. This campaign's supported route is the concrete preserved bundle below, with Codex specialists; v2 is for new work items. Bulk adoption/reseal is outside scope.

**P1 continuity repair.** Independent `plan-reviewer-result.md` found that the installed 6.0.30 cache cannot validate the current successor whose predecessor had no campaign (`successor context has no campaign bridge`). The coordinator has preserved a detached, clean worktree at `/home/carlosaraujo/orca/workspaces/grill-with-docs/continuity-5544829`, revision `5544829185c2e5d1d75e52736364aa00bede9323`, containing fix `f1475f4f9523fcd7063e32b547aa6fd8bc364528`. Freeze it before candidate code changes. Its CLI is `/home/carlosaraujo/orca/workspaces/grill-with-docs/continuity-5544829/plugin/skills/grill-with-docs/scripts/grill_workspace.py`; the candidate checkout is reserved for implementation and isolated validation, while this CLI coordinates the unchanged v1 campaign through ship.

**Evidence and limits.** Work-item `continuity-bundle-proof.json` has SHA-256 `89f6ede5fd321c1fe901271386458ba6fda452661a3758db4d2cedea0b4817fc`; it records the five file hashes/sizes and `plugin_tree=d5cc959f9c02a98ddc3a5adfd958d729b62807ce`, the tree of `plugin/skills/grill-with-docs`. It records coordinator adopt preview `PREVIEW`, successful Store validation and pure `prepare_activity` results `gpt-6-astra/xhigh` and `gpt-6-astra/high`; the coordinator reports presentation readiness for that preview. Round 2 independently matched the revision, clean detached state, subtree and five hashes, validated Store revision 3290 and reproduced both pure pairs without writing Store. This is not a CLI activity-prepare probe or end-to-end launch/accept/close proof. A preview from the round-2 specialist's own session correctly refused `CONTEXT-FENCED`; preview authority belongs to the bound coordinator.

**Operational decision.** The coordinator revalidates revision/tree/manifest, live Store and historical policy/activation/entrypoint/registry/catalog pins before candidate changes, each resume/session switch and every remaining step through ship. Each actual specialist still requires current presentation bootstrap, observed identity and pair, independent review, durable result and confirmed settlement/release/cleanup. The full procedure and refusal recovery are in [plan.md](plan.md), section 4, and [quickstart.md](quickstart.md), section 0. V1 continues to request Claude `fable`; no new Claude specialist is permitted on this route, and candidate Opus support does not alter the old seal. A separately justified safe Claude route or a nominal `GOAL-HOLD` is required. Failed revalidation is fail-closed; only authorized deterministic recovery is allowed, never rewriting policy, receipts, bridges, the bundle or upstream cache.

**Observed evidence.** `_activity_policy`, `_require_step_activities` and `gauntlet_step_enter_command` currently reopen `agent-orchestration.v1.json` directly. Init/adopt and presentation paths also hard-code that asset. `validate_transition` makes the work-item `policy_ref`/`policy_sha256` and existing context policy hashes immutable. Updating a single constant or asset would not preserve that chain. All policy-loading call sites must use one version-aware selection rule.

The v1 references also pin the supplement (`04b4533636117f26e6870bec6f43632bca8114d0bf1cc92911c15b5855ff7ed3`) and Files template (`4961ec90bd4c31b09aaecd00ed14cf28a7caa927081cdf50110bcc6b5a380eee`). Preserve those referenced bytes; no new supplement/template is needed for the role change. The current tier asset is not content-pinned by ESSENTIAL, only named; its current hash is `b0cdd4395f5d4eedb718282573c5451075ced407c9b302d190a239971b89c9b9`, and its current-policy shape may advance to binding v2 without rewriting any saved worker selection.

**Rationale.** Versioned policy retains the exact contract historical receipts name. Refusing fresh v1 preparation avoids silently applying new semantics to old hashes and avoids indefinite fresh generation-pinned dispatch.

**Alternatives rejected.** Editing v1; weakening hash comparison; loading an arbitrary stored path; silently deriving a family from a historical literal; a global policy migration/reseal command; falling back to the broken installed cache; postponing continuity until tasks; treating a different v2 work item as completion of this campaign.

## R8 — Release and pre-campaign successor regression

**Decision.** Propose minor release `6.1.0` from observed baseline `6.0.30`; choose a later unused number if integration requires it. Synchronize the eight distribution locations, add one cumulative CHANGELOG entry, and publish only through the canonical authorized pipeline.

**Observed evidence.** Commit `f1475f4f9523fcd7063e32b547aa6fd8bc364528` changes `agent_orchestration.validate_block` and adds `test_first_campaign_is_born_in_a_pre_campaign_successor`. It accepts a successor's first campaign when its predecessor had none and no bridge exists, while retaining refusal when the predecessor already had a campaign. Its commit message explicitly defers the bump to this feature release. CHANGELOG currently starts at `6.0.30` and does not yet record this fix.

**Rationale.** Shipping the model feature without that fix in the release description/bump would omit already included product bytes. The feature is additive and retains historical verification; a minor release is appropriate for the new current-policy behavior.

**Alternatives rejected.** An isolated unversioned fix; overwriting an existing tag; manual Release creation; invoking ship from this author session.

## Research closure

The catalog rule, malformed/tie handling, durability gap, complete caller set, Opus observation format, policy compatibility boundary, no-frontend classification and release contents have concrete decisions. No external research or unproven alias mapping is required. Independent review and executable candidate validation remain subsequent work, not claims made by these design artifacts.

# Implementation Plan: Latest model by family

**Branch**: `cadugevaerd/fix-latest-models` | **Date**: 2026-09-24 | **Spec**: [spec.md](spec.md)

**Input**: `specs/033-latest-models/spec.md`; work item `feature-latest-models-codex-ab7615f7e67f4e2c9d2b94f507c921ec`, FASE-001, DU-001; ADR-0001 and ADR-0002.

**Status**: Technical proposal for independent review. This document does not accept the macrostep, authorize implementation, or authorize publication.

## Summary

Resolve each new Codex dispatch from its declared family against the local `models_cache.json`, choosing the unique listed model with the lowest numeric priority. Preserve worker families Luna/Terra/Sol and reject frontier workers before resolving the catalog or creating effects. Resolve Codex specialists from Astra; request Claude specialists through `opus` with author `xhigh` and reviewer `high`.

Keep the sealed orchestration v1 asset unchanged and introduce v2 for new work items. Validate historical evidence against its original policy, without consulting today's catalog. Persist each new worker's resolution in the existing Store and reuse the specialist's existing requested/effective/resolved fields. The release includes the pre-campaign successor fix `f1475f4f9523fcd7063e32b547aa6fd8bc364528`.

## Technical Context

**Language/Version**: Python >=3.10; standard library only.

**Primary Dependencies**: Existing Store, tier binding, orchestration contracts and runtime observation boundary; local Codex catalog format observed at client version `0.155.1`.

**Storage**: Read-only Codex cache; existing Store snapshot/journal and immutable receipts. No database or new external service.

**Testing**: Existing `unittest`/assert validators, temporary repositories and injected catalog paths; `python3 tests/run_validators.py` and `git diff --check`.

**Target Platform**: Linux, macOS and Windows; existing Python 3.10/3.13 CI matrix.

**Project Type**: Plugin/CLI, `platform-devops`; frontend `NOT_APPLICABLE`, consistently with handoff and PLAN-CONTEXT. No HTML preview, PNG capture or visual approval is required.

**Performance Goals**: One bounded catalog read and O(number of entries) selection per new Codex resolution; no subprocess or network added. Retries of a recorded attempt use its saved model instead of selecting again.

**Constraints**: No last-known fallback; no user configuration changes; no runtime installation/upgrade; no changes to worker tier floors, leader recommendation, workflow order, ESSENTIAL tuples, or v3/v4 registries/catalogs. Preserve presentation bootstrap and independent review gates.

**Scale/Scope**: Three Codex worker tiers and two specialist roles in two runtimes. The observed cache has nine entries. The reader reuses the existing 16 MiB bounded regular-file boundary, without a persistent cache or daemon.

## Constitution Check

The pre-design and post-design checks use Constitution `2.1.0`, SHA-256 `54d5522b18e43efa05311dbf13ed79694b79ccfcb01509384b3572b2d5667569`. PASS here means the design respects the clause; execution and release remain future gates.

| Clause | Pre-design / post-design evidence |
|---|---|
| Evidence before assertion | PASS: repository call paths, actual local Codex cache and correlated Orca evidence are recorded in [research.md](research.md); no inferred full Opus slug. |
| Isolated work item and ownership | PASS: named work item/branch; author writes only these five design files. Leader owns `.grill/`, receipts and acceptance. |
| Feature/fix plan-only | PASS: this proposal changes no product code and grants no implementation/publication authority. The external canonical cycle owns later execution. |
| Required development sequence | PASS: `specify` attestation is an input; plan is followed by checklist/tasks/analyze and the remaining canonical gates. |
| Verify/review before ship | PASS: full offline validation, independent judgment and later human ship authorization remain mandatory. |
| Fail-closed without waiver | PASS: catalog ambiguity, unusable source, frontier worker and mismatched effective model refuse before dependent effects. |
| Traceability | PASS: ADRs, requirement mapping, selected model records and policy hashes remain correlated; historical evidence is never rewritten. |
| Worker model/effort tier | PASS: runtime/tier derive the model; no caller `--model` override; launch requested/effective and supported effort still require comparison. |
| Mandatory plugin bump | PASS: proposed release `6.1.0`, subject to being greater than the integrated base and unused; all eight distribution points move together. |
| Mandatory release per version | PASS: canonical pipeline creates immutable tag and corresponding Release at the same anchor; no manual Release workaround. |
| Governance | PASS: Constitution and project-wide WORKFLOW stay byte-identical; hooks remain read-only and no policy reseal is implicit. |

No constitutional exception is proposed. Frontend is not applicable; this is not a waiver of presentation or specialist gates.

## Project Structure

### Documentation (this feature)

```text
specs/033-latest-models/
├── spec.md                         # accepted input, unchanged by this author
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
└── contracts/model-selection.md
```

`tasks.md` is produced only by the subsequent canonical tasks step. It must use the existing Files/Result template and declared, file-disjoint grants; this plan is not a grant.

### Implementation locations

| Location | Planned responsibility |
|---|---|
| `plugin/skills/grill-with-docs/scripts/grill_core/tier_models.py` | Shared family parser/catalog resolver, closed binding v2 shape, unchanged frontier admission order and structured failure. |
| `plugin/skills/grill-with-docs/assets/workflow-tier-models.json` | Binding schema/version 2: Codex `family`, Claude `model`; no generation pins in current dispatch policy. Filename remains compatible with ESSENTIAL v4. |
| `plugin/skills/grill-with-docs/assets/agent-orchestration.v2.json` (new) | Current policy: Codex Astra family; Claude Opus alias; same efforts, activity matrix, references and presentation contract. |
| `plugin/skills/grill-with-docs/assets/agent-orchestration.v1.json` | Historical input, byte-identical; never overwritten or relabeled. |
| `plugin/skills/grill-with-docs/scripts/grill_core/agent_orchestration.py` | Pure policy-dependent preparation and validation; no catalog I/O here; preserve the pre-campaign successor fix. |
| `plugin/skills/grill-with-docs/scripts/grill_core/gauntlet_runs.py` and `store.py` | Persist immutable model binding at worker declaration; enforce it through prepare, reuse and remediation; tolerate historical records without inventing a model. |
| `plugin/skills/grill-with-docs/scripts/grill_workspace.py` | Select current versus sealed policy consistently; resolve before activity persistence; propagate named errors and metadata; thread worker runtime/tier through existing entrypoints. |
| `tests/validate_tier_model_binding_contract.py`, `validate_agent_orchestration_contract.py`, `validate_gauntlet_scheduler_contract.py`, `validate_gauntlet_run_contract.py`, `validate_orchestrator_store_contract.py` | Resolver, public refusal, durable record, retry/remediation and historical-policy regressions. Reuse existing fixtures/seams. |
| `tests/orchestration_fixture.py`, existing specialist helpers in scheduler/converge/status validators | Supply deterministic catalog/policy inputs; no dependency on the developer's cache. |
| `tests/fixtures/orchestration/codex-models-cache-0.155.1.json` (new) | Derived real catalog fixture, retaining all nine entries, visibility, priority, extra fields and upgrade shape. |
| Public role documentation and distribution files | Current policy guidance, catalog dependency, historical behavior, eight-point bump and cumulative CHANGELOG. |

`agent_runtime.py` already provides the required exact `opus` observation semantics and safe file-read primitive. `ensure_dependencies.py` provides the existing home convention. Reuse these capabilities; do not add alias guessing, new subprocesses, a downloader or a second home configuration.

## Design and execution sequence

### 1. Shared Codex resolution

Implement the exact selection/error contract in [contracts/model-selection.md](contracts/model-selection.md). Family extraction uses the last `-` segment of a valid `gpt-<numeric-generation>-<family>` slug. Ignore non-family entries and hidden entries; do not follow `upgrade`. Priorities are finite numeric values excluding booleans and strings. Invalid relevant candidates, duplicate relevant slugs or a tie for the minimum produce `TIER-MODEL-UNRESOLVED`.

The catalog path is `Path(CODEX_HOME)` when nonempty, otherwise `Path.home() / '.codex'`, followed by `models_cache.json`; tests inject a path. Reuse `agent_runtime._native_bytes` for a bounded regular-file read and translate its read/refusal failures into the catalog diagnostic. Parse UTF-8/JSON strictly, including duplicate keys and non-finite JSON constants. Extra metadata and model fields are allowed. Do not read user `config.toml`, invoke Codex or enforce a cache age limit.

### 2. Durable worker selection and sibling paths

The current `declare_worker` returns `model` only in stdout: its comment at the end explicitly defers durable storage. Extend Store validation with historically optional `model_binding` (mandatory in every new worker producer), using the existing resolver result shape described in [data-model.md](data-model.md). Record it atomically in the first `DECLARED` transaction, before lease-backed preparation or Git worktree creation; return fields remain sourced from this record.

Trace and cover all callers of `prepare_worker`: `declare_worker`, the public `gauntlet-prepare-worker` path, and `_mint_remediation_worker`. For passive public preparation, derive the minimum permitted tier from the activation's existing `_tier_floors` and the grant's markdown classification; derive runtime from the validated activation record returned by `gauntlet_run_admission` (`record["runtime"]["id"]`), whose hash is pinned in admission, never a CLI default. Existing explicit DAG tier continues to govern normal declaration. Refuse unresolved runtime/tier before any new worker effect.

A repeated operation reuses the same immutable recorded selection; it must not resolve a different model and return it for an existing worktree. Remediation is a new attempt: resolve the original recorded runtime/tier against the current catalog before spending budget, stalling the original, minting a lease or preparing the replacement. Legacy records lacking runtime/tier/model remain readable/cleanable; if a new dispatch or remediation cannot prove these values from its sealed DAG and matching activation, refuse rather than inventing them. Do not retrofit historical records in place.

### 3. Specialist preparation and effective-model validation

Resolve a new Codex Astra slug at the CLI boundary before `prepare_activity` or any Store write, then pass the resolved pair into the pure contract. `requested_model` and `requested_effort` become immutable when the activity is first recorded. Retry of that activity uses the recorded pair; a fresh activity performs a fresh resolution.

All later checks compare the observed pair to the recorded request under the activity's policy, including `verify_specialist`, `record_verified_activity`, `session_resource`, `accept_activity`, `_visual_activity` and `require_task_files_review`. They never reselect from the current catalog. Also check the observation's requested pair, provider and resolved ID, not only its effective fields; preserve identity, effort, independence, fencing and close checks.

For current Claude roles require `opus`/`xhigh` or `opus`/`high`. The actual Orca observation reports `opus` in both requested and effective model fields, so exact equality remains sufficient. Persist `resolved_model_id='opus'` as the observed identifier, without claiming a full provider slug. A future different observation format remains fail-closed until separately evidenced; no regex accepting arbitrary Opus-like aliases is introduced.

### 4. Versioned policy compatibility and rollout

Create `agent-orchestration.v2.json` with schema `grill-agent-orchestration-policy/v2` and `policy_version='2'`; the Store orchestration contract remains `grill-agent-orchestration/v1` because its existing activity/context shapes suffice. New init/adopt operations select v2. An already adopted item keeps its sealed v1 reference/hash through resumes/takeovers; loading selects from an exact allowlist of shipped ref/hash pairs, never an arbitrary path or the current default.

Use that same selection in `_bind_orchestration`, init/adopt, preflight/presentation, `_activity_policy`, coverage, step-enter, checkpoint/attest and continuity. No attempt to upgrade an existing seal silently is permitted. A v1 item's verification, cleanup and completion of already recorded activities use v1 expectations and do not consult the new cache. Historical fable evidence remains readable, but no new fable payload is released, even for an old prepared activity. New specialist preparation under v1 on the new binary refuses `ORCHESTRATION-MIGRATION-REQUIRED` before bootstrap; this prevents new fixed-generation/fable dispatch while retaining historical verification. It identifies the sealed policy and instructs the coordinator to finish the historical campaign with its pinned prior bundle or start a new v2 work item. No mass migration or new migration verb is part of this feature; no new Claude fable activity is permitted on either route.

#### Continuity bundle for this campaign (P1 repair)

Before any candidate code change or integration, the coordinator freezes and verifies the existing detached, clean worktree `/home/carlosaraujo/orca/workspaces/grill-with-docs/continuity-5544829` at revision `5544829185c2e5d1d75e52736364aa00bede9323`, which contains `f1475f4f9523fcd7063e32b547aa6fd8bc364528` and still prepares v1 Codex specialists. Its coordinator CLI is `/home/carlosaraujo/orca/workspaces/grill-with-docs/continuity-5544829/plugin/skills/grill-with-docs/scripts/grill_workspace.py`. It is outside upstream caches and receives no candidate edits or version bump.

The frozen evidence is `.grill/work-items/feature-latest-models-codex-ab7615f7e67f4e2c9d2b94f507c921ec/continuity-bundle-proof.json`, SHA-256 `89f6ede5fd321c1fe901271386458ba6fda452661a3758db4d2cedea0b4817fc`. Its `plugin_tree` value `d5cc959f9c02a98ddc3a5adfd958d729b62807ce` denotes `HEAD:plugin/skills/grill-with-docs`, not `HEAD:plugin`; its five file entries pin the CLI, orchestration core, v1 policy, supplement and Files template by size and SHA-256. The installed 6.0.30 cache is not a fallback: it lacks the successor fix and rejects this Store with `successor context has no campaign bridge`.

1. **Coordinator revalidation.** Before the first candidate change, every resume/session switch and each remaining canonical step through ship, compare detached HEAD, clean tracked/untracked status, the exact skill subtree and all manifest bytes; verify the fix is an ancestor. Validate the current Store's orchestration block with the preserved module. Compare the item's/context's v1 policy ref/hash, campaign activation, eleven entrypoint resolutions and registry/catalog hashes with their recorded historical pins; verify referenced bytes without resealing. A changed Store revision from normal canonical progress requires fresh validation, not restoration of an old snapshot.
2. **Separate command roots.** Use this absolute preserved CLI, with the active campaign root `/home/carlosaraujo/orca/workspaces/grill-with-docs/fix-latest-models` as `ROOT`, for v1 coordinator gates, activity preparation/acceptance, step entry, checkpoint/attestation and protected continuity/cleanup through ship. The coordinator invokes each pinned canonical skill in its own active session. The candidate checkout supplies implementation bytes and isolated validation; it must not coordinate new v1 activities against the live Store. Candidate v2 tests run in temporary projects, never by changing campaign seals.
3. **Codex lifecycle.** Read-only Store validation and pure `prepare_activity` checks against the current context must still produce `gpt-6-astra/xhigh` for authors and `gpt-6-astra/high` for reviewers. These checks do not launch or authorize payload. Every actual future specialist, including converge/review and any new ship judgment, gets a fresh correlated session with neutral bootstrap, installation/enablement/trust and full approved presentation load (`work_ready=true`), observed requested/effective/resolved pair, input manifest, fence and close capability before payload. Revalidate the same identity/pair on return; persist the result/diagnostic, require independent judgment and confirm settlement/release/cleanup by read-back before accepting the dependent gate. Recheck presentation after compaction; never inherit another session's load.
4. **Claude boundary.** The preserved v1 core still requests `fable`; never launch a new Claude specialist or release a new fable payload through it. Implementing v2 does not change the sealed campaign to Opus. This campaign uses Codex specialists; a Claude activity requires a separately justified, authorized safe route preserving its seals and proving Opus admission, otherwise a nominal hold before preparation. Starting another v2 work item does not complete this campaign.
5. **Refusal and release.** Any failed integrity, Store, pin, presentation, pair, independence or lifecycle check stops dependent work. The coordinator may perform only the already authorized deterministic recovery named by the gate, then repeat validation; if recovery needs a new decision or unavailable capability, record the diagnosis and emit `GOAL-HOLD` with the nominal code (or the residual clause when none exists). Do not patch the preserved bundle/cache, switch to the candidate to bypass a refusal, or edit policy, seals, existing receipts or historical bridges. Normal new evidence uses canonical operations. Keep the bundle frozen through verify, review, human ship authorization and pipeline completion; retire it only after campaign completion/cleanup is confirmed.

The supplied proof records coordinator adopt **preview** `PREVIEW`, Store validation and pure author/reviewer preparation; the coordinator also reported `presentation.work_ready=true`. No CLI activity-prepare probe or end-to-end specialist lifecycle was executed for that proof. These bounded observations support the route; future gates above remain mandatory. The combined predecessor/candidate/bundle scenario is specified in [quickstart.md](quickstart.md), section 2.

### 5. Validation, documentation and release

Cover the eight handoff scenarios plus malformed catalogs, ties, duplicate slugs, retry after cache change/deletion, remediation, legacy Store replay, v1/v2 selection and policy tampering. Assert the exact public refusal code and metadata, unchanged Store/worktree/lease counts, and absence of a technical payload. `TierModelError.extra` currently disappears through `_resolve_worker_model`; preserve runtime, tier/role, family, catalog path and reason through the core/CLI error boundary.

Update current public guidance in `SKILL.md`, `references/session-protocol.md`, `README.md` and the worker-floor ADR to describe family-based selection and actual durable recording. Historical v1 policy and historical CHANGELOG prose retain their original terms; tests must not prohibit historical `fable` evidence. Keep public leader recommendations `Sol`/`Opus` and Claude worker aliases unchanged.

Propose SemVer `6.1.0` for the feature plus `f1475f4` fix; re-evaluate the candidate number against the integrated base before ship. Synchronize:

1. `plugin/.claude-plugin/plugin.json` and `plugin/.codex-plugin/plugin.json`.
2. `.claude-plugin/marketplace.json` and `.agents/plugins/marketplace.json`.
3. `VERSION` in `tests/validate_distribution.py`.
4. Heading in `plugin/skills/grill-with-docs/SKILL.md` and heading in `plugin/skills/grill-with-docs/references/session-protocol.md`.
5. Version heading in `README.md`.

These are eight locations grouped above. Add one cumulative CHANGELOG entry covering both changes. Preserve the fix's positive case (first campaign in a successor whose predecessor had none) and negative case (predecessor with campaign still requires a bridge). Require full validators, diff hygiene, verify, independent review and authorized pipeline ship; publishing is outside this author's work.

## Requirements and validation traceability

| Requirements | Planned evidence |
|---|---|
| FR-001/002/005/006, SC-001/002/003 | Family/priority matrix, frontier-before-read check, structured CLI refusal and no-effect assertions. |
| FR-003/004/007, SC-001/002 | Author/reviewer lifecycle tests; saved worker binding; observed Opus equality; divergent requested/effective/resolved IDs refused. |
| FR-008/009, SC-004 | Claude worker/leader parity; byte-identical v1 asset; legacy context/receipt replay and no catalog dependency for historical acceptance. |
| FR-010/013, SC-005/008 | Real-shape Codex fixture and injected paths; all eight scenarios without network or installed agent CLIs. |
| FR-011, SC-006 | Current public role table and prose use Opus; immutable historical records are explicitly exempt from current-role search. |
| FR-012, SC-007/009 | Eight-point bump, cumulative CHANGELOG, pre-campaign regression, full validators, diff check and later pipeline anchor evidence. |

## Complexity Tracking

No new service, dependency, global setting, model-ranking heuristic, cache-refresh mechanism or alias resolver is needed. One new immutable policy file and one optional historical Store field are necessary to preserve old evidence while recording new worker selections. P1's continuity route is specified above using an existing preserved worktree, without a new migration mechanism. Independent review, candidate validation and live revalidation through ship remain required; this design does not claim those gates have passed.

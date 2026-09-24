# Tasks: Latest model by family

**Input**: Accepted `specs/033-latest-models/spec.md`, `plan.md`, `research.md`, `data-model.md`, `quickstart.md`, `contracts/model-selection.md` and `checklists/orchestration.md`; work-item ADR-0001, ADR-0002, PLAN-CONTEXT, continuity proof and approved plan review r2.

**Work item**: `feature-latest-models-codex-ab7615f7e67f4e2c9d2b94f507c921ec`, FASE-001, DU-001. Python >=3.10, standard library only. Frontend: `NOT_APPLICABLE`.

**Tests**: Required by FR-010 and FR-013. Add failing behavioral assertions before the implementation they cover. Reuse existing validators and injected runtime boundaries; no network, installed agent CLI, operator cache or configuration mutation. This file plans later implementation; its creation does not execute tasks, accept a macrostep or authorize ship.

<!-- grill-task-files:v1 -->

## Format and execution contract

- Every task has a sequential ID and an immediately following one-line JSON `Files:`. Each dispatchable writing task has exactly one `Result:` under `specs/033-latest-models/implement/`, also included in its grant. Its worker records the actual result and checks there; no implicit node sidecar.
- `Files: []` is read-only and has no Result. Tasks explicitly marked **DEFERRED TO LEADER** own reserved evidence, have no Result and never become worker grants. Evidence is written only by the bound coordinator through the canonical operations where required.
- `[P]` marks independent writing branches in the same phase. Tasks sharing files are intentionally serial within one conflict group, in ID order. Partition must not split such a group. Prose dependencies alone do not add edges to the parser's DAG.
- Numeric phases are barriers: converge all workers, then accept read-only/deferred tasks in listed order before opening the next phase. The final phase also needs positive acceptance. No empty or fictitious worker satisfies `implement-parallel`.
- Paths are repository-relative and grants are exact files. Inputs outside Files remain read-only. Preserve Constitution, WORKFLOW, ESSENTIAL tuples, v3/v4 registries/catalogs, worker floors and all historical receipts. No new model override, runtime installer, fallback or dependency.

## Campaign continuity — mandatory throughout execution

This campaign is sealed to orchestration **v1**. Before candidate changes, every resume/session switch and every remaining canonical step through ship, the coordinator revalidates the preserved bundle as specified in `specs/033-latest-models/quickstart.md`, section 0. The preserved root is `/home/carlosaraujo/orca/workspaces/grill-with-docs/continuity-5544829`, detached at `5544829185c2e5d1d75e52736364aa00bede9323`, containing `f1475f4f9523fcd7063e32b547aa6fd8bc364528`.

Use **only** `/home/carlosaraujo/orca/workspaces/grill-with-docs/continuity-5544829/plugin/skills/grill-with-docs/scripts/grill_workspace.py` for this campaign's coordinator gates, specialist preparation/acceptance, step entry, checkpoint/attestation, continuity and protected cleanup after candidate changes. Pass `/home/carlosaraujo/orca/workspaces/grill-with-docs/fix-latest-models` as ROOT. Candidate code and tests use the active checkout and temporary projects; candidate v2 never reseals or coordinates fresh v1 activities against the live campaign. The installed 6.0.30 cache lacks the successor fix and is not a fallback.

Revalidate proof SHA-256 `89f6ede5fd321c1fe901271386458ba6fda452661a3758db4d2cedea0b4817fc`, clean tracked/untracked status, fix ancestry, `HEAD:plugin/skills/grill-with-docs=d5cc959f9c02a98ddc3a5adfd958d729b62807ce`, the five manifest hashes/sizes, current Store validity and unchanged policy/activation/eleven-entrypoint/registry/catalog pins. Normal Store progress requires a fresh check, never snapshot restoration. Keep these historical source bytes unchanged:

| Historical source | SHA-256 |
|---|---|
| `plugin/skills/grill-with-docs/assets/agent-orchestration.v1.json` | `c30b3cecf9c5cc4949c8c3d14eca050608d773f4ffa690fc2c9e72e7a95a3553` |
| `plugin/skills/grill-with-docs/references/agent-orchestration.md` | `04b4533636117f26e6870bec6f43632bca8114d0bf1cc92911c15b5855ff7ed3` |
| `plugin/skills/grill-with-docs/assets/task-files.v1.template.md` | `4961ec90bd4c31b09aaecd00ed14cf28a7caa927081cdf50110bcc6b5a380eee` |

New live campaign specialists remain Codex `gpt-6-astra` with author `xhigh` or reviewer `high`, as pinned by v1. Every actual session needs neutral bootstrap, current approved presentation load, observed requested/effective/resolved pair, identity/fence/input correlation and close capability before payload; revalidate on return, persist result/diagnostic, then confirm settlement/release/cleanup by read-back. Reviewers remain independent of every author of reviewed bytes. Revalidate presentation after compaction; no inherited load. The proof's preview and pure pair checks do not prove that lifecycle.

The preserved v1 bundle still requests Claude `fable`: launch no new Claude specialist and release no new fable payload, including from old prepared activities. Candidate Opus support does not alter the campaign seal. A separately justified safe Claude route requires its own authorization/evidence; otherwise hold. Failed integrity, admission, presentation or lifecycle checks stop dependent work for authorized deterministic recovery and revalidation, or nominal `GOAL-HOLD`. Never patch the preserved bundle/cache or rewrite seals, receipts or bridges. Retain the bundle through authorized pipeline ship and confirmed campaign cleanup.

## Phase 1: Setup (campaign isolation and baseline)

**Purpose**: Establish the implementation baseline and refresh the coordinator's continuity evidence before the first candidate edit. No worker runs in this phase.

- [ ] T001 Read the accepted inputs in `specs/033-latest-models/plan.md` and `specs/033-latest-models/contracts/model-selection.md`, confirm `CLAUDE.md` and `.specify/memory/constitution.md` constraints, and run `python3 tests/run_validators.py` before touching candidate code; retain exact baseline failures and the count of `==>` markers for the coordinator without editing files.
  Files: []

- [ ] T002 **DEFERRED TO LEADER** — Revalidate `specs/033-latest-models/quickstart.md` section 0 against `.grill/work-items/feature-latest-models-codex-ab7615f7e67f4e2c9d2b94f507c921ec/continuity-bundle-proof.json` and record the current bundle/Store/pins/presentation result in `.grill/work-items/feature-latest-models-codex-ab7615f7e67f4e2c9d2b94f507c921ec/continuity-before-implementation.md`; require the bound coordinator's read-only preview, pure author/reviewer pairs and unchanged Store bytes before candidate edits, preserving the original proof.
  Files: [".grill/work-items/feature-latest-models-codex-ab7615f7e67f4e2c9d2b94f507c921ec/continuity-before-implementation.md"]

**Checkpoint**: Baseline understood and continuity verified. An unresolved baseline or continuity failure blocks Phase 2; no old PASS substitutes for the current check.

## Phase 2: Foundational (shared resolver and durable schema)

**Purpose**: Establish the two independent prerequisites used by all worker paths. T003 and T004 may run in parallel; each writes its tests before its product changes.

- [ ] T003 [P] Build the Codex 0.155.1-derived fixture in `tests/fixtures/orchestration/codex-models-cache-0.155.1.json`, add injected temporary-catalog support in `tests/orchestration_fixture.py`, write resolver assertions in `tests/validate_tier_model_binding_contract.py`, then implement the shared family resolver in `plugin/skills/grill-with-docs/scripts/grill_core/tier_models.py` and binding v2 in `plugin/skills/grill-with-docs/assets/workflow-tier-models.json` according to `specs/033-latest-models/contracts/model-selection.md` sections 1–2; run the resolver validator and record its result in `specs/033-latest-models/implement/T003.tasks.json` (FR-001/002/005/006/008/010/013).
  Files: ["tests/fixtures/orchestration/codex-models-cache-0.155.1.json", "tests/orchestration_fixture.py", "tests/validate_tier_model_binding_contract.py", "plugin/skills/grill-with-docs/scripts/grill_core/tier_models.py", "plugin/skills/grill-with-docs/assets/workflow-tier-models.json", "specs/033-latest-models/implement/T003.tasks.json"]
  Result: "specs/033-latest-models/implement/T003.tasks.json"

T003 must retain all nine catalog entries, actual visibility/priority values, hidden reserve/review entries, generic `gpt-5.5` and its upgrade object, representative extra fields and source version/date/hash provenance; sanitize account/host identity and do not expose model instructions in diagnostics. Compute expected winners independently from fixture priorities, including reversed Luna order and a newer Terra with worse/better priority. Reuse `agent_runtime._native_bytes` and the existing nonempty CODEX_HOME/home convention without modifying `agent_runtime.py`; normalize to an absolute path without resolving symlinks. Require full family grammar, strict UTF-8/JSON, finite numeric priorities excluding bool, unique relevant slugs and unique minimum; reject malformed relevant data with structured `TIER-MODEL-UNRESOLVED`. Frontier admission precedes catalog I/O. Claude aliases, leader recommendations and worker effort/floors remain unchanged. Fixture helpers must allow explicitly absent/bad catalogs; no global fallback may mask a negative test.

- [ ] T004 [P] Add historical replay and binding mutation tests in `tests/validate_orchestrator_store_contract.py`, then extend `plugin/skills/grill-with-docs/scripts/grill_core/store.py` with historically optional but immutable `worker.model_binding` using the exact six-key resolver result from `specs/033-latest-models/data-model.md`; test valid mint/transitions, invalid runtime/tier/adapter/frontier shapes, removal/change/retroactive addition refusal and legacy records/events without live-catalog access, and record results in `specs/033-latest-models/implement/T004.tasks.json` (FR-004/009/010).
  Files: ["tests/validate_orchestrator_store_contract.py", "plugin/skills/grill-with-docs/scripts/grill_core/store.py", "specs/033-latest-models/implement/T004.tasks.json"]
  Result: "specs/033-latest-models/implement/T004.tasks.json"

- [ ] T005 Run `python3 tests/validate_tier_model_binding_contract.py` and `python3 tests/validate_orchestrator_store_contract.py` against the integrated Phase 2 checkout; confirm the fixture requires no real runtime, Store replay does not resolve models and the historical policy/supplement/template hashes listed above remain unchanged.
  Files: []

**Checkpoint**: Both foundations pass independently and together. New worker producers must supply a binding in Phase 3; accepting historical absent fields is not permission to mint new unbound workers.

## Phase 3: User Story 1 — Preferred model within a Codex family (Priority: P1) — MVP

**Goal**: Every new worker producer resolves the declared family once and stores its selected model before dependent effects; retries retain the same choice.

**Independent Test**: Reverse Luna priorities and add a later Terra with worse/better priority in the fixture. Declare and directly prepare workers, inspect the first DECLARED record and response, then change/delete the catalog and retry. Exercise both remediation reasons as fresh attempts.

### Tests for User Story 1

- [ ] T006 [US1] Add failing worker selection/durability/retry/remediation assertions to `tests/validate_gauntlet_scheduler_contract.py` and direct passive-preparation assertions to `tests/validate_gauntlet_run_contract.py`; cover all three `prepare_worker` producers, catalog-ranked Luna/Terra, first DECLARED binding, saved response fields, changed/deleted-cache reuse, fresh replacement selection and unchanged Claude aliases, recording the intentional red results in `specs/033-latest-models/implement/T006.tasks.json` (FR-001/002/004/008/010/013).
  Files: ["tests/validate_gauntlet_scheduler_contract.py", "tests/validate_gauntlet_run_contract.py", "specs/033-latest-models/implement/T006.tasks.json"]
  Result: "specs/033-latest-models/implement/T006.tasks.json"

### Implementation for User Story 1

- [ ] T007 [US1] After T006, implement durable selection across `declare_worker`, `prepare_worker`, `_mint_remediation_worker` and saved response projections in `plugin/skills/grill-with-docs/scripts/grill_core/gauntlet_runs.py`, thread validated activation runtime and passive tier through `plugin/skills/grill-with-docs/scripts/grill_workspace.py`, and make the regressions in `tests/validate_gauntlet_scheduler_contract.py` and `tests/validate_gauntlet_run_contract.py` pass; record results in `specs/033-latest-models/implement/T007.tasks.json` (FR-001/002/004/008/009).
  Files: ["plugin/skills/grill-with-docs/scripts/grill_core/gauntlet_runs.py", "plugin/skills/grill-with-docs/scripts/grill_workspace.py", "tests/validate_gauntlet_scheduler_contract.py", "tests/validate_gauntlet_run_contract.py", "specs/033-latest-models/implement/T007.tasks.json"]
  Result: "specs/033-latest-models/implement/T007.tasks.json"

T007 resolves before first DECLARED mint/lease/worktree; response fields `model`, `model_frontier`, `model_runtime` project the stored binding. The actual worker launch must consume that saved model and retain the existing requested/effective model and supported-effort checks; selection alone is not execution proof. Runtime comes from the validated activation returned by `gauntlet_run_admission` as `record["runtime"]["id"]`, not admission hashes or a CLI default. Normal declaration keeps the explicit DAG tier; passive preparation uses `_tier_floors` plus grant markdown classification. Remediation resolves the original proven runtime/tier before budget spend, original-state mutation or replacement lease. Preserve one-remediation budget and concurrent cap. A recorded attempt reuses its binding after cache changes/deletion; a fresh attempt re-resolves. Historical unprovable dispatch/remediation refuses `WORKER-MODEL-UNPROVEN` without backfill, while historical read/cleanup remains available. Trace every caller before editing the shared preparation path.

- [ ] T008 [US1] Run `python3 tests/validate_gauntlet_scheduler_contract.py` and `python3 tests/validate_gauntlet_run_contract.py` with the injected fixture, verify all three producer records/projections and retry invariance, and confirm the Phase 2 Store/resolver checks still pass.
  Files: []

**Checkpoint**: US1 is independently demonstrable as the worker MVP. It is not release-ready until the refusal, specialist, continuity and distribution work below is complete. T006/T007 share test files and must remain one serial conflict group; their expected red intermediate state is not a phase acceptance.

## Phase 4: User Story 2 — Fail closed when choice is unproven (Priority: P1)

**Goal**: An unusable source or forbidden worker tier produces the exact public refusal before effects, with useful bounded metadata.

**Independent Test**: For each public worker producer, inject missing/unreadable/family-empty catalogs and compare Store revision/digest, journal/receipts, leases, grants, worktrees and payloads before/after. A frontier tier must refuse even when its catalog is absent, before any reader call. Specialist public refusal is completed by T012–T014 when that surface gains family selection.

- [ ] T009 [P] [US2] Extend `tests/validate_tier_model_binding_contract.py` with the catalog safety/ambiguity matrix from `specs/033-latest-models/contracts/model-selection.md`: invalid UTF-8/JSON/root/models/row shape, duplicate keys/non-finite JSON constants, unsafe/nonregular/oversized/racing input, missing or bool/string/null/non-finite relevant priorities, duplicate relevant slug, minimum ties, hidden/empty family, unrelated extra fields, catalog reordering, worse-priority ties, finite zero/negative/float priorities, and frontier-before-read; record exact outcomes in `specs/033-latest-models/implement/T009.tasks.json` (FR-005/006/010/013).
  Files: ["tests/validate_tier_model_binding_contract.py", "specs/033-latest-models/implement/T009.tasks.json"]
  Result: "specs/033-latest-models/implement/T009.tasks.json"

- [ ] T010 [P] [US2] Write public no-effect tests in `tests/validate_gauntlet_scheduler_contract.py` and `tests/validate_gauntlet_run_contract.py`, then preserve `TierModelError.extra` through `_resolve_worker_model` in `plugin/skills/grill-with-docs/scripts/grill_core/gauntlet_runs.py` and all worker/remediation CLI handlers in `plugin/skills/grill-with-docs/scripts/grill_workspace.py`; assert exit 2 plus BLOCKED JSON/code/runtime/tier/family/catalog_path/reason for declaration, passive preparation and both remediation reasons, and record results in `specs/033-latest-models/implement/T010.tasks.json` (FR-005/006/009/010/013).
  Files: ["tests/validate_gauntlet_scheduler_contract.py", "tests/validate_gauntlet_run_contract.py", "plugin/skills/grill-with-docs/scripts/grill_core/gauntlet_runs.py", "plugin/skills/grill-with-docs/scripts/grill_workspace.py", "specs/033-latest-models/implement/T010.tasks.json"]
  Result: "specs/033-latest-models/implement/T010.tasks.json"

T010 must compare actual public-command pre/post state, not just mock resolver output: unchanged Store revision/bytes, journal/receipt bytes, grant/lease/worktree counts and absence of payload; remediation failures also preserve original state and budget. Assert `FRONTIER-MODEL-FORBIDDEN` before reader access and effects, and `WORKER-MODEL-UNPROVEN` for historical effects without binding proof. Do not leak account identity, model instructions or user config in diagnostics; argparse exit 2 alone is not a passing refusal.

- [ ] T011 [US2] Run `python3 tests/validate_tier_model_binding_contract.py`, `python3 tests/validate_gauntlet_scheduler_contract.py` and `python3 tests/validate_gauntlet_run_contract.py`; verify every public negative has the named JSON refusal and unchanged state, including failed remediation and frontier with an absent catalog.
  Files: []

**Checkpoint**: Worker refusals are proven at the public boundary. T009 and T010 have disjoint grants and no dependency on each other's edits; a new resolver defect requires a scoped corrective task/review, not an undeclared source edit by T009.

## Phase 5: User Story 3 — Current specialist family and historical continuity (Priority: P2)

**Goal**: New Codex specialists use catalog-preferred Astra, new Claude specialists use exact Opus pairs, and recorded activities remain verifiable under their sealed policy.

**Independent Test**: Under v2, prepare both roles with opposing Astra priority orders; mutate/delete the catalog after preparation and compare native requested/effective/resolved fields to the saved pair. Exercise exact `opus` with author xhigh/reviewer high, divergent fields independently, historical v1 completion, fresh-v1 refusal and the combined predecessor/candidate/bundle scenario.

### Tests for User Story 3

- [ ] T012 [US3] Add failing pure and public specialist tests in `tests/validate_agent_orchestration_contract.py` for preferred Astra per role, saved-pair retry after cache change/deletion, immutable requested/effective facts, native requested/provider/effective/resolved divergences, exact Opus pairs, fable refusal, unresolved-catalog metadata with no bootstrap/Store/payload effects, v1 historical acceptance and fresh-v1 refusal; retain `test_first_campaign_is_born_in_a_pre_campaign_successor` with both bridge outcomes and record red results in `specs/033-latest-models/implement/T012.tasks.json` (FR-003/004/005/007/008/009/010/013).
  Files: ["tests/validate_agent_orchestration_contract.py", "specs/033-latest-models/implement/T012.tasks.json"]
  Result: "specs/033-latest-models/implement/T012.tasks.json"

### Implementation for User Story 3

- [ ] T013 [US3] After T012, add current `plugin/skills/grill-with-docs/assets/agent-orchestration.v2.json` and make `plugin/skills/grill-with-docs/scripts/grill_core/agent_orchestration.py` validate/prepare specialists from supplied policy and resolved pair without filesystem/catalog I/O; update the corresponding pure assertions in `tests/validate_agent_orchestration_contract.py` and record results in `specs/033-latest-models/implement/T013.tasks.json` (FR-003/004/007/008/009).
  Files: ["plugin/skills/grill-with-docs/assets/agent-orchestration.v2.json", "plugin/skills/grill-with-docs/scripts/grill_core/agent_orchestration.py", "tests/validate_agent_orchestration_contract.py", "specs/033-latest-models/implement/T013.tasks.json"]
  Result: "specs/033-latest-models/implement/T013.tasks.json"

T013 uses policy schema `grill-agent-orchestration-policy/v2`, `policy_version="2"` and unchanged Store contract `grill-agent-orchestration/v1`; Codex roles select Astra family, Claude roles exact `opus`, efforts unchanged. Preserve the activity matrix, presentation, references and recommendations. Cover all consumers: `prepare_activity`, `verify_specialist`, `record_verified_activity`, `session_resource`, `accept_activity`, `_visual_activity`, `require_task_files_review` and payload release. Recorded request is authoritative for the attempt, with family eligibility under its policy and exact observation equality; never accept another Astra generation or fabricate a full Opus provider slug. `resolved_model_id="opus"` records the observed alias. Keep deterministic activities model/runtime-null and catalog-free; preserve independence, identity, effort, fencing and close checks. Preserve `f1475f4` and its negative bridge check. Historical fable evidence remains readable/completable/cleanable, but no fresh fable payload may be released, including from an old BOOTSTRAPPING/VERIFIED activity.

- [ ] T014 [US3] After T013, implement the single allowlisted current/sealed policy-loading rule and fresh specialist resolution boundary in `plugin/skills/grill-with-docs/scripts/grill_workspace.py`, update policy-aware offline support in `tests/orchestration_fixture.py`, and make public/lifecycle/compatibility assertions pass in `tests/validate_agent_orchestration_contract.py`; record results in `specs/033-latest-models/implement/T014.tasks.json` (FR-003/004/005/007/008/009/010/013).
  Files: ["plugin/skills/grill-with-docs/scripts/grill_workspace.py", "tests/orchestration_fixture.py", "tests/validate_agent_orchestration_contract.py", "specs/033-latest-models/implement/T014.tasks.json"]
  Result: "specs/033-latest-models/implement/T014.tasks.json"

T014 applies the same exact shipped ref/hash allowlist and declared schema/version validation at `_bind_orchestration`, init/adopt, preflight/presentation, `_activity_policy`, coverage, step-enter, checkpoint/attest and continuity. New init/adopt selects v2; an existing adopted item and successor keep their original v1 ref/hash. Tampered bytes, unknown ref/version and contradictory context/activity seal refuse `ORCHESTRATION-POLICY-STALE`, with no arbitrary path loader or silent reseal. Resolve a fresh v2 Codex activity via the shared resolver before any Store write or bootstrap; a recorded retry uses its saved pair, and later verification/acceptance/cleanup never reads today's cache. Propagate catalog failure as `TIER-MODEL-UNRESOLVED` with role metadata rather than a capability wrapper. Fresh v1 preparation on the candidate refuses `ORCHESTRATION-MIGRATION-REQUIRED` before bootstrap, naming the preserved-bundle/new-v2-item recovery; a new v2 item does not complete this campaign. Preserve v1 asset/supplement/template bytes and historical receipts. Reuse the existing exact Opus observation boundary in `agent_runtime.py` unchanged.

- [ ] T015 [US3] **DEFERRED TO LEADER** — Execute the combined continuity scenario from `specs/033-latest-models/quickstart.md` section 2 in an isolated v1 fixture with predecessor lacking a campaign, successor having its first campaign and no bridge; compare preserved-bundle validation, candidate fresh-v1 `ORCHESTRATION-MIGRATION-REQUIRED` before effects and preserved-bundle Codex author plus independent reviewer bootstrap/admission/payload/result/acceptance/confirmed-close through offline runtime seams, then require refusal when the predecessor has a campaign but lacks its bridge, recording reproducible commands and pre/post evidence in `.grill/work-items/feature-latest-models-codex-ab7615f7e67f4e2c9d2b94f507c921ec/continuity-candidate-validation.md` (FR-009/010, SC-003/004).
  Files: [".grill/work-items/feature-latest-models-codex-ab7615f7e67f4e2c9d2b94f507c921ec/continuity-candidate-validation.md"]

T015 is an offline local continuity experiment with the two actual command roots, not a real specialist launch or a new dependency of the portable validator suite on a developer-specific worktree. Reuse the existing validator fixture/runtime seams in temporary projects. Assert candidate refusal preserves Store revision/digest, journal/receipt bytes, leases and payload absence; the preserved lifecycle appends only legitimate new activity evidence. Keep all pre-existing policy/pins/receipt/bridge bytes unchanged. Record the exact bundle revision, candidate revision/dirty-diff digest, source inputs and commands so the later verify gate can reproduce it. Read-only pure pair checks alone do not satisfy this task, and this experiment does not replace live campaign specialist admission.

- [ ] T016 [US3] Run `python3 tests/validate_agent_orchestration_contract.py` and `python3 tests/validate_orchestrator_store_contract.py`, confirm no catalog access during pure/historical checks, inspect T015 evidence and verify unchanged v1 seals plus current Opus/fable boundaries against `specs/033-latest-models/contracts/model-selection.md`.
  Files: []

**Checkpoint**: US3 behavioral and continuity evidence passes. T012–T014 all share the orchestration validator, making one serial conflict group; do not parallelize their code or tests. T015 and T016 follow worker convergence in that order.

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Update public guidance, complete suite integration, synchronize distribution and prepare evidence for the later canonical gates.

- [ ] T017 [P] Update current family/Opus/catalog/history guidance in `plugin/skills/grill-with-docs/SKILL.md`, `plugin/skills/grill-with-docs/references/session-protocol.md`, `README.md` and `docs/adr/0013-worker-model-floor.md`; bump all eight required version locations together, including `plugin/.claude-plugin/plugin.json`, `plugin/.codex-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.agents/plugins/marketplace.json` and `tests/validate_distribution.py` plus the three document headings, add one cumulative feature-and-`f1475f4` entry in `CHANGELOG.md`, run distribution validation and record results in `specs/033-latest-models/implement/T017.tasks.json` (FR-011/012).
  Files: ["plugin/skills/grill-with-docs/SKILL.md", "plugin/skills/grill-with-docs/references/session-protocol.md", "README.md", "docs/adr/0013-worker-model-floor.md", "plugin/.claude-plugin/plugin.json", "plugin/.codex-plugin/plugin.json", ".claude-plugin/marketplace.json", ".agents/plugins/marketplace.json", "tests/validate_distribution.py", "CHANGELOG.md", "specs/033-latest-models/implement/T017.tasks.json"]
  Result: "specs/033-latest-models/implement/T017.tasks.json"

T017 uses proposed `6.1.0` only if greater than the integrated base and unused; otherwise report the required later version for coordinator handling under the accepted release rule. Describe actual durable worker binding, preferred listed family rather than newest numeric generation, exact author/reviewer Opus efforts, unchanged leader/Claude worker behavior and fail-closed local catalog dependency without refresh/freshness claims. Point current orchestration guidance to v2 and explain immutable v1 compatibility, without changing pinned supplement/template or erasing historical CHANGELOG/fable evidence. Include the successor-first-campaign fix and retained bridge refusal in the cumulative release notes. This task changes no tag, Release or marketplace source anchor; publication belongs to the authorized pipeline.

- [ ] T018 [P] Adapt the specialist helpers in `tests/validate_gauntlet_scheduler_contract.py`, `tests/validate_gauntlet_converge_contract.py` and `tests/validate_status_contract.py` to the supplied fixture and owning policy/saved pair using `tests/orchestration_fixture.py`; preserve explicit historical-v1 scenarios and absent-cache negatives, run the affected validators and record results in `specs/033-latest-models/implement/T018.tasks.json` (FR-008/009/010/013).
  Files: ["tests/validate_gauntlet_scheduler_contract.py", "tests/validate_gauntlet_converge_contract.py", "tests/validate_status_contract.py", "tests/orchestration_fixture.py", "specs/033-latest-models/implement/T018.tasks.json"]
  Result: "specs/033-latest-models/implement/T018.tasks.json"

- [ ] T019 Run `python3 tests/run_validators.py` and `git diff --check` against the integrated candidate; count actual `==>` markers, confirm all eight quickstart scenarios and T015 combined continuity evidence, inspect `tests/validate_distribution.py` for the eight synchronized version points and cumulative `CHANGELOG.md`, and verify current public guidance no longer requires fable while historical evidence remains byte-identical.
  Files: []

- [ ] T020 **DEFERRED TO LEADER** — Capture implementation checks, task sidecar/receipt references, current candidate digest, T015 continuity evidence, preserved-bundle revalidation and remaining gates in `.grill/work-items/feature-latest-models-codex-ab7615f7e67f4e2c9d2b94f507c921ec/latest-models-implementation-validation.md`; hand off only after positive task/phase acceptance, explicitly retaining canonical converge, verify, independent review, human ship authorization, same-anchor immutable tag/Release pipeline and confirmed cleanup as subsequent obligations under `specs/033-latest-models/quickstart.md` section 4.
  Files: [".grill/work-items/feature-latest-models-codex-ab7615f7e67f4e2c9d2b94f507c921ec/latest-models-implementation-validation.md"]

**Checkpoint**: Implementation evidence is ready for canonical converge/verify/review, not a declaration that those steps or ship have passed. Verify must rerun the required executable gates on the integrated bytes and reproduce/revalidate the combined continuity case before ship; later changes invalidate earlier evidence as appropriate. The coordinator must use the preserved CLI for all remaining v1 gates, obtain any fresh judgment through independent specialist sessions, then request human ship authorization only after verify/review. The release pipeline must anchor tag and Release to the same commit; no manual Release workaround. Do not make those later gates prerequisites for closing an implementation task, which would create a workflow cycle.

## Dependencies & Execution Order

| Phase | Tasks | Required predecessors | Worker groups and final activities |
|---|---|---|---|
| 1 — Setup | T001–T002 | Accepted tasks/analyze/partition and admitted implementation context | No workers; read-only T001, then deferred T002 |
| 2 — Foundational | T003–T005 | Phase 1 accepted | Independent T003 and T004; then read-only T005 |
| 3 — US1 | T006–T008 | Phase 2 accepted | One serial group T006 → T007; then read-only T008 |
| 4 — US2 | T009–T011 | Phase 3 accepted | Independent T009 and T010; then read-only T011 |
| 5 — US3 | T012–T016 | Phase 4 accepted | One serial group T012 → T013 → T014; then deferred T015 and read-only T016 |
| 6 — Polish | T017–T020 | Phase 5 accepted | Independent T017 and T018; then read-only T019 and deferred T020 |

US1 depends on the shared resolver/schema. US2 extends the US1 worker path and retains its tests. US3 reuses that resolver and then completes specialist refusal coverage. These stories have independent acceptance scenarios, but share implementation files and therefore do not run concurrently. Phase boundaries serialize repeated ownership of `grill_workspace.py`, `gauntlet_runs.py` and validator/helper files. Conflicts inside US1/US3 intentionally keep test-first work with its implementation in one worker; preserve ID order even when a node contains several tasks.

## Parallel Examples by User Story

- **US1**: No parallel writing inside the story; T006 → T007 share scheduler/run validators. Its prerequisites T003 and T004 can execute concurrently in Phase 2.
- **US2**: T009 (resolver negative tests) and T010 (public worker failure boundary) can execute concurrently after US1 acceptance; their Files are disjoint.
- **US3**: No parallel writing inside the story; T012 → T013 → T014 share the specialist validator. The leader runs T015 only after that group converges.
- **Cross-cutting**: T017 (guidance/distribution) and T018 (downstream fixture callers) can execute concurrently after US3 acceptance, before the complete gate.

With width 2, these grants yield eight real worker nodes across five writing phases, with a maximum width of two; no worker is synthesized for Phase 1 or reserved evidence. A larger requested width adds no justified concurrency. Partition remains responsible for emitting/admitting the actual DAG after independent tasks review and analyze.

## Requirements and acceptance coverage

| Requirement | Tasks and evidence |
|---|---|
| FR-001/002 | T003, T006–T008: Luna/Terra catalog preference, retained family and frontier classification |
| FR-003/007 | T012–T016: Astra roles, exact Opus efforts, requested/effective/resolved comparison, fable refusal |
| FR-004 | T004, T006–T008, T012–T014: durable immutable worker/activity model and stable retry |
| FR-005/006 | T003, T009–T014: malformed/unusable family catalog, public metadata, frontier-before-read and no effects |
| FR-008 | T003, T006–T008, T012–T014, T018: Claude worker aliases, leader recommendation and effort/floor parity |
| FR-009 | T002, T004, T007, T012–T016, T018–T020: legacy replay, sealed v1 compatibility, fresh-v1 refusal, successor/bridge continuity and preserved bundle |
| FR-010/013 | T003–T016, T018–T019: real-shape fixture, all eight quickstart scenarios, offline seams, newer-but-not-preferred generation and meaningful failure assertions |
| FR-011 | T017, T019: current public tables/prose use Opus; immutable historical fable evidence is exempt |
| FR-012 | T017, T019–T020 and later canonical ship: eight-point bump, cumulative changelog including f1475f4, immutable same-anchor tag/Release |

## Implementation Strategy

1. Accept Setup and both foundations; demonstrate the US1 worker MVP with stored selection and retry invariance.
2. Prove US2 negative effects through public commands, then implement/test US3 pure policy, CLI selection and isolated continuity in declared order.
3. Integrate disjoint documentation/distribution and fixture-caller work; pass full offline validators and diff hygiene; record implementation evidence without accepting later macrosteps.
4. Continue the eleven-step canonical cycle with the preserved coordinator bundle: converge → verify → independent review → human-authorized ship and pipeline confirmation. Keep all lifecycle, policy and bundle checks active until cleanup.

**Counts**: 20 tasks total — US1: 3; US2: 3; US3: 5; Setup: 2; Foundational: 3; Polish: 4. Eleven dispatchable writing tasks, six read-only tasks and three leader-deferred evidence tasks. Six `[P]` tasks form three independent pairs; serial test/implementation groups preserve executable ordering.

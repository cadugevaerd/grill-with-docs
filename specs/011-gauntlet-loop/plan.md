# Implementation Plan: Gauntlet Loop Activation

**Branch**: `011-gauntlet-loop` | **Date**: 2026-08-14 | **Spec**: [spec.md](spec.md)
**Phase**: `FASE-001` | **Delivery Unit**: `DU-001` | **Work Item**: `feature-gauntlet-loop-0447622ec0714933a4e791d0b58b5420`

## Summary

Add an opt-in Gauntlet activation boundary for eligible V3 work items. A new public command family records a strict versioned configuration, proves the complete Claude Code skill catalog before activation, admits a run without dispatching work, exposes a read-only status projection, and preserves the existing V2 commands byte-for-byte. This phase deliberately excludes durable runs, worker creation, scheduling, worktrees, receipts, convergence, and review.

## Technical Context

**Language/Version**: Python 3.10+ (standard library only)
**Primary Dependencies**: Existing `grill_workspace.py` public CLI and `grill_core` V3 modules
**Storage**: Git-tracked project configuration at `.grill/gauntlet.yaml`, expressed as JSON-compatible YAML and atomically replaced; no database or Project Store run record in this phase
**Testing**: Python `unittest` contract validators invoked through the public CLI
**Target Platform**: POSIX Python CLI with full activation support; platforms without safe no-follow directory primitives, including the current Windows path, return an explicit safe block while existing commands remain supported
**Project Type**: Claude/Codex plugin command-line tool
**Performance Goals**: Status and admission complete with local file reads only; no network request or spawned runtime process
**Constraints**: One JSON document on stdout; fail closed; no V2 contract change; no secrets, host paths, process handles, or budget field; maximum selected workers is five; stall threshold is fifteen minutes
**Scale/Scope**: One configuration may contain explicit activation records for multiple V3 work items; this phase never starts a worker or persists a run

## Constitution Check

| Clause | Plan evidence | Status |
|---|---|---|
| Evidência antes de afirmação | Activation binds workflow, registry, catalog and work-item identities; command tests assert all denial paths leave no state. | PASS |
| Work item isolado e ownership | Every command requires one validated `--work-id`; config records it as the activation key. | PASS |
| Feature/fix plan-only | The implementation is developed under this separate work item and will not ship or publish before the external review/ship gates. | PASS |
| Sequência obrigatória | The public checkpoint matrix records this plan after the passed `specify` checkpoint and keeps canonical ordering. | PASS |
| Verify/review antes de ship | Tests, independent review, and ship remain later required stages. | PASS |
| Fail-closed sem waiver | Missing, malformed, untrusted, stale, unsupported, and symbolic-link inputs return named block outcomes before writes. | PASS |
| Rastreabilidade | Config, status, tests, and checkpoint evidence all carry work item and current immutable identities. | PASS |
| Bump obrigatório do plugin | No merge/push occurs in this phase. If FASE-001 ships independently, every distribution surface first receives a synchronized version greater than 2.5.4. The planned single feature release keeps the branch unmerged through FASE-003 and raises all surfaces to 2.6.0 in FASE-004 before merge/ship. | PASS |

## Design

### Public command surface

Add distinct subcommands to `grill_workspace.py`; do not modify `init`, `status`, `audit`, `checkpoint`, `phase-turn`, or V2 migration semantics.

| Command | Inputs | Success | Safe denial / phase boundary |
|---|---|---|---|
| `gauntlet-init` | root, `--work-id`, required selected workers | `ACTIVATED` or `REUSED` | `BLOCKED` with `ACTIVATION-CONFLICT`, `WORKFLOW-INCOMPATIBLE`, `WORK-ITEM-V3-REQUIRED`, `RUNTIME-ENTRYPOINT-UNPROVEN`, or another named code |
| `gauntlet-run` | root, `--work-id` | `RUN-ADMITTED` after fresh validation | `BLOCKED` with `ACTIVATION-REQUIRED`, stale/invalid identity code; never creates run/worker state |
| `gauntlet-status` | root, `--work-id` | `STATUS` plus exactly one state: `ELIGIBLE`, `ACTIVATED`, `STALE`, or `BLOCKED` | Read-only status with reason for stale/blocked |
| `gauntlet-resume` | root, `--work-id` | none in FASE-001 | Missing/stale activation: `BLOCKED` with `ACTIVATION-REQUIRED`; current activation: `BLOCKED` with `SCHEDULING-NOT-AVAILABLE`, no write |
| `gauntlet-cleanup` | root, `--work-id` | none in FASE-001 | `BLOCKED` with `SCHEDULING-NOT-AVAILABLE`, no deletion |

The shared CLI boundary loads the new core through `grill_core_module()`, catches arbitrary load errors, translates V3 and Gauntlet error codes to kebab case, and keeps stdout to exactly one JSON document. Success is a `verdict`; domain denials are `{"verdict":"BLOCKED","code":"KEBAB-CASE"}`.

### Eligibility and proof

`gauntlet-init` and `gauntlet-run` perform the same admission chain before any mutation:

1. Read `WORKFLOW.md` safely and apply `workflow_v3.execution_gate()`; this proves the V3 marker, canonical eleven-stage sequence, and current registry pin.
2. Open the named work item through `open_development_item_fd()` and read it using `work_item_v3.read_document_with_digest_at()`. Pass its parsed metadata to `work_item_v3.require_v3()`, compare `immutable["workflow"]["sha256"]` with the accepted `WORKFLOW.md` digest from step 1, and block with `WORK-ITEM-WORKFLOW-DIVERGENT` on mismatch. A missing safe descriptor capability is `SAFE-PATH-UNAVAILABLE`. Retain the full document digest separately.
3. Safely read a new immutable plugin asset `assets/claude-code-local-skills.catalog.json`, parse it strictly, and load the shipped `workflow-trusted-catalogs.json` pin. For every canonical step, call `step_skills.resolve_workflow_skill(step, "claude", registry_sha256, registry=registry_bytes, catalog=claude_catalog)`. The catalog must match its shipped trust pin; an activation cannot self-authorize a catalog.
4. Derive immutable SHA-256 identities for the workflow bytes, registry bytes, trusted-catalog asset bytes, Claude catalog bytes and ID, and the V3 `WORK-ITEM.json` bytes. Persist only these logical identities and the approved runtime/adapter description.

The first release accepts no Codex, Hermes, alias, emulation, or runtime fallback. The public adapter uses this closed error translation table; its literal allowlist is part of `gauntlet.py`, and the validator parametrizes one failure fixture for every member plus the fallback. No unknown reason reaches stdout verbatim.

| Origin | Closed condition set | Public code |
|---|---|---|
| `SkillResolutionError` | Code `STALE_SKILL_RESOLUTION` (checked before its reason) | `STALE-SKILL-RESOLUTION` |
| `SkillResolutionError` | `INVALID_DIGEST`, `INVALID_RESOLVER_VERSION`, `INVALID_VERSION`, `UNKNOWN_RUNTIME`, `UNKNOWN_STEP`, `RUNTIME_UNSUPPORTED`, `RUNTIME_ENTRYPOINT_UNPROVEN`, `ADAPTER_MISMATCH`, `ENTRYPOINT_ABSENT`, `ENTRYPOINT_KIND_MISMATCH`, `AMBIGUOUS_ENTRYPOINT`, `NO_NATIVE_ENTRYPOINT`, `SOURCE_REF_MISMATCH`, `VERSION_BELOW_MINIMUM`, `REGISTRY_SHA256_MISMATCH`, `SKILL_NOT_PUBLISHED`, `SKILL_CHANGED_AFTER_PREFLIGHT`, `PINNED_RESOLUTION_INVALID`, or `PINNED_RESOLUTION_TAMPERED` | Kebab-case equivalent of the reason |
| `SkillResolutionError` | `REGISTRY_ADAPTER`, `REGISTRY_ALLOWED_ENTRYPOINTS`, `REGISTRY_CATALOG_ID`, `REGISTRY_DUPLICATE_ENTRYPOINT`, `REGISTRY_DUPLICATE_SKILL_ID`, `REGISTRY_ENTRYPOINT`, `REGISTRY_ENTRYPOINT_KIND`, `REGISTRY_HUMAN_AUTHORIZATION`, `REGISTRY_INVALID`, `REGISTRY_PROPOSED_SKILL_ID`, `REGISTRY_RESOLUTIONS`, `REGISTRY_RESOLUTION_INVALID`, `REGISTRY_RUNTIMES`, `REGISTRY_SCHEMA`, `REGISTRY_SKILL_ID`, `REGISTRY_SOURCE_REF`, `REGISTRY_STEPS`, `REGISTRY_STEP_INVALID`, `REGISTRY_STEP_NOT_REQUIRED`, `REGISTRY_STEP_SET`, `REGISTRY_UNREADABLE`, `REGISTRY_UNRESOLVED_REASON`, `REGISTRY_VERSION`, `REGISTRY_WORKFLOW_VERSION` | Kebab-case equivalent of the reason |
| `SkillResolutionError` | `CATALOG_ABSENT`, `CATALOG_CONTENT_MISMATCH`, `CATALOG_DIGEST`, `CATALOG_ENTRIES`, `CATALOG_ENTRY_INVALID`, `CATALOG_ID`, `CATALOG_INVALID`, `CATALOG_MISMATCH`, `CATALOG_RUNTIME`, `CATALOG_RUNTIME_MISMATCH`, `CATALOG_SCHEMA`, `CATALOG_SHA256_MISMATCH`, `UNTRUSTED_CATALOG` | Kebab-case equivalent of the reason |
| `SkillResolutionError` | `TRUSTED_CATALOGS_INVALID`, `TRUSTED_CATALOGS_SCHEMA`, `TRUSTED_CATALOGS_UNREADABLE`, `TRUSTED_CATALOGS_WORKFLOW_VERSION` | Kebab-case equivalent of the reason |
| `SkillResolutionError` | Any other code or reason | `BLOCKED-CAPABILITY` |
| `CliFailure` from `open_development_item_fd()` | Code `SAFE-DIRECTORY-FD-UNAVAILABLE` | `SAFE-PATH-UNAVAILABLE` |
| Gauntlet workflow binding | Current work-item and workflow identities differ | `WORK-ITEM-WORKFLOW-DIVERGENT` |

`gauntlet-status` evaluates the same chain without writing and selects a state in strict precedence: existing identity mismatch is `STALE`; otherwise an eligibility failure is `BLOCKED`; otherwise a matching activation is `ACTIVATED`; otherwise `ELIGIBLE`.

### Versioned configuration

Create `.grill/gauntlet.yaml` only after all admission checks pass. The file uses JSON syntax, which is valid YAML, so Python's standard library can enforce a closed and deterministic schema without adding a YAML parser dependency. It is project versioned rather than a common-Git Store policy because it is an explicit, reviewable project configuration. The file is the single authorized project-scoped mutation after successful activation; failed admission never creates or changes it.

```json
{
  "schema": "grill-gauntlet/v1",
  "activations": {
    "<work-item-id>": {
      "work_item_id": "<work-item-id>",
      "work_item": {"document_sha256": "<sha256>"},
      "workflow": {"version": "v3", "sha256": "<sha256>", "registry_sha256": "<sha256>"},
      "runtime": {"id": "claude", "adapter": "claude-code-skill/v1"},
      "catalog": {"id": "claude-code-local-skills", "document_sha256": "<sha256>", "resolution_sha256": "sha256:<jcs-entries-digest>", "trusted_asset_document_sha256": "<sha256>"},
      "limits": {"max_workers": 1, "stall_minutes": 15},
      "tier_policy": {"adapter": "claude-code-skill/v1", "minimum_by_step": {"specify": "large", "plan": "large", "checklist": "small", "tasks": "medium", "analyze": "large", "agent-assign": "large", "agent-execute": "medium", "converge": "medium", "verify": "medium", "review": "large", "ship": "large"}, "supplemental": {"markdown-maintenance": "small"}, "promotions": []}
    }
  }
}
```

The activated value for `max_workers` is selected by the operator in the inclusive range 1–5; five is only the maximum, not an inferred default. `tier_policy` binds each abstract tier to the selected native Claude adapter and stores any promotion as a closed pre-dispatch record; phase one creates no promotion and dispatches none. The schema rejects duplicate keys, BOM/non-UTF-8 data, unknown keys, incorrect primitive types, floats, booleans used as integers, unrecognized enum values, paths, credentials, and every `budget` or cost field.

A configuration-wide directory lock lives at `.grill/.gauntlet-config.lock`, independent of the work-item lock, and serializes all activation writers. `gauntlet-init` acquires it first, then acquires the existing named work-item lock before reading identity or mutating the activation map; it releases the work-item lock before the config lock. `migrate-v3 --rebind-workflow` owns only the named work-item lock, so it cannot deadlock and an activation waits for its rebind to finish. `run`, `status`, `resume`, and `cleanup` are read-only in FASE-001 and acquire neither lock. Existing or malformed lock state returns a named contention/unsafe-lock block; every owner removes only its own lock and no failure may leave a temporary config file or a lock it did not create.

On a platform with `O_NOFOLLOW` and directory-descriptor support, the command opens the `.grill` chain and configuration through descriptors, snapshots the prior bytes, strictly parses and mutates only the named activation map entry, rechecks the expected bytes immediately before replacement, writes and fsyncs a temporary regular file, atomically replaces it, and fsyncs the parent directory. A changed snapshot returns `CONFIG-CHANGED`; an interrupted write leaves the old complete document or the new complete document. A platform without those primitives returns `BLOCKED` with `SAFE-PATH-UNAVAILABLE`; it never uses a weaker path-based fallback. Equivalent activation is byte-identical `REUSED`; a conflicting record returns `BLOCKED` with `ACTIVATION-CONFLICT` unchanged. Tests cover concurrent activations for different work items, lock ordering/contention/cleanup, replacement interruption, symbolic-link substitution, and unavailable safe-path capability.

`gauntlet-status` never mutates and, when a valid root and work item can be identified, converts eligibility-proof errors such as `SAFE-PATH-UNAVAILABLE` into `{"verdict":"STATUS","activation_state":"BLOCKED","reason":"..."}`. Root/argument misuse and loader failures before a status projection remains possible are command failures with top-level `{"verdict":"BLOCKED","code":"..."}`.

The public boundary classifies `INVALID-ARGUMENTS`, invalid or non-Git root, invalid/missing work-item identity, and any core loader failure before a valid status subject exists as stable top-level `BLOCKED` command failures. Only after root and work-item identity are safe and valid may workflow, catalog, configuration, safe-path, or V3-binding proof failures be represented as `STATUS` with activation state `BLOCKED` and a reason. The validator snapshots exact one-JSON output, verdict/code shape, and no writes for both classes.

### Phase boundary

`gauntlet-run` returns `RUN-ADMITTED` only after fresh matching activation and eligibility checks. It records no durable run, lease, receipt, worker, worktree, branch, child process, or dispatch. `resume` first verifies activation: absent or stale activation blocks with `ACTIVATION-REQUIRED`; current activation returns `SCHEDULING-NOT-AVAILABLE`. `cleanup` returns `SCHEDULING-NOT-AVAILABLE` and cannot delete anything. FASE-003 owns the scheduler, DAG waves, and stall recovery; FASE-004 owns convergence, independent review, and the human ship gate.

### Explicit legacy workflow rebind

Current V3 migration preserves the work item's historic workflow identity. To make that identity current without silently rewriting authority, extend the existing `migrate-v3` command with `--rebind-workflow`: preview returns the before/after immutable workflow digests and changes nothing; `--rebind-workflow --apply` requires a current V3 workflow gate, no-follow work-item descriptor, CAS match of `WORK-ITEM.json`, and the existing work-item lock before recalculating its immutable/content hashes. The rebind changes only the immutable workflow binding and dependent hashes, preserves every unrelated top-level field byte/logically unchanged, preserves the original `WORK-ITEM.json` mode, and writes through the existing descriptor-protected `_atomic_replace_at` path.

Before the rebind uses that helper, strengthen `_atomic_replace_at`: an `os.fchmod` error while restoring the requested mode raises `MODE-PRESERVATION-FAILED` before file data or rename, rather than being ignored. `gauntlet-init` never performs this rebind. The validator covers V2-to-V3 migration before rebind, preview no-op, apply success, unrelated field and original-mode preservation, injected mode-restoration failure, stale CAS, interrupted-write failure preservation, and idempotent reapply.

## Project Structure

```text
plugin/skills/grill-with-docs/
├── scripts/
│   ├── grill_workspace.py                 # additive public gauntlet commands
│   └── grill_core/
│       └── gauntlet.py                    # closed config, admission, status and controls
└── assets/
    ├── workflow-step-skills.json          # existing runtime registry, read only
    ├── workflow-trusted-catalogs.json     # existing trust pin, read only
    └── claude-code-local-skills.catalog.json # immutable catalog, added and pinned

tests/
└── validate_gauntlet_activation_contract.py

specs/011-gauntlet-loop/
├── plan.md
├── research.md
├── data-model.md
├── contracts/gauntlet-cli.md
└── quickstart.md
```

**Structure Decision**: Add exactly one core module and one dedicated contract validator. Existing V3 guard modules remain their single sources of truth; no schema field is added to `orchestrator.json`, and no current generic `status` payload changes.

## Complexity Tracking

| Decision | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| JSON-compatible YAML | Project requested a versioned `.yaml` configuration while the plugin must remain standard-library-only and reject malformed/duplicate input deterministically. | A general YAML parser adds a dependency and parser variability; an unversioned common-Git policy is not reviewable project configuration. |
| Separate Gauntlet command family | Existing V2 CLI payloads are contract-tested and must not change. | Extending `init` or `status` risks silently changing V2 behaviour and output shape. |
| Admission-only `run` | The handoff requires a run to start, while FASE-002 owns durable run state and FASE-003 owns dispatch. | Starting workers or storing a partial run now violates the phase boundary; rejecting run entirely violates the handoff. |

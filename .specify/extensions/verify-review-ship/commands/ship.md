---
description: "Capture approved project learnings, revalidate, merge safely, clean up, and summarize delivery"
---

# Ship, Learn, Merge, Cleanup, and Delivery Summary

Run after official `/speckit.converge`, `/speckit.verify-review-ship.verify`, and `/speckit.verify-review-ship.review`.

## User Input

$ARGUMENTS

## Purpose

```text
AWAITING_LEARNING_APPROVAL | MERGED | MERGED_WITH_CLEANUP_WARNINGS |
MERGED_WITH_POST_MERGE_WARNINGS | NO-GO | BLOCKED | DRY-RUN READY
```

`--dry-run` produces evidence and exact Git operations without persisting a proposal, editing files, fetching, pruning, merging, pushing, or changing refs. Dry-run never writes a proposal.

Approval arguments: `--approve all`, `--approve LRN-001,LRN-003`, `--reject LRN-002`, `--defer LRN-004`, and `--proposal <proposal-hash>`. Ambiguity or an invalid hash returns `AWAITING_LEARNING_APPROVAL`.

## Phase A — Evidence Freshness

Consume reports whose source fingerprints exactly match the current worktree:

```text
Converge: `CONVERGED`
Verify: PASS
Review: APPROVE
Fingerprint: tree / work / plan, each reported separately
             (computed by `scripts/source-fingerprint.sh`; see `verify` for the contract)
```

`tasks_appended`, missing, stale, contradictory, or failed evidence is `BLOCKED`; resume with `/speckit.implement` and `/speckit.converge` as applicable.

This phase must not run a new independent Code Reviewer, must not run a new independent Security Auditor, and must not run a new independent Test Engineer. Official Converge owns completeness; Verify owns executable gates; Review owns technical risk. Check rollback and monitoring evidence, unresolved Critical/Important findings, and report freshness only. On success record immutable `source_head` and provisional GO.

## Phase B — Learning / Policy Gate

Extract deterministic `LRN-###` candidates only from concrete Converge, Verify, Review, gate, rollback, decision, retry, and user-correction evidence. Each includes evidence, scope, duplicate result, destination, bounded diff, risk, and required revalidation. A candidate without evidence is `BLOCKED` and cannot be applied.

### B1. Deduplicate and route

Route only one destination: `constitution`, `agent-context`, `adr-docs`, `backlog`, `memory`, or `discard`. Never duplicate a rule between Constitution, agent context, and memory. Feature-local, transient, secret-bearing, unsupported, or duplicate observations are `discard`.

### B2. Validate destinations

- Constitution must exist; a candidate is blocked if it is missing. Apply SemVer, amendment date, sync-impact report, and propagation.
- Agent context respects configured files and managed markers; never overwrite managed markers. Missing files are proposed as `CREATE`, never created silently.
- ADR/docs and backlog use approved project-relative paths; no destination fallback is silent.
- Generic Spec Kit has no memory API. `host-write` requires a documented, idempotent adapter and real success evidence; otherwise use `propose-only`.

### B3. Proposal, approval, and commit

Persist non-dry-run proposals outside the worktree keyed by `source_head` and proposal hash. Any HEAD or proposal-hash change invalidates approval. Apply only approved versioned changes and prove allowed paths/hunks.

`ship.learning_gate.auto_commit_versioned_changes` must be `true`; false or missing is `BLOCKED`. Create `docs(ship): capture approved project learnings`; never stash, discard, or commit user work.

### B4. Revalidate final HEAD

Applied changes make previous evidence stale.

| Applied change | Required resume path |
|---|---|
| Constitution, spec.md, plan.md, or tasks.md | run `/speckit.analyze` then `/speckit.converge`; if `tasks_appended`, stop for implement |
| Executable code/configuration | run `/speckit.converge` |
| ADR/docs/context/backlog | run affected executable gates and review |
| Memory only | finalize after merge |

After required Converge reaches `CONVERGED`, rerun `verify`, `review`, and affected integration gates. Missing/failing evidence is `BLOCKED`/`NO-GO` and never merges.

## Phase C — Git Pre-flight

Require a named clean worktree, distinct work/primary branches, no operation in progress, fresh final evidence, a discovered remote/base, and `no-ff` or `ff-only`. Never guess `main`, force-push, stash, reset hard, git clean, or delete unleased work.

## Phase D — Isolated Integration Transaction

Create an integration worktree from fetched primary HEAD, merge final work HEAD, run affected gates, push without force, and read remote primary back for exact equality. Conflicts, divergence, or concurrent primary changes return `BLOCKED`/`NO-GO` and preserve work.

## Phase E — Memory and Cleanup

With default configuration, finalize approved memory only after remote primary-ref verification. `propose-only` remains pending. A required memory failure returns `MERGED_WITH_POST_MERGE_WARNINGS`; cleanup failure returns `MERGED_WITH_CLEANUP_WARNINGS` and never rolls back a verified merge.

## Phase F — Report

Report source/proposal hashes, evidence consumed, approval decisions, applied commit, Converge/Verify/Review results, remote refs, cleanup, pending memory, and a safe resume action for every non-merged status.

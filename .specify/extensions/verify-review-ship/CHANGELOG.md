# Changelog

## 0.4.2 - 2026-07-26

### Fixed

- The source fingerprint no longer includes `HEAD`, and now excludes gate-report paths. Writing
  and committing `verify.md` changed `HEAD` without changing the reviewed content, so the
  fingerprint a report had just declared was invalidated before `review` consumed it — forcing a
  spurious `BLOCKED` on work that never moved.
- `verify` gained a canonical **Source Fingerprint** section computing a reviewed-scope tree
  hash, an uncommitted diff hash, and the `tasks.md` hash; `review` and `ship` reference it
  instead of restating the rule in prose.
- Added `converge.fingerprint_exclude` to the manifest and the configuration template so
  projects storing gate reports elsewhere can extend the exclusion list. The script reads that
  key, so the published setting and the algorithm share one effective set.
- Untracked files now count toward the fingerprint. `git diff HEAD` does not see a file that was
  never added, so an implementation delivered as a new unstaged file could have passed a
  matching-evidence check without being reviewed.

### Added

- `scripts/source-fingerprint.sh` — the single executable implementation of the fingerprint.
  `verify`, `review` and `ship` defer to it instead of restating the algorithm in prose.
- `tests/test_source_fingerprint.py` — behavioural tests that run the script against throwaway
  repositories: committing a gate report must not move the fingerprint, a real content change
  must, an untracked file must, `tasks.md` is pinned separately, and the configured exclusion
  list actually drives the result.

## 0.4.1 - Unreleased

### Changed

- Adopt the official `/speckit.converge` loop as the sole authority for spec/plan/tasks-to-code completeness.
- `verify` now consumes fresh Converge evidence and focuses on executable gates, contracts, quickstart, and diff hygiene.
- `review` now focuses on runtime correctness, test quality, readability, architecture, security, and performance without re-auditing completeness or every Constitution item.
- `ship` consumes fresh Converge/Verify/Review evidence instead of launching duplicate reviewer, security, and test passes.
- Constitution and Spec Kit artifact learning changes now require `analyze → converge` before Verify and Review.
- Removed the post-implement extension hook; the extension now exposes three commands and zero hooks.
- Minimum supported Spec Kit version is `0.11.2` because `/speckit.converge` is required.

## 0.4.0 - 2026-07-26

### Added

- `ship` now has an evidence-backed learning and policy gate before the Git integration transaction.
- Candidates are deduplicated and routed to Constitution, agent context, ADR/docs, backlog, external memory, or discard.
- The user can approve all, approve/reject/defer individual stable IDs, and resume only when the recorded work HEAD and proposal hash still match.
- Approved versioned changes are committed on the work branch, then `analyze` (for Constitution changes), `verify`, `review`, and affected integration gates are rerun before merge.
- Ship reports now include learning evidence, proposals, approvals, applied changes, revalidation, and pending/unavailable persistence.

### Changed

- Context-file targeting follows the optional Spec Kit `agent-context` configuration when present; managed blocks are never overwritten.
- External memory defaults to `propose-only`; host writes require a documented adapter and are finalized after the remote primary ref is verified unless rollback is supported.

## 0.3.0 - 2026-07-24

### Changed

- `ship` now treats a successful GO decision as authorization to integrate the recorded work HEAD into the discovered primary branch.
- Integration runs in an isolated temporary worktree, reruns mandatory gates, pushes without force, and verifies the remote primary ref before cleanup.
- Completed linked worktrees and local/remote work branches are removed only after ancestry, cleanliness, and immutable-ref checks pass.
- Final output classifies the delivery (product, feature, bugfix, security, refactor, documentation, chore, or other) and summarizes business outcome, evidence, merge, and cleanup.
- Extension effect changed from `read-only` to `read-write`; `--dry-run` previews the transaction without mutation.

## 0.2.0 - 2026-07-16

### Added

- Subagent/worker pre-flight discovery with explicit sequential fallback for `verify` and `review`.
- Atomic validation ledgers: one fresh, read-only validator per artifact, gate, requirement/task traceability item, and review axis.
- Constitution compliance review: each actionable `.specify/memory/constitution.md` item receives one dedicated validator.
- Validator identity, execution mode, capacity, and evidence in reports.
- Orchestration configuration for discovery, required availability, and bounded parallelism.

## 0.1.0 - 2026-07-09

### Added

- Initial Spec Kit extension manifest, verify/review/ship commands, hook, and configuration template.

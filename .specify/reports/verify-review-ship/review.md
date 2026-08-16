## Review Report — FASE-004 (Convergência, Revisão e Entrega Verificável)

Verdict: APPROVE
Source fingerprint: `c7997425107aec7de207c0fe880225aba58df5eea8b3fe27aa50c9f80b032fab` (matches `verify.md`'s fingerprint above — same tree, no change between verify and this review)

This is a single independent adversarial code-review round, run by a fresh Code Reviewer subagent with no prior involvement in writing this code, against the same working tree `verify.md` fingerprints. The reviewer read `spec.md`, `plan.md`, all four ADRs (0020-0023), the CLI contract, and `quickstart.md` in full before touching code, then read the real diff function-by-function against the contract's stated 6-step check order, read the entire new test file (1457 lines), and independently re-ran every FASE-004-relevant validator rather than trusting T031's recorded evidence blindly.

### Round 1 — full adversarial review (verdict: APPROVE, no re-review round needed)

Confirmed all FR-001 through FR-014 against the actual code, one by one, not against `plan.md`'s restatement of them:

- **FR-001** (convergence ordering and DAG-driven completion): the DAG-pin check runs before the terminal-run check exactly as the contract specifies; merges happen alphabetically by `node_id` within a wave; `COMPLETE` fires only when the whole pinned DAG's node set converges, never by counting waves — confirmed with a two-wave test where the run correctly stays `ADMITTED` after wave 1.
- **FR-002/FR-003** (scope pre-pass, conflict handling): scope overlap blocks the whole wave before any merge; a real Git conflict blocks only that worker without reverting already-merged siblings in the same call — confirmed HEAD advances by exactly one commit, not zero or two, in the conflict test.
- **FR-004/FR-004b/FR-004c** (ordering, scope-at-declaration, DAG pin): all three confirmed independently, including that the pin write-once guard correctly rejects a Store-injected `DECLARED` wave carrying real members disguised as the bootstrap placeholder.
- **FR-005** (idempotent reuse): both the in-progress-wave reuse and the run-already-`COMPLETE`-via-this-wave reuse path are tested; a `COMPLETE` run queried with any other wave id correctly gets `RUN-NOT-ELIGIBLE`.
- **FR-006** (no auto-resolution): confirmed by omission — the reviewer read every branch of `converge_wave` and found no auto-merge/retry/rewrite path.
- **FR-007** (ship gate scans every admitted run, not a default selection): the strongest test in the suite per the reviewer — two admitted runs, the lexicographically-max one (what a default selection would show) already `COMPLETE`, the other still `ADMITTED` with zero dispatched workers; the gate still blocks and names the right one.
- **FR-008/FR-009** (compatibility, no push/release): a full V2 work item with no Store ships untouched; `grep` confirms no `push`/`fetch`/`pull`/`--force` anywhere in `gauntlet_runs.py`.
- **FR-010/FR-011** (event/status projection): all 5 event names present with a closed envelope; `gauntlet-status` correctly surfaces an open conflict from a *superseded* wave, not just the newest one — exactly ADR-0022's own motivating scenario, exercised end-to-end.
- **FR-012** (admission boundary scope): `gauntlet-converge` goes through the common boundary; `gauntlet-run-abandon` correctly bypasses it by design; the ship gate stays outside it (read-only).
- **FR-013** (version bump): confirmed, 2.8.0 across all 8 surfaces.
- **FR-014** (abandon authorization): every failure mode collapses to `ABANDON-AUTHORIZATION-INVALID`; identity is derived from the target run's own recorded admission — proven with a test that runs a real `git gc --prune=now` to make the run's original base commit genuinely unreachable before confirming abandon still succeeds.

**ADR-0023's 7 `_run_for_worker` call sites** (`declare_wave`, `prepare_worker`, `declare_worker`, `record_progress`, `terminate_worker`, `remediate_node`, `cleanup_worker`) were individually grepped and mapped — each now reads `identity = run["admission"]` immediately after the call, and `_run_for_worker` itself compares only the four planning-identity hashes. `converge_wave`'s own separate, manually-inlined identity check (it can't reuse `_run_for_worker`, which uniformly rejects `BLOCKED`/`COMPLETE` and would break FR-005's replay path) was independently confirmed to have received the same narrowing. The end-to-end regression test (`test_wave_declare_after_a_successful_converge_is_not_identity_stale`) was read and confirmed to exercise the full declare→converge→declare-next-wave flow this fix exists to unblock.

Adversarial probing that specifically tried to break the implementation and did not: crash recovery between the last worker's convergence and the wave/run-completion transaction (self-heals via `max(run["waves"])`, provably always the correct wave); crash recovery between a successful on-disk merge and its Store transaction (self-heals via the is-ancestor trivial-success check, no duplicate merge commit); a `gauntlet-run-abandon` bundle scoped to a foreign run id (rejected at the CLI validation layer, never reaches the Store); the superseded-wave mutation exception (proven scoped to exactly `{last_conflict, converged}`, not `state`/`node_ids`).

### Resolution

No code change required. Two cosmetic nits were logged, neither blocking:

1. `converge_wave` reads `git status --porcelain` twice per call (once directly for `untracked`, once inside `_exact_worktree_is_clean`) instead of the single read plan.md's Convergence §4 describes. No correctness impact — no TOCTOU window opens within one synchronous call — just a redundant subprocess spawn.
2. `tasks.md`'s T017 text names `validate_gauntlet_converge_contract.py` as the landing file for the review-boundary regression test; it actually landed in `validate_checkpoint_contract.py::test_review_blocked_makes_ship_unreachable`. The test exists, passes, and proves the claimed regression — filed in a different (still correct, arguably more correct) validator file than the task text implied.

Both are recorded here as follow-up notes, not filed as BLs — neither changes behavior or requires a decision.

### Critical Issues

None.

### Important Issues

None blocking. The two nits above are the only findings from this round.

### Final Recommendation

**APPROVE.** A single full adversarial review round, run independently (fresh reviewer, no prior involvement in authoring this code), found zero real defects across 14 functional requirements individually verified against the actual code, all 4 ADRs (including ADR-0023's architecturally significant fix, confirmed complete at all 7 call sites), and the CLI contract's exact check ordering. The test suite was confirmed to be real (subprocess-driven CLI, real Git merges/conflicts, a real `git gc` for the abandon base-commit-unreachable case), not mocked, with each spot-checked assertion correlating to an actual requirement. 940 tests total in the full suite, zero regressions, `git diff --check` clean.

This APPROVE is for the **plan-only substantive deliverable** — spec, plan, tasks, implementation, and tests — per this work item's constitution ("Feature e fix permanecem plan-only"). It is not, by itself, ship authorization: `checkpoint --step specify --state complete` remains produced by direct authorship with independent-critic review rather than a genuine `speckit-specify` attestation bundle (recorded honestly, not fabricated), and any commit/merge/push remains a separate, explicit human act — push in particular requires fresh confirmation in this chat regardless of any active `/goal`.

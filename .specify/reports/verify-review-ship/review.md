## Review Report

Verdict: REQUEST-CHANGES
Source fingerprint: 9190ecb4bb48b4324d9a2a94b0c38d8f0823d7e9 (tree 284ea5616d5ba3a3ebc5cba9f8a557c3c8db6d34) / independent read-only review of `git diff origin/main...HEAD` (22 files, +4200/-49), of `specs/012-durable-run-state/{spec,plan,data-model,research,quickstart,tasks}.md` and `contracts/gauntlet-run-cli.md`, of `.specify/memory/constitution.md` and ADR-0003/0005/0006/0010, plus test evidence re-executed by this reviewer on this exact tree (not inherited from `verify.md`).

Reproduced gate evidence (all run by this reviewer at the fingerprint above):

| Command | Result |
|---|---|
| `python3 tests/validate_orchestrator_store_contract.py` | PASS — Ran 85 tests, OK, exit 0 |
| `python3 tests/validate_gauntlet_run_contract.py` | PASS — Ran 23 tests, OK, exit 0 |
| `python3 tests/validate_workspace_contract.py` | PASS — Ran 67 tests, OK (skipped=1), exit 0 |
| `python3 tests/validate_step_skill_registry_contract.py` | PASS — Ran 103 tests, OK, exit 0 |
| `python3 tests/validate_gauntlet_activation_contract.py` | PASS — Ran 43 tests, OK, exit 0 |
| `python3 tests/run_validators.py` | PASS — 18 validators, 803 tests, 1 skip, exit 0 |
| `git diff --check origin/main...HEAD` | PASS — no whitespace errors, exit 0 |
| `python3 tests/check_version_bump.py --base-ref origin/main` | **FAIL — `MISSING-BUMP`, exit 1** |

The last row is the blocking gap. It was not run in `verify.md` and is not covered by `run_validators.py`.

### Test Quality

Strong, and stronger than the phase required. The store suite adds 20 tests that are genuinely adversarial rather than confirmatory:

- `test_wal_recovery_is_deterministic_at_every_receipt_event_anchor_snapshot_and_intent_boundary` injects a fault at all six declared WAL boundaries (`after-intent`, `after-receipt`, `after-event`, `after-anchor`, `after-snapshot`, `after-intent-removal`), asserts the exact published/not-published outcome per boundary, asserts byte identity of `orchestrator.json` when not published, and re-runs recovery to prove idempotency. This is the hardest thing in the diff and it is the best-tested.
- `test_concurrent_receipt_collision_has_one_winner_and_leaves_no_wal_residue` uses a real two-thread barrier and asserts exactly one winner, one `STATE_DIVERGENCE` loser, an empty `locks/` directory, and no WAL residue — then proves the store still accepts the next transition.
- Tamper tests rewrite the pending intent (`test_recovery_rejects_pending_candidate_with_transition_sequence_not_owned_by_semantic_event`, `..._with_illegal_admitted_to_complete_jump`, `..._malformed_pending_wal...`) with a recomputed `content_sha256` so they defeat the cheap hash check and exercise the real correlation logic.
- The run-contract suite asserts negative space, not just verdicts: `assert_no_execution_artifacts`, `store_snapshot`, `root_snapshot` and `worktree_snapshot` comparisons make "no write" an actual byte/tree assertion in the stale, unsafe-grant, forged-evidence, and V2 cases.
- Eight-way concurrency on both admission and resume (`test_eight_concurrent_identical_admissions...`, `..._eligible_resumes...`) covers the reuse-vs-conflict convergence path that the `ADMISSION-CONFLICT` / `RECOVERY-NOT-ELIGIBLE` catch blocks in `gauntlet_runs.py` exist to serve.
- `tests/validate_workspace_contract.py::test_v2_item_rejects_durable_worker_controls_without_workspace_mutation` is the right FR-012 regression: it drives all four new controls at a V2 item and asserts `WORKFLOW-INCOMPATIBLE` plus unchanged HEAD, branch, `status --porcelain`, and `worktree list`.

Gaps worth naming rather than blocking:

- The `CLEANED` success path is only reachable in tests via Store-side fixture seeding, because nothing in FASE-002 can set `converged`/`cleanup_eligible` to `true` (see Important #6). The removal logic is therefore proven against synthetic state, never against state the shipped CLI can produce.
- No test asserts the cost or the file-count sensitivity of the status receipt scan (Important #1).
- No test pins which run `gauntlet-status` selects when several runs exist for one work item (Important #3).

### Runtime Correctness

Scope is clean. I looked specifically for FASE-003/004 leakage and found none:

- The only `subprocess` calls in `gauntlet_runs.py` are `git` (`cat-file -e`, `worktree list/add/remove`, `show-ref`, `status`). No model invocation, no `claude`, no shell.
- No threads, timers, watchdogs, heartbeats, signal handlers, or background processes anywhere in the diff.
- `WAVE_STATES = frozenset({"DECLARED"})` in `store.py` makes wave *progression* structurally unrepresentable, and `WAVE_ID` is the hard-coded constant `"wave-0001"`. Wave selection cannot be expressed, not merely unimplemented.
- No convergence, review, ship, push, publish, or release path is added. `gauntlet-cleanup` and `gauntlet-resume` retain their FASE-001 `SCHEDULING-NOT-AVAILABLE` response for the legacy argument form, so the older control surface did not silently change meaning.
- `record_resume_decision` caps recovery at exactly one (`recovery_count in (0, 1)` enforced in Store validation *and* in the transition edge table `RECOVERY_RECORDED -> {RECOVERY_RECORDED, BLOCKED, COMPLETE}`), matching FR-010's "one recorded decision, no automatic replacement/relaunch/retry" and correctly deferring ADR-0005's 15-minute automatic substitution to FASE-003.

Two behavioural notes:

- `admit_or_reuse_run` calls `store.bootstrap(root)`. FASE-001 activation deliberately had no Store side effect, so `gauntlet-run` is now the first command that can create the project Store. This is a real behaviour change, it is commented in place, and it only happens after the full activation proof — but it is not stated in `plan.md` or `contracts/gauntlet-run-cli.md`, which both describe `gauntlet-run` purely as a record-creating command.
- `_matching_run` requires exact admission equality, and `admission.base_commit` is `git rev-parse HEAD` at the time of the call. Any commit to the repository therefore makes the next `gauntlet-run` create a *new* run rather than reuse. `plan.md` §Scale/Scope explicitly permits multiple retained runs, so this is plan-conformant, but it sits awkwardly against the literal FR-003/SC-001 wording ("without creating a second run") and it interacts badly with the status default-run selection (Important #3).

### Readability

Mostly good, with one real defect and one stylistic pattern that will cost future reviewers.

The defect: `plugin/skills/grill-with-docs/scripts/grill_core/store.py:1437` opens `_recover_pending_transition_locked` with

```python
    if True:  # retains the raw recovery body under one fail-closed wrapper
```

followed by **98 blank lines** (1440–1537 contain only two orphan comments) before the body resumes at line 1538. This is refactor residue — a removed `try:` that was replaced by an always-true guard and never cleaned up. It sits in the single most safety-critical function in the diff, it inflates the function to ~135 lines of which ~100 are empty, and any future reader will reasonably wonder what invariant the `if True:` is protecting. `git diff --check` does not catch it because the lines are genuinely empty.

The pattern: `store.py` and `gauntlet_runs.py` both use dense single-line `if <long condition>: _invalid(...)` and semicolon-joined statements (e.g. `gauntlet_runs.py:798`, `store.py` `_validate_gauntlet_worker`). Several validation lines exceed 300 characters. It is internally consistent and the surrounding file already leans compact, so this is a preference call, not a defect — but the gauntlet validators are the densest code in the module and they are exactly the code a reviewer must read most carefully.

Positives: the comments earn their place. They explain *why* (`# This must run under the same lock as intent creation: otherwise two concurrent calls can both observe an empty name...`, the `ADMISSION-CONFLICT` convergence rationale, the `_workspace_target_absent` note that `git worktree remove` intentionally leaves the branch). Names are honest: `_require_active_lease`, `_workspace_target_absent`, `_verify_coordinator_receipt` all say what they enforce.

### Architecture

The core decision — extend the existing Project Store with a strict optional per-work-item block rather than add a second authority — is right and is implemented as designed. Specifics that hold up:

- `transact_with_event` is a genuine WAL, not an event/snapshot pair. The intent is written and fsynced with the full candidate document before any receipt, event, or anchor exists, and it is removed only after the snapshot is published. `recover_pending_transition` runs before every mutable FASE-002 command and never before read-only status, matching `plan.md` §"Run transition and evidence boundary" exactly.
- The generic write paths (`write_snapshot`, `transact`) call `_validate_gauntlet_state_transitions(...)` **without** `allow_existing_gauntlet_changes`, so any gauntlet mutation through the ordinary Store API is rejected with `STATE_DIVERGENCE`. Only `transact_with_event` passes the flag. This is the load-bearing architectural boundary of the phase and it is enforced in the Store, not in the CLI — correct, and covered by `test_generic_transact_cannot_bypass_existing_run_state_admission_or_evidence`.
- State edges live in the Store (`run_edges`, `worker_edges`), so the durable graph is authoritative regardless of which future caller writes it. `_validate_document` runs before `_validate_gauntlet_state_transitions` on every path, so the edge checker's unguarded subscripting (`new_run["admission"]`, `worker["state"]`) is safe.
- The CLI is a thin adapter. `gauntlet_run_admission` re-proves the FASE-001 activation for every mutable command rather than trusting a prior status call, and it is the only place raw bytes are hashed into the admission identity.

Layering concern: `gauntlet_runs.py` reaches into five Store privates — `store._validate_directory`, `store._validate_regular`, `store._read_regular`, `store._decode`, `store._receipt_payload`. The plan says these helpers are "Store-owned"; in practice the receipt-verification half of the evidence boundary lives in `gauntlet_runs` and borrows Store internals to do it. It works today because both modules ship together, but it means a Store refactor can silently break the evidence boundary without any signature changing.

### Security

This is the dimension the phase exists for, and the coordinator/worker authority split holds. Checked explicitly against ADR-0006 (menor privilégio) and ADR-0010 (Evidence Boundary):

- **Worker cannot obtain Store or receipt authority.** There is no API in the diff that a worker process could call to write coordinator state. Grants are a passive recorded allowlist (`_GRANT_CAPABILITIES = ["git-local", "workspace-read-write"]`), Store validation constrains `grant.capabilities` to a subset of that exact frozenset, and no code path reads a grant to authorise anything. FASE-002 records the boundary; it does not yet enforce a runtime sandbox, which `plan.md` states outright ("Same-UID hostile-process isolation is explicitly out of scope").
- **Receipts are content-bound, not name-trusted.** `_bind_receipt_hash` recomputes the JCS digest of the durable payload and rejects any event whose `receipt_sha256` does not name those exact bytes. `_write_immutable_receipt` refuses to overwrite an existing receipt with different bytes (`STATE_DIVERGENCE`) and re-reads after write. `_verify_coordinator_receipt` refuses to trust a receipt by name at all — it re-reads bytes and requires `raw == jcs(receipt) + b"\n"` plus full correlation equality. Forged and `sha256:`-prefixed digests are rejected without mutation (`test_worker_originated_or_prefixed_digest_evidence_is_rejected_without_mutation`).
- **Worker-scoped evidence is fenced.** `_transition_fields` requires all three of `worker_id`/`lease_id`/`fencing_token` or none, and `_candidate_transition` requires the named lease and positive fencing token to already exist in the candidate document. Evidence naming an unrecorded worker or lease is rejected (`test_worker_evidence_cannot_name_an_unrecorded_worker_or_lease`).
- **Path authority is derived, never supplied.** `_workspace_identity` builds its single target as `store.git_common_dir(root) / "grill" / f"wt-{run_id}-{worker_id}"`, with `work_id`/`run_id`/`worker_id` each validated by `SAFE_NAME_RE` (`^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$`, no `/`, no `.`-only, no `..`). No caller can inject a host path or a ref name. The branch (`grill/<work>/<run>/<worker>`) is likewise derived and re-validated in Store (`startswith("grill/")`, no `..` segment, no control characters).
- **No-follow / symlink handling.** `_workspace_git_state` returns `DIVERGENT` immediately for a symlinked target, before any Git call or removal, and `_workspace_target_absent` treats `is_symlink()` as present. Receipt reads go through `store._validate_regular` / `_read_regular`. Hooks and status remain read-only.
- **Cleanup never scans or guesses.** `cleanup_worker` accepts exactly one validated pair, re-derives the unique target, and requires `TERMINAL` + `clean` + `converged` + `cleanup_eligible` + `EXACT` Git identity. It then re-checks `git status --porcelain` in the exact worktree immediately before `git worktree remove` — i.e. the recorded `clean` predicate is deliberately not trusted as a substitute for live evidence. `test_cleanup_preserves_terminal_eligible_worker_when_exact_worktree_is_untracked_dirty` proves this. Every rejection returns `PRESERVED` with no deletion.
- **Fail-closed on every denial.** `main()` has a catch-all `except Exception` that emits `{"verdict":"BLOCKED","code":"UNEXPECTED-FAILURE"}` at `EXIT_BLOCKED`, so even an unhandled `KeyError` inside a `mutate` closure cannot produce a traceback or an out-of-contract exit code. Tests assert `process.stderr == ""` on the denial paths.
- The `_mutex` change that restores the lock directory's `st_atime_ns`/`st_mtime_ns` is a deliberate forensic-invariance measure so a rejected request is tree-identical; it is best-effort (`except OSError: pass`) and does not weaken locking.

One residual, non-blocking: `_strict_scopes` rejects `..`, absolute paths, backslashes, control characters, and `.git` **as the first segment only**. A scope such as `plugin/.git` or a symlinked scope path is recordable. Harmless in FASE-002 because grants are inert, but this record is what FASE-003 will enforce against.

### Performance

Adequate for the phase, with one growth curve that should be fixed before FASE-003 multiplies transition volume.

`_verify_coordinator_receipt` (`gauntlet_runs.py:243`) resolves the event's bare receipt digest by iterating **every** `*.json` file under `receipts/runtime`, reading each one in full, parsing it, and JCS-hashing it, then requiring exactly one match. Every `gauntlet-status` call pays this. The receipt count grows monotonically — one per run admission, per resume, and per worker `declared`/`preparing`/`prepared`/`cleaning`/`cleaned` transition — and nothing ever prunes it. Status is therefore O(all runtime receipts ever written) in both file opens and bytes read, which contradicts `plan.md` §Technical Context ("Admission, status, resume, preparation, and cleanup use bounded local I/O"). The design reason is sound (a receipt *name* must never be an accepted input), but the fix is cheap: derive the filename from the content digest, or persist the coordinator-owned locator alongside `receipt_sha256` in `last_transition`.

Secondary: `runs` has no cardinality cap (workers are capped at 5 per run by `_validate_gauntlet_block`), and every commit produces a new admission identity, so `orchestrator.json` grows without bound for an actively developed work item. Each growth also re-validates the whole document on every Store read.

Everything else is bounded: one Store transaction per material transition under the existing global lock, no network, no background process, admission retry capped at 3 total attempts.

### Critical Issues

**1. 🔴 Constitution "Bump obrigatório do plugin" — merging or pushing this branch as-is violates it; the gate fails today.**

The diff modifies three files under `plugin/**`:

- `plugin/skills/grill-with-docs/scripts/grill_core/gauntlet_runs.py` (new, 862 lines)
- `plugin/skills/grill-with-docs/scripts/grill_core/store.py` (+461)
- `plugin/skills/grill-with-docs/scripts/grill_workspace.py` (+163/-15)

The declared version is `2.5.4` at HEAD and `2.5.4` at `origin/main` in all four manifests. No distribution surface was touched. Reproduced:

```
$ python3 tests/check_version_bump.py --base-ref origin/main
FAIL MISSING-BUMP: plugin/ mudou sem bump. Versão na base de merge: 2.5.4; versão no HEAD: 2.5.4.
A versão declarada em plugin/.claude-plugin/plugin.json precisa aumentar.
$ echo $?
1
```

This is the exact command `.github/workflows/bump-gate.yml` runs. The constitution says: *"Toda alteração em `plugin/**` MUST incrementar a versão SemVer antes de merge ou push."* Since this review gates a **direct merge and push to `origin/main` with no PR**, the gate will never run in CI — the check exists precisely for this and it fails.

Note that the full validator suite does **not** catch this and neither did `verify.md`. `tests/validate_distribution.py` prints `distribution: OK` because it only checks *internal consistency* of `2.5.4` across the eight surfaces; `tests/validate_bump_gate_contract.py` (44 tests, OK) tests the gate's own logic against fixtures, not this branch. A green `run_validators.py` is not evidence of bump compliance.

`plan.md` §Constitution Check marks this clause `PASS` on the grounds that *"FASE-004 synchronizes every distribution surface to 2.6.0 before any merge, push, tag, or publication."* That deferral is itself the problem: the constitution's "Fail-closed sem waiver" clause states *"não existe waiver implícito"*, and a plan row cannot grant one. Either the bump lands in this commit, or the merge does not happen until FASE-004 lands with it.

**Required before merge/push — pick one:**

- (a) Bump to `2.6.0` in this branch across all eight surfaces named in `CLAUDE.md` (`plugin/.claude-plugin/plugin.json`, `plugin/.codex-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.agents/plugins/marketplace.json`, the `VERSION` constant in `tests/validate_distribution.py`, the `# Grill with Docs vX.Y.Z` heading in `plugin/skills/grill-with-docs/SKILL.md`, the `# Protocolo de sessão vX.Y.Z` heading in `plugin/skills/grill-with-docs/references/session-protocol.md`, and the `**vX.Y.Z` heading in `README.md`), then re-run `tests/validate_distribution.py` and `tests/check_version_bump.py --base-ref origin/main`; **or**
- (b) hold the merge until FASE-004 delivers the synchronized bump, and keep this branch unpushed until then.

Nothing else in this diff blocks. Everything below is a follow-up.

### Important Issues

**1. 🟡 `gauntlet-status` reads and hashes every runtime receipt on every call** — `plugin/skills/grill-with-docs/scripts/grill_core/gauntlet_runs.py:243` (`_verify_coordinator_receipt`).

**Why:** the journal event stores only a bare `receipt_sha256`, so resolving it to bytes requires a full directory scan with a per-file read + parse + JCS hash. Receipts accumulate one per transition forever. Status cost grows linearly with total project history, which contradicts `plan.md`'s "bounded local I/O" constraint for status and will get materially worse once FASE-003 adds per-wave and per-dispatch transitions.

**Suggestion:** keep the "never trust a caller-supplied receipt name" rule, but make the lookup O(1) — either name the receipt file after its content digest, or persist a coordinator-owned locator next to `receipt_sha256` in `last_transition` and still verify the bytes after opening it.

**2. 🟡 Dead `if True:` block with 98 blank lines inside the WAL recovery function** — `plugin/skills/grill-with-docs/scripts/grill_core/store.py:1437-1537`.

**Why:** `_recover_pending_transition_locked` is the function that decides whether an interrupted transition becomes authoritative. Leaving refactor residue (`if True:  # retains the raw recovery body under one fail-closed wrapper` followed by ~100 empty lines) inside it makes the safest-critical code in the diff look unfinished and hides the actual body 100 lines below its signature. `git diff --check` cannot flag it because the lines are truly empty.

**Suggestion:** delete the `if True:` guard, dedent the body, and keep the two explanatory comments adjacent to the code they describe.

**3. 🟡 `gauntlet-status` without `--run-id` picks the lexicographically largest run id** — `plugin/skills/grill-with-docs/scripts/grill_core/gauntlet_runs.py:406` (`run_id = sorted(runs)[-1]`).

**Why:** run ids are `run-<sha256[:24]>` of the admission, so lexicographic order is effectively random. With more than one run for a work item, the default status can project an old `BLOCKED` run while an `ADMITTED` one exists. SC-001 asks an operator to *"identify the affected run and its recovery state from one stable run projection"*; this is stable but arbitrary, which is the wrong property for a diagnosis command.

**Suggestion:** select by the highest `last_transition.event_sequence` (monotonic, coordinator-owned, already validated), or project all runs and let the operator choose. Add a test pinning the selection rule either way.

**4. 🟡 Runs accumulate without bound, and any commit forces a new one** — `gauntlet_runs.py:139` (`_matching_run`) plus `_validate_gauntlet_block` in `store.py`.

**Why:** `base_commit` comes from `git rev-parse HEAD` at admission, and reuse requires exact admission equality, so `gauntlet-run` after any commit creates a second run. Workers are capped at 5 per run but `runs` has no cap, so `orchestrator.json` grows monotonically for an active work item and is fully re-validated on every Store read. `plan.md` permits multiple runs, so this is not a scope violation — but the growth is unmanaged and there is no retention or `COMPLETE`-pruning story.

**Suggestion:** cap `runs` per work item in Store validation (as workers already are), and decide now whether terminal runs are pruned or archived — before FASE-003 makes runs cheap to create.

**5. 🟡 `gauntlet_runs.py` depends on five Store private helpers** — `store._validate_directory`, `store._validate_regular`, `store._read_regular`, `store._decode`, `store._receipt_payload`.

**Why:** `plan.md` places the evidence boundary behind "Store-owned" helpers, but receipt verification is implemented in `gauntlet_runs` using Store internals. Nothing in the type signatures or the test suite would flag a Store refactor that changed `_receipt_payload`'s key ordering or `_read_regular`'s no-follow semantics, yet either would silently alter what the evidence boundary accepts.

**Suggestion:** promote the receipt-verification primitive into `store` as a public function (e.g. `verify_receipt_for_event`) so the boundary is one module's responsibility and its contract is testable in the Store suite.

**6. 🟡 The `CLEANED` path cannot be reached through the public CLI in FASE-002** — `gauntlet_runs.py:811`, `prepare_worker` sets `converged: False` / `cleanup_eligible: False` and no FASE-002 command sets them true.

**Why:** this is the documented phase boundary (`quickstart.md` says so plainly), so it is not a defect. But it means the destructive branch of `cleanup_worker` — the only code in the diff that deletes anything — is exercised solely against state written by test-side Store fixtures, never against state the shipped CLI can produce. There is currently no traceable owner for "who records convergence and eligibility".

**Suggestion:** add an explicit FASE-003/FASE-004 handoff line naming the command that will set `converged`/`cleanup_eligible`, and keep the fixture-seeded cleanup tests as the contract that command must satisfy.

**7. 🟡 Grant scope validation only rejects `.git` at the first path segment** — `gauntlet_runs.py:502` (`pieces[0] == ".git"`).

**Why:** `plugin/.git`, `a/b/.git`, or a scope path that is a symlink to somewhere outside the project are all recordable. Inert in FASE-002 because grants are passive, but this record is exactly what FASE-003 will enforce a worker against, so a permissive record now becomes a permissive sandbox later.

**Suggestion:** reject `.git` at any segment and decide the symlink policy for scope paths in the same commit that starts enforcing grants.

**8. 🟡 `gauntlet-run` now bootstraps the project Store, which is undocumented in the contract** — `gauntlet_runs.py:328` (`store.bootstrap(root)`).

**Why:** FASE-001 activation had no Store side effect by design. `contracts/gauntlet-run-cli.md` describes `gauntlet-run` only as creating or reusing a run record and states it "never creates a worker, worktree, process, dispatch, or skill invocation" — it says nothing about initialising the Store. The behaviour is correct (it runs only after the full activation proof, and the V2 test proves no Store is created for incompatible items) but it is a real side effect that the published contract does not mention.

**Suggestion:** one line in `contracts/gauntlet-run-cli.md` and `quickstart.md` stating that first admission initialises the project Store.

### Final Recommendation

**REQUEST-CHANGES.** The engineering is sound and I would approve it on technical merit alone — the WAL is a genuine write-ahead log with correct recovery at all six fault boundaries, the coordinator/worker authority split is enforced in the Store rather than in the CLI (so it cannot be bypassed by a future caller), path and ref derivation admit no caller-supplied input, cleanup re-verifies live Git state instead of trusting its own recorded predicate, and the scope discipline is exemplary: no scheduler, no worker execution, no convergence, no dispatch, no network. All 803 tests across 18 validators pass on this exact tree, reproduced independently, and `git diff --check` is clean.

The single blocking gap is procedural but non-negotiable: **`plugin/**` changed and the SemVer version did not.** `python3 tests/check_version_bump.py --base-ref origin/main` fails with `MISSING-BUMP` right now, and this review gates a direct merge and push to `origin/main` with no PR — meaning CI will never catch it. `plan.md` defers the bump to FASE-004, but the constitution's "Fail-closed sem waiver" clause forbids exactly that kind of implicit waiver, and its bump clause says "antes de merge ou push", not "antes de publicação".

**To convert this to APPROVE, one of:**

1. Bump to `2.6.0` in this branch across all eight surfaces listed in `CLAUDE.md`, then re-run `python3 tests/validate_distribution.py`, `python3 tests/check_version_bump.py --base-ref origin/main`, and `python3 tests/run_validators.py`, and record the three results here; **or**
2. Hold the merge (and the push) until FASE-004 delivers the synchronized bump in the same push.

Important issues 1–8 are follow-ups and none of them should hold the merge once the bump lands. I would prioritise #2 (dead block in the recovery function — trivial, and it is in the code future readers most need to trust) and #1 (status receipt scan — cheap now, expensive to retrofit after FASE-003 multiplies transition volume).

## Review Report

Verdict: APPROVE
Source fingerprint: `09321dfdb96905872f82e20159905236ab662147a2ee2759fe9f69a8f91b847f` (matches `verify.md`'s fingerprint above — same tree, no change between verify and this review)

This is a synthesis of three independent, adversarial code-review rounds run against this tree during this session (none of them the same session that wrote the code they reviewed), not a fourth freestanding pass. Full findings and reproduction detail live in the session transcript and are summarized in `verify.md`'s Converge section; this report records the final disposition.

### Round 1 — implementation review (verdict at the time: BLOCKED)

Found six real defects (B1-B6), all in coordinator-authority code (Store schema, worker lease/grant lifecycle): a remediation replacement worker could never record progress or terminate (B1); the worker it replaced was never freed from `PREPARED`, permanently leaking a cap slot and blocking dependents (B2); `gauntlet-worker-declare` never applied FR-004's DAG-scope rejection to its own `--files` (B3); it never checked wave membership or dependency readiness either (B4); a wave could reach `COMPLETE` while a declared member had no worker yet (B5, root cause of B1/B2); the Store never enforced FR-008(e)'s shared remediation budget across workers (B6). Each was reproduced with real probe scripts against the shipped code, not inferred from reading alone.

### Round 2 — re-verification of B1-B6, discovery of F1-F4 (verdict at the time: BLOCKED)

Independently re-derived and reproduced all six B1-B6 fixes as genuinely correct. Found four more real defects the first round's scope didn't cover: `gauntlet-prepare-worker` (the existing FASE-001/002 command, untouched by the B3 fix) had the identical scope-bypass (F1); `gauntlet-remediate` never checked the effective concurrent cap before minting (F2); the Store's budget-lineage check only saw already-committed workers, so two remediation-shaped records added in one transaction both passed (F3); an injected out-of-sequence wave id could permanently wedge a run (F4). F1 was explicitly flagged as needing an operator decision rather than a unilateral fix, since it changes an existing FASE-002 command's behavior (FR-015 tension). The operator decided: close it globally, unconditionally, in every grant-minting command — recorded in `DECISION-BACKLOG.md` BL-0002.

### Round 3 — final confirmation (verdict at the time: REQUEST-CHANGES)

Independently re-derived and reproduced all four F1-F4 fixes as correct, and re-confirmed no regression to B1-B6 under combined stress (e.g. remediating into an already-superseded wave while a newer wave exists). Found no further code defect. Blocked only on the evidence package itself: `quickstart.md`, `contracts/gauntlet-scheduler-cli.md`, and `verify.md` had not been re-synchronized after the B5 fix reverted the wave schema back to persisting `node_ids` — they still described the abandoned journal-scan design, one doc used that false premise as the normative justification for a `WAVE-REUSED` behavior, and three gate rows understated their real test counts (98/43/859 vs. the actual 106/53/877 after the F1-F4 tests landed). The reviewer's own stated resolution: correct the three documents, no code change required, and the verdict becomes APPROVE.

### Resolution

`quickstart.md` and `contracts/gauntlet-scheduler-cli.md` were corrected to state the true shipped schema (`node_ids` is a required, immutable-once-set wave field) and to document `gauntlet-prepare-worker`'s `GRANT-OUT-OF-SCOPE` behavior change. `verify.md` was rewritten with the real, freshly-reproduced gate counts (106/53/23/43/103/877) and an accurate Converge narrative covering all three rounds. `CLAUDE.md`'s stale test-count line was updated. No production code changed in this pass. All corrections verified by direct grep against the corrected files (no residual `_wave_node_ids`/"does not persist" claims; `GRANT-OUT-OF-SCOPE` present in all three FASE-003 docs; no stale count strings remain).

### Critical Issues

None.

### Important Issues

None blocking. Three items were explicitly named as legitimate follow-up backlog, not merge blockers, and are not yet filed as BLs — recommended for FASE-004 or a dedicated follow-up: (1) the Store's raw-bypass threat model still allows laundering an existing worker's `remediates`/`recovery_count` back to a fresh state via a direct `transact_with_event` call, undercutting the budget guarantee's own stated "independent of what `remediates` claims"; (2) a brand-new run's `waves` map isn't validated by the same sequencing rule F4 added for an existing run; (3) `gauntlet-remediate` enforces only the activation-configured half of FR-005's effective cap (no `--dag`, so it can't also honor a DAG's lower `max_workers`), while `gauntlet-wave-declare` enforces both halves — the two commands can disagree on the same run's effective cap.

### Final Recommendation

**APPROVE.** Ten real defects were found across two full adversarial rounds and a confirmation pass, all in coordinator-authority code where a bug is a security/correctness boundary failure — every one is fixed, independently reproduced as fixed, and covered by a regression test. The evidence package now accurately describes the shipped code. 877 tests, zero regressions, `git diff --check` clean.

This APPROVE is for the **plan-only substantive deliverable** — spec, plan, tasks, implementation, and tests — per this work item's constitution ("Feature e fix permanecem plan-only"). It is not, by itself, ship authorization: `checkpoint --step specify --state complete` remains unreachable this session (no genuine `speckit-specify` attestation bundle was produced, honestly recorded rather than fabricated), and any commit/merge/push remains a separate, explicit human act.

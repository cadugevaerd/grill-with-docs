# Same-context presentation refresh — 6.0.22

Worktree: `/home/carlosaraujo/orca/workspaces/grill-with-docs/fix-mixed-run-import`.
Base: `02db2e6` (6.0.21); task `task_08a02c621177`, dispatch `ctx_5b8720f6d73e`.
Direct correction/publication authorization is in the dispatch. No hermes-k3s access or mutation was performed.

## Diagnosis

Root cause proven in an isolated Store: an ACTIVE canonical leader at epoch 16, with completed historical workers and mixed-run task imports, cannot refresh its presentation after a GWD/configuration upgrade. The regression models the reported Hermès 6.0.20 → 6.0.21 transition by changing the temporary GWD heading and observed configuration digest, then obtaining a new correlated load request and full read. It retains the same leader observation, session identity, runtime, scope and policy. Before the correction the final admission raises `STYLE-SCOPE-CONFLICT: presentation configuration changed; bootstrap again`, despite fresh `work_ready=true` and `use_ready=true`.

`_gauntlet_authorized` compared configuration and GWD skill hashes as immutable authority fields. Those hashes intentionally change during an upgrade. `_session_readiness` had already validated current installation, enablement, trust, approved content and the full-read event against the new hashes; the later equality check nevertheless rejected them. Repeating bootstrap could never repair the recorded-context equality.

All production applications of `_gauntlet_authorized` were inspected before editing: run admission and scheduler resume; cleanup and constitution reseal; worker preparation, declaration, progress, termination and remediation; wave declaration and convergence; run abandonment; partition emission, task import/reconcile/migration; step entry, preview/decision and activity; attest, checkpoint and phase turn. They share this boundary. Read-only previews, administrative recovery and the narrowly scoped released-leader abandonment exception retain their existing behavior.

## Correction

The shared guard validates fresh presentation with the existing contract validator, keeps session identity, runtime, GWD scope and policy immutable, and permits refreshed configuration/GWD hashes only with `use_ready=true`. Native authority checks and the existing full-context CAS still run before admission. The existing Store transaction updates only the active context's presentation plus normal revision/hash/journal/current-worktree-receipt bookkeeping. It appends a commit anchor; it does not rewrite history or migrate context, run, DAG, tasks or accepted/import/execution receipts. Repeating the same observation performs no write.

This is structural evidence, not cryptographic provenance or proof of behavioral compliance. Configuration approval is supplied by the existing runtime observations and policy checks; the guard does not infer a human authorization from a changed hash. A same-session presentation suspension remains supported for unchanged configuration/version; refreshing changed hashes requires active fresh loading.

## Regression

The new check reuses the existing mixed-run fixture, real Git history, accepted import receipts and Store. It verifies old loading refuses before mutation, fresh loading succeeds, epoch/context and every other semantic field stay unchanged, historical journal records remain an exact prefix, and historical files/receipts remain byte-identical. Only the ordinary current Store projections may change. An actual public `gauntlet-step-enter` succeeds with the same context after refresh, and replay is byte-identical.

Negative controls reject changed session identity, runtime, work item/root scope, policy, authority arguments, revoked dispatch, stale loading, false work/use readiness, disabled/untrusted/incompatible presentation, suspended refresh and a concurrent context mutation. They preserve the Store footprint and never enter the handler. The existing all-entry contract now tests configuration changes without a fresh read as `STYLE-LOAD-UNCONFIRMED`.

Pre-patch RED: `/tmp/gwd-6022-red.log`, exact `STYLE-SCOPE-CONFLICT` at the positive admission. Focused regression: one test PASS. Orchestration contract: 42 tests PASS. Distribution assertions and `git diff --check` PASS. The complete validator run and immutable source manifest are recorded in `/home/carlosaraujo/.local/state/grill-with-docs/releases/6.0.22/`; final results are appended before publication.

## Bootstrap and rollback

The installed 6.0.21 skill was selected. Native plugin listing, runtime config enablement/trust, approved reference and full read were correlated to this dispatch. Preflight returned `work_ready=true`, `use_ready=true`, `functional_verified=false`; loading event `orca:ctx_5b8720f6d73e:ctco_01a0cbb7-311d-7400-8804-49c5d8c760bb`. No upstream cache was edited.

Rollback is a new patch release reverting the guard change; published tags and historical receipts remain immutable. Prior Codex caches are retained and checked by per-file hashes. Native installation and remote refs are recorded in the external release evidence directory after publication.

## Focused evidence hashes

- RED log: `b89673bb86d5f6282e6a5746c61290cec585fe5299da8abfbcf1d2c583a6a31f`.
- One regression PASS: `39dfe2b15a69ad19d5805e791abc1215aaef44d135db2b640d76a3edc409ea8b`.
- Orchestration (42 tests): `270997fddc87c430163748724d605690c8f029fc24cbe9556ec13ea17cf3fe0a`.
- Mixed-run imports (21 tests): `ec936d7ee0b5029abf46f8da2c8fbf2b7b8403bf79abdedcda20dd7ff7856377`.

The required initial `python3 tests/run_validators.py` started before edits and overlapped subsequent changes. It is not claimed as a frozen baseline or release validation. The separate complete run uses the frozen 154-file plugin/test manifest and is the release gate.

## Independent technical review

Orca reviewer `ctx_9b02953e3b26`, identified by the coordinator as `gpt-6-astra/high`, reviewed the 23 consumers, negative controls, CAS and epoch-16/import preservation in a separate read-only session. The coordinator relayed GO with no findings in message `msg_f73ea31545c9`; the exact delivery is preserved as `review.json` in the release evidence directory. The reviewer encountered `LEADER-ADAPTER-UNSUPPORTED` and did not prove `work_ready`; this is an independent technical review, not a claim of that session's GWD bootstrap compliance. The coordinator explicitly authorized completing publication under the existing direct authorization once the full suite passes.

## Final full validation

`PYTHONDONTWRITEBYTECODE=1 python3 -B tests/run_validators.py`: exit 0, 31 validators, 30 unittest suites, 1509 cases, one expected platform skip; 1304.431 seconds summed unittest runtime. All 154 plugin/test files match the before/after manifest exactly. Full log SHA-256: `238a8915ca112279e751b2c8e6b5e86b928e51a13a1b6f2dc3eaf856ece2fd86`. No product/test change followed the independent review or this frozen run.

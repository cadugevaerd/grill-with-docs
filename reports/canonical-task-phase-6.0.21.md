# Canonical task phase identity — 6.0.21

Worktree: `/home/carlosaraujo/orca/workspaces/grill-with-docs/fix-mixed-run-import`.
Base: `da4db8a30a039a660c66d857abd2b5c49accb6e0` (6.0.20).
Task: `task_9265cd5d2974`; dispatch: `ctx_64c1ba63651e`.
Scope: the scheduler adapter, its existing mixed-run validator, eight distribution version surfaces and release documentation. Direct implementation/publication authorization is in this dispatch; no hermes-k3s access or mutation was performed.

## Diagnosis

Root cause proven by the isolated public wave-handler regression: a T010 activity with the canonical hash returned by `validate_execution_dag` is ignored by `_scheduler_accepted_tasks`, producing `TASK-PHASE-PENDING:T010`. `_task_phase_documents` passed SHA-256 of serialized DAG bytes into the canonical-content parameter of `task_phase_barrier`. Both ordinary JSON and differently indented/key-sorted JSON reproduced the error. A raw-byte activity binding was incorrectly accepted by 6.0.20; the negative control now rejects it.

The direct production caller of `gauntlet_runs.task_phase_barrier` is `_require_scheduler_task_phase`. Its callers are `gauntlet-wave-declare`, `gauntlet-worker-declare`, `gauntlet-prepare-worker` and `gauntlet-remediate`. Explicit DAG paths, revision paths and discovery through an existing run pin share `_task_phase_documents`. Core wave validation and the transaction-time DAG pin check already use `store.jcs_sha256`; they require no change. The separate orchestration and attestation barrier helpers consume supplied guards/bindings and do not hash files.

## Correction and compatibility

All document resolver branches now return `store.jcs_sha256(dag)`, exactly as DAG validation and scheduler pins do. No fallback accepts a raw activity hash. Semantically different DAG content leaves the task pending; missing evidence and existing fail-closed checks remain unchanged.

6.0.20 mixed-run import receipts contain both `dag_sha256` (raw evidence bytes) and `dag_content_sha256` (canonical identity), but their per-task bindings historically use the raw digest. The unchanged `verified_task_import` first revalidates the entire immutable receipt, original source lifecycle, integrated sidecar bytes and original DAG evidence. Only then does the scheduler copy those accepted records into a canonical in-memory projection. The serialized producer and reader remain unchanged, so old receipts stay valid without supersession, migration or history edits. A separately formatted, canonically identical scheduling DAG is accepted; editing the original byte-fenced imported evidence still produces `TASK-IMPORT-DIVERGENT`.

## Regression evidence

`tests/validate_task_import_contract.py` now has 20 tests. Its canonical-activity test exercises the actual DAG validator, wave handler and Store wave activation; the native session/admission and accepted-activity observation use the existing offline seams. It verifies original and reformatted JSON release a wave, pinned-DAG discovery succeeds without `--dag`, divergent content and raw activity bindings reject before Store mutation, and the activity remains unchanged. The import regression creates real mixed-run receipts with 6.0.20 serialization, projects their bindings, declares a wave through a revision DAG copy, proves the original receipt unchanged, and rejects altered original evidence without writes. Existing transactional races, reconciliation and import replay checks remain passing.

Pre-patch regression: two expected `TASK-PHASE-PENDING:T010` errors and one expected missing-refusal assertion for the raw-hash control. This RED result proves sensitivity and is not counted as a passing product test.

Focused command: `PYTHONDONTWRITEBYTECODE=1 python3 -B tests/validate_task_import_contract.py`; exit 0, 20 tests, 42.670 seconds. Distribution assertions and `git diff --check` passed. Final complete-suite and publication evidence are recorded below when available.

## Bootstrap

Installed GWD 6.0.20 was selected before changes. Runtime-correlated installation, enablement and trust were observed separately, followed by a full approved-reference read, event `orca:ctx_64c1ba63651e:ctco_01a0cb91-941d-7ee1-a413-1d189098b1dc`. Revalidation: `work_ready=true`, `use_ready=true`, `functional_verified=false`. No upstream cache or unrelated configuration was changed during bootstrap.

## Rollback

Retain installed 6.0.20 and earlier caches. A code rollback must be a new patch release reverting this change; never rewrite v6.0.21 or historical accepted/import receipts. No persistent data schema changes were introduced.

## Evidence hashes

- `/tmp/gwd-6021-focused.log`: `562e339325401dcd1a052ffd624f2a41a6df2ae893b96e4cf25a13d261e0371c`.
- `/tmp/gwd-6021-red.log`: `cb1a5c498e6a70c7956f77be46e92154d34901fbdb14b215ad294451058bb33a`.
- `/tmp/gwd-6021-bootstrap-ready.json`: `ac4e85190d5e9b068f48fd6cb02db36946b1960d9bb4760031e8ebe7165d6d8c`.
- `/tmp/gwd-6021-source-before.json`: `b2c6fcab5cc91dff3371c6845bb3a8b34831af96f9ad3c6ae0609aa25612422c`.

## Independent review

The Orca coordinator reviewed the concrete diff in a separate session and replied through this dispatch's blocking question: shared resolver/projection changes are centralized, 6.0.20 evidence remains immutable, only the validated projection is canonicalized, and `git diff --check` is clean. Review approved continuation through complete-suite validation and the already authorized release. The implementation was not changed after that review.

The exact checked-in two new test methods were then run with only the two changed CLI functions replaced in-process by their source from `da4db8a`. Result: three expected canonical-consumer errors and one expected missing-refusal assertion, with no product files changed; the sensitivity driver exits 0 only for that exact RED result.

Sensitivity log SHA-256: `a44e5fe2c07a8e7ddfd01efc1a994e809b8ef75b7633ef9f3b00ab5e86677c0c`.

## Initial-run limitation

The required initial `python3 tests/run_validators.py` was launched before product edits. It overlapped the subsequent version change and stopped in `GauntletConvergeContractHarness.test_converge_tolerates_untracked_paths_no_worker_touches` with `STYLE-SCOPE-CONFLICT: presentation configuration changed; bootstrap again`; the presentation fence includes `gwd_skill_sha256`. That run is not claimed as baseline PASS or release validation. The named test then passed against the frozen candidate (1 test, 4.767 seconds; `/tmp/gwd-6021-initial-failure-recheck.log`). The separately started full run hashes all plugin/test files before and after execution and is the release gate.

## Final full validation

`PYTHONDONTWRITEBYTECODE=1 python3 -B tests/run_validators.py`: exit 0; 31 validators, 30 unittest suites, 1,508 cases, one expected Linux platform skip. Summed unittest runtime: 1528.847 seconds. All 154 plugin/test files remained byte-identical between the before/after manifests. Full log SHA-256: `99a0310cd329297070f74b4347c50ed396bebb4d5e06aba56a9436abb754400d`.

The durable release evidence directory is `/home/carlosaraujo/.local/state/grill-with-docs/releases/6.0.21/`. Its final `report.md` and JSON observations record exact commit/remote/tag refs, publication pipeline, native Codex installation, distribution hashes, cache retention and clean release trees after shipping.

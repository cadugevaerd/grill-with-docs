# Mixed-run task import — 6.0.20

Base: `origin/main`, commit `94fabcd32769d6509d77b04a2315d08f0cb1acf7`.
Worktree: `fix-mixed-run-import`.
Dispatch: `ctx_9f5f75ce8b95`; task: `task_58cf480b21c1`.

## Root cause and change

The previous reconcile accepted a single scheduler run, while readiness required predecessor workers in that same run. Proven sidecars from multiple historical runs therefore could not release a successor without replay or direct Store edits.

`gauntlet-tasks-import` imports one explicit, immutable batch into an admitted successor with no dispatch. The batch identifies each task's source run, groups complete nodes, checks the sealed v2 DAG and current task fingerprint/phase, derives the current attempt from worker lineage, verifies positive terminal/convergence/cleanup receipts against the journal, and binds committed sidecar bytes to their hashes. A Store transaction writes the successor's import and DAG pin with an immutable runtime receipt; preview/apply uses the complete input hash, CAS and the existing WAL. Retry reuses accepted work; the public apply recovers only its matching pending import, with leader authority reobserved on adopted work items.

Reconcile, task phase acceptance, scheduler dependency readiness, convergence and status share the imported evidence. Imported nodes cannot be dispatched again. No historical DAG, run, sidecar, receipt, worktree or worker is rewritten or synthesized.

## Public operation

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B plugin/skills/grill-with-docs/scripts/grill_workspace.py \
  gauntlet-tasks-import ROOT --work-id WORK_ID --run-id SUCCESSOR \
  --dag specs/FEATURE/execution-dag.r3.json \
  --source-task T007=SOURCE_A --source-task T008=SOURCE_A --source-task T009=SOURCE_B \
  --session-ref SESSION
```

Inspect the preview, then repeat the exact arguments with `--apply --expected-sha256 HASH`. Reconcile with `gauntlet-tasks-reconcile ROOT --work-id WORK_ID --run-id SUCCESSOR --dag DAG`, adding `--apply` only to mark checkboxes. Read-only/deferred activities retain their own acceptance requirements.

## Evidence and limits

The source diagnostic is `continuity-epoch15-mixed-run-blocked-20260922.md` in the supplied hermes-k3s work item. That repository was read only; no command applied an import there. The corresponding live sidecars were present in Git HEAD with the diagnostic hashes:

- T007: `2cde11fe5ec5bd8615bf66da3f7fc359edae6981b973fd2cef25c2acab49ff17`.
- T008: `7c78d1c917ec7b2a0477ceebacaf6b5352ae21ee0e6f492faf572a8cb037a090`.
- T009: `6bf268c8c72098c396bd476157fcfb9aacf83fa159f0225245ee25c1191ac045`.

Old scheduler receipts did not seal sidecar hashes. The import binds their proven successful lifecycle to the task/run/attempt asserted in already committed result bytes, then seals that structural association. It does not claim cryptographic proof of execution. Imports require the same DAG v2 across source runs and successor, full nodes from one source each, confirmed cleanup and a single batch before successor dispatch.

The selected installed GWD 6.0.19 preflight observed installation, enablement, trust and a full reference read in this dispatch: `work_ready=true`, `use_ready=true`, `functional_verified=false`; full-read event `orca:ctx_9f5f75ce8b95:ctco_01a0caa4-2f7a-7e22-a782-2068ac883e0f`; revalidated after compaction with full-read event `orca:ctx_9f5f75ce8b95:ctco_01a0cac7-ce40-7000-933d-897c107eb786`. No cache, configuration, publication, tag, merge or hermes-k3s state was changed.

## Validation at 68034c2 (before the P1 correction)

- `PYTHONDONTWRITEBYTECODE=1 python3 -B tests/run_validators.py`: exit 0; all 31 validators completed, including 1495 unittest cases across 30 suites and the distribution assertions. One platform skip: `test_reject_symlink_chain_accepts_macos_var_root_alias` because Linux has no `/var -> /private/var` alias.
- `PYTHONDONTWRITEBYTECODE=1 python3 -B tests/validate_task_import_contract.py`: 7 tests passed, covering public mixed-source preview/apply, unchanged history, reconciliation/barrier/readiness, replay after successor progress, CAS, mismatched/tampered/missing evidence, symlinks and interrupted WAL recovery.
- The adopted-work-item entry-guard regression passed; the new command remains subject to current leader authority and presentation requirements. All 111 step-skill registry tests passed after adding the public import to the explicit approved handler set; the production resolver allowlist was not widened.
- The final full run used frozen source bytes: SHA-256 comparison confirmed all 154 plugin/test files unchanged throughout execution. Final `git diff --check` passed; staged diff hygiene is checked before the delivery commit. No bytecode compilation, network dependency, cache installation or external publication was used.

Full-run log SHA-256: `0f9c816b518f9954657d9566911f828e51514cf33dc3054f129248ce2811d717`. Frozen source manifest SHA-256: `d6373e266397ac7ec97dbb8b7d06317ea56040ac527b87c58dbdb2b87f16cb6a`. Temporary execution logs and the manifest are removed before commit; the delivered source hashes and fixture receipt hashes below remain in this report.

## Delivered file SHA-256 at dd8290a (historical)

- `.agents/plugins/marketplace.json`: `5b3342917911703015a2be50862a84e49b4eb2fd713f588640057a7460b31e25`.
- `.claude-plugin/marketplace.json`: `6f189dabb3786da1680e5eea2fdfe5fa6b674d45a12192f56be2ac6a3773ff4b`.
- `CHANGELOG.md`: `650a9efabc2ec2750ce9623d068907219ec468ac5805608d49d972ce04123091`.
- `README.md`: `f6a200984d65bac8aa8d0cccee1e92967a07f7609c5beb6ff0aff397060761b1`.
- `plugin/.claude-plugin/plugin.json`: `2202e2c97dc483e4987d96e30b4826f814be4683c588dc5069f267f0828d9bcb`.
- `plugin/.codex-plugin/plugin.json`: `ad934ca65d17252fd8df930e29da7e998d0eaafb747992bd72cf3bbae3894e44`.
- `plugin/skills/grill-with-docs/SKILL.md`: `9a820008297259b808d6c52ae8fa54bb9e6dacbea9b150aac79bf412e7677ac2`.
- `plugin/skills/grill-with-docs/references/session-protocol.md`: `88efaefb053e5d07fc21b04015d5df9ba98c49b56e6831708298964baf333ebe`.
- `plugin/skills/grill-with-docs/scripts/grill_core/gauntlet_runs.py`: `27afa8e7b9aef8b7382601e6539f41b934a741d8dd0a8f9125ef1345ebc1c38d`.
- `plugin/skills/grill-with-docs/scripts/grill_core/store.py`: `e17c165dc6f4008058983fd538b46c2873c338bfd624cfa52a52cbcd627fd360`.
- `plugin/skills/grill-with-docs/scripts/grill_workspace.py`: `77aa14ab70e44bc2610f111a0fa8208e9e47e217cff586df9d2c6232b387a6a4`.
- `tests/validate_agent_orchestration_contract.py`: `418b7491d4bd7ceab14585e16effc2b7245ce6659bf94825e7d52c70e6442124`.
- `tests/validate_distribution.py`: `fcd065448071f2f672bdd0efd86d4dbc5d665894e86506d4124eff6d24cedaf6`.
- `tests/validate_task_import_contract.py`: `1f31a72463aabfa8360aaa38f4134aa86af69c57bd3c4ea54d084f30070afa4b`.
- `tests/validate_step_skill_registry_contract.py`: `572f996a4beb975187291978100f973e73df7ee75e569bd51371cea78950be60`.

## Isolated public CLI reproduction

Git, Store, worker lifecycle and receipts are real in the offline fixture; activation/work-item admission uses the test seam; adopted-session authority is covered by the separate entry-guard regression. No historical task was dispatched during import.

```json
{
  "apply": "APPLIED",
  "barrier_pending": [],
  "expected_sha256": "679a399d5c85d4b697edc0e220fc053c76df35e2ca5440974eb121819b54107b",
  "historical_sha256_after": "2287a0c9d33323d4955f7651573bfb3957eb0642dd867474fcecdd88c8085107",
  "historical_sha256_before": "2287a0c9d33323d4955f7651573bfb3957eb0642dd867474fcecdd88c8085107",
  "imported_tasks": {
    "T007": {
      "attempt_id": "attempt-1",
      "node_id": "p03-a",
      "result_sha256": "d19ce1233c019187d159a66c05a4b2a6a0456b97af77c4c7fba4f983da9738a2",
      "source_run_id": "run-15c2b5c2205f120b556a506c"
    },
    "T008": {
      "attempt_id": "attempt-1",
      "node_id": "p03-a",
      "result_sha256": "5e8b27052d356598b99729fba3a76fce9d51bc31fec73ab683ecd79ad419f030",
      "source_run_id": "run-15c2b5c2205f120b556a506c"
    },
    "T009": {
      "attempt_id": "attempt-1",
      "node_id": "p03-b",
      "result_sha256": "4cd883afeb08d0a160d6fc9941a67ba8363e6a87fe66bac8d0f11407533ed8b6",
      "source_run_id": "run-11c5e62938007816907c4d52"
    }
  },
  "preview": "PREVIEW",
  "receipt_sha256": "a65632bb3912c8bcdd9aad8af4c0decd680d2d488450a8bebdc3b44cacdcf2e1",
  "reconcile_marked": [
    "T007",
    "T008",
    "T009"
  ],
  "retry": "REUSED",
  "successor_workers": {}
}
```

## P1 correction — transactional exclusion

Follow-up dispatch `ctx_851a3fb22bdc`, task `task_21d2fb7215c2`, on the same branch after `68034c2f1706682c10ee490732f96e958d5d403a`. The independent review in `/tmp/gwd-review-68034c2-report.md` reproduced an import committing after a local writer's preliminary guard but before its declaration transaction. Both operations could report success and leave an imported node with a local worker or wave.

`prepare_worker` now rechecks the resolved node inside its declaration mutator, and `declare_wave` rechecks every requested node inside `activate`. These mutators run under the same existing Store transaction lock as the import, before any receipt, worker intent, grant, worktree or wave is written. If local execution commits first, the import CAS rejects the stale snapshot; the import also rechecks successor eligibility inside its own mutator. No extra lock or Store schema change was introduced.

`verified_task_import` rejects any overlap with local worker node IDs or wave members as `TASK-IMPORT-DIVERGENT`, including persisted conflicting state accepted by the previous implementation. This shared reader protects import retry, reconcile, status and scheduler consumers while allowing local execution of the remaining, disjoint nodes.

Five new tests exercise both deterministic interleavings for import/worker and import/wave, plus legacy worker/wave conflicts. Thread events pause the losing operation immediately before its real Store transaction; the winning operation completes before release. Rejected operations leave durable files, receipts, journal, Git refs and registered worktrees unchanged. Legacy fixtures use real Store transitions and verify refusal by import preview/apply, reconcile apply, status and wave readiness without writes.

Validation of the correction:

- `PYTHONDONTWRITEBYTECODE=1 python3 -B tests/validate_task_import_contract.py`: exit 0, 12 tests, 26.759 s. Log `/tmp/gwd-p1-focused.log`, SHA-256 `0abdff15169d48afa30b464eef32d4974171f592733302419f7f7ad7ebb20391`.
- Original reproduction `/tmp/gwd-review-68034c2-race.py`: before the fix, exit 0 with `APPLIED` plus `WORKER-PREPARED`; after the fix, expected exit 1 at the new transactional guard with `GauntletRunError: node was already accepted: p03-a` (`TASK-ALREADY-IMPORTED`). The reproduction still asserts the old broken outcome, so its new nonzero exit is expected; the passing regression tests assert the repaired behavior and absence of local effects. Before/after logs: `/tmp/gwd-p1-race-before.log` (`1573951add24bd0b7ccf2f69a8471aa8b77e90daac3d620c5f341534f479d1cb`) and `/tmp/gwd-p1-race-after.log` (`96ccd840ce026079eb0dabbbf22ba29e22106fb95d2b6f5ed5c2cbfab4989b77`).
- Regression sensitivity against the original `68034c2` module, loaded only into the temporary test process: both import-first races and both legacy conflicts fail with `GauntletRunError not raised`; the two local-first races pass. Five test methods, four expected assertion failures, 8.721 s. Log `/tmp/gwd-p1-regression-original-verified.log`, SHA-256 `d13df77552670ac6766b3c12c517711c592ac1e4ce700b12eebeef7ce982e3e7`.
- `PYTHONDONTWRITEBYTECODE=1 python3 -B tests/run_validators.py`: exit 0; all 31 validators completed, 30 unittest suites, 1,500 cases, one Linux platform skip (`test_reject_symlink_chain_accepts_macos_var_root_alias`). Summed unittest runtime: 1,750.657 s. Final log `/tmp/gwd-p1-full.log`, SHA-256 `0e01fdd68ab485c0f6d06dbf3db1a718065f34c1fe77f0db6551703d14dda3eb`.
- All 58 Python source/test files remained byte-identical throughout the final full run; manifest `/tmp/gwd-p1-source-manifest.json`, SHA-256 `130a30096dfeddd0e68c38c3b21bfdebe07b908cd5431643f480727e38fced23`. All 15 delivered-file hashes above were reverified. `git diff --check` passed before the follow-up commit.

The installed GWD 6.0.19 bootstrap was reobserved for this dispatch: installation, enablement and trust confirmed; approved reference read in full, event `orca:ctx_851a3fb22bdc:ctco_01a0cb0a-da65-7e52-9b47-dc94639d2818`; `work_ready=true`, `use_ready=true`, `functional_verified=false`. Version remains 6.0.20 as requested; existing public documentation and distribution pins are unchanged. Temporary logs and scripts remain outside the worktree; no install, publication, merge, tag, push or hermes-k3s mutation was performed.

## P2 correction — current run and DAG contract under the Store lock

Follow-up dispatch `ctx_b5c920c63258`, task `task_f9b1674d7a6f`, after `dd8290a817e9030a97bbeff02d829a2e91b5b28e`. The final independent review in `/tmp/gwd-final-review-report.md` reported two additional P2 races. Both original reproductions were read in full and reproduced unchanged before the patch: an alternate-DAG wave became ACTIVE after the import pinned the canonical DAG, and a generic prepare left a DECLARED worker plus receipt/journal changes after a total import completed the run.

The existing `_run_for_worker` guard now also accepts the transaction's current candidate, so both declaration mutators reuse the same admission, run-state and imported-evidence validation before the Store writes its WAL. `activate` rechecks the current DAG pin, rereads the requested DAG's content digest, verifies imported-node exclusion and dependency readiness, requires the unchanged placeholder/wave allocation, and recomputes worker occupancy against the effective cap. The worker declaration rechecks the current run and imported-node exclusion and rejects a pin changed since preparation began. A generic prepare has no DAG argument; a newly pinned DAG therefore requires a fresh invocation of its public guards rather than inheriting the stale unpinned decision.

All original preliminary checks remain, preserving their sequential refusal order. The existing Store lock is reused; the guards do not acquire a work lock or recursively acquire the Store lock, create resources, or persist anything. Public flags, serialized schemas, successful sequential behavior and version 6.0.20 remain unchanged.

Sibling audit: the only local mint paths that can race an undispatched successor import are wave activation and a new worker declaration. `declare_worker` reaches the latter through `prepare_worker`; its active-wave prerequisite also excludes a successful simultaneous import. Remediation, lease repair, preparation/finalization of an existing worker, progress, termination, convergence and cleanup require a preexisting worker or real wave, which already excludes import. Import itself rechecks the snapshot CAS, all source evidence and undispatched eligibility before writes; resume/abandon already recheck their current state inside their mutators. No unrelated scheduler transitions were changed.

Six additional deterministic regressions cover the two P2 cases, the sibling COMPLETE-wave and changed-pin prepare cases, and the stale DAG-content/worker-cap checks in the same wave mutator. The four import races use thread events to pause immediately before the real Store transaction; the two wave-input races inject the competing change at that same boundary. Store persistence, imports, Git worktrees, receipts and journals remain real. The loser must preserve every captured durable byte, Git ref and registered worktree, with no local worker or worktree created by the loser. All six tests fail against the untouched dd8290a source; the original overlap races and nominal mixed-run scenario remain covered.

The adapted P2-A reproduction preserves the public phase check and the original alternate DAG/p03-x interleaving, now requiring `DAG-CONTENT-MISMATCH`, a placeholder wave and byte-identical effects, followed by successful canonical-DAG continuation. The adapted P2-B reproduction preserves the pause in `_new_coordinator_lease` and real completion of T011, now requiring `RUN-NOT-ELIGIBLE`, COMPLETE with no worker and byte-identical effects. These are offline core/adapter fixtures, not live session/admission attestations.

Bootstrap used the installed GWD 6.0.19 without changing any cache/configuration. Installation, enablement and trust were observed separately; the approved reference was read in full and correlated as `orca:ctx_b5c920c63258:ctco_01a0cb4d-0218-7792-813b-56bcb18ee760`. Revalidation recorded `work_ready=true`, `use_ready=true`, `functional_verified=false` in `/tmp/gwd-p2-bootstrap-ready.json`. No publication, installation, merge, tag, push or hermes-k3s mutation was performed.

### P2 validation

The independent dd8290a baseline already completed all 31 validators and 1,500 unittest cases (`/tmp/gwd-final-full.log`). This dispatch also started `python3 tests/run_validators.py` before editing; that redundant run was stopped at the coordinator's explicit request during validator 31 so the post-patch run could start. That interrupted run is not counted as a pass. Its 63 Python files remained unchanged (`/tmp/gwd-p2-baseline-python-before.json` and `/tmp/gwd-p2-baseline-python-after.json`); partial log `/tmp/gwd-p2-baseline-suite.log` is preserved.

- Baseline regression sensitivity: six new tests, six expected assertion failures with the exact checked-in tests against dd8290a; no errors, 12.492 s. The three changed functions were loaded from `git show dd8290a`, with all other definitions checked identical and the real Store identity preserved. `/tmp/gwd-p2-regression-dd8290a-final.log` records the expected RED result, not a passing product test.
- `PYTHONDONTWRITEBYTECODE=1 python3 -B tests/validate_task_import_contract.py`: exit 0, 18 tests, 39.693 s; `/tmp/gwd-p2-focused.log`.
- `PYTHONDONTWRITEBYTECODE=1 python3 -B /tmp/gwd-p2-dag-race.py`: exit 0; `DAG-CONTENT-MISMATCH`, `loser_side_effects=false`, verified import and successful canonical continuation; `/tmp/gwd-p2-dag-race.log`.
- `PYTHONDONTWRITEBYTECODE=1 python3 -B /tmp/gwd-p2-complete-race.py`: exit 0; `RUN-NOT-ELIGIBLE`, COMPLETE with zero workers and `loser_side_effects=false`; `/tmp/gwd-p2-complete-race.log`.
- `git diff --check`: exit 0; `/tmp/gwd-p2-diff-check.log`.

Current changed Python source SHA-256:

- `plugin/skills/grill-with-docs/scripts/grill_core/gauntlet_runs.py`: `c542da05185ffb7021b2e66354fc5b73a70f81af91e4e7325417b90e2c1ebc8e`.
- `tests/validate_task_import_contract.py`: `cb7dff3253647a4d329d23f3b1764e23621763a06d30c51653c4d435567d41d6`.

Final complete run: `PYTHONDONTWRITEBYTECODE=1 python3 -B tests/run_validators.py` exited 0, with 31 validators, 30 unittest suites and 1,506 cases. The sole platform skip remains `test_reject_symlink_chain_accepts_macos_var_root_alias` on Linux. Summed unittest runtime was 1,321.899 s; elapsed runtime was 1,324.568 s. Log: `/tmp/gwd-p2-full.log`; structured result: `/tmp/gwd-p2-validation.json`.

All 63 Python files in the worktree (including tracked scaffolding, not only plugin/tests) were hashed before and after the full run. Both manifests are byte-identical: `/tmp/gwd-p2-python-before.json` and `/tmp/gwd-p2-python-after.json`. No Python source changed during validation. The final staged diff passed `git diff --cached --check` before the additional commit; the three changed files are the core module, its existing import validator and this report.

Evidence SHA-256:

- `/tmp/gwd-p2-full.log`: `1e7d479cac22357ee000f6c8dc35de9c959dfdb66e441ecc8e33b07049ffe28a`.
- `/tmp/gwd-p2-focused.log`: `3ddc5ae3fdec7d4f2388e862931556a93f9d86f17015191d679502acc0db07b7`.
- `/tmp/gwd-p2-regression-dd8290a-final.log`: `0ad37e531ae0c4c6092e406c4f7a7aa279e1664f4af47681487212a29685cdde`.
- `/tmp/gwd-p2-dag-race.py`: `bd6f3a76e6dc6e27040e67150b432dce6217263c22fa86beec9c11384741e467`.
- `/tmp/gwd-p2-dag-race.log`: `54c3acf60c21481f382b8ff124a7b2ad29706a53bd248ff70483b396cc02f7e4`.
- `/tmp/gwd-p2-complete-race.py`: `9c057241c7dd3183d37ffc49eff8122cee01d7c5af7d58329bced445805703db`.
- `/tmp/gwd-p2-complete-race.log`: `212eb9052626fe0cc71be557ec4745b1c5acfa9bde7c2e56388393bed337e050`.
- `/tmp/gwd-p2-python-before.json`: `bd364df831a332367590fc02ad19df3678905780bfc6ab983e29f7e328648692`.
- `/tmp/gwd-p2-python-after.json`: `bd364df831a332367590fc02ad19df3678905780bfc6ab983e29f7e328648692`.
- `/tmp/gwd-p2-validation.json`: `bcbd41f6646051a56d62dbb8b36e3c9eece804741ba47ab59d2b8494797840b9`.

The complete evidence hash inventory, including bootstrap and preserved baseline logs, is `/tmp/gwd-p2-artifact-hashes.json`. The implementation and requested validation are complete; independent review of this follow-up remains with the coordinator.

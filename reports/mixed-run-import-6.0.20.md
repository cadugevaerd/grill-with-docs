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

## Validation

- `PYTHONDONTWRITEBYTECODE=1 python3 -B tests/run_validators.py`: exit 0; all 31 validators completed, including 1495 unittest cases across 30 suites and the distribution assertions. One platform skip: `test_reject_symlink_chain_accepts_macos_var_root_alias` because Linux has no `/var -> /private/var` alias.
- `PYTHONDONTWRITEBYTECODE=1 python3 -B tests/validate_task_import_contract.py`: 7 tests passed, covering public mixed-source preview/apply, unchanged history, reconciliation/barrier/readiness, replay after successor progress, CAS, mismatched/tampered/missing evidence, symlinks and interrupted WAL recovery.
- The adopted-work-item entry-guard regression passed; the new command remains subject to current leader authority and presentation requirements. All 111 step-skill registry tests passed after adding the public import to the explicit approved handler set; the production resolver allowlist was not widened.
- The final full run used frozen source bytes: SHA-256 comparison confirmed all 154 plugin/test files unchanged throughout execution. Final `git diff --check` passed; staged diff hygiene is checked before the delivery commit. No bytecode compilation, network dependency, cache installation or external publication was used.

Full-run log SHA-256: `0f9c816b518f9954657d9566911f828e51514cf33dc3054f129248ce2811d717`. Frozen source manifest SHA-256: `d6373e266397ac7ec97dbb8b7d06317ea56040ac527b87c58dbdb2b87f16cb6a`. Temporary execution logs and the manifest are removed before commit; the delivered source hashes and fixture receipt hashes below remain in this report.

## Delivered file SHA-256

- `.agents/plugins/marketplace.json`: `5b3342917911703015a2be50862a84e49b4eb2fd713f588640057a7460b31e25`.
- `.claude-plugin/marketplace.json`: `6f189dabb3786da1680e5eea2fdfe5fa6b674d45a12192f56be2ac6a3773ff4b`.
- `CHANGELOG.md`: `650a9efabc2ec2750ce9623d068907219ec468ac5805608d49d972ce04123091`.
- `README.md`: `f6a200984d65bac8aa8d0cccee1e92967a07f7609c5beb6ff0aff397060761b1`.
- `plugin/.claude-plugin/plugin.json`: `2202e2c97dc483e4987d96e30b4826f814be4683c588dc5069f267f0828d9bcb`.
- `plugin/.codex-plugin/plugin.json`: `ad934ca65d17252fd8df930e29da7e998d0eaafb747992bd72cf3bbae3894e44`.
- `plugin/skills/grill-with-docs/SKILL.md`: `9a820008297259b808d6c52ae8fa54bb9e6dacbea9b150aac79bf412e7677ac2`.
- `plugin/skills/grill-with-docs/references/session-protocol.md`: `88efaefb053e5d07fc21b04015d5df9ba98c49b56e6831708298964baf333ebe`.
- `plugin/skills/grill-with-docs/scripts/grill_core/gauntlet_runs.py`: `e98a6c33ba315b1096ddc00e2afd1d858165b0c873c0a528c5e1baccd503ffaa`.
- `plugin/skills/grill-with-docs/scripts/grill_core/store.py`: `e17c165dc6f4008058983fd538b46c2873c338bfd624cfa52a52cbcd627fd360`.
- `plugin/skills/grill-with-docs/scripts/grill_workspace.py`: `77aa14ab70e44bc2610f111a0fa8208e9e47e217cff586df9d2c6232b387a6a4`.
- `tests/validate_agent_orchestration_contract.py`: `418b7491d4bd7ceab14585e16effc2b7245ce6659bf94825e7d52c70e6442124`.
- `tests/validate_distribution.py`: `fcd065448071f2f672bdd0efd86d4dbc5d665894e86506d4124eff6d24cedaf6`.
- `tests/validate_task_import_contract.py`: `8611b60e012ab0026ecd772bc4c727dd9ed3888ebf646a4e1b45f06b8056310c`.
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

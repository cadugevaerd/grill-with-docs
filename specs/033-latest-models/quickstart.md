# Quickstart: validate latest-model selection

Run from the repository root after the implementation described in [plan.md](plan.md). These commands validate the candidate; this design document is not evidence that the feature has already been implemented or accepted.

## Prerequisites and isolation

Use Python >=3.10 and Git, as for the existing validators. No real `codex`, `claude`, `node`, `specify` or network service is required. Tests inject a temporary catalog derived from `tests/fixtures/orchestration/codex-models-cache-0.155.1.json`; they must not read the operator's live cache or edit user configuration.

Keep the current GWD campaign on the preserved bundle defined below. Candidate policy v2 is exercised in temporary projects. Do not modify existing `.grill/` receipts or run a real worker to satisfy an offline scenario. The offline suite needs no agent CLI; actual campaign coordination separately requires the normal live bootstrap, observed pair and independent session.

## 0. Freeze and revalidate the campaign coordinator bundle

The coordinator must complete this check before any candidate code change/integration, on every resume/session switch and before each remaining canonical step through ship. The preserved worktree already exists; do not recreate, reset, edit or bump it. Run from `/home/carlosaraujo/orca/workspaces/grill-with-docs/fix-latest-models`:

```bash
python3 -B - <<'PY'
import hashlib
import json
import subprocess
from pathlib import Path

proof_path = Path('.grill/work-items/feature-latest-models-codex-ab7615f7e67f4e2c9d2b94f507c921ec/continuity-bundle-proof.json')
raw = proof_path.read_bytes()
assert hashlib.sha256(raw).hexdigest() == '89f6ede5fd321c1fe901271386458ba6fda452661a3758db4d2cedea0b4817fc'
proof = json.loads(raw)
bundle = Path('/home/carlosaraujo/orca/workspaces/grill-with-docs/continuity-5544829')
revision = '5544829185c2e5d1d75e52736364aa00bede9323'
def git(*args):
    return subprocess.check_output(['git', '-C', str(bundle), *args], text=True).strip()
assert proof['bundle_root'] == str(bundle)
assert git('rev-parse', 'HEAD') == proof['revision'] == revision
assert subprocess.run(['git', '-C', str(bundle), 'symbolic-ref', '-q', 'HEAD'], capture_output=True).returncode == 1
assert git('status', '--porcelain', '--untracked-files=all') == ''
assert git('rev-parse', 'HEAD:plugin/skills/grill-with-docs') == proof['plugin_tree'] == 'd5cc959f9c02a98ddc3a5adfd958d729b62807ce'
subprocess.run(['git', '-C', str(bundle), 'merge-base', '--is-ancestor', 'f1475f4f9523fcd7063e32b547aa6fd8bc364528', revision], check=True)
for entry in proof['files']:
    data = (bundle / entry['path']).read_bytes()
    assert len(data) == entry['size']
    assert hashlib.sha256(data).hexdigest() == entry['sha256'], entry['path']
print('continuity revision, skill subtree and five file hashes: PASS')
PY
```

`plugin_tree` refers to the skill subtree, not `HEAD:plugin`. The five pinned files are the CLI, orchestration module, v1 policy, supplement and Files template. CLI SHA-256 is `00c1220ff3fd167149134792a16b9e35d0b2349b431f6e75e818bf3c54822389`; the orchestration module is `aad0a06e5d8d51c6f75e1126a09410e6fc67b65f72f48083e8731e6eeaca9b1b`. The installed 6.0.30 cache is not a fallback: it rejects this campaign's pre-campaign predecessor with `successor context has no campaign bridge`.

After integrity passes, the **bound coordinator**, using its own actual session reference, performs the read-only preview below; set `GWD_COORD_SESSION_REF` to that reference. A specialist must not impersonate it: a different session can return `CONTEXT-FENCED`.

```bash
python3 -B /home/carlosaraujo/orca/workspaces/grill-with-docs/continuity-5544829/plugin/skills/grill-with-docs/scripts/grill_workspace.py \
  gauntlet-orchestration-adopt /home/carlosaraujo/orca/workspaces/grill-with-docs/fix-latest-models \
  --work-id feature-latest-models-codex-ab7615f7e67f4e2c9d2b94f507c921ec \
  --runtime codex --session-ref "${GWD_COORD_SESSION_REF:?set the bound coordinator session reference}"
```

Expected: `PREVIEW`, exit 0 and `presentation.work_ready=true`, without `--apply`. If it returns a presentation `load_request`, complete the exact approved full-read bootstrap in that same session and work-item scope and repeat; a root-only load does not establish work-item readiness. Compare Store/journal/receipt bytes before and after the read-only probe. Never use CLI activity preparation as a read-only probe: it persists state.

The coordinator must also perform these bounded checks, without writing Store or the preserved worktree:

1. Read the current `grill/orchestrator.json` under the repository's Git common directory and call the preserved module's pure `validate_block(snapshot['agent_orchestration'])`. Use `python3 -B` and import only from the preserved `plugin/skills/grill-with-docs/scripts`; do not instantiate a writer. Retain the observed Store revision/digest, not an expectation that normal progress leaves the revision frozen.
2. For the item's current context, call pure `new_activity`/`prepare_activity` in memory for author and reviewer. Expect `BOOTSTRAPPING`, `gpt-6-astra/xhigh` and `gpt-6-astra/high`; discard those probe objects. No Store record, lease, worker or payload may result. Compare live Store bytes before/after; these pair checks do not prove CLI preparation, launch, acceptance or close.
3. Revalidate the sealed policy ref/hash (`assets/agent-orchestration.v1.json`, `c30b3cecf9c5cc4949c8c3d14eca050608d773f4ffa690fc2c9e72e7a95a3553`), supplement/template hashes, campaign activation and all eleven canonical entrypoint/registry/catalog pins against their recorded references and bytes. Preserve admissions, DAGs and accepted receipt references; never substitute a candidate resolution or reattest old evidence to pass the check.

The supplied `continuity-bundle-proof.json` records successful coordinator preview, Store validation and the two pure pairs; the coordinator separately reported presentation readiness. It contains no CLI activity-prepare or end-to-end lifecycle proof. These observations must be refreshed as above, not treated as permanent admission.

Through ship, use that absolute preserved CLI with the **active campaign root** for v1 coordinator gates, real activity preparation/acceptance, step entry, checkpoints/attestations and continuity/cleanup. The candidate checkout supplies implementation and isolated validation only; do not invoke its new v1 preparation guard against the live campaign. Keep invoking the eleven pinned canonical skills in order. For each real new Codex specialist, observe neutral bootstrap and current presentation readiness, requested/effective/resolved model and effort, identity/fence/input hashes and close capability before payload; use an independent reviewer. On return, revalidate, persist result/diagnostic and confirm settlement/release/cleanup by read-back. Repeat for converge/review and any ship judgment after later bytes exist; old activities cannot cover future outputs.

V1 still requests Claude `fable`. No new Claude specialist or new fable payload is allowed through this bundle, including old prepared activities; candidate Opus support does not change that seal. Continue with Codex specialists, or stop with a nominal hold until a separately justified safe Claude route is authorized. Preserve the bundle until authorized ship, pipeline completion and campaign cleanup are confirmed; a new v2 work item does not discharge this campaign.

## 1. Check resolver and specialist contracts

```bash
python3 tests/validate_tier_model_binding_contract.py
python3 tests/validate_agent_orchestration_contract.py
```

Expected: both exit 0. The updated validators cover every handoff scenario:

| Scenario | Input/action | Expected observation |
|---|---|---|
| 1 — Luna priority | Two listed Luna generations, then reverse their priority values. | Each fresh declaration chooses the unique lower numeric priority and persists that slug, even when the preferred model is older. |
| 2 — Terra continuity | Base fixture without a later Terra, then add one with worse and better priority. | Medium remains Terra; only a better priority changes the selected generation. |
| 3 — Astra roles | Author and reviewer, then a different preferred Astra. | Requests use the fixture-selected slug with xhigh/high; observed effective must match the recorded selection. |
| 4 — Missing/unreadable cache | Missing file and injected read failure through public worker/specialist paths. | `TIER-MODEL-UNRESOLVED`, runtime/tier-or-role/family/path/reason present, no new effects. |
| 5 — Unlisted family | Remove listed family entries or make them hidden. | Same named refusal; no last-known fallback. |
| 6 — Frontier worker | Large worker with both valid and missing catalogs. | `FRONTIER-MODEL-FORBIDDEN` before catalog read, lease or worktree. |
| 7 — Claude specialists | Native-shape requested/effective Opus; then requested/effective fable independently. | Opus author xhigh/reviewer high accepted; fable and mismatched pairs refused before payload. |
| 8 — Unchanged behavior | Claude worker tiers and leader recommendations. | haiku/sonnet/opus and Sol/Opus retain their prior behavior; frontier Opus worker still refused. |

The expected winner comes from the supplied fixture values, not a hard-coded current generation. Preserve hidden `gpt-reserve`, generic `gpt-5.5` with its `upgrade` object, and `codex-auto-review` in the real-shape fixture.

Additional negative cases: invalid UTF-8/JSON/root/models/row shape, duplicate JSON keys, non-regular/unsafe/racing input, invalid relevant priorities (including bool/string/null/non-finite), duplicate relevant slug, and a tie for the minimum. Reordering the catalog must not change a unique winner. Extra metadata and unrelated model fields must be accepted without influencing selection.

## 2. Check persistence, retries and historical compatibility

```bash
python3 tests/validate_gauntlet_scheduler_contract.py
python3 tests/validate_gauntlet_run_contract.py
python3 tests/validate_orchestrator_store_contract.py
```

Expected: exit 0, with these targeted additions:

1. New declaration and direct passive preparation persist `model_binding` before worktree effects; public model fields equal the saved object. Changing/removing an existing binding is refused by Store transitions.
2. Retry the same prepared worker/activity after changing or deleting its catalog. It retains its original selected model and does not mint a second attempt. A fresh attempt resolves the current catalog and refuses if unresolved.
3. Both remediation reasons preserve budget/cap semantics; a missing catalog leaves the original state, replacement count, lease count, worktree list and Store revision unchanged. Successful remediation records its own selected model for the same runtime/tier.
4. Read/replay an unmodified v1 policy/context/checkpoint/activity and legacy worker record without a model binding. Verification/cleanup must not consult the cache, invent a model or rewrite historical bytes. New v2 init/adopt pins v2; unknown/tampered policy is refused. Fresh v1 specialist preparation on the candidate refuses before bootstrap.
5. Preserve `test_first_campaign_is_born_in_a_pre_campaign_successor`: no fictitious bridge when the predecessor had no campaign; a predecessor with a campaign still requires the real bridge.

**Combined continuity scenario (P1).** In an isolated copy/fixture with the same v1 lineage, the current context has its first campaign, its predecessor has none, and no campaign bridge exists. Validate it using the preserved bundle; then invoke candidate fresh v1 specialist preparation and require `ORCHESTRATION-MIGRATION-REQUIRED` before bootstrap or any Store/lease/payload change. Against that same unchanged fixture, use the preserved bundle to prepare a new Codex author and a distinct reviewer, assert the v1 pairs, and exercise bootstrap, observed-pair admission, payload, result, independent acceptance and confirmed close with offline runtime seams. Recheck policy/pins and all pre-existing receipt/bridge bytes throughout; only legitimate new activity/lifecycle evidence may be appended. Repeat the negative predecessor-with-campaign case without a bridge and require refusal. This scenario is a future candidate test, not a claim that the current read-only proof ran that lifecycle or that real workers should be launched by the offline suite. Live campaign specialists still need the checks in section 0.

For every negative public command, assert both exit 2 and the named JSON code. Compare pre/post Store revision and digest, journal/receipt bytes, lease/worktree counts and payload presence. An argparse error or a mocked resolver alone does not prove the public no-effect guarantee.

## 3. Run the complete offline gate and distribution checks

```bash
python3 tests/run_validators.py
git diff --check
```

Expected: all validator processes exit 0 and diff hygiene is clean. Count validators by the runner's `==>` markers; `validate_distribution.py` prints `distribution: OK` rather than a unittest count. Run without installed agent CLIs/network in CI using the existing seams; do not set a global fallback that hides missing-catalog tests.

The full gate also checks current public role documentation, sealed policy compatibility and all eight synchronized version points. The cumulative CHANGELOG entry must include this feature and fix `f1475f4f9523fcd7063e32b547aa6fd8bc364528`. The proposed release number is `6.1.0`, revised only if the integrated base already requires a later unused version.

## 4. Review and release handoff

Give the independent reviewer the five design artifacts, implementation diff, validator results, unchanged v1 policy hash and durable model-record examples. Frontend classification is `NOT_APPLICABLE`; presentation bootstrap and author/reviewer evidence still apply.

After verify/review and explicit ship authorization, the existing pipeline must create an immutable version tag and matching Release at the same commit. No publication command belongs to this quickstart. A tag alone or a manually created Release does not satisfy the release gate.

## Recovery expectations

If resolution refuses, inspect the named catalog path/reason. Runtime owners may refresh their own catalog through their normal workflow; the core does not fetch, repair or replace it. Retry only after the required evidence exists, with a fresh activity/attempt when changing a previously recorded model. Historical campaign seals are never edited to force current-policy admission.

If continuity revalidation or a real lifecycle gate refuses, stop dependent work and preserve the exact code/evidence. The coordinator may complete an already authorized deterministic recovery (such as the requested same-session presentation load) and revalidate. Otherwise record the diagnosis and emit `GOAL-HOLD` with the nominal code, or the residual clause if none applies. Do not edit the bundle/cache, policy, Store, seals, existing receipts or historical bridges; do not lower effort, substitute a model or switch CLI to evade the refusal.

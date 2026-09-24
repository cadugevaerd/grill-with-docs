# Plan reviewer task — independent, read-only

Review `specs/033-latest-models/plan.md` and its four support artifacts under the local `.agents/skills/speckit-plan/SKILL.md`, constitution, spec, PLAN-CONTEXT, ADR-0001/0002 and GWD orchestration policy. Inspect all 34 files in the sealed input manifest below (or the portions relevant to each claim); author result and prior observations are context, not substitutes for your own review. Do not edit files, commit, launch workers or perform later macrosteps.

Return a durable report at `.grill/work-items/feature-latest-models-codex-ab7615f7e67f4e2c9d2b94f507c921ec/plan-reviewer-result.md` with exact verdict `APPROVED` or `CHANGES_REQUIRED`, prioritized findings with file/line and concrete correction, evidence and residual risk. Coordinator copies the report verbatim; tell it when done.

Critical checks: whether v1 campaign can finish after candidate code introduces `ORCHESTRATION-MIGRATION-REQUIRED` for new v1 specialist preparation; whether checkout vs pinned cache CLI treatment of f1475f4 leaves a concrete continuity path without forbidden cache edits; how v1 policy remains byte-identical while new v2 policy is loaded; all three worker prepare branches and persisted binding; fail-closed negative effects; alias `opus` evidence and selector semantics; eight SemVer locations and CHANGELOG explicitly including f1475f4. State any need for CHANGES_REQUIRED rather than assuming future stages will solve it.

Files in sealed input manifest (`plan-reviewer-input.json`):
- `goal.md` (sha256 `af97e2899ddd6668c5fc80eef153cd94b7d88ea92235650370572770e5b291d1`)
- `CLAUDE.md` (sha256 `107f4273e63bca63d7e0f7a9c782e55de2d409d62be8e03c4c59779082ce1152`)
- `.specify/memory/constitution.md` (sha256 `54d5522b18e43efa05311dbf13ed79694b79ccfcb01509384b3572b2d5667569`)
- `.specify/extensions.yml` (sha256 `fb23337f023f64ea78f064abfcf5afa9689f717428e5807e0b3ae77824cc694b`)
- `.agents/skills/speckit-plan/SKILL.md` (sha256 `b3dca1c679a2452e8e3aa84c96b42fc5cee42e8b0cb3c30fa77a60ff83db6d4d`)
- `plugin/skills/grill-with-docs/references/agent-orchestration.md` (sha256 `04b4533636117f26e6870bec6f43632bca8114d0bf1cc92911c15b5855ff7ed3`)
- `plugin/skills/grill-with-docs/assets/agent-orchestration.v1.json` (sha256 `c30b3cecf9c5cc4949c8c3d14eca050608d773f4ffa690fc2c9e72e7a95a3553`)
- `plugin/skills/grill-with-docs/assets/task-files.v1.template.md` (sha256 `4961ec90bd4c31b09aaecd00ed14cf28a7caa927081cdf50110bcc6b5a380eee`)
- `plugin/skills/grill-with-docs/assets/workflow-tier-models.json` (sha256 `b0cdd4395f5d4eedb718282573c5451075ced407c9b302d190a239971b89c9b9`)
- `plugin/skills/grill-with-docs/scripts/grill_core/tier_models.py` (sha256 `89b6cdf6d0704c4e70c4b4f82f4df206465721e42e882d65756c109a30085d44`)
- `plugin/skills/grill-with-docs/scripts/grill_core/agent_orchestration.py` (sha256 `aad0a06e5d8d51c6f75e1126a09410e6fc67b65f72f48083e8731e6eeaca9b1b`)
- `plugin/skills/grill-with-docs/scripts/grill_core/agent_runtime.py` (sha256 `2b5e43c77526423ef3b54bf28e98492fab92a800faf617175c4e2c690afd1bfa`)
- `plugin/skills/grill-with-docs/scripts/grill_core/gauntlet_runs.py` (sha256 `c7e8d1cc6a4803712eec105e9ef4757339d708ab24bbac02a053ec8e50acb49c`)
- `plugin/skills/grill-with-docs/scripts/ensure_dependencies.py` (sha256 `0a084ae400c07d592b816d2e424ea9afc7010b61b43a8b52ff1e5645502274f1`)
- `docs/adr/0013-worker-model-floor.md` (sha256 `645b2fb5b72d4647402f6b5a585b709d44b1ee3ee5dd1f603f0e00475b84116f`)
- `tests/validate_tier_model_binding_contract.py` (sha256 `da60225e4438d5b26f4c9ebaea8f66fea5658c25af7b6ae78b577383a6af0f3f`)
- `tests/validate_agent_orchestration_contract.py` (sha256 `56c3328eef1b84d83beef2262fa68d7669497c14621546e3e5eb25b2aacdb102`)
- `tests/validate_distribution.py` (sha256 `57dc2450fb5bcba4e2df1ae41d3e10aac4878470808952e7d442053a0f36e018`)
- `CHANGELOG.md` (sha256 `776b1066885380c4dcfce02533a371f7d160eb3ed97857d8462b063a3a515988`)
- `specs/033-latest-models/spec.md` (sha256 `96033b87503c3db544d33913baaf81df7b6e262fde3f2be8f5a8d625825a9fee`)
- `.grill/work-items/feature-latest-models-codex-ab7615f7e67f4e2c9d2b94f507c921ec/handoffs/FASE-001-SPECIFY-HANDOFF.md` (sha256 `bc6ae0e3c765adbdc779ed63db352e47d55c7b384a7aa7528ceb6fdd5eaf1c55`)
- `.grill/work-items/feature-latest-models-codex-ab7615f7e67f4e2c9d2b94f507c921ec/PLAN-CONTEXT.md` (sha256 `12a77d42be80a76dfb7a38d92254bcbdaf8d56b424616d1aff455ee2a7ce683a`)
- `.grill/work-items/feature-latest-models-codex-ab7615f7e67f4e2c9d2b94f507c921ec/docs/adr/ADR-0001.md` (sha256 `d52fcc97e32192015aef21fef662f12862edcfd942e2341fc88acd2fcf67bd2e`)
- `.grill/work-items/feature-latest-models-codex-ab7615f7e67f4e2c9d2b94f507c921ec/docs/adr/ADR-0002.md` (sha256 `d688e624871463f1ee4fbda6402c3b33dcededebea3b9a53c2a0f6f8d6718142`)
- `.grill/work-items/feature-latest-models-codex-ab7615f7e67f4e2c9d2b94f507c921ec/agent-orchestration/attestations/specify.json` (sha256 `c024b1998a16cce2bfa40a498818c0a58d9310c3682f4ab6733fb2cfb9e0e3e9`)
- `specs/033-latest-models/plan.md` (sha256 `9c6d2893282010994e1c371ef61e7162fec217ad901f2d428528bea7b14c6810`)
- `specs/033-latest-models/research.md` (sha256 `e8f2610cd0d9c28829c94d9d0212ef08a35955bbfd6537a8f4218f011cf31f0b`)
- `specs/033-latest-models/data-model.md` (sha256 `12e14b7c9e9ede21bd63e17263dc72ce80960005e4e63e5005e02ab7a11c1817`)
- `specs/033-latest-models/quickstart.md` (sha256 `90adcb8f5a01df33d62b9596b13241d36dcf4b2236ee3ec627a02b95237de844`)
- `specs/033-latest-models/contracts/model-selection.md` (sha256 `e9f373cc5bcdc7d0cb4437333ffe691574bd6adfb5d3a378db7c8256949e7498`)
- `.grill/work-items/feature-latest-models-codex-ab7615f7e67f4e2c9d2b94f507c921ec/plan-author-result.md` (sha256 `afd9f7dad2a3425a4bb9388f75a5bf3f3ee8e38dd1e38ee3835d33c3aa4539d9`)
- `.grill/work-items/feature-latest-models-codex-ab7615f7e67f4e2c9d2b94f507c921ec/plan-author-observation.json` (sha256 `fec9bbc1055fdffcb2bfb95567810e886cf3fd0f4a1f9a15c764aa2d644fac96`)
- `.grill/work-items/feature-latest-models-codex-ab7615f7e67f4e2c9d2b94f507c921ec/plan-author-observation-closed.json` (sha256 `1ec7ee71de0ddcff03b3dab6516874f06733002123e9979fdcbae92211ae3929`)
- `.grill/work-items/feature-latest-models-codex-ab7615f7e67f4e2c9d2b94f507c921ec/opus-alias-launch-evidence.json` (sha256 `657e761d31b2be862cc6a2fd445fa52b7419e67c7d2aebf3e5f6d01f263fe343`)

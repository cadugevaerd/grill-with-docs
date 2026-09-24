Atividade técnica plan-author-latest-models, payload do gauntlet-activity DISPATCHED no contexto ctx-3fec10eddb66b60e2ffa1290, epoch 4. Execute a autoria técnica do plano da feature specs/033-latest-models via a skill canônica speckit-plan; não declare a macroetapa concluída.

Leia todos estes arquivos de contexto antes de decidir e escrever:
- goal.md
- CLAUDE.md
- .specify/memory/constitution.md
- .specify/extensions.yml
- .agents/skills/speckit-plan/SKILL.md
- plugin/skills/grill-with-docs/references/agent-orchestration.md
- plugin/skills/grill-with-docs/assets/agent-orchestration.v1.json
- plugin/skills/grill-with-docs/assets/task-files.v1.template.md
- plugin/skills/grill-with-docs/assets/workflow-tier-models.json
- plugin/skills/grill-with-docs/scripts/grill_core/tier_models.py
- plugin/skills/grill-with-docs/scripts/grill_core/agent_orchestration.py
- plugin/skills/grill-with-docs/scripts/grill_core/agent_runtime.py
- plugin/skills/grill-with-docs/scripts/grill_core/gauntlet_runs.py
- plugin/skills/grill-with-docs/scripts/ensure_dependencies.py
- docs/adr/0013-worker-model-floor.md
- tests/validate_tier_model_binding_contract.py
- tests/validate_agent_orchestration_contract.py
- tests/validate_distribution.py
- CHANGELOG.md
- specs/033-latest-models/spec.md
- specs/033-latest-models/plan.md
- .grill/work-items/feature-latest-models-codex-ab7615f7e67f4e2c9d2b94f507c921ec/handoffs/FASE-001-SPECIFY-HANDOFF.md
- .grill/work-items/feature-latest-models-codex-ab7615f7e67f4e2c9d2b94f507c921ec/PLAN-CONTEXT.md
- .grill/work-items/feature-latest-models-codex-ab7615f7e67f4e2c9d2b94f507c921ec/docs/adr/ADR-0001.md
- .grill/work-items/feature-latest-models-codex-ab7615f7e67f4e2c9d2b94f507c921ec/docs/adr/ADR-0002.md
- .grill/work-items/feature-latest-models-codex-ab7615f7e67f4e2c9d2b94f507c921ec/agent-orchestration/attestations/specify.json

Saídas autorizadas exclusivamente:
- specs/033-latest-models/plan.md
- specs/033-latest-models/research.md
- specs/033-latest-models/data-model.md
- specs/033-latest-models/quickstart.md
- specs/033-latest-models/contracts/model-selection.md

Decisões exigidas: implementar ADR-0001/ADR-0002; fonte local models_cache.json com prioridade de listados, fail-closed antes de efeitos; preservar contextos selados com policy versionada; observar o formato efetivo do alias Claude opus; manter worker não-frontier. Classificação frontend NOT_APPLICABLE (platform-devops sem superfície). Release deve incluir também o fix pre-campaign successor do commit f1475f4, além da feature, no bump SemVer dos oito pontos e CHANGELOG.

Use somente stdlib Python >=3.10; nenhuma rede, subprocesso novo no core, ou alteração da configuração do usuário. Considere o validador offline e o fixture Codex 0.155.1 real. Não escreva .grill/ nem .specify/reports/, não faça commit, não despache agentes, não modifique código de produto. Ao terminar, informe arquivos escritos, decisões técnicas, gates executados e dúvidas/impasses ao coordenador por worker_done; ele copiará o resultado bruto para o líder.

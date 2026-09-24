# DELIVERY-MAP

decomposition-schema: v1

## MOD-001 — Resolução de modelo por runtime
- module-kind: platform
- responsibility: Transformar tier ou papel de especialista em um slug Codex concreto a partir do catálogo local, registrando o resultado e recusando fail-closed quando não resolve
- boundary: `plugin/skills/grill-with-docs/scripts/grill_core/tier_models.py`, `gauntlet_runs.py` (declare), `agent_orchestration.py` (papéis), assets de binding e policy, tabela de papéis em `SKILL.md`/`session-protocol.md`/`README.md`; contratos em `tests/validate_tier_model_binding_contract.py` e `tests/validate_agent_orchestration_contract.py`
- depends-on: none

### DU-001 — Família Codex resolvida contra o catálogo local e especialista Claude em Opus
- development-type: platform-devops
- phase: FASE-001
- scope-in: famílias por tier e por papel Codex; resolução pelo catálogo local; registro do slug resolvido; recusa nomeada; fixture real do catálogo 0.155.1; par autor/revisor Claude `opus` (xhigh/high); oito cenários do handoff; bump e release
- scope-out: tiers Claude e seus aliases; recomendação do líder; configuração global do Codex; rede
- depends-on: none
- acceptance: oito cenários cobertos offline; `python3 tests/run_validators.py` exit 0; `git diff --check` limpo; tiers Claude inalterados; nenhum `fable` como par exigido

> IDs are stable within this work item. `module-kind` is one of `domain|platform|cross-cutting`; each DU has exactly one closed development type.

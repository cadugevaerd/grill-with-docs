# DELIVERY-MAP

decomposition-schema: v1

## MOD-001 — Observação de apresentação por runtime
- module-kind: platform
- responsibility: Transformar a listagem nativa de plugins do runtime ativo no eixo `installation` da apresentação, sem inferir o que a evidência não sustenta
- boundary: `plugin/skills/grill-with-docs/scripts/grill_core/agent_runtime.py` (observer de instalação); contrato em `tests/validate_agent_orchestration_contract.py`
- depends-on: none

### DU-001 — Instalação Codex derivada da listagem nativa
- development-type: platform-devops
- phase: FASE-001
- scope-in: reconhecer a instalação Codex a partir de campos da listagem nativa, confirmada em disco e por hash (ADR-0001); fixture real do Codex 0.154.0; seis cenários do handoff
- scope-out: runtime Claude; demais lacunas do T029; instalação ou reparo da cópia
- depends-on: none
- acceptance: seis cenários cobertos offline; `python3 tests/run_validators.py` exit 0; `git diff --check` limpo; Claude inalterado

> IDs are stable within this work item. `module-kind` is one of `domain|platform|cross-cutting`; each DU has exactly one closed development type.

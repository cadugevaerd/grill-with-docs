# Agent Assign: Detecção de extensão pelo registro

**Date**: 2026-08-20

## Decisão de atribuição

Owner único para todas as tasks. A mudança é um módulo coeso (`ensure_dependencies.py`) mais o manifest que ele lê; dividir entre agentes criaria fronteiras onde não há costura real, e T003-T008 tocam a mesma função em sequência. Paralelizar aqui produziria conflito de escrita no mesmo arquivo, não velocidade.

Nenhum subagente foi disparado: o usuário não pediu orquestração multi-agente e o escopo não a justifica.

## Escopos de arquivo

| Task | Arquivos com permissão de escrita |
|---|---|
| T001 | `tests/validate_extension_detection.py` (novo) |
| T002 | `plugin/skills/grill-with-docs/assets/dependencies.json` |
| T003–T008 | `plugin/skills/grill-with-docs/scripts/ensure_dependencies.py` |
| T009 | `tests/validate_dependencies_contract.py` |
| T010 | `plugin/.claude-plugin/plugin.json`, `plugin/.codex-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.agents/plugins/marketplace.json`, `tests/validate_distribution.py`, `plugin/skills/grill-with-docs/SKILL.md`, `plugin/skills/grill-with-docs/references/session-protocol.md`, `README.md`, `CHANGELOG.md` |
| T011–T012 | nenhum — verificação |

## Fora de escopo (F3)

`.grill/**` (bundle já auditado e commitado), `.specify/extensions/**` (código de terceiros vendorizado), `WORKFLOW.md`, `.specify/memory/constitution.md`, hooks, workflows de CI.

O bundle do work item não é reaberto: ele registrou o plano e foi selado com `audit GO`. Alterá-lo agora invalidaria o hash auditado sem que nenhuma decisão tenha mudado.

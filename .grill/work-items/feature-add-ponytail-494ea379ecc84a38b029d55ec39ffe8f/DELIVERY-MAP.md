# DELIVERY-MAP

decomposition-schema: v1

## MOD-001 — Preflight de dependências
- module-kind: platform
- responsibility: Declarar, detectar e remediar dependências externas do grill-with-docs por runtime
- boundary: plugin/skills/grill-with-docs/assets/dependencies.json, plugin/skills/grill-with-docs/scripts/ensure_dependencies.py, tests/validate_dependencies_contract.py
- depends-on: none

### DU-001 — Kind harness-plugin e entrada ponytail
- development-type: platform-devops
- phase: FASE-001
- scope-in: kind novo no manifesto e no detector; entrada ponytail com min, install por runtime e marketplace; testes por runtime com fixtures; bump SemVer minor; menção em SKILL.md e README.md
- scope-out: detecção via CLI; estado habilitado; gate incondicional
- depends-on: none
- acceptance: preflight reporta present/outdated/missing do ponytail nos dois runtimes sem rede; --allow-install executa a sequência declarada pela CLI do harness; suíte verde na matriz de CI

## MOD-002 — Documentação do agente deste repositório
- module-kind: cross-cutting
- responsibility: Declarar o ponytail como parte da stack para quem conduz sessões neste repositório
- boundary: CLAUDE.md, AGENTS.md, .claude/settings.json
- depends-on: MOD-001

### DU-002 — CLAUDE.md, AGENTS.md e ativação versionada
- development-type: documentation
- phase: FASE-001
- scope-in: seção "Ponytail na stack" em CLAUDE.md; AGENTS.md novo para Codex; .claude/settings.json com enabledPlugins
- scope-out: qualquer arquivo de projeto consumidor
- depends-on: DU-001
- acceptance: os três arquivos no diff, consistentes entre si e com dependencies.json

> IDs are stable within this work item. `module-kind` is one of `domain|platform|cross-cutting`; each DU has exactly one closed development type.

# PLAN-CONTEXT

## FASE-001 — Ponytail na stack oficial: detecção, instalação delegada e documentação
- phase: FASE-001
- ADRs: ADR-0001, ADR-0002, ADR-0003, ADR-0004
- BLs: BL-0001
- delivery-units: DU-001, DU-002
- development-type: platform-devops, documentation

### HOW
- **Manifesto** (`plugin/skills/grill-with-docs/assets/dependencies.json`): nova entrada `{"id":"ponytail","kind":"harness-plugin","required":true,"plugin":"ponytail","marketplace":"ponytail","marketplace_source":"DietrichGebert/ponytail","min":"4.9.0","owner":"plugin ponytail","reason":"modo de trabalho oficial do projeto","install":{"claude":[["claude","plugin","marketplace","add","DietrichGebert/ponytail"],["claude","plugin","install","ponytail@ponytail"]],"codex":[["codex","plugin","marketplace","add","DietrichGebert/ponytail"],["codex","plugin","add","ponytail@ponytail"]]}}`. Hoje `install` é lista única; `remediation()`/`_run_installers` precisam aceitar mapa por runtime (ou a entrada usa placeholder `${GRILL_RUNTIME}` — a decidir no plan; mapa por runtime é mais legível e já existe `runtime` no `detect`).
- **Detector** (`ensure_dependencies.py`): acrescentar `"harness-plugin"` a `KINDS` (linha 24) e um ramo em `detect()` (linhas 222-320). Claude: ler `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/plugins/installed_plugins.json`, chave `plugins["<plugin>@<marketplace>"]`, primeiro item com `version`/`installPath`. Codex: `${CODEX_HOME:-$HOME/.codex}/plugins/cache/<marketplace>/<plugin>/<versão>/.codex-plugin/plugin.json`, maior versão presente. Home resolvido por `tools.environ` (seam já usada em `search_paths` do backlogctl). `meets(found, min)` já existe.
- **Sem subprocesso na detecção** (ADR-0003). Instalação só em `_run_installers` sob `allow_install`, pelo `tools.run` com `INSTALL_TIMEOUT`.
- **Limite documentado**: no Codex, `present` não prova habilitado (BL-0001). No Claude, `enabledPlugins` não é lido (DQ-0005).
- **Hooks do ponytail exigem `node` no PATH** (README:117); sem `node` as skills funcionam e a ativação automática fica muda. Não vira dependência nova: registrar no `reason`/docs.
- **Testes** (`tests/validate_dependencies_contract.py`): fixtures de `installed_plugins.json` e de cache Codex sob `HOME` temporário via `Toolchain(environ=...)`; casos present/outdated/missing por runtime; `--allow-install` chama exatamente a sequência declarada; sem a flag nada roda. Contrato de `KINDS` ampliado no validador de manifesto.
- **Docs**: `SKILL.md#Dependências e backlog` e `README.md` citam o ponytail; `CLAUDE.md` deste repo ganha seção "Ponytail na stack"; `AGENTS.md` novo (Codex) com a mesma seção + texto de modo do ponytail (fonte: `AGENTS.md` do plugin 4.9.0); `.claude/settings.json` com `{"enabledPlugins":{"ponytail@ponytail":true}}`.
- **Bump** (DQ-0007, cláusula "Bump obrigatório do plugin"): minor, `5.3.4 → 5.4.0`, nos oito pontos listados em `CLAUDE.md#Distribuição`; `CHANGELOG.md` com a entrada.
- **Restrições**: somente stdlib, Python >= 3.10; CI sem rede, sem `claude`/`codex`; core nunca baixa bytes; hooks read-only inalterados.

> Mantenha um bloco por fase e referências ADR/BL exatamente equivalentes ao ROADMAP e ao handoff. Nunca registre `selected-handoff` aqui.

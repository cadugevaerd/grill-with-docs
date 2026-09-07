# DECISION-BACKLOG

## BL-0001 — Estado "habilitado" do ponytail no Codex
- state: resolved
- phase: FASE-001
- owner: carlosaraujo
- evidence-needed: Registro em disco, ou saída estruturada de `codex plugin`, que distinga plugin instalado de plugin habilitado no Codex.
- next-action: none
- evidência: `codex plugin list --help` (2026-09-07) não tem `--json`; `~/.codex/config.toml` só tem `hooks.state` e `[marketplaces.ponytail]`, sem tabela `plugins` para o ponytail; `~/.codex/plugins/cache/ponytail/ponytail/4.9.0/` existe.
- risco: preflight `--runtime codex` pode reportar `present` para um ponytail instalado mas desabilitado.
- gatilho: Nova versão do Codex com registro estruturado, ou primeiro relato de falso `present`.
- resolução: Limite aceito nesta fase (ADR-0003): no Codex o detector reporta `present` pelo cache e a documentação declara que instalado não prova habilitado. Reabrir como work item próprio quando o gatilho disparar; não bloqueia o specify.
- final-ref: ADR-0003

> Estados: `open | resolved | superseded`; `resolved` e `superseded` são terminais. Todo BL pertence a exatamente uma fase e deve ser referenciado no ROADMAP, handoff e PLAN-CONTEXT. Não fabrique um BL apenas para preencher o template.

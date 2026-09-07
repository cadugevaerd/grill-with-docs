# DECISION FRONTIER

## DQ-0001 — Quais `CLAUDE.md`/`AGENTS.md` recebem a informação do ponytail: os deste repositório ou os do projeto consumidor via `init`?
- phase: FASE-001
- fingerprint: escopo-documental-repo-vs-consumidor
- impact: high
- state: resolved
- context-refs: documentação do agente, stack oficial, preflight
- artifacts: ROADMAP.md, ADR-0001, DELIVERY-MAP.md
- depends-on: none
- final-ref: ADR-0001

## DQ-0002 — O ponytail entra como `required: true` (falta vira `MISSING-DEPENDENCY` sob `--require-dependencies`) ou como dependência opcional só reportada?
- phase: FASE-001
- fingerprint: required-vs-opcional
- impact: high
- state: resolved
- context-refs: stack oficial, preflight
- artifacts: ADR-0002, PLAN-CONTEXT.md
- depends-on: DQ-0001
- final-ref: ADR-0002

## DQ-0003 — Qual é a fonte de verdade da detecção por runtime (registro de plugins do harness) e isso exige um `kind` novo no manifesto?
- phase: FASE-001
- fingerprint: fonte-de-deteccao-por-runtime
- impact: high
- state: resolved
- context-refs: registro de plugins do harness, kind de dependência
- artifacts: ADR-0003, PLAN-CONTEXT.md
- depends-on: DQ-0002
- final-ref: ADR-0003, BL-0001

## DQ-0004 — `--allow-install` pode registrar o marketplace terceiro `DietrichGebert/ponytail` e instalar pelo dono do artefato, e em qual escopo (`user` ou `project`)?
- phase: FASE-001
- fingerprint: instalacao-delegada-e-confianca
- impact: high
- state: resolved
- context-refs: dono do artefato, decisão de confiança
- artifacts: ADR-0004, PLAN-CONTEXT.md
- depends-on: DQ-0003
- final-ref: ADR-0004

## DQ-0005 — Além de instalado, o ponytail deve ficar habilitado por projeto (`enabledPlugins` versionado) ou instalação basta?
- phase: FASE-001
- fingerprint: ativacao-por-projeto
- impact: medium
- state: resolved
- context-refs: stack oficial, documentação do agente
- artifacts: ADR-0001, ROADMAP.md
- depends-on: DQ-0004
- final-ref: ADR-0001

## DQ-0006 — Versão mínima exigida do ponytail?
- phase: FASE-001
- fingerprint: versao-minima
- impact: medium
- state: resolved
- context-refs: preflight
- artifacts: PLAN-CONTEXT.md
- depends-on: DQ-0003
- final-ref: PLAN-CONTEXT.md#HOW (min 4.9.0)

## DQ-0007 — Magnitude do bump SemVer (minor por dependência e `kind` novos)?
- phase: FASE-001
- fingerprint: bump-semver
- impact: low
- state: resolved
- context-refs: stack oficial
- artifacts: PLAN-CONTEXT.md
- depends-on: DQ-0003
- final-ref: PLAN-CONTEXT.md#HOW (5.3.4 → 5.4.0)

> Estados: open | resolved | deferred | split | blocked | out-of-scope. Não duplique fingerprints abertos.

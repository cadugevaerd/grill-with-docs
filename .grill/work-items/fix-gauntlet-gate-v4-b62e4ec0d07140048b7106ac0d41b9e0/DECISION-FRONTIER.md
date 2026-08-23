# DECISION FRONTIER

## DQ-0001 — Como a CLI escolhe o módulo de gate do Gauntlet
- phase: FASE-001
- fingerprint: cli-escolhe-modulo-gate-gauntlet
- impact: high
- state: resolved
- context-refs: módulo de gate, ponto de injeção, frontier ativa, tabela por versão
- artifacts: docs/adr/ADR-0001.md, DECISION-BACKLOG.md#BL-0001
- depends-on: none
- final-ref: ADR-0001

## DQ-0002 — O keyword argument `workflow_v3=` deve ser renomeado neste fix
- phase: FASE-001
- fingerprint: renomear-kwarg-workflow-v3-para-neutro
- impact: medium
- state: resolved
- context-refs: ponto de injeção, módulo de gate
- artifacts: PLAN-CONTEXT.md
- depends-on: DQ-0001
- final-ref: R-0006

## DQ-0003 — `state.json` grava `workflow.version` divergente do marcador do documento
- phase: FASE-001
- fingerprint: state-json-workflow-version-divergente-marcador
- impact: medium
- state: resolved
- context-refs: marcador de workflow, frontier ativa
- artifacts: docs/adr/ADR-0006.md
- depends-on: none
- final-ref: ADR-0006

## DQ-0004 — Que teste teria reprovado este bug, e entra nesta fase
- phase: FASE-001
- fingerprint: cobertura-de-teste-que-pega-gate-hardcoded
- impact: high
- state: resolved
- context-refs: ponto de injeção, frontier ativa, tabela por versão
- artifacts: docs/adr/ADR-0002.md
- depends-on: DQ-0001
- final-ref: ADR-0002

## DQ-0005 — O SSOT declara v3 executável; ADR-0001 aceita quebrá-la
- phase: FASE-001
- fingerprint: ssot-declara-v3-executavel-versus-adr-0001
- impact: high
- state: resolved
- context-refs: frontier ativa, tabela por versão, módulo de gate
- artifacts: docs/adr/ADR-0003.md
- depends-on: DQ-0001
- final-ref: ADR-0003

## DQ-0006 — Separar "versão executável" de "versão legível" sem desfazer a 4.0.1
- phase: FASE-001
- fingerprint: separar-executavel-de-legivel-no-ssot
- impact: high
- state: resolved
- context-refs: tabela por versão, frontier ativa
- artifacts: docs/adr/ADR-0004.md
- depends-on: DQ-0005
- final-ref: ADR-0004

## DQ-0007 — A CLI duplica o SSOT em vez de importá-lo; entra neste fix
- phase: FASE-001
- fingerprint: cli-duplica-tabelas-do-ssot
- impact: high
- state: resolved
- context-refs: tabela por versão, frontier ativa, ponto de injeção
- artifacts: docs/adr/ADR-0005.md
- depends-on: none
- final-ref: ADR-0005

## DQ-0008 — Documento v3 perde o gate de atestação de checkpoint
- phase: FASE-001
- fingerprint: gate-atestacao-checkpoint-por-versao
- impact: high
- state: resolved
- context-refs: módulo de gate, frontier ativa, marcador de workflow
- artifacts: docs/adr/ADR-0007.md
- depends-on: DQ-0005
- final-ref: ADR-0007

## DQ-0009 — O Gauntlet não pode atestar o conserto do próprio Gauntlet
- phase: FASE-001
- fingerprint: bootstrap-fora-da-cadeia-atestada
- impact: high
- state: resolved
- context-refs: gate de execução, frontier ativa
- artifacts: docs/adr/ADR-0008.md
- depends-on: DQ-0001
- final-ref: ADR-0008

> Estados: open | resolved | deferred | split | blocked | out-of-scope. Não duplique fingerprints abertos.

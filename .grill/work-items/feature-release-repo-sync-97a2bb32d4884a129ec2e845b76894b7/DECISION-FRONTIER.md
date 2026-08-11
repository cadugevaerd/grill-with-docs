# DECISION FRONTIER

## DQ-0001 — Quem escreve na cópia vendorizada: o canônico empurra ou o marketplace puxa?
- phase: FASE-001
- fingerprint: direcao-da-publicacao-push-vs-pull
- impact: high
- state: resolved
- context-refs: Repositório canônico, Marketplace, Cópia vendorizada, Publicação
- artifacts: ADR-0001, ROADMAP
- depends-on: none
- final-ref: ADR-0001

## DQ-0002 — O que dispara a publicação: todo merge na main ou só mudança de versão?
- phase: FASE-001
- fingerprint: gatilho-da-publicacao
- impact: high
- state: resolved
- context-refs: Publicação, Drift de publicação
- artifacts: ADR-0002, ROADMAP
- depends-on: DQ-0001
- final-ref: ADR-0002

## DQ-0003 — Qual o mapeamento de conteúdo entre `plugin/` e `plugins/grill-with-docs/`?
- phase: FASE-002
- fingerprint: shape-do-conteudo-vendorizado
- impact: high
- state: resolved
- context-refs: Cópia vendorizada, Manifesto do plugin
- artifacts: ADR-0003
- depends-on: DQ-0001
- final-ref: ADR-0003

## DQ-0004 — Como o pipeline autentica escrita em dois repositórios de terceiros?
- phase: FASE-002
- fingerprint: credencial-cross-repo
- impact: high
- state: resolved
- context-refs: Marketplace, Publicação
- artifacts: ADR-0004, BL-0001
- depends-on: DQ-0001
- final-ref: ADR-0004

## DQ-0005 — Publicação nos dois marketplaces é atômica ou independente?
- phase: FASE-003
- fingerprint: atomicidade-entre-dois-marketplaces
- impact: medium
- state: resolved
- context-refs: Marketplace, Publicação, Drift de publicação
- artifacts: ADR-0005
- depends-on: DQ-0001, DQ-0002
- final-ref: ADR-0005

## DQ-0006 — O drift acumulado (2.4.0 → 2.5.0) é reconciliado pelo pipeline ou por publicação manual única?
- phase: FASE-003
- fingerprint: tratamento-do-drift-existente
- impact: medium
- state: resolved
- context-refs: Drift de publicação
- artifacts: ROADMAP#FASE-003
- depends-on: DQ-0002
- final-ref: ROADMAP#FASE-003

> Estados: open | resolved | deferred | split | blocked | out-of-scope. Não duplique fingerprints abertos.

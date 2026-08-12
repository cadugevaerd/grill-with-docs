# DECISION FRONTIER

## DQ-0001 — Como estruturar as fases, dado que SGD-6 impede a transição entre elas
- phase: FASE-001
- fingerprint: estrutura-de-fases-sob-restricao-de-transicao
- impact: high
- state: resolved
- context-refs: Matriz de etapas, Virada de fase
- artifacts: ROADMAP.md, ADR-0001
- depends-on: none
- final-ref: ROADMAP.md#execution-order

## DQ-0002 — Qual correção para a matriz que não reseta entre fases
- phase: FASE-001
- fingerprint: correcao-matriz-sem-reset-entre-fases
- impact: high
- state: resolved
- context-refs: Matriz de etapas, Trilha de checkpoint, Virada de fase
- artifacts: ADR-0001, ROADMAP.md#FASE-001
- depends-on: DQ-0001
- final-ref: ADR-0001

## DQ-0003 — Como corrigir a deriva viva, com head insatisfazível e branch insatisfazível após o ship
- phase: FASE-002
- fingerprint: correcao-live-vs-recorded
- impact: high
- state: resolved
- context-refs: Pino de identidade, Deriva viva, Work item terminal
- artifacts: ADR-0002, ROADMAP.md#FASE-002
- depends-on: none
- final-ref: ADR-0002

## DQ-0004 — Como tornar o gate de bump bloqueante sem travar PR que o filtro pula
- phase: FASE-003
- fingerprint: gate-bump-required-sem-travar-pr
- impact: high
- state: resolved
- context-refs: Gate de bump, Required status check, Filtro de paths
- artifacts: ADR-0003, ROADMAP.md#FASE-003
- depends-on: none
- final-ref: ADR-0003

> Estados: open | resolved | deferred | split | blocked | out-of-scope. Não duplique fingerprints abertos.

## Fora da fronteira, registrado por transparência

- **BKL-3** (`item edit` e `item move` mutam sem confirmação) é `high` aberto, mas pertence ao `backlogctl`, cujo código não está nesta árvore. `out-of-scope` por impossibilidade material, não por prioridade.
- **SGD-5** (gate não redispara em PR retargetada) é `low` e não entra no recorte pedido. Interage com ADR-0003: mover o gate para workflow próprio permite dar a ele `types:` próprio sem arrastar a matriz, o que barateia a correção futura.

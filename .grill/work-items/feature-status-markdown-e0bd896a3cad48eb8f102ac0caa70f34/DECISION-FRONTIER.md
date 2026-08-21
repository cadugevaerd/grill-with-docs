# DECISION FRONTIER

## DQ-0001 — Qual superfície deve entregar a tabela Markdown sem quebrar consumidores existentes?
- phase: FASE-001
- fingerprint: superficie-markdown-sem-quebrar-json
- impact: high
- state: resolved
- context-refs: status bruto, status humano
- artifacts: docs/adr/ADR-0001.md
- depends-on: none
- final-ref: ADR-0001

## DQ-0002 — Quando um work item pode ser omitido como fechado?
- phase: FASE-001
- fingerprint: predicado-work-item-coerentemente-fechado
- impact: high
- state: resolved
- context-refs: work item coerentemente fechado, etapa GWD, pendência operacional
- artifacts: docs/adr/ADR-0002.md
- depends-on: DQ-0001
- final-ref: ADR-0002

## DQ-0003 — Como a resposta humana deve representar zero ou mais pendências de forma estável?
- phase: FASE-001
- fingerprint: contrato-deterministico-status-humano
- impact: high
- state: resolved
- context-refs: status humano, pendência operacional, all good, inicialização pendente
- artifacts: docs/adr/ADR-0003.md
- depends-on: DQ-0002
- final-ref: ADR-0003

## DQ-0004 — Qual incremento SemVer a nova interface pública exige?
- phase: FASE-001
- fingerprint: incremento-semver-status-markdown
- impact: medium
- state: resolved
- context-refs: bump obrigatório, status humano
- artifacts: docs/adr/ADR-0004.md
- depends-on: DQ-0003
- final-ref: ADR-0004

> Estados: open | resolved | deferred | split | blocked | out-of-scope. Não duplique fingerprints abertos.
> Fronteira vazia: nenhuma DQ material aberta.

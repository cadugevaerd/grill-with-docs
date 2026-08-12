# Analysis — FASE-002

## Cobertura

| FR | Onde | Task |
|---|---|---|
| FR-001 commit não alarma | remoção do operando de head | T-001 |
| FR-002 ramo alarma enquanto não terminal | condição composta | T-001 |
| FR-003 terminal não alarma | idem | T-001 |
| FR-004 campos ausentes = não terminal | leitura conservadora do estado | T-001 |
| FR-005 commits visíveis na saída | já estão em `recorded` e `locations` | T-002 verifica |
| FR-006 demais achados inalterados | nada mais é tocado | T-002 verifica |

## Riscos

**R-1 — Duas noções de terminal.** A situação passa a decidir com base nos mesmos campos que o auditor usa, mas por código próprio. Divergirem é o modo de falha: o alarme sumiria cedo demais, ou tarde demais. Mitigado por usar os dois campos exatos e nada além.

**R-2 — Perda de um caminho de detecção.** Trocar o bundle entre commits deixa de ser observado por `status`. Continua coberto pelo hash de identidade, que é tamper-evident, e pelo de governança. Registrado como consequência negativa em ADR-0002, não como efeito colateral esquecido.

**R-3 — Silenciar cedo demais.** Um work item marcado terminal por engano deixa de alarmar. Como marcar terminal exige o marco fechado, e isso é verificado pelo auditor, o engano precisa passar por dois lugares.

**R-4 — Bump publica.** `plugin/` muda, então o merge cria a tag e publica. Comportamento desejado e já provado duas vezes hoje.

## Dependências

T-001 → T-002 → T-003 → T-004. Nenhuma externa.

## Fora de escopo

- Alterar o registro de identidade ou o hash que o protege.
- Expor a deriva de commit como campo informativo.
- Unificar em código a noção de terminal entre situação e auditor.

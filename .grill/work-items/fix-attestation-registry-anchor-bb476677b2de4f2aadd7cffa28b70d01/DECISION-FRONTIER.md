# DECISION FRONTIER

## DQ-0001 — Qual registry julga a atestação de um work item, e por onde essa versão viaja?
- phase: FASE-001
- fingerprint: autoridade-do-registry-na-atestacao
- impact: high
- state: resolved
- context-refs: versão declarada, registry ancorado, resolução de skill
- artifacts: ADR-0001, ROADMAP.md
- depends-on: none
- final-ref: ADR-0001

## DQ-0002 — Com que código o operador recebe uma skill não resolvida no gate de atestação?
- phase: FASE-001
- fingerprint: codigo-de-contrato-para-skill-nao-resolvida
- impact: high
- state: resolved
- context-refs: código de contrato, atestação, versão declarada
- artifacts: ADR-0002
- depends-on: DQ-0001
- final-ref: ADR-0002

## DQ-0003 — O parâmetro da versão declarada é opcional com default ou obrigatório?
- phase: FASE-001
- fingerprint: default-do-parametro-de-versao-nas-entradas-publicas
- impact: high
- state: resolved
- context-refs: versão declarada, versão ativa, registry ancorado
- artifacts: ADR-0001
- depends-on: DQ-0001
- final-ref: ADR-0001

## DQ-0004 — Como declarar o escopo diante de recibo concluído que reivindica os mesmos arquivos?
- phase: FASE-001
- fingerprint: escopo-honesto-contra-reivindicacao-historica
- impact: high
- state: resolved
- context-refs: escopo declarado, reivindicação histórica, conflito de escopo
- artifacts: WORK-ITEM.json, BL-0001
- depends-on: DQ-0001
- final-ref: BL-0001

> Estados: open | resolved | deferred | split | blocked | out-of-scope. Não duplique fingerprints abertos.

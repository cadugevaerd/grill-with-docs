# Analysis — FASE-003

## Cobertura

| FR | Onde | Task |
|---|---|---|
| FR-001 veredito em toda proposta | workflow sem filtro | T-001 |
| FR-002 sem aprovação simulada | ausência de shim, verificada | T-003 |
| FR-003 matriz restrita | filtro preservado no `ci.yml` | T-002, T-003 |
| FR-004 base do payload | preservada na migração | T-001, T-003 |
| FR-005 histórico suficiente | `fetch-depth: 0` preservado | T-001, T-003 |
| FR-006 ato humano declarado | `CLAUDE.md` | T-004 |

## Riscos

**R-1 — Ficar sem gate.** Remover do `ci.yml` e errar o arquivo novo deixaria o repositório descoberto sem sintoma. O contrato executável passa a exigir a existência e a forma dos dois workflows, então o buraco falha alto.

**R-2 — Perder um dos dois cuidados na migração.** `fetch-depth: 0` ausente faz o gate falhar ao procurar a merge base; base por nome de ramo o faz comparar contra a coisa errada. O primeiro é ruidoso, o segundo é silencioso e pior. Fixados por teste.

**R-3 — O ato humano nunca acontecer.** É o risco que sobrevive à fase: o código fica pronto e a regra segue sendo convenção. Mitigado só por declaração explícita.

## Fora de escopo

- Marcar o check como obrigatório na proteção da linha principal.
- `types:` do gate para redisparo em proposta retargetada — é SGD-5, e o workflow próprio barateia essa correção futura.

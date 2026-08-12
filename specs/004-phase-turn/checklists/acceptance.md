# Checklist de aceite — FASE-001

Item sem evidência nomeada não conta.

## Virada

- [ ] CHK-001 — Registro com todos os 11 passos `complete` é reiniciado, e todos voltam a `pending`.
- [ ] CHK-002 — `current_step` volta ao primeiro passo da sequência.
- [ ] CHK-003 — A entrada da virada aparece na trilha com a razão declarada.
- [ ] CHK-004 — Razão vazia é recusada; nada muda.
- [ ] CHK-005 — Registro parcialmente concluído é recusado; nenhum passo muda de estado.
- [ ] CHK-006 — Registro já reiniciado devolve `REUSED` sem escrever no arquivo.
- [ ] CHK-007 — Work item sem `development` rastreado é recusado como legado.
- [ ] CHK-008 — A virada não altera a forma do estado: as chaves de `development` permanecem as mesmas.

## Recusa que ensina

- [ ] CHK-009 — Iniciar passo com todos os passos `complete` devolve `PHASE-TURN-REQUIRED`, não `INVALID-TRANSITION`.
- [ ] CHK-010 — Transição realmente inválida, como pular um passo, continua devolvendo `INVALID-TRANSITION`.

## Ciclo completo

- [ ] CHK-011 — Um work item completa dois ciclos de 11 passos com uma virada no meio.
- [ ] CHK-012 — Lida após duas viradas, a trilha permite distinguir as três fases.

## Não-regressão

- [ ] CHK-013 — O work item já reconciliado continua legível, sem migração.
- [ ] CHK-014 — A projeção global continua válida e `reconcile` continua devolvendo `REUSED`.
- [ ] CHK-015 — A guarda de mutação global continua ativa na virada.
- [ ] CHK-016 — O lock continua serializando escritores na virada.

## Gates

- [ ] CHK-017 — `python3 tests/run_validators.py` exit 0, contagem ≥ 291.
- [ ] CHK-018 — Versão subida em oito lugares; gate de bump aprova.

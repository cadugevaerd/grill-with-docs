# Quickstart: validar o emissor

**Fase 1** | **Data**: 2026-08-24

## Gate da suíte

```bash
python3 tests/run_validators.py
```

Esperado: exit `0`. A baseline sobe com esta feature — o contrato próprio
acrescenta 18 testes.

## Cenário 1 — A tabela é total e concorda com o despacho (SC-002, SC-003)

```bash
python3 tests/validate_attestation_emitter_contract.py
```

Esperado: `ExecutionClassTable` passa. Cobre que toda etapa de toda versão tem
classe, que os valores estão no conjunto fechado, e que a única etapa
`worker-required` é exatamente a que despacha workers.

**Falha**: uma etapa acrescentada a uma sequência sem entrada na tabela de
classes. É o caso que o teste existe para pegar.

## Cenário 2 — Leader recusado onde o isolamento é a proteção (SC-004)

Pedir emissão de execução direta para a etapa de execução paralela.

Esperado: `EmissionError`, razão `WORKER_REQUIRED_STEP`, detalhe nomeando a
etapa.

**Falha**: aceitar. Seria atestar um isolamento que não houve.

## Cenário 3 — Alteração do artefato é detectável (SC-005)

Emitir sobre um artefato, alterá-lo, recalcular.

Esperado: digests diferentes. É a garantia inteira do mecanismo.

## Cenário 4 — Nenhuma cadeia com digest vazio (SC-006)

Pedir emissão com artefato ausente, com caminho vazio, e com um leitor que
devolva texto em vez de bytes.

Esperado: recusa nomeada nos três casos, antes de qualquer emissão. No caso do
caminho vazio, a recusa precede até a chamada do leitor — o teste usa um leitor
que levanta se for chamado.

## Cenário 5 — Fechamento do bootstrap (SC-001)

**Ainda não executável**: depende da montagem dos quatro elos e do verbo de
linha de comando.

Quando existir: conduzir uma etapa deste próprio work item, apontar o artefato,
emitir, e verificar que `checkpoint --state complete` passa a ser aceito. É o
teste que fecha a circularidade descrita em ADR-0204.

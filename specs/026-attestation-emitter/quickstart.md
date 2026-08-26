# Quickstart: validar o emissor

**Fase 1** | **Data**: 2026-08-24

## Gate da suíte

```bash
python3 tests/run_validators.py
```

Esperado: exit `0`.

## Cenário 1 — A tabela é total e concorda com o despacho (SC-002, SC-003)

```bash
python3 tests/validate_attestation_emitter_contract.py
```

Esperado: `ExecutionClassTable` passa. Cobre que toda etapa de toda versão tem
classe, que os valores estão no conjunto fechado, e que a única etapa
`worker-required` é exatamente a que despacha workers.

**Falha**: uma etapa acrescentada a uma sequência sem entrada na tabela de
classes. É o caso que o teste existe para pegar.

## Cenário 2 — Execução direta recusada onde o isolamento é a proteção (SC-004)

Pedir emissão para a etapa de execução paralela sem que exista wave convergida
na run — isto é, sem prova de que workers isolados fizeram o trabalho.

Esperado: `EmissionError`, razão `WORKER_EXECUTION_UNPROVEN`, detalhe nomeando a
etapa e o que falta.

**Falha**: aceitar. Seria atestar um isolamento que não houve.

A recusa é da *execução direta*, não de quem pede: o receipt de etapa é sempre
do leader. Com waves convergidas na run, a mesma emissão passa e reporta
`execution_class: worker-required` com `worker_execution_proven: true`.

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

Conduzir uma etapa deste próprio work item, apontar o artefato, emitir e
concluir:

```bash
python3 plugin/skills/grill-with-docs/scripts/grill_workspace.py \
  attest . --work-id <ID> --step <STEP> \
  --artifact <ARTEFATO> --out .grill/attestations/<STEP>.json

python3 plugin/skills/grill-with-docs/scripts/grill_workspace.py \
  checkpoint . --work-id <ID> --step <STEP> --state complete \
  --evidence <ARTEFATO> --attestation .grill/attestations/<STEP>.json \
  --reason "<por quê>"
```

Esperado: `ATTESTED` e depois `UPDATED`. É o teste que fecha a circularidade
descrita em ADR-0204.

## Cenário 6 — Corrigir o artefato de uma etapa fechada (SC-009)

Depois de fechar uma etapa, alterar o artefato por motivo legítimo e emitir a
cadeia sucessora:

```bash
python3 plugin/skills/grill-with-docs/scripts/grill_workspace.py \
  attest . --work-id <ID> --step <STEP> --artifact <ARTEFATO> \
  --out .grill/attestations/<STEP>-r2.json \
  --supersedes .grill/attestations/<STEP>.json

python3 plugin/skills/grill-with-docs/scripts/grill_workspace.py \
  checkpoint . --work-id <ID> --step <STEP> --state complete \
  --evidence <ARTEFATO> --attestation .grill/attestations/<STEP>-r2.json \
  --supersedes-attestation .grill/attestations/<STEP>.json \
  --reason "<por que o artefato mudou>"
```

Esperado: `execution_round: 2` na emissão; depois `UPDATED`, com o estado da
etapa **inalterado** em `complete`. Em `state.json`,
`development.superseded_outputs[<STEP>]` guarda o registro anterior com a razão
declarada e o `step_execution_id` que o substituiu, e o bundle antigo continua
no disco.

As etapas posteriores que já tinham selado o registro substituído aparecem em
`development.chain_stale` e precisam ser atestadas de novo — `ship` recusa com
`CHAIN-STALE` enquanto a lista não esvaziar.

**Falha**: o receipt anterior desaparecer ou ser reescrito. A auditoria perderia
justamente a distinção entre correção honesta e adulteração.

Travado por `test_an_accepted_supersession_records_what_it_replaced_and_why` e
`test_ship_refuses_while_a_step_still_rests_on_a_replaced_output` em
`tests/validate_v3_wiring_contract.py`.

## Cenário 7 — Substituição só contra o registro que o item aceitou (SC-010)

Cunhar um bundle bem-formado para a mesma etapa que **não** seja o aceito, e
apresentá-lo como `--supersedes-attestation`.

Esperado: recusa `SUPERSEDE-BUNDLE-NOT-RECORDED`, e `state.json` byte-idêntico.

**Falha**: aceitar. Toda a cadeia sucessora seria forjável — bastaria cunhar um
bundle novo e chamá-lo de original.

Travado por `test_a_supersession_needs_the_bundle_this_item_actually_accepted`.

Sucessor sem razão declarada é `REASON-REQUIRED`; sucessor que não muda nem o
artefato nem o predecessor é `SUPERSEDE_WITHOUT_CHANGE`.

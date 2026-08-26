# Rollback e monitoração — 5.2.0 (026-attestation-emitter)

## Superfície publicada

Núcleo (`grill_core/attestation.py`): `supersede_step_execution`, `mint_chain`
com `supersedes_*` e `human_authorization`. CLI (`grill_workspace.py`):
`attest --supersedes|--authorization`, `checkpoint --supersedes-attestation`,
`verify_supersession`, `mark_chain_stale`, gate `CHAIN-STALE` em `ship` e em
`phase-turn`. Estado: `superseded_outputs`, `chain_stale`,
`attested_executions`.

## Plano de rollback

**Gatilho.** Qualquer um destes, observado num projeto consumidor:

1. `checkpoint --state complete` recusando etapa que antes era aceita, sem que
   o artefato tenha mudado — indicaria que o pino da execução está reprovando
   receipt legítimo.
2. `ship` ou `phase-turn` recusando com `CHAIN-STALE` sobre lista que não
   esvazia por re-atestação — indicaria ledger que não destrava.
3. `HUMAN_AUTHORIZATION_REQUIRED` em etapa que não é `ship`.

**Ação.** Republicar 5.1.0 nos marketplaces. A tag `v5.1.0` é imutável e já
existe, então o rollback é apontar os marketplaces de volta, não recriar
artefato. Consumidores que já instalaram 5.2.0 voltam com o pin de versão.

**Custo de dados.** Nenhum destrutivo. Os três campos novos de estado são
aditivos: um `state.json` escrito pela 5.2.0 é lido pela 5.1.0 sem erro — a
versão antiga simplesmente ignora `superseded_outputs`, `chain_stale` e
`attested_executions`. Não há migração para desfazer.

**O que o rollback perde.** O caminho de correção volta a não existir: um
artefato editado depois do selo torna a cadeia divergente para sempre, que é
exatamente BL-0201. Quem já tiver supersessões gravadas mantém o histórico em
`superseded_outputs`, mas sem verbo que o leia.

**Bump.** Rollback de código exige bump próprio (cláusula *Bump obrigatório do
plugin*); reverter a versão publicada não é reutilizar 5.1.0 como número novo.

## Monitoração

Não há telemetria: o plugin é biblioteca padrão, offline, sem rede por
restrição de projeto. A monitoração é, portanto, deliberadamente manual e vale
declarar assim em vez de inventar um painel.

**Sinais a observar**, em ordem de gravidade:

| Sinal | Onde aparece | O que significa |
|---|---|---|
| `SUPERSEDE-BUNDLE-NOT-RECORDED` com `expected_step_execution_id` | saída JSON do `checkpoint` | o bundle apresentado não é o aceito — ou tentativa de forja, ou operador com bundle errado em mãos |
| `CHAIN-STALE` que não esvazia | `ship` e `phase-turn` | ledger travado; investigar se `mark_chain_stale` está marcando etapa sem receipt |
| `SUPERSEDE_WITHOUT_CHANGE` recorrente | `checkpoint` | operador tentando re-atestar sem ter mudado nada — provável mal-entendido do fluxo |
| `HUMAN_AUTHORIZATION_REQUIRED` | `attest` | esperado só em `ship` |

**Gate contínuo.** `.github/workflows/ci.yml` (matriz 3 SOs × Python 3.10/3.13)
e `bump-gate.yml` rodam em toda PR. A suíte de 1303 testes é o detector
primário de regressão nesta superfície.

**Primeiro uso real.** Este próprio work item: quatro cascatas completas de
re-atestação sobre oito a nove etapas, todas convergindo para `chain_stale`
vazia e receipts casando com os bytes correntes.

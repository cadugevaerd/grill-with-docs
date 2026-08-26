# Contrato: superfície de emissão

## O que a cadeia cunhada prova

Que o artefato existia, que foi lido no momento da emissão, e que alterá-lo
depois quebra a correlação.

## O que ela não prova

Que a capacidade registrada foi executada. Um agente pode produzir o artefato por
outro meio e declará-lo; a cadeia não distingue.

Isto não é lacuna a corrigir depois: `specs/010-execution-attestation` declara
proveniência criptográfica e defesa contra agente hostil como fora de escopo, e
o `WORKFLOW.md` repete que os receipts "não são prova criptográfica nem protegem
contra um executor malicioso". A garantia é modesta **por desenho**, e descrevê-la
como mais do que é seria a mesma sobre-afirmação que o mecanismo existe para
impedir.

## Funções entregues

```text
execution_class(step_id, workflow_version, versions) -> "leader-allowed" | "worker-required"
require_emission_allowed(step_id, workflow_version, versions, *,
                         worker_execution_proven=False) -> "leader-allowed" | "worker-required"
artefact_digest(read_bytes, path) -> (digest, size)
mint_chain(...) -> bundle
leader_lease(run_id, step_id) -> (lease_id, fencing_token)
supersede_step_execution(store, superseded, successor) -> "RECORDED"
```

`require_emission_allowed` devolve a classe satisfeita, e não `None`: quem cunha
registra qual regra atendeu. `worker-required` **não** significa "o worker
escreve o receipt" — nenhum worker escreve receipt de etapa. Significa que o
*trabalho* foi feito por workers despachados, e o leader só emite contra prova
disso, lida do estado durável da run e nunca declarada por quem pede
(BL-0202 / ADR-0203).

`supersede_step_execution` autoriza a cadeia sucessora quando o artefato de uma
etapa fechada muda por motivo legítimo: o receipt anterior nunca é reescrito, o
sucessor nomeia o que substitui e avança a ronda (BL-0201 / ADR-0205).

`versions` é injetado, não importado: `attestation.py` não pode depender em tempo
de import de outro módulo do núcleo, e o chamador já tem o módulo carregado.

`read_bytes` é injetado pelo mesmo motivo mais um: a fronteira segura de leitura
é do chamador, e o módulo de atestação não faz I/O próprio.

## Recusas

| Razão | Quando |
|---|---|
| `EXECUTION_CLASS_VERSION_UNKNOWN` | versão de ciclo sem tabela |
| `EXECUTION_CLASS_UNDECLARED` | etapa sem classe na tabela da versão |
| `EXECUTION_CLASS_INVALID` | valor fora do conjunto fechado |
| `WORKER_EXECUTION_UNPROVEN` | etapa `worker-required` sem wave convergida que prove o despacho |
| `ARTEFACT_PATH_INVALID` | caminho vazio, só espaços, ou não-texto |
| `ARTEFACT_UNREADABLE` | ausente, ilegível, ou leitor devolvendo não-bytes |
| `SUPERSEDE_LINK_INCOMPLETE` | uma retro-referência sem a outra |
| `SUPERSEDE_ROUND_NOT_ADVANCED` | sucessor em ronda 1, ou ronda não maior que a substituída |
| `SUPERSEDE_NOT_LINKED` | sucessor que não nomeia a execução que substitui |
| `SUPERSEDE_ATTEMPT_NOT_LINKED` | sucessor que nomeia a tentativa errada |
| `SUPERSEDE_STEP_MISMATCH` | os dois receipts não descrevem a mesma etapa |
| `SUPERSEDE_WITHOUT_CHANGE` | nem o artefato nem o predecessor mudaram |

As de emissão carregam `code = EMISSION_REFUSED` e detalhe nomeando o caso; as de
supersessão vêm de `STATE_DIVERGENCE` ou `UNATTESTED_STEP_OUTPUT`, conforme o
elo que falhou.

## Superfície de linha de comando

```text
attest ROOT --work-id ID --step STEP --artifact PATH --out BUNDLE [--supersedes ANTERIOR]
checkpoint ROOT --work-id ID --step STEP --state complete --evidence PATH \
    --attestation BUNDLE [--supersedes-attestation ANTERIOR --reason "por quê"]
```

Cunhar e aceitar permanecem separados: um comando que fizesse os dois tornaria
"a cadeia foi aceita" indistinguível de "a cadeia foi escrita por quem queria
que fosse aceita".

O verbo recusa antes de qualquer leitura quando a classe não permite. Na
aceitação de uma supersessão, o bundle substituído precisa ser **aquele que o
work item aceitou** — provado contra `output_sha256`, `receipt_ref` **e** o
`step_execution_id` gravado em `development.attested_executions[step]` —, e não
apenas um bundle bem-formado da mesma etapa (`SUPERSEDE-BUNDLE-NOT-RECORDED`).
Os dois primeiros não dependem da execução: duas cadeias da mesma etapa e do
mesmo artefato, diferindo só no índice de onda, os carregam idênticos sob
execuções distintas.

As etapas a jusante entram em `development.chain_stale`, e tanto `ship` quanto a
virada de fase recusam com `CHAIN-STALE` enquanto a lista não esvaziar.

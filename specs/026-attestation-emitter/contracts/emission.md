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
require_leader_allowed(step_id, workflow_version, versions) -> None
artefact_digest(read_bytes, path) -> (digest, size)
```

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
| `WORKER_REQUIRED_STEP` | leader tentando cunhar para etapa que exige worker |
| `ARTEFACT_PATH_INVALID` | caminho vazio, só espaços, ou não-texto |
| `ARTEFACT_UNREADABLE` | ausente, ilegível, ou leitor devolvendo não-bytes |

Todas carregam `code = EMISSION_REFUSED` e detalhe nomeando o caso.

## Superfície por fazer

```text
mint_chain(...) -> bundle          # os quatro elos, correlacionados
grill_workspace.py attest ...      # o verbo de linha de comando
```

O verbo precisa aceitar: work item, etapa, caminho do artefato, e o executor
declarado. Precisa recusar antes de qualquer escrita quando a classe não permite.

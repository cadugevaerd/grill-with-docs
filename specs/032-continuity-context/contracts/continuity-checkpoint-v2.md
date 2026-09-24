# Contrato: checkpoint de continuidade v2

Mesmas chaves obrigatórias de `grill-continuity-checkpoint/v1`, com dois nomes corrigidos:

| v1 | v2 | conteúdo real |
|---|---|---|
| `workflow_sha256` | `context_inputs_sha256` | digest das entradas do contexto (`context["inputs_sha256"]`) |
| `constitution_sha256` | `origin_metadata_sha256` | digest dos metadados de origem do work item (`item["origin"]["metadata_sha256"]`) |

- Emissão passa a produzir v2.
- Leitura aceita v1 e v2; a escolha das chaves é feita pelo `schema` declarado no documento.
- Nenhum checkpoint v1 é reescrito, migrado ou re-selado.
- Esta versão **não** acrescenta comparação com os digests reais de `WORKFLOW.md` ou da Constituição (BL-0001).

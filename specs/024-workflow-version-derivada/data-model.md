# Data Model: Versão de workflow derivada do documento

**Phase**: 1 | **Spec**: [spec.md](./spec.md) | **Research**: [research.md](./research.md)

Nenhuma entidade nova. O trabalho muda a **origem** de dois campos existentes e o **predicado** que os valida.

## Entidades

### Documento de workflow (`WORKFLOW.md`)

Autoridade sobre a versão. Project-wide, um por repositório.

| Atributo | Origem | Observação |
|---|---|---|
| declaração de versão | corpo do documento, `grill-with-docs-workflow:vN` | Zero, uma ou várias ocorrências; só uma é válida |
| impressão digital | SHA-256 dos bytes | Já derivada hoje |

**Regra de validação**: exatamente uma declaração, e o valor pertence a `ACCEPTED_WORKFLOW_MARKERS`.

### Registro de estado (`state.json`)

#### `workflow`

| Campo | Antes | Depois | Domínio |
|---|---|---|---|
| `path` | derivado | derivado (inalterado) | — |
| `sha256` | derivado | derivado (inalterado) | — |
| `version` | literal `"v2"` | declaração resolvida do documento | `v2 \| v3 \| v4` |

Responde: **qual versão o documento declarava quando este work item nasceu.**

#### `development`

| Campo | Antes | Depois | Domínio |
|---|---|---|---|
| `schema` | `grill-development/v2` | inalterado | — |
| `workflow_version` | literal `"v4"` do asset | derivado, com a equivalência de R3 | `v3 \| v4` |
| `sequence` | do asset | inalterado nesta fase | — |

Responde: **qual sequência este bundle fala.** Domínio menor que o de `workflow.version` porque `SEQUENCE_BY_VERSION` não tem entrada v2.

### Mapa de derivação

| Declaração do documento | `workflow.version` | `development.workflow_version` |
|---|---|---|
| `v2` | `v2` | `v3` (equivalência R3: sequência idêntica) |
| `v3` | `v3` | `v3` |
| `v4` | `v4` | `v4` |
| ausente / múltipla / não reconhecida | — | — (criação recusada) |

A linha `v2` é a única equivalência deste mapa. Ela existe porque `SEQUENCE_BY_VERSION` não tem entrada v2 e `WORKFLOW_SEQUENCE_BY_MARKER` prova que v2 e v3 declaram a **mesma** tupla de onze etapas. FR-002 exige que toda equivalência seja justificada assim, e proíbe introduzir equivalência por conveniência de implementação: uma linha nova aqui só é legítima se a identidade das sequências for verificável (V-5).

### Metadata imutável (`WORK-ITEM.json`)

**Não muda.** `immutable.workflow` continua com `path` e `sha256` apenas — ver R2: acrescentar `version` ali criaria staleness no rebind e alteraria a construção de `immutable_sha256`.

## Transições de estado

Nenhuma. Os campos são gravados uma vez, na criação do bundle, e nenhum comando os reescreve — nem `rebind_workflow_bundle`, que toca apenas `immutable.workflow.sha256`.

## Regras de validação

| Id | Regra | Onde |
|---|---|---|
| V-1 | Declaração única e reconhecida, senão recusa antes de qualquer escrita | criação |
| V-2 | `workflow.version` pertence a `ACCEPTED_WORKFLOW_MARKERS` | auditoria |
| V-3 | `development.workflow_version` pertence a `SEQUENCE_BY_VERSION` | projeção/checkpoint (já existente) |
| V-4 | Resolução da criação e verificação da auditoria concordam em toda a matriz | teste de paridade |
| V-5 | Toda equivalência aplicada na derivação é justificada por identidade comprovada das sequências de etapas envolvidas | criação (SC-007) |

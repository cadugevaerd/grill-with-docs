# Data Model: Versão de workflow derivada do documento

**Phase**: 1 | **Spec**: [spec.md](./spec.md) | **Research**: [research.md](./research.md)

Nenhuma entidade nova. O trabalho muda a **origem** de um campo existente e acrescenta a recusa que protege essa origem.

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

**Fora de escopo.** A 5.0.0 renomeou o campo de versão deste bloco para `schema` e o redefiniu como tag de forma do próprio bloco, com leitura dupla permanente para bundles anteriores. Sob essa definição ele não descreve artefato externo algum, e o literal que carrega é legítimo. Este trabalho não o toca — ver ADR-0003.

#### `development`

| Campo | Antes | Depois | Domínio |
|---|---|---|---|
| `schema` | `grill-development/v2` | inalterado | — |
| `workflow_version` | literal `"v4"` do asset, nunca sobrescrito | derivado do marcador, com a equivalência de R3 | `v3 \| v4` |
| `sequence` | do asset, sempre a da versão ativa | derivada junto com `workflow_version`, da mesma resolução | tupla da versão derivada |

Responde: **qual sequência este bundle fala.** Domínio menor que o de `workflow.version` porque `SEQUENCE_BY_VERSION` não tem entrada v2.

### Mapa de derivação

| Declaração do documento | `development.workflow_version` |
|---|---|
| `v2` | `v3` (equivalência R3: sequência idêntica) |
| `v3` | `v3` |
| `v4` | `v4` |
| ausente / múltipla / não reconhecida | — (criação recusada) |

A linha `v2` é a única equivalência deste mapa. Ela existe porque `SEQUENCE_BY_VERSION` não tem entrada v2 e `WORKFLOW_SEQUENCE_BY_MARKER` prova que v2 e v3 declaram a **mesma** tupla de onze etapas. FR-002 exige que toda equivalência seja justificada assim, e proíbe introduzir equivalência por conveniência de implementação: uma linha nova aqui só é legítima se a identidade das sequências for verificável (V-4).

### Metadata imutável (`WORK-ITEM.json`)

**Não muda.** `immutable.workflow` continua com `path` e `sha256` apenas — ver R2: acrescentar `version` ali criaria staleness no rebind e alteraria a construção de `immutable_sha256`.

## Transições de estado

Nenhuma. Os campos são gravados uma vez, na criação do bundle, e nenhum comando os reescreve — nem `rebind_workflow_bundle`, que toca apenas `immutable.workflow.sha256`.

## Regras de validação

| Id | Regra | Onde |
|---|---|---|
| V-1 | Declaração única e reconhecida, senão recusa antes de qualquer escrita | criação |
| V-2 | `development.workflow_version` pertence a `SEQUENCE_BY_VERSION` | projeção/checkpoint (já existente) |
| V-3 | Resolução da criação e verificação da auditoria concordam em toda a matriz | teste de paridade |
| V-4 | Toda equivalência aplicada na derivação é justificada por identidade comprovada das sequências de etapas envolvidas | criação (SC-007) |
| V-5 | `workflow_version` e `sequence` do bloco `development` declaram a mesma versão; um bundle que declare uma e liste a outra é inválido | criação |

# Data Model: Continuidade de contexto sem líder vivo

## Contexto de orquestração (existente, estendido)

| Campo | Mudança |
|---|---|
| `contexts[id].state` | ganha a transição `ACTIVE -> RELEASED` por tomada, além da já existente por troca preparada |
| `contexts[id].leader.state` | idem |
| `epoch` | a tomada abre a época seguinte |
| `succession` (novo, por contexto novo) | `{ "from_context_id", "from_session_ref", "reason": "takeover", "evidence": { "observation_ref", "observation_sha256", "dispatch_status", "liveness" }, "taken_at" }` |

## Entrada da tomada (lida)

| Campo | Origem | Uso |
|---|---|---|
| `work_id` | argumento | alvo |
| `session_ref` | argumento | quem assume |
| observação do dispatch anterior | adapter | prova de encerramento (R1) |
| `expected_sha256` | preview | confirma que as entradas não mudaram entre prévia e efetivação |

## Checkpoint de continuidade

- `grill-continuity-checkpoint/v1`: inalterado, continua legível.
- `grill-continuity-checkpoint/v2`: mesmas chaves, exceto `workflow_sha256` → `context_inputs_sha256` e `constitution_sha256` → `origin_metadata_sha256`.
- Leitura: escolhe o conjunto de chaves pelo valor de `schema`; nunca por tentativa.

## Transições

`ACTIVE` → (tomada autorizada) → contexto anterior `RELEASED` + contexto novo `ACTIVE` na época seguinte.
`ACTIVE` → (prova ausente ou insuficiente) → recusa nomeada, nenhum byte escrito.

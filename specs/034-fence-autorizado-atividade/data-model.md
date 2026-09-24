# Data Model: Fence autorizado de atividade órfã

Nenhuma chave nova no schema do Store. Muda um literal de aresta (`agent_orchestration.py:48`) e entram registros novos nas estruturas existentes: uma operação com `kind` novo, uma atividade em `FAILED` e um recurso de sessão em `CLOSED`.

## Atividade de especialista (existente)

| Campo | Antes do fence | Depois do fence |
|---|---|---|
| `state` | `DISPATCHED` (forma órfã) ou `RESULT_RECORDED` (forma retida) | `FAILED` — aresta `DISPATCHED → FAILED` existente; `RESULT_RECORDED → FAILED` nova (DQ-0009, R9) |
| `diagnostic_ref` | `None` (6094; 942-956) | `activity-fence/<operation_id>.json` — `result_ref` da operação; first-bound a partir de `None` (1537-1539); obrigatório em `FAILED` (784-785) |
| `result_ref`, `result_sha256`, `output_manifest` | `None` (órfã) ou preenchidos (retida) | inalterados; a tripla coerente é válida em `FAILED` (762, 770) |
| `accepted_by_context`, `acceptance_ref`, `review_verdict`, `released_at` | `None` | `None` — nada é aceito (FR-007); `accept_activity` recusa fora de `RESULT_RECORDED` (964-965) |
| identidade (`activity_id`, `context_id`, `attempt`, `input_manifest`, …) | — | intocada (1532-1536) |

## Recurso de sessão (existente)

| Campo | Antes | Depois |
|---|---|---|
| `state` | `REGISTERED` (órfã) ou `CLOSE_PENDING` (retida) | `CLOSED`; órfã percorre `REGISTERED → CLOSE_PENDING` no salto 1 e `CLOSE_PENDING → CLOSED` no salto 2; retida percorre `CLOSE_PENDING → CLOSED` num salto (arestas 49; R7) |
| `evidence_manifest.receipts` | `[{ref: "orca:<owner_dispatch>", sha256}]` | acrescenta `{ref: "orca:<owner_dispatch>:fence", sha256: <digest da observação do especialista>}` (refs únicos, 1054-1058; append, 1550-1553) |
| `last_observation` | `orca:<owner_dispatch>` | `orca:<owner_dispatch>:fence` (precisa constar em receipts, 1066-1068) |
| `operation_id` | `None` | `<operation_id>` (nullable; precisa existir em `operations`, 1002-1003 e 1442) |
| `result_acceptance_ref` | `None` | `None` — nada foi aceito; `cleanup_reasons` continua a devolver `RESULT_NOT_DURABLE` (1082-1083), irrelevante após supersede |
| `preservation_reasons` | `[]` | `[]` |
| identidade (`identity`, `creation_observation`, …) | — | intocada (1542-1546) |

## Operação `activity-fence` (nova instância, forma existente 639-662)

| Campo | Valor |
|---|---|
| `operation_id` (chave) | `"fence-" + sha256(canonical({"context": context_id, "activity": activity_id}))[:24]` — determinístico, reencontrável no replay (R2) |
| `kind` | `"activity-fence"` (string livre, 643) |
| `context_id` | contexto da atividade, lido do Store |
| `fence` | `contexts[context_id]["leader"]["fence"]` (obrigatório igual, 1378) |
| `subject_ids` | `[activity_id, resource_id]` |
| `input_sha256` | `expected` da prévia (R6) |
| `expected_before` | `{"context_id", "activity_id", "activity_state", "resource_id", "resource_state"}` (Finding 4) |
| `intended_after` | `{"reason": "activity-fence", "activity_state": "FAILED", "resource_state": "CLOSED", "evidence": {...}, "requester": {...}, "authorization": <bundle verbatim>, "successor": "attempt-2-in-successor-context", "applied_at": <RFC3339 UTC>}` |
| `idempotency_key` | `operation_id` (identidade `(kind, context_id, subject_ids, input_sha256)`, 1379-1381) |
| `state` | `"CONFIRMED"` (exige `observation_ref` e `result_sha256`, 651-652; imutável depois, 1525) |
| `result_ref` | `f"activity-fence/{operation_id}.json"` — referência lógica, como `context-takeover/…` (4286); nenhuma categoria nova em `RECEIPT_CATEGORIES` (`store.py:100-111`) |
| `result_sha256` | `store.jcs_sha256({"evidence", "requester", "authorization"})` |
| `observation_ref` | igual a `result_ref` |
| `error` | `None` |

`evidence` = `{"specialist": {"session_ref": "orca:<owner_dispatch>", "observation_ref", "observation_sha256", "dispatch_status", "liveness", "verdict": "terminal"}, "leader": {"session_ref": <context.leader.session_ref>, "observation_ref", "observation_sha256", "dispatch_status", "liveness", "verdict": "terminal" | "active"}}` (campos de 4195-4196 por observação).

`requester` = `{"role": "successor", "ref", "sha256", "incarnation"}` (de `_session_readiness`, 1654-1655) ou `{"role": "current-leader", "ref", "sha256", "incarnation"}` (de `context["leader"]`, provados por `_require_current_leader`, 1658-1670).

## Autorização humana exata (lida; forma existente `attestation.py:191-193`)

| Chave | Valor exigido |
|---|---|
| `schema` | `"human-authorization/v1"` |
| `scope` | `f"{work_id}:{context_id}:{activity_id}"` — `context_id` da atividade no Store, não do chamador |
| `decision` | `"APPROVED"`; qualquer outro valor = ausência (spec, edge case) |
| `authorized_by`, `receipt_ref` | `FREE_REF_RE` (134); `receipt_ref` é o recibo humano preexistente |
| `content_sha256` | `SHA256_RE` (130), só forma (R5; DQ-P1) |

## Entradas do verbo (lidas)

| Campo | Origem | Uso |
|---|---|---|
| `work_id`, `activity_id` | argumentos | alvo; `context_id`, `resource_id`, `epoch` e `fence` derivam do Store |
| `session_ref` | argumento | solicitante; sucessor (líder terminal) ou o próprio líder corrente (líder vivo) |
| `authorization` | caminho relativo ao root | bundle acima |
| observação do especialista | adapter, por `orca:<owner_dispatch>` | prova terminal (R3) |
| observação do líder | adapter, por `context.leader.session_ref` | autoridade (R4) |
| readiness do solicitante | adapter, por `session_ref`, só com líder terminal | prova do host do sucessor (F4) |
| `expected_sha256` | prévia | confirma que as entradas não mudaram entre prévia e efetivação (R6) |

## Hash da prévia

`expected = jcs_sha256({work_id, context_id, activity_id, activity_state, resource_id, resource_state, to_session_ref, specialist: {verdict, reference}, leader: {verdict, reference}, authorization: {scope, decision, authorized_by, receipt_ref, content_sha256}})`. Sem digest de resposta nem revisão do Store (R6).

## Aresta nova (DQ-0009)

`_ACTIVITY_EDGES["RESULT_RECORDED"]`: `{"RESULT_RECORDED", "ACCEPTED"}` → `{"RESULT_RECORDED", "ACCEPTED", "FAILED"}`. Literal congelado, não derivado; `FAILED` já exige `diagnostic_ref` (784-785). `_RESOURCE_EDGES`, `_OPERATION_EDGES`, `SPECIALIST_PAIRS`, policy e `RECEIPT_CATEGORIES` inalterados.

## Transições

- Forma órfã: `(DISPATCHED, REGISTERED)` → salto 1 → `(FAILED, CLOSE_PENDING)` + operação `CONFIRMED` → salto 2 → `(FAILED, CLOSED)`.
- Forma retida: `(RESULT_RECORDED, CLOSE_PENDING)` → salto 1 → `(FAILED, CLOSED)` + operação `CONFIRMED`.
- Qualquer recusa → nenhum byte escrito (prévia e apply).
- Replay sobre `(FAILED, CLOSED)` com a operação presente → `FENCE-REUSED`, nenhum byte escrito.
- Retomada sobre `(FAILED, CLOSE_PENDING)` com a operação presente → só o salto 2.
- Depois: `_continuity_quiescence` não lista a atividade (3664, 3668); `gauntlet-context-takeover` admite; `gauntlet-activity --phase accept` recusa `ACTIVITY-STATE-DIVERGENCE` (6074-6075).

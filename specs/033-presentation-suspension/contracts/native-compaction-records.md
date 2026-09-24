# Contrato: forma dos registros nativos usados nos testes (FR-011)

Capturado em 2026-09-24 de sessões reais locais, **somente chaves e tipos**; nenhum conteúdo copiado. Os testes constroem registros mínimos com estas chaves, com valores sintéticos.

## Claude Code (`~/.claude/projects/<proj>/<sessionId>.jsonl`)

Amostra: 2515 arquivos; 34 com compactação; 52 registros `compact_boundary` em 9 variantes; versões 2.1.219 a 2.1.281. Fonte do T029: sessão `bb37d5f5…`, frase às 2026-09-19T16:41:07Z.

Marcador de compactação (chaves comuns a todas as variantes):

```json
{"type": "system", "subtype": "compact_boundary", "content": "<str>", "uuid": "<str>", "sessionId": "<str>",
 "parentUuid": null, "logicalParentUuid": "<str>", "isSidechain": false, "level": "<str>", "timestamp": "<str>",
 "compactMetadata": {"trigger": "manual|auto", "preTokens": 0, "postTokens": 0, "cumulativeDroppedTokens": 0, "durationMs": 0,
                     "preservedSegment": {"headUuid": "", "anchorUuid": "", "tailUuid": ""},
                     "preservedMessages": {"anchorUuid": "", "uuids": [], "allUuids": []}},
 "userType": "<str>", "entrypoint": "<str>", "cwd": "<str>", "version": "<str>", "gitBranch": "<str>"}
```

Variantes: `isMeta: bool` presente em 19 de 52; `slug`, `sessionKind`, `teamName`/`agentName` e `compactMetadata.preCompactDiscoveredTools` opcionais. O normalizador lê só `type`, `subtype` e `sessionId`.

Resumo pós-compactação (nunca conta como usuário):

```json
{"type": "user", "isCompactSummary": true, "isVisibleInTranscriptOnly": true, "promptId": "<str>",
 "message": {"role": "user", "content": "<str>"}, "uuid": "<str>", "sessionId": "<str>", "parentUuid": "<str>", "timestamp": "<str>"}
```

Mensagem digitada pelo usuário (a forma da frase do T029):

```json
{"type": "user", "message": {"role": "user", "content": "<str>"}, "uuid": "<str>", "sessionId": "<str>", "promptId": "<str>",
 "parentUuid": "<str>", "isSidechain": false, "permissionMode": "<str>", "origin": {"kind": "<str>"}, "promptSource": "<str>",
 "timestamp": "<str>", "userType": "<str>", "entrypoint": "<str>", "cwd": "<str>", "version": "<str>", "gitBranch": "<str>"}
```

De 7288 mensagens de usuário não-meta: 6467 com `content` string, 803 com lista de um único `{"type": "text"}`, 18 com imagem, 1 com `<system-reminder>` anexado.

## Codex (`~/.codex/sessions/AAAA/MM/DD/rollout-<ts>-<uuid>.jsonl`)

Amostra: rollout de referência `rollout-2026-08-21T09-17-09-*` (cli 0.149.0, 687 linhas, 1 `compacted`) e os 60 rollouts mais recentes (cli 0.155.1, 16 `compacted` em 2 variantes).

Envelope de todo registro: `{"timestamp": "<str>", "ordinal": <int>, "type": "<str>", "payload": {...}}`.

Primeiro registro (o normalizador exige `payload.id` ou `payload.session_id` igual ao id da sessão):

```json
{"type": "session_meta", "payload": {"id": "<uuid>", "session_id": "<uuid>", "timestamp": "<str>", "cwd": "<str>",
 "originator": "<str>", "cli_version": "<str>", "source": "<str>", "model_provider": "<str>"}}
```

Marcador de compactação (0.149.0):

```json
{"type": "compacted", "payload": {"message": "<str>", "window_number": <int>, "first_window_id": "<uuid>",
 "previous_window_id": "<uuid>", "window_id": "<uuid>",
 "replacement_history": [
   {"type": "message", "id": "<str>", "role": "user|developer", "content": [{"type": "input_text", "text": "<str>"}],
    "internal_chat_message_metadata_passthrough": {"turn_id": "<str>", "create_time": 0.0}},
   {"type": "compaction", "id": "<str>", "encrypted_content": "<str>", "internal_chat_message_metadata_passthrough": {"turn_id": "<str>"}}]}}
```

Marcador de compactação (0.155.1) acrescenta em `payload`: `guardian_history` (mesma forma de `replacement_history`), `retained_context: {"verified_answers": [], "incomplete": bool, "user_messages": [], "user_messages_incomplete": bool, "next_order": int}`, `compaction_response_id: str` e `latest_token_usage_record: {...}`. O normalizador lê só `type`; tudo em `payload` é descartado.

Mensagem do usuário (única forma observada nos 61 rollouts; nenhum `event_msg` de tipo `user_message`):

```json
{"type": "response_item", "payload": {"type": "message", "id": "<str>", "role": "user",
 "content": [{"type": "input_text", "text": "<str>"}],
 "internal_chat_message_metadata_passthrough": {"turn_id": "<str>", "create_time": 0.0}}}
```

Mensagens `role: "developer"` (instruções injetadas) têm a mesma forma e são normalizadas como `developer`, nunca `user`.

## Asserções do teste `test_native_compaction_records_become_compaction_blocks`

| Entrada | Saída de `_native_messages(raw, runtime, session_id)` |
|---|---|
| Claude `compact_boundary` | `{"id": <uuid>, "role": "system", "blocks": [{"type": "compaction"}]}` |
| Claude `isCompactSummary` | `role == "system"` |
| Claude mensagem digitada `stop adhd mode` | `{"role": "user", "blocks": [{"type": "text", "text": "stop adhd mode"}]}` |
| Codex `compacted` (as duas variantes) | `{"id": "native:<n>", "role": "system", "blocks": [{"type": "compaction"}]}`; nenhum texto de `replacement_history` na lista |
| Codex `response_item` message `role=user` | `{"id": <payload.id>, "role": "user", "blocks": [{"type": "text", "text": ...}]}` |
| Codex `response_item` message `role=developer` | `role == "developer"` |

Os blocos de compactação usados nos cenários de suspensão (`test_presentation_control_from_session_user_message`) são os devolvidos por esta normalização, não literais.

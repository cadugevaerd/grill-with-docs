# Contrato: forma dos registros nativos usados nos testes (FR-011)

Capturado em 2026-09-24 de sessões reais locais, **somente chaves e tipos**; nenhum conteúdo copiado. Os testes constroem registros mínimos com estas chaves, com valores sintéticos, e passam **todas** as mensagens de cenário por `_native_messages(raw, runtime, session_id)` (helper `native(runtime, records)` do validador; research R10). Nenhuma mensagem de cenário é literal normalizado.

As contagens abaixo são de **amostra** (a do autor e a da revisão independente diferem em tamanho e em resultado: número de variantes de chaves, versão máxima da CLI, papéis em `replacement_history`). Nenhuma lista de chaves opcionais, variantes ou versões é enumeração fechada. O contrato afirma só o que o normalizador lê.

## Claude Code (`~/.claude/projects/<proj>/<sessionId>.jsonl`)

Amostra do autor: 2515 arquivos, 34 com compactação, 52 registros `compact_boundary`, versões 2.1.219 em diante. Fonte do T029: sessão `bb37d5f5…`, frase às 2026-09-19T16:41:07Z.

O normalizador lê: `type`, `subtype`, `sessionId` (quando presente, tem de ser o da sessão), `uuid` (id da mensagem), `isMeta`/`isSynthetic`/`isCompactSummary`, `message.role`, `message.content` (string ou lista de blocos `{type, ...}`).

Marcador de compactação (chaves comuns às variantes vistas; o resto é opcional e varia):

```json
{"type": "system", "subtype": "compact_boundary", "content": "<str>", "uuid": "<str>", "sessionId": "<str>",
 "parentUuid": null, "logicalParentUuid": "<str>", "isSidechain": false, "level": "<str>", "timestamp": "<str>",
 "compactMetadata": {"trigger": "manual|auto", "preTokens": 0, "postTokens": 0, "...": "..."},
 "userType": "<str>", "entrypoint": "<str>", "cwd": "<str>", "version": "<str>", "gitBranch": "<str>"}
```

Variantes vistas: `isMeta: bool` em parte dos registros; `slug`, `sessionKind`, `teamName`/`agentName` e chaves extras de `compactMetadata` opcionais. Só `type`, `subtype` e `sessionId` importam.

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

Na amostra, a maioria das mensagens de usuário não-meta tem `content` string; o resto é lista com um único `{"type": "text"}`; multi-bloco é `image + text`; contexto de hook/harness vem em registros **separados** com `isMeta: true` (string ou lista de um `text`).

Mensagem sintética/meta (cenário US3.3 no Claude): a mesma forma de mensagem digitada com `isMeta: true` (ou `isSynthetic: true`).

Fala do agente: `{"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "<str>"}]}, "uuid": "<str>", "sessionId": "<str>"}`.

## Codex (`~/.codex/sessions/AAAA/MM/DD/rollout-<ts>-<uuid>.jsonl`)

Amostras: rollout de referência `rollout-2026-08-21T09-17-09-*` (cli 0.149.0, 1 `compacted`), os 60 rollouts mais recentes do autor (cli 0.155.1) e os 591 rollouts do revisor (cli 0.120.0–0.155.1).

Envelope de todo registro: `{"timestamp": "<str>", "ordinal": <int>, "type": "<str>", "payload": {...}}`.

O normalizador lê: `type`; em `session_meta`, `payload.id`/`payload.session_id` (primeiro registro, tem de ser o da sessão); em `response_item`, `payload.id` (id da mensagem; ausente → `native:<n>`), `payload.type`, `payload.role`, `payload.content[].type` e `.text`; em `compacted`, nada além de `type`.

Primeiro registro:

```json
{"type": "session_meta", "payload": {"id": "<uuid>", "session_id": "<uuid>", "timestamp": "<str>", "cwd": "<str>",
 "originator": "<str>", "cli_version": "<str>", "source": "<str>", "model_provider": "<str>"}}
```

Marcador de compactação — o conjunto de chaves de `payload` **varia com a versão da CLI** (há forma sem `window_*` em CLI antiga; 0.155.x acrescenta `guardian_history`, `retained_context`, `compaction_response_id`, `latest_token_usage_record`); `replacement_history` carrega itens `user`, `developer`, `assistant`, `agent_message` e `compaction`. Forma de referência (0.149.0):

```json
{"type": "compacted", "payload": {"message": "<str>", "window_number": <int>, "first_window_id": "<uuid>",
 "previous_window_id": "<uuid>", "window_id": "<uuid>",
 "replacement_history": [
   {"type": "message", "id": "<str>", "role": "user|developer|assistant", "content": [{"type": "input_text|output_text", "text": "<str>"}],
    "internal_chat_message_metadata_passthrough": {"turn_id": "<str>", "create_time": 0.0}},
   {"type": "compaction", "id": "<str>", "encrypted_content": "<str>", "internal_chat_message_metadata_passthrough": {"turn_id": "<str>"}}]}}
```

Tudo em `payload` é descartado pelo normalizador; os testes usam duas variantes (com e sem as chaves de 0.155.x) só para provar que o descarte não depende delas. Confirmado na amostra do revisor: o Codex **não reemite** `replacement_history` como `response_item` depois de `compacted`.

Mensagem do usuário — **duas formas** capturadas, mesma chave `content`, número de blocos diferente:

```json
{"type": "response_item", "payload": {"type": "message", "id": "<str>", "role": "user",
 "content": [{"type": "input_text", "text": "<str>"}],
 "internal_chat_message_metadata_passthrough": {"turn_id": "<str>", "create_time": 0.0}}}
```

```json
{"type": "response_item", "payload": {"type": "message", "id": "<str>", "role": "user",
 "content": [{"type": "input_text", "text": "<str>"},
             {"type": "input_text", "text": "<environment_context>…</environment_context>"}]}}
```

A segunda forma é, na amostra, quase sempre a **primeira mensagem do usuário na sessão** (a CLI anexa o contexto de ambiente ao mesmo `response_item`); há também a forma `(recommended_plugins, plain, environment_context)` com três blocos. O normalizador produz um bloco `text` por `input_text`; a regra de bloco único não reconhece a frase nessas formas (limitação declarada, research R2). `payload.id` pode faltar (amostra do revisor: 79 casos) → id `native:<n>`.

Injeção do harness como usuário (cenário US3.3 no Codex): a primeira forma, com `text` iniciado por tag XML (`<environment_context>`, `<codex_internal_context>`, `<hook_prompt>`). Não há marca de sintética; a mensagem permanece `role=user` e não conta só porque o texto não é a frase.

Mensagens `role: "developer"` têm a mesma forma (uma ou várias `input_text`, em geral iniciadas por tag XML) e são normalizadas como `developer`, nunca `user`. Fala do agente: `response_item` com `payload: {type: "message", id, role: "assistant", content: [{type: "output_text", text}]}`.

Nenhum `event_msg` de tipo `user_message` nas amostras (tipos vistos: `task_started`, `item_completed`, `token_count`, `task_complete`, `turn_aborted`, `thread_settings_applied`, `thread_goal_updated`); o ramo correspondente do normalizador fica sem teste com forma real.

## Asserções do teste `test_native_compaction_records_become_compaction_blocks`

| Entrada | Saída de `_native_messages(raw, runtime, session_id)` |
|---|---|
| Claude `compact_boundary` | `{"id": <uuid>, "role": "system", "blocks": [{"type": "compaction"}]}` |
| Claude `isCompactSummary` | `role == "system"` |
| Claude `isMeta` / `isSynthetic` | `role == "system"` |
| Claude mensagem digitada `stop adhd mode` (`content` string) | `{"id": <uuid>, "role": "user", "blocks": [{"type": "text", "text": "stop adhd mode"}]}` |
| Claude `assistant` com `text` | `role == "assistant"` |
| Codex `compacted` (as duas variantes) | `{"id": "native:<n>", "role": "system", "blocks": [{"type": "compaction"}]}`; nenhum texto de `replacement_history`/`retained_context` na lista |
| Codex `response_item` message `role=user`, um `input_text` | `{"id": <payload.id>, "role": "user", "blocks": [{"type": "text", "text": ...}]}` |
| Codex `response_item` message `role=user`, sem `payload.id` | `id == "native:<n>"` |
| Codex `response_item` message `role=user`, dois `input_text` (`plain`, `<environment_context>`) | `role == "user"`, dois blocos `text` (não conta como frase) |
| Codex `response_item` message `role=user`, um `input_text` iniciado por tag XML | `role == "user"`, um bloco `text` com texto ≠ frase |
| Codex `response_item` message `role=developer` | `role == "developer"` |
| Codex `response_item` message `role=assistant`, `output_text` | `role == "assistant"` |

Os cenários de suspensão (`test_presentation_control_from_session_user_message` e os demais) usam exclusivamente mensagens devolvidas por esta normalização sobre os registros acima, nos dois runtimes, concatenadas às `messages` do transcript da fixture.

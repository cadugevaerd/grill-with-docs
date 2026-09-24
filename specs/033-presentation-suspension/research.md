# Research: Suspensão e reativação da apresentação local no core

Terminologia conforme `CONTEXT.md` do work item: apresentação local, suspensão, reativação, fonte não-agente da sessão, bloco de compactação.

## R1 — Onde a suspensão é produzida

- **Decision**: um único produtor, dentro de `project_leader_presentation` (`agent_runtime.py:1107-1129`). Nova função pura `_presentation_control(messages) -> tuple[int, int, dict | None]` devolve o índice da última `stop adhd mode`, o índice da última `start adhd mode` e a mensagem da última frase (ou `-1, -1, None`). `project_leader_presentation` decide: `stop > start` → projeção suspensa; `start > stop >= 0` → reativada; caso contrário → fluxo atual sem mudança.
- **Rationale**: o laudo prova que não existe produtor em lugar nenhum (`grep suspension grill_workspace.py` → 0) e que `presentation_state` já projeta a suspensão quando recebe `application` e `suspension` (Exp A3). `_session_readiness` e todos os verbos passam por `project_leader_presentation`, então um ponto cobre preflight, init, adopt, step-enter e o refresh de contexto sem tocar chamador nenhum.
- **Alternatives considered**: produzir em `_session_readiness` (duplicaria a lógica no CLI e deixaria o fixture de teste sem caminho puro); flag de CLI `--suspended` (viola FR-006: suspensão informada pelo chamador).

## R2 — Regra de reconhecimento da frase (FR-001, FR-003)

- **Decision**: mensagem com `role == "user"`, exatamente um bloco, `block["type"] == "text"`, `block["text"].strip()` igual a `stop adhd mode` ou `start adhd mode`. Comparação exata, sensível a caixa; qualquer texto adicional, bloco extra (imagem, segundo texto) ou caixa diferente não conta.
- **Rationale**: no transcript Claude real, a frase do T029 (`bb37d5f5…`, 2026-09-19T16:41:07Z) é `type=user` com `message.content` string, que o normalizador vira um único bloco `text`; de 7288 mensagens de usuário locais não-meta, 6467 são string e 803 são lista com um único `text`; só 1 traz `<system-reminder>` junto e 18 trazem imagem — a regra de bloco único é a forma real e barra os casos com conteúdo extra. `strip()` cobre o edge case dos espaços nas pontas.
- **Alternatives considered**: busca por substring (aceitaria a frase citada dentro de outro texto, que a spec proíbe); normalizar caixa (a spec fixa comparação exata).

## R3 — Fonte não-agente da sessão (FR-004)

- **Decision**: a varredura só considera `role == "user"` na lista normalizada. Nenhuma lógica nova de origem: `_native_messages` já rebaixa para `system` os registros Claude com `isMeta`, `isSynthetic` ou `isCompactSummary` (`agent_runtime.py:680`) e já reduz o registro Codex `compacted` a um único bloco `compaction`, descartando `payload.message`, `replacement_history`, `guardian_history` e `retained_context.user_messages` (`:637-638`). `assistant`, `tool`, `developer`, `reasoning` e `system` nunca contam.
- **Rationale**: é o máximo que o transcript prova (ADR-0001). O resumo de compactação Claude é `type=user` com `isCompactSummary=true` e vira `system`; o resumo Codex nem chega à lista. A frase em `replacement_history` (Codex) ou no corpo do resumo (Claude) não tem como suspender.
- **Alternatives considered**: exigir `userType`/`promptSource` do registro nativo (não existem no transporte Orca live, que já entrega normalizado); assinatura humana externa (rejeitada no ADR-0001).

## R4 — Suspensão atravessa a compactação (FR-002)

- **Decision**: `_presentation_control` percorre `transcript["messages"]` inteiro, sem cortar no último bloco `compaction`. Só `_full_read` continua cortando (`agent_runtime.py:1074-1079`), e ele não é chamado quando a suspensão vale.
- **Rationale**: contrato (`SKILL.md` l.32): a suspensão "mantém apenas `work_ready` após compactação, sem reinjetar o corpo". Cortar na compactação faria o fluxo pedir justamente a recarga que a suspensão proíbe (Exp A2 do laudo).

## R5 — Reativação exige leitura posterior (FR-003, edge case "start sem stop")

- **Decision**: quando `start > stop >= 0`, `project_leader_presentation` passa a `_full_read` o transcript fatiado em `messages[start + 1:]`; o fluxo de carga é o atual (preflight `BLOCKED` com `load_request` seguido de `cat -- SKILL.md`, ambos depois da frase). `start adhd mode` sem `stop` anterior na sessão (`stop == -1`) não fatia nada: a leitura vigente permanece.
- **Rationale**: ADR-0002: reativar custa uma leitura integral como no início da sessão. Fatiar compõe com o corte de compactação de `_full_read` (só leituras depois de ambos contam). A spec fixa que `start` sem suspensão anterior não tem efeito.
- **Alternatives considered**: fatiar em todo `start` (violaria o edge case declarado); tratar `start` como reset total do transcript (perderia o par preflight/cat quando o preflight veio antes da frase — mas esse par é justamente o que a reativação deve invalidar, então o fatiamento é o comportamento certo).

## R6 — Registro de suspensão (FR-005, FR-007)

- **Decision**: `{"command": "stop adhd mode", "source_ref": observed["source_ref"] + ":" + message["id"], "source_sha256": sha256(text.encode("utf-8")), "session_identity": leader_session_identity(observed), "config_fingerprint": <fingerprint corrente>, "scope": scope}`. O digest é do texto do bloco como observado, antes do `strip()`. O registro é reconstruído a cada observação com a configuração corrente; por isso, depois de um upgrade, "o registro passa a identificar a configuração nova" (FR-007) sem código adicional.
- **Rationale**: é exatamente a forma que `presentation_state` valida (`agent_runtime.py:275-280`) e que `_presentation` (`agent_orchestration.py:1117-1119`) aceita como JSON. `source_ref` segue a convenção de `_full_read` (`event_ref = source_ref + ":" + event_id`). Ids reais: Claude `uuid`; Codex `payload.id` do `response_item` ou `native:<n>` no `event_msg` (`agent_runtime.py:629, 640`).
- **Alternatives considered**: digest dos bytes nativos do registro (o adapter não os expõe por mensagem; limitação já anotada no laudo).

## R7 — Gate de upgrade durante a suspensão (ADR-0003, FR-007)

- **Decision**: em `grill_workspace.py:3470-3474`, a recusa `STYLE-LOAD-UNCONFIRMED` por mudança de `config_fingerprint` ou `gwd_skill_sha256` ganha a condição adicional `and readiness["presentation"]["application"] != "suspended_by_user"`. O bloco seguinte (l.3475-3482) já grava a apresentação nova no contexto. A comparação de `session_identity`, `runtime`, `scope` e `policy_sha256` (l.3465-3467, `STYLE-SCOPE-CONFLICT`) não muda.
- **Rationale**: `require_presentation_work_ready(readiness)` (l.3462) já correu, então `application == "suspended_by_user"` implica suspensão válida na observação corrente, na mesma sessão e escopo. Uma condição, uma linha; o refresh existente faz o resto.
- **Alternatives considered**: comparar também `context["presentation"]["application"]` (desnecessário: o que vale é a observação corrente, e o contexto pode ter sido gravado antes do `stop`).

## R8 — Nenhum verbo aceita suspensão do chamador (FR-006)

- **Decision**: nenhuma flag, nenhum campo de entrada. `presentation_state` mantém assinatura e continua validando só forma; o único chamador que lhe passa `suspension` é `project_leader_presentation`, a partir do transcript observado. `_session_readiness` não muda.
- **Rationale**: o laudo Q3 mostra que a função pura aceitaria um dict forjado; o risco fica latente enquanto não houver chamador que aceite entrada externa, e este plano não cria nenhum.

## R9 — Exposição (FR-013)

- **Decision**: nenhum campo novo. A projeção já carrega `application`, `use_ready`, `work_ready` e `suspension`; todos os pontos que reportam apresentação repassam o dict inteiro: `preflight` (`grill_workspace.py:1304-1309`), `_session_readiness` (`:1655`), init/adopt (`:1720, 1736, 1792-1834`), checkpoint (`:1958, 3806`), gauntlet (`:4062-4336`), `grill_status.py:174-175` e o Store (`store.py:289-294`). O teste CLI assere `preflight` com `verdict=OK`, `application=suspended_by_user`, `use_ready=false`, `work_ready=true`, `suspension` presente e `load_request` ausente.
- **Rationale**: preencher o produtor já satisfaz o requisito em todos os pontos; acrescentar campo obrigaria a mudar `_presentation` e o schema do checkpoint sem ganho.

## R10 — Forma real dos registros nativos (FR-011, US5.2)

Capturado localmente em 2026-09-24, **somente chaves e tipos**, nenhum conteúdo copiado. Detalhe completo em `contracts/native-compaction-records.md`.

- **Claude Code** (`~/.claude/projects/*/*.jsonl`, 2515 arquivos, 34 com compactação, 52 registros `compact_boundary` em 9 variantes de chaves, versões 2.1.219–2.1.281): sempre `type="system"`, `subtype="compact_boundary"`, `content: str`, `uuid`, `sessionId`, `compactMetadata: {trigger, preTokens, postTokens, …}`; parte traz `isMeta: bool`. Resumo pós-compactação: `type="user"`, `isCompactSummary: true`, `isVisibleInTranscriptOnly: bool`, `message: {role, content: str}`. Mensagem digitada: `type="user"`, `message: {role: "user", content: str}`, `uuid`, `sessionId`, `promptId`, `origin: {kind}`, `promptSource`. Coincide com a forma anotada no laudo.
- **Codex** (rollout `~/.codex/sessions/2026/08/21/rollout-2026-08-21T09-17-09-*.jsonl`, cli 0.149.0; mais 60 rollouts recentes, cli 0.155.1, 16 registros `compacted` em 2 variantes): todo registro é `{timestamp: str, ordinal: int, type: str, payload: dict}`. `compacted.payload`: `message: str` (vazio no rollout de referência), `replacement_history: [ {type, id, role, content: [{type, text}], internal_chat_message_metadata_passthrough} ]` com papéis `user`/`developer` e um item `{type: "compaction", id, encrypted_content}`, `window_number: int`, `first_window_id`, `previous_window_id`, `window_id`; em 0.155.1 acrescenta `guardian_history`, `retained_context: {verified_answers: [], incomplete: bool, user_messages: [], user_messages_incomplete: bool, next_order: int}`, `compaction_response_id` e `latest_token_usage_record`. Mensagem do usuário: `response_item` com `payload: {type: "message", id, role: "user", content: [{type: "input_text", text}], internal_chat_message_metadata_passthrough: {turn_id, create_time}}`. Não há `event_msg` de tipo `user_message` em nenhum dos 61 rollouts inspecionados (tipos vistos: `task_started`, `item_completed`, `token_count`, `task_complete`, `thread_goal_updated`, `thread_settings_applied`). `session_meta.payload` traz `id`, `session_id`, `timestamp`, `cwd`, `originator`, `cli_version`.
- **Decision**: o teste de `_native_messages` constrói registros mínimos com essas chaves (as que o normalizador lê mais as identificadoras: `sessionId`/`uuid` no Claude, `session_meta.payload.id` no Codex) e assere: `compact_boundary` e `compacted` → `{"role": "system", "blocks": [{"type": "compaction"}]}`; `isCompactSummary` → `role=system`; mensagem digitada → `role=user` com um bloco `text`; conteúdo de `replacement_history`/`retained_context` não aparece na lista. O bloco de compactação usado nos cenários de suspensão vem de `_native_messages` sobre esses registros, não do literal abstrato `{"type": "compaction"}`.
- **Rationale**: fecha a lacuna do laudo Q2 (nenhum teste exercita a tradução nativa) e cumpre FR-011 sem copiar conteúdo. O ramo `event_msg.user_message` fica intocado e sem teste novo, porque não há captura real dele.

## R11 — Códigos de recusa (FR-010)

- **Decision**: nenhum código novo, nenhum código muda de significado. Durante a suspensão válida, `STYLE-LOAD-UNCONFIRMED` simplesmente não é emitido (a condição `application == "active"` em `agent_runtime.py:272` já cuida disso). `STYLE-SCOPE-CONFLICT` continua para sessão, runtime, escopo e policy, e para suspensão desvinculada. Faltando pré-requisito, o primeiro diagnóstico (`STYLE-DISABLED`, `STYLE-DEPENDENCY-*`, `STYLE-TRUST-PENDING`, `STYLE-CONFIG-UNPROVEN`) nomeia o que falta, como hoje.

## R12 — C1: `work_ready` só com pré-requisitos comprovados (FR-002, US1.4)

- **Decision**: nada a implementar; `presentation_state` já calcula `work_ready = prerequisites and (use_ready or (suspended and valid))` (`agent_runtime.py:287`), com `prerequisites` exigindo `config_fingerprint` observado, instalação `present`, compatibilidade `approved`, habilitação `enabled` e confiança `ready`. O teste `test_presentation_suspension_requires_prerequisites` prova pelo produtor: adapter com `enablement.state = "disabled"` e a frase no transcript → `application = suspended_by_user`, `work_ready = false`, primeiro diagnóstico `STYLE-DISABLED`; repetir com `installation.status = "missing"` e `trust.state = "pending"`.

## R13 — Versão (Constituição: bump e release)

- **Decision**: patch acima da versão publicada no momento do ship, nos oito pontos: `plugin/.claude-plugin/plugin.json`, `plugin/.codex-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.agents/plugins/marketplace.json`, `VERSION` em `tests/validate_distribution.py`, heading `# Grill with Docs vX.Y.Z` em `SKILL.md`, heading `# Protocolo de sessão vX.Y.Z` em `session-protocol.md`, heading `**vX.Y.Z` em `README.md`. Hoje: `origin/main` publica **6.0.30** (`32c4954`); a branch está em 6.0.28 com `f1475f4` cherry-picked e não contém a `main` (3 commits à frente). Alvo hoje: **6.0.31**; se a `main` avançar antes do ship, o alvo é `<publicada> + 1`, resolvido na etapa ship com `git show origin/main:plugin/.claude-plugin/plugin.json`.
- **Rationale**: cláusulas `Bump obrigatório do plugin` e `Release obrigatória por versão`; `bump-gate.yml` reprova a PR sem bump e `publish.yml` cria tag e release no push.

## R14 — Transporte Orca live e limites do offline

- **Decision**: aceitar o risco residual. No caminho `contentComplete=true`, `LeaderBoundary.transcript` usa as mensagens já normalizadas pelo Orca (`agent_runtime.py:1065-1067`); a marcação de mensagens sintéticas nesse transporte não é verificável sem runtime real (laudo H3). O fallback local (`_local_transcript`) está provado com formato real e é o caminho do T029.
- **Rationale**: os dois caminhos convergem na mesma lista normalizada e na mesma regra de bloco único; a fixture oficial (`orchestration_fixture.boundary`) usa o transporte live com `messages` explícitas, que é o que os testes de cenário exercitam.

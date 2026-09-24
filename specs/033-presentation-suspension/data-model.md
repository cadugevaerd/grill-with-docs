# Data Model: Suspensão e reativação da apresentação local no core

Nenhum schema novo. A entrega preenche campos que `grill-gwd-presentation/v1` já declara e que `_presentation` (`agent_orchestration.py`) já valida.

## Estado de apresentação (existente, agora produzido)

| Campo | Ativa (hoje) | Suspensa (novo) | Reativada (novo) |
|---|---|---|---|
| `application` | `active` | `suspended_by_user` | `active` |
| `loading` | `unconfirmed` / `loaded` | `stale` | `unconfirmed` até leitura posterior à frase, depois `loaded` |
| `load_request` | pedido quando não `loaded` | `None` | pedido até leitura posterior à frase |
| `use_ready` | `prerequisites and loaded` | `false` | `prerequisites and loaded` (leitura posterior) |
| `work_ready` | `= use_ready` | `prerequisites and valid_suspension` | `= use_ready` |
| `suspension` | `None` | registro abaixo | `None` |
| `diagnostics` | `STYLE-LOAD-UNCONFIRMED` quando não lida | só pré-requisitos ausentes, nunca `STYLE-LOAD-UNCONFIRMED` | como ativa |

Todos os demais campos (`installation`, `compatibility`, `enablement`, `trust`, `behavior`, `evidence`, `functional_verified`) não mudam de cálculo.

## Registro de suspensão (`presentation.suspension`)

| Chave | Tipo | Origem | Regra |
|---|---|---|---|
| `command` | `str` | literal | sempre `stop adhd mode` |
| `source_ref` | `str` | `observed["source_ref"] + ":" + message["id"]` | id normalizado da mensagem de usuário (Claude `uuid`; Codex `payload.id` ou `native:<n>`) |
| `source_sha256` | `str` hex 64 | `sha256(block["text"].encode("utf-8"))` | digest do texto observado no bloco, antes de `strip()` |
| `session_identity` | `str` | `leader_session_identity(observed)` | igual ao da projeção; outra sessão/incarnation invalida |
| `config_fingerprint` | `str` | `_presentation_config_fingerprint(...)` corrente | reconstruído a cada observação: depois de upgrade aponta a configuração nova (FR-007) |
| `scope` | `dict` | `scope` da observação | `{"kind": "gwd", "root", "work_id"}` |

Validado por `presentation_state` (`valid_suspension`) e persistido tal qual no `presentation` do contexto.

## Frase de controle (entrada lida)

| Campo | Regra |
|---|---|
| `message["role"]` | `user`, e só `user` |
| `message["blocks"]` | exatamente um bloco |
| `blocks[0]["type"]` | `text` |
| `blocks[0]["text"].strip()` | igual a `stop adhd mode` ou `start adhd mode`, sensível a caixa |
| posição | vale a mais recente entre as duas; a varredura não corta na compactação |

Resultado de `_presentation_control(messages)`: `(stop_index, start_index, message)`, com `-1` para ausência.

## Decisão em `project_leader_presentation`

```text
stop_index > start_index            -> suspensa: presentation_state(**kwargs, application="suspended_by_user",
                                                   loading={"stale": True}, suspension=registro); _full_read não é chamado
start_index > stop_index >= 0       -> reativada: fluxo atual com _full_read sobre messages[start_index + 1:]
stop_index == -1                    -> fluxo atual, inalterado (inclui "start" sem "stop" anterior)
```

## Contexto de orquestração (existente, inalterado)

`contexts[id].presentation` recebe a projeção suspensa pelo refresh existente (`grill_workspace.py`, bloco `if context["presentation"] != readiness["presentation"]`). Nenhuma chave nova no Store, no checkpoint (`grill-continuity-checkpoint/v2`) nem no `state.json` do work item.

## Marcador de compactação (existente, agora testado com forma real)

| Runtime | Registro nativo | Normalizado |
|---|---|---|
| Claude Code | `type="system"`, `subtype="compact_boundary"` | `{"role": "system", "blocks": [{"type": "compaction"}]}` |
| Claude Code | `type="user"`, `isCompactSummary=true` | `role="system"` (nunca `user`) |
| Codex | `type="compacted"` | `{"role": "system", "blocks": [{"type": "compaction"}]}`; `replacement_history`, `guardian_history` e `retained_context` descartados |

Formas completas (chaves e tipos) em `contracts/native-compaction-records.md`.

## Transições

```text
ativa --(stop adhd mode, user, bloco único)--> suspensa
suspensa --(compactação, upgrade de plugin ou de configuração)--> suspensa (registro reconstruído)
suspensa --(start adhd mode, user, bloco único)--> ativa sem leitura (load_request pedido)
ativa sem leitura --(preflight BLOCKED + cat posterior à frase)--> ativa loaded
qualquer --(nova sessão, runtime ou incarnation)--> ativa (transcript novo, sem frase)
qualquer --(pré-requisito ausente)--> work_ready=false, diagnóstico nomeia o pré-requisito
```

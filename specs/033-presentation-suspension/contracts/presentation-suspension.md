# Contrato: suspensão e reativação da apresentação local

## Frases de controle

| Frase | Efeito | Condições |
|---|---|---|
| `stop adhd mode` | suspende | mensagem `role=user` da própria sessão, com `id` string não vazio; bloco único `text`; igualdade exata após `strip()` |
| `start adhd mode` | reativa | as mesmas; só tem efeito se houve `stop` anterior na sessão |

Entre as duas, vale a mais recente. Fala do agente, resumo de compactação, mensagem sintética/meta (Claude) e mensagens `tool`, `developer`, `reasoning` nunca mudam o estado. Caixa diferente, texto extra ou bloco extra não contam; mensagem `user` sem `id` é ignorada.

Limitações declaradas (research R2, R3, R14):

- **Codex, primeira mensagem da sessão**: a CLI anexa `<environment_context>` como segundo bloco `input_text` do mesmo `response_item`; a frase dita ali tem dois blocos e não conta. Repetir a frase numa mensagem posterior.
- **Codex, sintética**: o rollout não marca mensagem sintética; injeções do harness chegam como `role=user` de bloco único iniciado por tag XML e só não contam porque o texto não é a frase.

## Projeção

| Estado | `application` | `loading` | `use_ready` | `work_ready` | `load_request` | `suspension` |
|---|---|---|---|---|---|---|
| suspensa, pré-requisitos ok | `suspended_by_user` | `stale` | `false` | `true` | ausente | registro |
| suspensa, pré-requisito ausente | `suspended_by_user` | `stale` | `false` | `false` | ausente | registro; diagnóstico nomeia o pré-requisito |
| reativada, sem leitura posterior | `active` | `unconfirmed` | `false` | `false` | presente (`STYLE-LOAD-UNCONFIRMED`) | ausente |
| reativada, leitura posterior à frase | `active` | `loaded` | `true` | `true` | ausente | ausente |

A suspensão persiste através de compactação, upgrade do plugin e mudança de configuração na mesma sessão, incarnation e escopo. Nova sessão, runtime ou incarnation começa ativa.

## Registro de suspensão

```json
{"command": "stop adhd mode",
 "source_ref": "<observed.source_ref>:<id da mensagem>",
 "source_sha256": "<sha256 do texto do bloco>",
 "session_identity": "<leader_session_identity(observed)>",
 "config_fingerprint": "<fingerprint da observação corrente>",
 "scope": {"kind": "gwd", "root": "<root>", "work_id": "<id ou null>"}}
```

## Entrada dos verbos

- Nenhum verbo aceita suspensão informada pelo chamador: não há flag nem campo. A suspensão só nasce da observação do transcript em `project_leader_presentation`.
- Todo ponto que reporta `presentation` (preflight, init, adopt, step-enter, checkpoint, gauntlet, status, Store) expõe `application`, `use_ready`, `work_ready` e `suspension` pelo mesmo dict, sem campo novo.
- A política `assets/agent-orchestration.v1.json` não muda: `suspend_command` é declarativo (nenhum leitor no código); as duas frases são literais em `agent_runtime.py`; editar o asset mudaria `policy_sha256` e derrubaria todo contexto aberto em `STYLE-SCOPE-CONFLICT` (research R8).

## Gate de upgrade (`_gauntlet_authorized`)

Quem recusa `STYLE-LOAD-UNCONFIRMED` é `_session_readiness` (`grill_workspace.py:1646-1650`): apresentação ativa e não lida projeta `work_ready=false` com esse diagnóstico e o verbo para ali, antes do gate. O gate (`:3462` em diante) só recebe `work_ready=true`, que é `use_ready=true` (ativa, lida) ou suspensão válida. O bloco que recusaria `STYLE-LOAD-UNCONFIRMED` por mudança de `config_fingerprint`/`gwd_skill_sha256` sem `use_ready` (`:3468-3474`) é removido: hoje inalcançável, com o produtor seria a recusa errada (research R7).

| Mudança observada | Apresentação corrente ativa | Apresentação corrente suspensa |
|---|---|---|
| `session_identity`, `runtime`, `scope` ou `policy_sha256` | `STYLE-SCOPE-CONFLICT` no gate (inalterado) | `STYLE-SCOPE-CONFLICT` no gate (inalterado) |
| `config_fingerprint` ou `gwd_skill_sha256`, apresentação não lida | `STYLE-LOAD-UNCONFIRMED` por `_session_readiness`, antes do gate (inalterado) | **liberado**: `_session_readiness` devolve `work_ready=true`; o gate não recusa e o refresh grava a apresentação nova com `application=suspended_by_user` e o registro com a configuração nova |
| `config_fingerprint` ou `gwd_skill_sha256`, apresentação lida (`use_ready=true`) | liberado; refresh grava a apresentação nova (inalterado) | — |

Teste do gate: caso existente em `tests/validate_task_import_contract.py` (`test_same_context_presentation_refresh_preserves_imported_history`, l.179-185), invertido e movido para o fim do método: readiness suspensa com `config_fingerprint` novo entra (`ENTERED`), é persistida com `application=suspended_by_user` e o registro novo, `revision` avança em um.

## Códigos

Nenhum código novo. Nenhum código existente muda de significado. `STYLE-LOAD-UNCONFIRMED` não é emitido enquanto a suspensão vale; seu emissor continua sendo a projeção (`presentation_state`) lida por `_session_readiness`.

## Texto do contrato publicado (FR-012)

Quatro lugares, todos no nó de documentação da partition.

Substituir, em `plugin/skills/grill-with-docs/SKILL.md` §"Bootstrap de apresentação obrigatório" (l.32), o trecho de "`stop adhd mode` documentado…" até "…exigem nova leitura." por:

> `stop adhd mode`, dito como conteúdo único de uma mensagem de usuário da própria sessão (fonte não-agente: num despacho Orca pode ser o coordenador), suspende a apresentação: mantém apenas `work_ready`, com `use_ready=false` e `loading=stale`, antes e depois de compactação na mesma sessão/incarnation/escopo, sem reinjetar o corpo, inclusive durante upgrade do plugin ou mudança de configuração. Fala do agente, resumo de compactação e mensagem sintética nunca suspendem nem reativam. `start adhd mode`, nas mesmas condições, é a reativação explícita: volta ao padrão ativo e exige nova leitura integral posterior à frase. Nova sessão e troca de runtime/incarnation também voltam ao padrão ativo e exigem nova leitura.

Substituir, em `plugin/skills/grill-with-docs/references/session-protocol.md` §"Apresentação local obrigatória" (l.9), a frase "`stop adhd mode` é a única suspensão local: requer fonte humana da mesma sessão/incarnation/escopo, deixa `work_ready=true` somente após revalidar instalação, compatibilidade, enablement e trust, mantém `loading=stale` e não recarrega/aplica o corpo. A sessão nova não herda essa suspensão." por:

> `stop adhd mode` é a única suspensão local: requer fonte não-agente da própria sessão (mensagem de usuário do transcript, como conteúdo único; num despacho Orca pode ser o coordenador), nunca fala do agente, resumo de compactação ou mensagem sintética; deixa `work_ready=true` somente após revalidar instalação, compatibilidade, enablement e trust, mantém `loading=stale`, não recarrega/aplica o corpo e sobrevive a compactação, upgrade e mudança de configuração na mesma sessão/incarnation/escopo, com o registro apontando a configuração corrente. `start adhd mode`, nas mesmas condições, é a reativação explícita e exige leitura integral posterior à frase. A sessão nova não herda essa suspensão.

Substituir, em `README.md` (l.72), a frase "`stop adhd mode` suspende somente a apresentação na mesma sessão/incarnation/escopo: revalidar fonte humana e pré-requisitos, permitir `work_ready=true` sem reinjeção, com `use_ready=false` e `functional_verified=false`." por:

> `stop adhd mode`, dito como conteúdo único de uma mensagem de usuário da própria sessão (fonte não-agente; num despacho Orca pode ser o coordenador), suspende somente a apresentação na mesma sessão/incarnation/escopo: pré-requisitos revalidados, `work_ready=true` sem reinjeção, `use_ready=false` e `functional_verified=false`, inclusive após compactação, upgrade ou mudança de configuração. `start adhd mode`, nas mesmas condições, reativa e exige nova leitura integral posterior à frase.

Substituir, em `plugin/skills/grill-with-docs/references/agent-orchestration.md` §"Apresentação local GWD" (l.25), a frase "`stop adhd mode` suspende somente a apresentação na sessão comprovada; nova sessão volta ao default ativo." por:

> `stop adhd mode`, dito como conteúdo único de uma mensagem de usuário da própria sessão (fonte não-agente), suspende somente a apresentação nessa sessão; `start adhd mode`, nas mesmas condições, reativa e exige nova leitura integral; nova sessão volta ao default ativo.

Os headings de versão de `SKILL.md`, `session-protocol.md` e `README.md` mudam no bump (R13).

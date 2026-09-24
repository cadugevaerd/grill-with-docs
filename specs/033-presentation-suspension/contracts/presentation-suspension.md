# Contrato: suspensão e reativação da apresentação local

## Frases de controle

| Frase | Efeito | Condições |
|---|---|---|
| `stop adhd mode` | suspende | mensagem `role=user` da própria sessão; bloco único `text`; igualdade exata após `strip()` |
| `start adhd mode` | reativa | as mesmas; só tem efeito se houve `stop` anterior na sessão |

Entre as duas, vale a mais recente. Fala do agente, resumo de compactação, mensagem sintética/meta e mensagens `tool`, `developer`, `reasoning` nunca mudam o estado. Caixa diferente, texto extra ou bloco extra não contam.

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

## Gate de upgrade (`_gauntlet_authorized`)

| Mudança observada | Apresentação corrente ativa | Apresentação corrente suspensa |
|---|---|---|
| `session_identity`, `runtime`, `scope` ou `policy_sha256` | `STYLE-SCOPE-CONFLICT` (inalterado) | `STYLE-SCOPE-CONFLICT` (inalterado) |
| `config_fingerprint` ou `gwd_skill_sha256`, sem `use_ready` | `STYLE-LOAD-UNCONFIRMED` (inalterado) | **liberado**; o contexto grava a apresentação nova com `application=suspended_by_user` e o registro com a configuração nova |

## Códigos

Nenhum código novo. Nenhum código existente muda de significado. `STYLE-LOAD-UNCONFIRMED` não é emitido enquanto a suspensão vale.

## Texto do contrato publicado (FR-012)

Substituir, em `plugin/skills/grill-with-docs/SKILL.md` §"Bootstrap de apresentação obrigatório" (l.32), o trecho de "`stop adhd mode` documentado…" até "…exigem nova leitura." por:

> `stop adhd mode`, dito como conteúdo único de uma mensagem de usuário da própria sessão (fonte não-agente: num despacho Orca pode ser o coordenador), suspende a apresentação: mantém apenas `work_ready`, com `use_ready=false` e `loading=stale`, antes e depois de compactação na mesma sessão/incarnation/escopo, sem reinjetar o corpo, inclusive durante upgrade do plugin ou mudança de configuração. Fala do agente, resumo de compactação e mensagem sintética nunca suspendem nem reativam. `start adhd mode`, nas mesmas condições, é a reativação explícita: volta ao padrão ativo e exige nova leitura integral posterior à frase. Nova sessão e troca de runtime/incarnation também voltam ao padrão ativo e exigem nova leitura.

Substituir, em `plugin/skills/grill-with-docs/references/session-protocol.md` §"Apresentação local obrigatória" (l.9), a frase "`stop adhd mode` é a única suspensão local: requer fonte humana da mesma sessão/incarnation/escopo, deixa `work_ready=true` somente após revalidar instalação, compatibilidade, enablement e trust, mantém `loading=stale` e não recarrega/aplica o corpo. A sessão nova não herda essa suspensão." por:

> `stop adhd mode` é a única suspensão local: requer fonte não-agente da própria sessão (mensagem de usuário do transcript, como conteúdo único; num despacho Orca pode ser o coordenador), nunca fala do agente, resumo de compactação ou mensagem sintética; deixa `work_ready=true` somente após revalidar instalação, compatibilidade, enablement e trust, mantém `loading=stale`, não recarrega/aplica o corpo e sobrevive a compactação, upgrade e mudança de configuração na mesma sessão/incarnation/escopo, com o registro apontando a configuração corrente. `start adhd mode`, nas mesmas condições, é a reativação explícita e exige leitura integral posterior à frase. A sessão nova não herda essa suspensão.

Os headings de versão dos dois arquivos mudam no bump (R13).

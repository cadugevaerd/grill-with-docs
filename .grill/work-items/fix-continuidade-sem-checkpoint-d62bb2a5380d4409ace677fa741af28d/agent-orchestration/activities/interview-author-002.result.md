# Relatório do autor — interview-author-002 (fable/xhigh)

- work item: `fix-continuidade-sem-checkpoint-d62bb2a5380d4409ace677fa741af28d` (W), plugin 6.0.30, worktree `/home/carlosaraujo/orca/workspaces/grill-with-docs/fix-leader`
- activity: `interview-author-002`, context `ctx-0c0155ef5a94`, fence 1, dispatch `ctx_13f383f025a1`, launch efetivo = requested (claude/fable/xhigh)
- payload lido por inteiro: `agent-orchestration/activities/interview-author-002.payload.md` sha256 `f247a77d70063741d608c43752a059ddf3cbf68998dbd6b52d6be235baabf376`
- adendo lido por inteiro (DQ-0007): `interview-author-002.payload-addendum.md` sha256 `1ea5e8ba9f28dc5e692078a46b3413292555d3d05b1c8cf26dc2d496c9de73c3` (fora do input manifest, por decisão do líder)
- input manifest: 15/15 sha256 conferidos, zero divergência
- nada escrito em `.grill/` nem em `.specify/reports/`; nenhum relatório de outra sessão de autor foi lido

## Evidência viva colhida nesta sessão (read-only)

- Store (revision 3240): `current_context_id=ctx-0c0155ef5a94` ACTIVE epoch 1, líder `orca:ctx_ad48e72ddf4c` ACTIVE fence 1, `campaign=None`, `checkpoint_head=None`; `interview-author-001` author `RESULT_RECORDED` attempt 1, recurso `session-41f426b742f4d78264386360` `CLOSE_PENDING` owner `ctx_2923e0218c89`, `result_acceptance_ref=None`; `interview-author-002` author `DISPATCHED`, recurso `REGISTERED` owner `ctx_13f383f025a1`.
- Orca `worker-show --dispatch ctx_2923e0218c89`: `dispatch.status=completed`, `completedAt=capabilityRevokedAt=2026-09-24T13:09:45.059Z`, `worker.stage=settled`, `worker.state=succeeded`, `projection.liveness={verdict: unverifiable, reason: missing_status}`, `terminalResource.ownershipState=user_owned`, `releaseState=retained`, `retainedReason=user_takeover`, `archive={source: null, status: null}`, `terminal.connected=false`, `terminal.writable=false`, `terminal.orphaned=false`, `observation={status: exited, exactWorker: true}`. Confirma a variante 2 do adendo.
- Caso X7 (leituras literais do coordenador em `DECISION-FRONTIER.md` DQ-0001/DQ-0005): `ACTIVE None False []`; `A converge-final-author-x7-3 author DISPATCHED ctx-3d2202b3201b converge REGISTERED ctx_822340e6d1d1`; `R session-1b989c4a052f0b3550a2e811 session REGISTERED`. Variante 1: atividade `DISPATCHED`, recurso `REGISTERED`, líder liberado.

## CONTEXT.md

```markdown
# CONTEXT

## Glossário

| Termo canônico | Definição | Termos a evitar | Evidência |
|---|---|---|---|
| atividade órfã | Atividade de especialista em `DISPATCHED` cujo dispatch Orca já terminou sem resultado gravado e cujo líder de origem também terminou; nenhum verbo existente a leva a estado terminal. | atividade travada, atividade zumbi, atividade pendente | DQ-0005/DQ-0006; X7 `converge-final-author-x7-3 DISPATCHED` com líder liberado; `_continuity_quiescence` conta `DISPATCHED` como ativa (grill_workspace.py:3654-3672) |
| sessão retida | Atividade `RESULT_RECORDED` cujo recurso de sessão ficou `CLOSE_PENDING` porque o Orca reteve o terminal (`releaseState=retained`, `ownershipState=user_owned`, `retainedReason=user_takeover`) com liveness `unverifiable`; o aceite recusa `SESSION-CLOSE-UNPROVEN` e não há aresta para `FAILED`. | sessão presa, terminal fantasma | DQ-0007 (adendo); `interview-author-001`/`ctx_2923e0218c89` observado nesta sessão; agent_runtime.py:1222-1233; agent_orchestration.py:972-977 |
| fence autorizado | Rota de recuperação, preview-first, que leva uma atividade órfã ou de sessão retida a estado terminal não aceito e fecha seu recurso de sessão, somente com prova terminal Orca do especialista e do líder e autorização humana exata. | cancelamento, abandono de atividade, limpeza automática | DQ-0006 opção A; DQ-0007; precedente `gauntlet-run-abandon` (grill_workspace.py:5153-5195) |
| prova terminal Orca | Observação correlacionada do dispatch exato via `worker-show`: `status` fora de `dispatched|running`, ou `capabilityRevokedAt` não nulo, ou liveness `exited` por `agent_status`. Silêncio, expiry, liveness `unverifiable` sozinha e observação incompleta não provam nada. | timeout, lease vencido, "não responde" | agent_runtime.py:1249-1292 `observe_predecessor_termination`; grill_workspace.py:1565-1610; session-protocol.md:85-87 |
| autorização humana exata | Documento `human-authorization/v1` (`schema`, `scope`, `decision=APPROVED`, `authorized_by`, `receipt_ref`, `content_sha256`) cujo `scope` vincula `work_id + context_id + activity_id` exatos; escopo de outro contexto, atividade ou run é inválido. | aprovação verbal, flag `--force`, `--yes` | attestation.py:191-193, 773-781; DQ-0006; precedente `gauntlet-run-abandon` com `scope == run_id` |
| takeover | `gauntlet-context-takeover`: sessão nova assume o work item após prova terminal do líder anterior; herda só workers `PREPARED`; qualquer atividade em voo recusa `TAKEOVER-WORK-ACTIVE`. | retomada, resume, switch | grill_workspace.py:4126-4345; session-protocol.md:85 |
| quiescência | Conjunto vazio de atividades ativas e sessões desconhecidas. Ativa = `BOOTSTRAPPING|VERIFIED|DISPATCHED|RESULT_RECORDED` sem sessão `CLOSED` com `result_acceptance_ref == result_ref`; `FAILED` e `ACCEPTED` são quietas. | inatividade, silêncio, ociosidade | grill_workspace.py:3654-3672 |
| attempt 2 | Reexecução do autor no contexto sucessor, depois do takeover, como atividade nova; o resultado da atividade fenced nunca é aceito nem herdado. | retry do resultado, reaproveitamento, aceite tardio | DQ-0006 (resolution); session-protocol.md:87 "Resultados de atividades nunca herdam essas exceções" |
| resultado não aceito | Estado terminal `FAILED` da atividade fenced: sem `acceptance_ref`, sem `accepted_by_context`, sem `review_verdict`; `gauntlet-activity --phase accept` passa a recusar `ACTIVITY-STATE-DIVERGENCE`. | resultado descartado, resultado arquivado | agent_orchestration.py:45-48; grill_workspace.py:6074-6075 |

> Somente linguagem ubíqua; decisões e tarefas vivem em ADR/BL/ROADMAP.
```

## docs/adr/ADR-0001.md

```markdown
---
managed-by: grill-with-docs/v1
id: ADR-0001
title: Atividade órfã ou de sessão retida sai por fence autorizado; o resultado nunca é aceito e o sucessor reexecuta como attempt 2
status: accepted
evidence-status: verified
sources:
  - type: repo
    title: Protocolo de sessão — continuidade, takeover e exceção exclusiva do run-abandon
    url: plugin/skills/grill-with-docs/references/session-protocol.md
    version: 6.0.30
    section: linhas 85-87 ("Resultados de atividades nunca herdam essas exceções")
    consulted: 2026-09-24
  - type: repo
    title: attestation.py — human-authorization/v1
    url: plugin/skills/grill-with-docs/scripts/grill_core/attestation.py
    version: 6.0.30
    section: 191-193 (_HUMAN_AUTHORIZATION_KEYS), 773-781 (_validate_human_authorization)
    consulted: 2026-09-24
  - type: repo
    title: grill_workspace.py — quiescência, takeover e run-abandon
    url: plugin/skills/grill-with-docs/scripts/grill_workspace.py
    version: 6.0.30
    section: 3654-3672, 3432-3441, 4126-4345, 5153-5195, 6074-6083
    consulted: 2026-09-24
  - type: repo
    title: agent_orchestration.py — estados e arestas de atividade/recurso
    url: plugin/skills/grill-with-docs/scripts/grill_core/agent_orchestration.py
    version: 6.0.30
    section: 45-49, 639-660, 917-930, 959-992, 1376-1380, 1529-1554
    consulted: 2026-09-24
  - type: decision
    title: DQ-0006 (R-0005) e DQ-0007 (adendo, msg_ff60609e12bb) — decisões humanas do coordenador
    url: DECISION-FRONTIER.md
    version: 2026-09-24
    section: DQ-0002, DQ-0005, DQ-0006, adendo DQ-0007
    consulted: 2026-09-24
---
# ADR-0001 — Atividade órfã ou de sessão retida sai por fence autorizado; o resultado nunca é aceito e o sucessor reexecuta como attempt 2

## Contexto
O takeover exige quiescência: toda atividade `BOOTSTRAPPING|VERIFIED|DISPATCHED|RESULT_RECORDED` sem sessão `CLOSED` correlacionada ao resultado conta como ativa (grill_workspace.py:3654-3672) e recusa `TAKEOVER-WORK-ACTIVE` (4169-4174). Só workers `PREPARED` são herdados (3675-3680, session-protocol.md:85). No X7 a atividade `converge-final-author-x7-3` ficou `DISPATCHED` com recurso `REGISTERED`, o especialista terminou sem gravar resultado e o líder foi liberado (DQ-0005). Nenhum verbo alcança esse estado: `--diagnostic` exige o líder corrente (`@_gauntlet_authorized`, 3393) e `prepare-switch --released-source` só aquieta `RESULT_RECORDED` com release arquivado (3684-3714). O adendo DQ-0007 acrescenta a variante de sessão retida: `RESULT_RECORDED` com recurso `CLOSE_PENDING` e terminal retido pelo Orca (`retained/user_owned/user_takeover`, liveness `unverifiable`), observada nesta sessão em `interview-author-001`/`ctx_2923e0218c89`; o aceite recusa `SESSION-CLOSE-UNPROVEN` (agent_orchestration.py:972-977; agent_runtime.py:1222-1233) e `RESULT_RECORDED → FAILED` não é aresta válida (agent_orchestration.py:48).

O protocolo já fixa o princípio: a prova de líder liberado só é herdada por `gauntlet-run-abandon`, e ainda assim com autorização humana exata para o run; "Resultados de atividades nunca herdam essas exceções" (session-protocol.md:87). O precedente valida `human-authorization/v1` com `scope == run_id` (attestation.py:773-781; grill_workspace.py:5175-5186).

## Decisão
Rota de **fence autorizado** (DQ-0006 opção A, estendida por DQ-0007): verbo novo preview-first com `--apply --expected-sha256`, que exige (1) prova terminal Orca do dispatch do especialista **e** do líder da atividade e (2) `human-authorization/v1` com `scope` vinculado a `work_id + context_id + activity_id` exatos. O fence leva a atividade a `FAILED` com `diagnostic_ref` apontando o receipt do fence e fecha o recurso de sessão com receipt correlacionado. O resultado gravado, quando existir, **não é aceito**: nenhum `acceptance_ref`, nenhum `accepted_by_context`, nenhum aceite posterior. O contexto sucessor, após o takeover, reexecuta o autor como attempt 2 (atividade nova). A variante de sessão retida entra no mesmo verbo; a aresta que lhe falta é decisão pendente (DQ proposta abaixo).

## Opções e custos
Rótulos B/C conforme a rodada DQ-0006; o texto das alternativas é reconstrução deste autor a partir da evidência da fronteira — o líder confere contra a pergunta original.
- **A (escolhida): fence autorizado, resultado não aceito, attempt 2 no sucessor.** benefício: coerente com session-protocol.md:87 e com o precedente do run-abandon (mesma forma de autorização, mesma família de recusas), fail-closed em cada prova, sem mexer em takeover/prepare-switch; **custo:** verbo e códigos novos no contrato público, um humano no loop a cada órfã, e reexecução do autor (custo de tokens) mesmo quando um resultado já existe na variante 2.
- **B: quiescência automática por observação.** takeover ou prepare-switch aquietariam a órfã só com a prova terminal do especialista; benefício: zero fricção; **custo:** torna a exceção do run-abandon herdável por atividades, o que o protocolo proíbe (87); silêncio/expiry viram prova; sem rastro humano da decisão de descartar trabalho (Constituição: fail-closed sem waiver, rastreabilidade).
- **C: aceitar ou transferir o resultado gravado para o sucessor.** benefício: não perde o resultado da variante 2; **custo:** aceite sem prova de fechamento da sessão exata (`SESSION-CLOSE-UNPROVEN` existe para isso), resultado de contexto superseded herdado por contexto novo, e na variante 1 nem existe resultado; contradiz "sem aceitar nem reexecutar" do protocolo.

## Consequências
- Estado terminal novo alcançável por verbo: `DISPATCHED → FAILED` já é aresta válida (agent_orchestration.py:48); `RESULT_RECORDED → FAILED` não é e exige decisão (DQ proposta 0009).
- `_continuity_quiescence` deixa de contar a atividade fenced; o takeover passa a abrir sem tocar na regra de herança de workers `PREPARED`.
- O fence é registrado como operação `CONFIRMED` sob o contexto da atividade, com o fence do líder daquele contexto (agent_orchestration.py:1376-1380), a autorização verbatim e os digests das duas observações — mesma rastreabilidade do run-abandon (gauntlet_runs.py:3119-3126).
- `gauntlet-activity --phase accept` sobre a atividade fenced recusa `ACTIVITY-STATE-DIVERGENCE` (grill_workspace.py:6074-6075): a não-aceitação é estrutural, não convenção.
- Attempt 2 é atividade nova no contexto sucessor; o campo `attempt` é identidade write-once e o CLI grava 1 (agent_orchestration.py:1529; grill_workspace.py:5990) — ver DQ proposta 0010.
- Fora do escopo, por DQ-0002: SGD-37 (transcript > 16 MiB), SGD-38 (KeyError com `campaign` e head nulo), checkpoint automático. Nada muda em Constituição, WORKFLOW, `ESSENTIAL` ou registries.
- Bump de distribuição obrigatório nos oito pontos (CLAUDE.md, "Distribuição").

## Relações
- amends: none
- supersedes: none
- superseded-by: none
- exception: none
- backlog: SGD-37, SGD-38 (registrados em DQ-0002; não são BL deste work item)
```

## ROADMAP.md

```markdown
# ROADMAP

- execution-order: FASE-001

## FASE-001 — Fence autorizado de atividade órfã
- state: ready-for-specify
- objetivo: um work item cujo líder terminou com uma atividade de especialista órfã (`DISPATCHED`, sem resultado) ou de sessão retida (`RESULT_RECORDED`, recurso `CLOSE_PENDING`, terminal retido pelo Orca) volta a admitir `gauntlet-context-takeover` por um verbo preview-first que exige prova terminal Orca do especialista e do líder e autorização humana exata, leva a atividade a estado terminal não aceito, fecha o recurso com receipt e deixa o autor ser reexecutado como attempt 2 no contexto sucessor. Observável: no X7, `TAKEOVER-WORK-ACTIVE` some após o fence; no work item corrente, `interview-author-001` deixa de contar como ativa.
- scope-in: verbo novo com preview/apply e `--expected-sha256`; prova terminal do especialista e do líder pela mesma observação do takeover; `human-authorization/v1` com `scope = work_id + context_id + activity_id`; transição da atividade para `FAILED` com `diagnostic_ref` do receipt; fechamento do recurso de sessão com receipt correlacionado; operação `CONFIRMED` rastreável; os quatro testes negativos de DQ-0006 mais preview sem escrita, hash stale e replay idempotente; documentação do verbo no protocolo de sessão; bump nos oito pontos de distribuição.
- scope-out: SGD-37 (transcript do líder > 16 MiB); SGD-38 (KeyError do prepare-switch com `campaign` preenchido e head nulo); prevenção por checkpoint automático (T005 já cobre head nulo); aceitar, transferir ou reaproveitar o resultado gravado; fence de workers de run (já coberto por `gauntlet-run-abandon`); alterações em Constituição, WORKFLOW, `ESSENTIAL`, registries ou no Orca; mudança nas regras de herança do takeover.
- context-refs: atividade órfã, sessão retida, fence autorizado, prova terminal Orca, autorização humana exata, takeover, quiescência, attempt 2, resultado não aceito
- ADRs: ADR-0001
- BLs: none
- depends-on: none
- specify-handoff: handoffs/FASE-001-SPECIFY-HANDOFF.md
- delivery-units: DU-001

> Estados: `planned | ready-for-specify | blocked | complete | superseded`. `complete` e `superseded` são terminais. `execution-order` é explícita, topológica e independente dos números de fase. Cada fase tem um handoff exclusivo; somente a primeira incompleta pode ficar `ready-for-specify`. Se todas forem terminais e não houver BL/DQ material aberto, grave `milestone_status=completed`, `state.status=complete`, `active_phase=null` e `audit_verdict=GO`; a auditoria retorna `MILESTONE-COMPLETE`.

## Delivery First
Feature/fix phases are plan-only. Hotfix-fast incidents are tracked in the work-item HOTFIX.md and reconciled after ship.
```

## handoffs/FASE-001-SPECIFY-HANDOFF.md

```markdown
# FASE-001 — Fence autorizado de atividade órfã

- phase: FASE-001
- state: ready-for-specify
- roadmap: ROADMAP.md#FASE-001
- context-refs: atividade órfã, sessão retida, fence autorizado, prova terminal Orca, autorização humana exata, takeover, quiescência, attempt 2, resultado não aceito
- ADRs: ADR-0001
- BLs: none

## WHAT
- delivery-units: DU-001
- development-type: platform-devops

### Resultado
Um operador com autorização humana exata consegue encerrar, sem aceitar, uma atividade de especialista órfã ou de sessão retida, de modo que o work item volte a admitir takeover e o contexto sucessor reexecute o autor como attempt 2. A rota é preview-first: a prévia mostra exatamente o que será encerrado e um hash; só a aplicação com esse hash muda o estado.

### Atores
- **Líder sucessor**: sessão nova que precisa assumir o work item e é recusada por trabalho ativo de uma atividade sem dono.
- **Humano autorizador**: quem decide descartar o trabalho da atividade e assina a autorização exata para este work item, este contexto e esta atividade (no adendo DQ-0007 a decisão chegou como mensagem do coordenador; é esse tipo de recibo que a autorização referencia).
- **Especialista órfão**: sessão de autor cujo dispatch já terminou; ou não gravou resultado (variante 1), ou gravou mas sua sessão ficou retida pelo Orca e nunca poderá provar fechamento (variante 2).
- **Líder corrente** (só na variante 2): líder vivo que pede o fence de uma atividade própria de sessão retida — autoridade a decidir em DQ proposta 0008.

### Cenários
1. **Órfã (caso X7)**: atividade `DISPATCHED`, especialista terminado, líder liberado. Prévia lista a atividade, os dois dispatches e seus veredictos terminais, e o hash. Aplicação com o hash e a autorização exata: atividade termina não aceita, recurso de sessão é fechado com recibo, takeover passa a ser admitido, sucessor prepara attempt 2 como atividade nova.
2. **Sessão retida (caso `interview-author-001`)**: atividade com resultado gravado, sessão retida pelo Orca, dispatch terminado. Mesma rota; o resultado gravado permanece registrado, mas nunca é aceito nem herdado. Depende de DQ propostas 0008 e 0009.
3. **Negativo — sem autorização**: prévia e aplicação recusam com o mesmo código; nada muda no estado.
4. **Negativo — autorização de outro contexto, atividade ou run**: recusa idêntica ao caso 3; nada muda.
5. **Negativo — líder vivo**: o dispatch do líder da atividade ainda está ativo; recusa própria; nada muda. (Na variante 2 o líder vivo pode ser o próprio solicitante — DQ 0008.)
6. **Negativo — especialista vivo**: o dispatch do especialista ainda está ativo; recusa própria; nada muda.
7. **Negativo — evidência inconclusiva**: observação ausente, ilegível, não correlacionada ou liveness sem veredicto terminal; recusa de prova não comprovada; nada muda.
8. **Hash stale / replay**: aplicação com hash divergente recusa; aplicação repetida com os mesmos inputs devolve reuso sem segundo efeito.
9. **Aceite tardio**: qualquer tentativa de aceitar a atividade encerrada é recusada.

### Critérios de aceite
- Prévia nunca escreve; o hash da prévia cobre atividade, contexto, veredictos e referências das duas observações e a autorização.
- Os quatro negativos de DQ-0006 e o inconclusivo deixam o estado bit a bit igual.
- Após o fence no cenário 1, o takeover é admitido sem alterar a regra de herança de workers; após o fence no cenário 2, a atividade deixa de contar como ativa para takeover e prepare-switch.
- A atividade encerrada não possui aceite, e aceite posterior é recusado.
- A operação de fence fica rastreável ao work item, ao contexto, à atividade, aos digests observados e à autorização verbatim.
- Attempt 2 nasce como atividade nova no contexto sucessor; nada do resultado encerrado migra.
- Versão do plugin incrementada nos oito pontos de distribuição; suíte `tests/run_validators.py` verde nos três SOs sem rede.

## WHY
- **Valor**: hoje o X7 está preso: instalar 6.0.30 não destrava (DQ-0005), porque nenhum verbo alcança uma atividade `DISPATCHED` sem líder; a única saída seria editar o Store à mão, o que a Constituição trata como contorno. Este work item é a menor rota legítima.
- **Evidência**: leituras literais do Store do X7 pelo coordenador (DQ-0001, DQ-0005); estado vivo de `interview-author-001` observado nesta sessão (dispatch `completed`, capability revogada, terminal retido, liveness `unverifiable`), que reproduz a variante 2 no próprio repositório; decisões humanas DQ-0002 (escopo A), DQ-0006 (opção A) e DQ-0007 (adendo).
- **Restrições**: autorização humana é obrigatória e exata (nunca genérica, nunca por flag); prova terminal vem do ambiente, nunca da alegação do chamador; silêncio e expiry não provam; o resultado da atividade encerrada nunca é aceito nem herdado; nada muda na Constituição, no WORKFLOW ou nos registries; fix é plan-only e termina em `PLAN_ONLY_STOP`.

> Não inclua headings/campos de stack, banco, framework, classes, componentes, implementação ou API interna. Este handoff cobre somente uma fase.

> Feature/fix handoffs remain plan-only. Incident hotfixes use HOTFIX.md and do not bypass constitutional safety.
```

## PLAN-CONTEXT.md

```markdown
# PLAN-CONTEXT

## FASE-001 — Fence autorizado de atividade órfã
- phase: FASE-001
- ADRs: ADR-0001
- BLs: none
- delivery-units: DU-001
- development-type: platform-devops

### HOW
**Verbo.** `gauntlet-activity-fence ROOT --work-id ID --activity-id ID --session-ref REF --authorization PATH [--apply --expected-sha256 HASH]`, em `grill_workspace.py`, ao lado de `gauntlet_context_takeover_command` (4126-4345), reusando sua forma: mesmas checagens em preview e apply, apply só acrescenta o hash e a mutação CAS. Não decorado com `@_gauntlet_authorized` na rota órfã (o líder está terminal e `require_authority` recusaria `LEADER-AUTHORITY-UNPROVEN`); `context_id`/`epoch` derivam da atividade no Store, nunca do chamador. Códigos KEBAB novos, um por recusa: `FENCE-ACTIVITY-NOT-FOUND`, `FENCE-ACTIVITY-STATE` (estado fora de `DISPATCHED|RESULT_RECORDED`), `FENCE-AUTHORIZATION-INVALID` (ausente, ilegível, malformada, não aprovada, escopo divergente — um código só, como `ABANDON-AUTHORIZATION-INVALID`, 5175-5186), `FENCE-NOT-OBSERVABLE`, `FENCE-SPECIALIST-ACTIVE`, `FENCE-SPECIALIST-UNPROVEN`, `FENCE-LEADER-ACTIVE`, `FENCE-LEADER-UNPROVEN`, `FENCE-INPUTS-STALE`, `FENCE-CAS-CONFLICT`; veredictos `FENCE-PREVIEW`, `FENCE-APPLIED`, `FENCE-REUSED`.

**Provas exigidas (duas observações, mesma função).** Reusar `_takeover_observation` (1565-1610) sobre `observe_predecessor_termination` (agent_runtime.py:1249-1292) para o dispatch do especialista (`resource.identity.owner_dispatch`, 3684-3690) e para o dispatch do líder do contexto da atividade (`context.leader.session_ref`). Mapeamento idêntico ao takeover (4157-4166): `not_observable` → `FENCE-NOT-OBSERVABLE`; não terminal com `status ∈ {dispatched, running}` → `*-ACTIVE`; qualquer outro não terminal → `*-UNPROVEN`. Definição fail-closed de "especialista vivo", inclusive na variante 2: o dispatch ainda pode gravar resultado, isto é, `status ∈ {dispatched, running}` com `capabilityRevokedAt == null`. Na sessão retida o que se prova é o dispatch `completed/settled` com capability revogada (observado em `ctx_2923e0218c89`); o processo do agente dentro do terminal retido pelo usuário é irrelevante para o fence, porque nenhum `gauntlet-activity` correlaciona outro `owner_dispatch` (6052-6055). Liveness `unverifiable` sozinha nunca decide: sem `status` terminal nem capability revogada → `FENCE-SPECIALIST-UNPROVEN`. Ambas as leituras vão para `evidence` (`observation_ref`, `observation_sha256`, `dispatch_status`, `liveness`) como no takeover (4195-4196).

**Autorização.** `load_checkpoint_attestation` (5340-5362) + `attestation._validate_human_authorization(bundle, scope)` (773-781), sem tocar na função: `scope` canônico `f"{work_id}:{context_id}:{activity_id}"` (ids não admitem `:`; agent_orchestration.py:40). Escopo de outro contexto, atividade ou run difere e cai em `HUMAN_AUTHORIZATION_SCOPE` → `FENCE-AUTHORIZATION-INVALID`. `receipt_ref` = recibo humano (na DQ-0007, a mensagem do coordenador). `content_sha256` é validado só na forma, como no precedente; endurecimento opcional (não exigido por DQ-0006): a prévia publica `authorization_content_sha256 = jcs({work_id, context_id, activity_id, observações})` e apply compara. Bundle gravado verbatim em `intended_after.authorization`, como `abandon_run` grava no run (gauntlet_runs.py:3119-3126).

**Hash da prévia.** `expected = jcs_sha256({work_id, context_id, activity_id, activity_state, resource_id, specialist: {verdict, reference}, leader: {verdict, reference}, authorization: {scope, decision, authorized_by, receipt_ref, content_sha256}})`. Sem digest de resposta nem `snapshot.revision` (T018/T024, 4249-4262); a revisão é reconferida em `mutate`.

**Mutação (estado terminal + fechamento).** Operação `kind="activity-fence"` (kind é string livre, agent_orchestration.py:639-643), `context_id` = contexto da atividade, `fence` = `contexts[ctx].leader.fence` (obrigatório, 1376-1380), `subject_ids=[activity_id, session_resource_id]`, `input_sha256=expected`, `state="CONFIRMED"`, `result_ref=observation_ref=f"activity-fence/{operation_id}.json"` (referência lógica, como `context-takeover/...` em 4286; nenhuma categoria nova em `RECEIPT_CATEGORIES`, store.py:100-111), `result_sha256=jcs({...evidence, authorization})`, `intended_after={reason: "fence", evidence, authorization, successor: "attempt-2-in-successor-context"}`. Atividade: `state="FAILED"`, `diagnostic_ref=result_ref` (campo first-bound a partir de `None`, 1532-1536; aresta `DISPATCHED→FAILED` válida, 48). Recurso: `evidence_manifest.receipts` recebe `{ref: <dispatch do especialista>+":fence", sha256: observation_sha256}` (append permitido, 1545-1551), `last_observation` idem, `result_acceptance_ref` fica `None` (nullable, 1002-1003; nada foi aceito). Arestas de recurso (49, 1554): variante 2 é um salto `CLOSE_PENDING→CLOSED`; variante 1 exige dois (`REGISTERED→CLOSE_PENDING→CLOSED`), então o apply faz dois `store.transact` com a mesma `idempotency_key`: o primeiro grava operação + `FAILED` + `CLOSE_PENDING`, o segundo fecha; replay com operação já presente e recurso ainda `CLOSE_PENDING` completa só o segundo salto e devolve `FENCE-REUSED`. Guarda de revisão e de estado dentro de `mutate` como no takeover (4304-4316); conflito → `FENCE-CAS-CONFLICT`. `# ponytail:` dois saltos por causa da aresta; se o contrato ganhar `REGISTERED→CLOSED`, vira um.

**Interação com `_continuity_quiescence` (3654-3672).** Sem mudança: `FAILED` não está no conjunto ativo (3661-3663) e o recurso `CLOSED` não é `UNKNOWN` (3665-3666). Após o fence o takeover deixa de acusar `TAKEOVER-WORK-ACTIVE` sem tocar em `_takeover_prepared_workers`; `prepare-switch` deixa de acusar `CONTINUITY-ACTIVE-WORK` por essa atividade.

**Interação com `gauntlet-context-takeover` (4126-4345).** Ordem: fence → takeover preview → takeover apply. O `expected` do takeover não cobre atividades (4256-4260), mas `mutate` fixa `document["revision"]` (4308-4309): fence entre preview e apply do takeover → `TAKEOVER-CAS-CONFLICT`, nova prévia. `TAKEOVER-REUSED` (4148-4154) e `CONTINUITY-CHECKPOINT-MISSING` (4184-4187) inalterados; no X7 `campaign=None`, sem checkpoint exigido. O contexto da atividade permanece `ACTIVE` com líder terminal até o takeover o superseder; um líder "ressuscitado" continua recusado por `observe()` (`LEADER-AUTHORITY-UNPROVEN`, agent_runtime.py:808-823).

**Attempt 2 no contexto sucessor.** Depois de `TAKEOVER-APPLIED`, o sucessor roda `gauntlet-activity --phase prepare|dispatch` com `activity_id` novo no `context_id` novo; `activity_id` é chave única do dicionário (`value["activity_id"] != activity_id` recusa, agent_orchestration.py:720) e `attempt` é identidade write-once gravada como 1 pelo CLI (5990; 1529). O input manifest do attempt 2 não lista a atividade fenced em `required_activity_ids`/`author_activity_ids`. Convenção de nome e registro do vínculo: DQ 0010.

**Testes negativos (regra 11 — ver nota).** Em `tests/validate_agent_orchestration_contract.py`, padrão de `test_context_takeover` (2234-2330): `takeover_show` (fixture enveloped), `guarded_run` interceptando só `worker-show` e roteando por `--dispatch`, `assert_refused_and_unwritten` comparando `content_sha256` do Store antes/depois em preview **e** apply. Casos: (n1) sem `--authorization`/arquivo ausente/ilegível/malformado/`decision != APPROVED` → `FENCE-AUTHORIZATION-INVALID`; (n2) escopo de outro `context_id`, outro `activity_id` e um `run_id` → `FENCE-AUTHORIZATION-INVALID`; (n3) líder `dispatched` + liveness `live/agent_status` → `FENCE-LEADER-ACTIVE`; (n4) especialista `dispatched`/`running` + `live` → `FENCE-SPECIALIST-ACTIVE`; (n5) liveness `unverifiable` com `status=dispatched` e `capabilityRevokedAt=null` → `FENCE-SPECIALIST-UNPROVEN`; (n6) `not_observable`; (n7) hash stale → `FENCE-INPUTS-STALE`; (n8) atividade `ACCEPTED`/`FAILED`/`VERIFIED` → `FENCE-ACTIVITY-STATE`. Positivos: (p1) X7-shape (`DISPATCHED` + `REGISTERED`, líder `completed`, especialista `completed` com capability revogada) → `FENCE-PREVIEW`, `FENCE-APPLIED`, atividade `FAILED` com `diagnostic_ref`, recurso `CLOSED` com receipt, operação `CONFIRMED` com autorização verbatim, depois `gauntlet-context-takeover` → `TAKEOVER-APPLIED`; (p2) forma retida (`RESULT_RECORDED` + `CLOSE_PENDING`, `retained/user_owned`, `unverifiable`) — condicionado a DQ 0009; (p3) replay → `FENCE-REUSED` sem segundo evento; (p4) `gauntlet-activity --phase accept` após fence → `ACTIVITY-STATE-DIVERGENCE` (6074-6075); (p5) apply interrompido entre os dois saltos e reaplicado → `CLOSED`. Contrato de arestas travado em `validate_agent_orchestration_contract.py` se DQ 0009 escolher A. Sem rede, sem `orca` real (transporte injetado), CI ubuntu/windows/macos, Python 3.10/3.13.

**Restrições.** Somente stdlib, Python ≥ 3.10. Nenhuma edição em `.specify/memory/constitution.md`, `WORKFLOW.md`, tuplas `ESSENTIAL` (`ensure_workflow`, `workflow_v3`, `workflow_v4`), registries/catálogos/snapshots de confiança. Nenhuma alteração em `SPECIALIST_PAIRS`, na policy `agent-orchestration.v1.json` nem no schema do Store além do que DQ 0009 decidir. Hooks continuam read-only.

**Bump de distribuição (CLAUDE.md, "Distribuição").** Oito pontos, hoje `6.0.30`: `plugin/.claude-plugin/plugin.json:3`, `plugin/.codex-plugin/plugin.json:3`, `.claude-plugin/marketplace.json:11`, `.agents/plugins/marketplace.json:7`, `tests/validate_distribution.py:8` (`VERSION`), `plugin/skills/grill-with-docs/SKILL.md:6` (`# Grill with Docs vX.Y.Z`), `plugin/skills/grill-with-docs/references/session-protocol.md:1` (`# Protocolo de sessão vX.Y.Z`), `README.md:3` (`**vX.Y.Z`). Fix → PATCH (6.0.31, salvo bump intermediário). Documentação: parágrafo de session-protocol.md:87 ganha o verbo, as duas provas, a autorização exata e a frase de que o resultado fenced nunca é aceito; verbo listado onde o protocolo enumera `gauntlet-context-takeover`/`gauntlet-run-abandon` (85-89). `publish.yml` cria tag e Release no merge (Constituição: bump e release obrigatórios).

**Riscos e lock-in.**
- Códigos, veredictos e `kind="activity-fence"` viram contrato público travado por teste; renomear depois custa bump e migração de prosa.
- `content_sha256` sem comparação (precedente) permite reutilizar a mesma autorização enquanto a tripla não mudar; o hash da prévia inclui a autorização, mas não a amarra às observações. Mitigação opcional acima.
- Dois saltos de recurso na variante 1: janela de crash entre saltos deixa `FAILED` + `CLOSE_PENDING`; coberto por replay idempotente (p5). Não bloqueia takeover, pois `CLOSE_PENDING` não é `UNKNOWN`.
- O Store do X7 vive em outra máquina (EVIDENCE GAP, DQ-0001): rodar a prévia lá antes de qualquer apply; a prévia é read-only.
- Campos Orca `retained`/`user_takeover`/`missing_status` não são contrato versionado; a prova usa só `status`, `capabilityRevokedAt` e `liveness`, já consumidos pelo takeover.
- Lock-in de vocabulário: `scope` canônico com `:`; mudar o separador invalida autorizações já emitidas.
- Recurso fechado sem `result_acceptance_ref` continua `RESULT_NOT_DURABLE` em `cleanup_reasons` (agent_orchestration.py:1082); irrelevante após supersede (cleanup filtra pelo contexto corrente, 4272-4280), mas aparece em auditoria.

> Mantenha um bloco por fase e referências ADR/BL exatamente equivalentes ao ROADMAP e ao handoff. Nunca registre `selected-handoff` aqui.
```

## DELIVERY-MAP.md

```markdown
# DELIVERY-MAP

decomposition-schema: v1

## MOD-001 — Continuidade do líder (core CLI)
- module-kind: platform
- responsibility: Levar atividades órfãs ou de sessão retida a estado terminal não aceito, sob prova terminal Orca e autorização humana exata, para que takeover e prepare-switch voltem a admitir o work item
- boundary: `grill_workspace.py` (verbo, admissão, mutação CAS), `grill_core/agent_orchestration.py` (arestas, somente se DQ 0009 escolher A), `tests/validate_agent_orchestration_contract.py`, `references/session-protocol.md`, oito pontos de distribuição; sem tocar `attestation.py`, `agent_runtime.py`, policy, registries, Constituição ou WORKFLOW
- depends-on: none

### DU-001 — Verbo de fence autorizado
- development-type: platform-devops
- phase: FASE-001
- scope-in: verbo preview-first com `--apply --expected-sha256`; provas terminais do especialista e do líder pela observação do takeover; `human-authorization/v1` com escopo `work_id + context_id + activity_id`; atividade `FAILED` com `diagnostic_ref`; recurso `CLOSED` com receipt; operação `CONFIRMED` com evidência e autorização verbatim; testes negativos e positivos; parágrafo no protocolo de sessão; bump de versão
- scope-out: aceite, transferência ou reaproveitamento de resultado; fence de workers de run; SGD-37; SGD-38; checkpoint automático; mudanças no Orca, na policy ou nos registries
- depends-on: none
- acceptance: `tests/run_validators.py` verde sem rede em ubuntu/windows/macos × Python 3.10/3.13; os quatro negativos de DQ-0006 mais inconclusivo, stale e replay deixam o Store bit a bit igual; forma X7 fenced e em seguida `TAKEOVER-APPLIED`; aceite tardio recusado; `validate_distribution.py` casando a versão nova nos oito pontos

> IDs are stable within this work item. `module-kind` is one of `domain|platform|cross-cutting`; each DU has exactly one closed development type.
```

## DQs propostas

Nenhuma decidida aqui. Cada uma é atômica, com opções e recomendação.

### DQ-0008 — Quem tem autoridade para pedir o fence quando o líder da atividade está vivo (variante de sessão retida)?
- phase: FASE-001 · impact: high · depends-on: DQ-0006, DQ-0007
- contexto: no X7 o líder está terminal e o solicitante é uma sessão sucessora. Em `interview-author-001` o líder corrente `orca:ctx_ad48e72ddf4c` está vivo e seria ele o solicitante. O negativo "líder vivo" de DQ-0006 foi decidido para a órfã.
- opções:
  - **A (recomendada)**: um verbo, admissão derivada da observação do líder. Líder terminal → qualquer `--session-ref` sucessor, sem `@_gauntlet_authorized`; líder vivo → o chamador tem de ser o líder corrente exato (`_require_current_leader`, 1658-1671); líder vivo e chamador ≠ líder → `FENCE-LEADER-ACTIVE`. O negativo passa a ler "líder vivo que não é o chamador". Menor diff, uma superfície.
  - **B**: dois verbos (`gauntlet-activity-fence` para órfã; `gauntlet-activity --phase accept --fence` para sessão retida sob `@_gauntlet_authorized`). Mais claro, duas superfícies, dois conjuntos de testes.
  - **C**: fence só com líder terminal; sessão retida com líder vivo espera o líder terminar. Não resolve o caso corrente sem matar o líder, o que o protocolo proíbe (83).
- recomendação: A.

### DQ-0009 — Como levar `RESULT_RECORDED` a estado terminal não aceito, dado que `RESULT_RECORDED → FAILED` não é aresta válida?
- phase: FASE-001 · impact: high · depends-on: DQ-0007
- evidência: `_ACTIVITY_EDGES["RESULT_RECORDED"] == {"RESULT_RECORDED", "ACCEPTED"}` (agent_orchestration.py:48), aplicado em `validate_transition` (1538); `CLOSE_PENDING → CLOSED` é válida (49, 1554). Sem aresta, a atividade continua contando como ativa (3658-3661) mesmo com recurso fechado sem aceite.
- opções:
  - **A (recomendada)**: acrescentar `FAILED` ao conjunto de `RESULT_RECORDED` (um literal), com `diagnostic_ref` obrigatório nessa aresta e guarda no CLI de que só o fence a percorre; travar no validador de contrato. Mudança de schema mínima e absorvente (`FAILED` é terminal).
  - **B**: manter `RESULT_RECORDED`, fechar o recurso e gravar `result_acceptance_ref = result_ref` sem `ACCEPTED`, imitando o fechamento por release (3929-3934). Sem schema, mas a atividade fica não terminal e um aceite posterior continua estruturalmente possível; contradiz "estado terminal" de DQ-0007.
  - **C**: estado novo `FENCED`. Maior mudança de schema, sem ganho sobre A.
- recomendação: A.

### DQ-0010 — Como identificar o attempt 2 no contexto sucessor?
- phase: FASE-001 · impact: medium · depends-on: DQ-0006
- evidência: `activity_id` é chave única (720); `attempt` é identidade write-once (1529) e o CLI grava sempre 1 (grill_workspace.py:5990); o X7 já usa sufixo numérico (`converge-final-author-x7-3`).
- opções:
  - **A (recomendada)**: attempt 2 = atividade nova com `activity_id` novo (convenção do líder, sufixo incrementado), `attempt` permanece 1; o vínculo fica só no `intended_after` da operação de fence. Zero mudança de CLI/schema.
  - **B**: flag `--attempt N` em `gauntlet-activity prepare` mantendo o mesmo `activity_id`. Inviável sem chave composta (schema).
  - **C**: campo novo `supersedes_activity_id` na atividade. Schema e validação novos; rastreabilidade melhor, custo maior.
- recomendação: A.

## Notas ao líder (não são decisões)

- **"regra 11" não localizada nos inputs**: `SKILL.md` lista nove regras invioláveis (16-26) e o protocolo não numera regras; interpretei como "testes negativos obrigatórios, um por recusa, com Store inalterado". Se a regra estiver noutro documento, ajusto a seção de testes.
- **Divergência doc/código, fora do escopo**: session-protocol.md:87 diz que o fechamento por release ocorre "sem aceitar nem reexecutar o resultado", mas `gauntlet_prepare_switch_command` marca a atividade `ACCEPTED` com `review_verdict=APPROVED` e `acceptance_ref=result_ref` (grill_workspace.py:3934-3939). Relevante ao princípio que o ADR invoca; sugiro registrar como achado lateral (backlog), sem mexer neste fix.
- **Alternativas B/C do ADR** são reconstrução a partir da evidência da fronteira; a rodada DQ-0006 só registrou "opção A".

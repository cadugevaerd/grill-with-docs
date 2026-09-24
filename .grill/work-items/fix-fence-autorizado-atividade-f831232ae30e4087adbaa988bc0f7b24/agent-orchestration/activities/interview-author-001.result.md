# Resultado — interview-author-001 (AUTOR, claude/fable/xhigh, requested == effective)

- work item: `fix-fence-autorizado-atividade-f831232ae30e4087adbaa988bc0f7b24` (NOVO), contexto `ctx-146fb68d0d6e`, fence 1, dispatch `ctx_9c921b52a19f`
- fonte: `fix-continuidade-sem-checkpoint-d62bb2a5380d4409ace677fa741af28d` (ANTIGO), contexto `ctx-0c0155ef5a94`, líder `orca:ctx_ad48e72ddf4c`
- worktree `/home/carlosaraujo/orca/workspaces/grill-with-docs/fix-leader`, HEAD `39380f7` (6.0.30 + cherry-pick `f1475f4`)
- payload lido por inteiro: sha256 `9bcaee86a17c39e29ed03534ac037923bffff8fb4539b84305a91405bf1d5c33` (confere)
- input manifest: 27/27 sha256 conferidos, zero divergência
- nada escrito em `.grill/` nem em `.specify/reports/`; `git status` só tem o bundle do NOVO untracked
- decisões DQ-0001..DQ-0011 preservadas: nenhuma reaberta, ampliada ou estreitada
- `f1475f4` acrescenta 3 linhas em `agent_orchestration.py:1393-1395`; toda citação desse arquivo a partir daí foi deslocada +3 e reconferida. `grill_workspace.py`, `agent_runtime.py`, `attestation.py`, `store.py`, `gauntlet_runs.py` e `session-protocol.md` não mudaram desde a revisão do ANTIGO (`git log`), e as citações foram reconferidas por grep. `tests/validate_agent_orchestration_contract.py` deslocou +23 (`test_context_takeover` 2234 → 2257).
- convenção abaixo: `<ANTIGO>` = `fix-continuidade-sem-checkpoint-d62bb2a5380d4409ace677fa741af28d`. Nos artefatos o id vai por extenso.

## CONTEXT.md

```markdown
# CONTEXT

## Glossário

| Termo canônico | Definição | Termos a evitar | Evidência |
|---|---|---|---|
| atividade órfã | Atividade de especialista em `DISPATCHED` cujo dispatch Orca já terminou sem resultado gravado e cujo líder de origem também terminou; nenhum verbo existente a leva a estado terminal. | atividade travada, atividade zumbi, atividade pendente | DQ-0005/DQ-0006; X7 `converge-final-author-x7-3 DISPATCHED` com líder liberado; `_continuity_quiescence` conta `DISPATCHED` como ativa (grill_workspace.py:3654-3672) |
| sessão retida | Atividade `RESULT_RECORDED` cujo recurso de sessão ficou `CLOSE_PENDING` porque o Orca reteve o terminal (`releaseState=retained`, `ownershipState=user_owned`, `retainedReason=user_takeover`) com liveness `unverifiable`; o aceite recusa `SESSION-CLOSE-UNPROVEN` e não há aresta para `FAILED`. | sessão presa, terminal fantasma | DQ-0007 (adendo); `interview-author-001`/`ctx_2923e0218c89` do work item fix-continuidade-sem-checkpoint-d62bb2a5380d4409ace677fa741af28d, onde bloqueou o próprio takeover (`TAKEOVER-WORK-ACTIVE`); agent_runtime.py:1223-1236; agent_orchestration.py:972-975 |
| fence autorizado | Rota de recuperação, preview-first, que leva uma atividade órfã ou de sessão retida a estado terminal não aceito e fecha seu recurso de sessão, somente com prova terminal Orca do especialista e do líder e autorização humana exata. | cancelamento, abandono de atividade, limpeza automática. Nota: "fence" sozinho é ambíguo, pois já nomeia o inteiro de autoridade do líder (`leader.fence`, agent_orchestration.py:1378; `fence=1` no payload) e o `release_proof=resource-fence` do release estrito do líder (agent_runtime.py:1042; session-protocol.md:87); dizer sempre "fence autorizado" ou "fence de atividade" | DQ-0006 opção A; DQ-0007; precedente `gauntlet-run-abandon` (grill_workspace.py:5152-5189) |
| prova terminal Orca | Observação correlacionada do dispatch exato via `worker-show`: `status` fora de `dispatched|running`, ou `capabilityRevokedAt` não nulo, ou liveness `exited` por `agent_status`. Silêncio, expiry, liveness `unverifiable` sozinha e observação incompleta não provam nada. | timeout, lease vencido, "não responde" | agent_runtime.py:1249-1292 `observe_predecessor_termination` (veredicto em 1286-1291); grill_workspace.py:1565-1609; session-protocol.md:85-87 |
| autorização humana exata | Documento `human-authorization/v1` (`schema`, `scope`, `decision=APPROVED`, `authorized_by`, `receipt_ref`, `content_sha256`) cujo `scope` vincula `work_id + context_id + activity_id` exatos; escopo de outro contexto, atividade ou run é inválido. | aprovação verbal, flag `--force`, `--yes` | attestation.py:191-193, 773-781; DQ-0006; precedente `gauntlet-run-abandon` com `scope == run_id` |
| takeover | `gauntlet-context-takeover`: sessão nova assume o work item após prova terminal do líder anterior; herda só workers `PREPARED`; qualquer atividade em voo recusa `TAKEOVER-WORK-ACTIVE`. | retomada, resume, switch | grill_workspace.py:4126-4350; session-protocol.md:85; no work item fix-continuidade-sem-checkpoint-d62bb2a5380d4409ace677fa741af28d a recusa foi `TAKEOVER-WORK-ACTIVE` com `activity:interview-author-001` |
| quiescência | Conjunto vazio de atividades ativas e sessões desconhecidas. Ativa = `BOOTSTRAPPING|VERIFIED|DISPATCHED|RESULT_RECORDED` sem sessão `CLOSED` com `result_acceptance_ref == result_ref`; `FAILED` e `ACCEPTED` são quietas. | inatividade, silêncio, ociosidade | grill_workspace.py:3654-3672 |
| attempt 2 | Reexecução do autor no contexto sucessor, depois do takeover, como atividade nova com `activity_id` novo e `attempt=1`; o resultado da atividade fenced nunca é aceito nem herdado. | retry do resultado, reaproveitamento, aceite tardio | DQ-0006 (resolution); DQ-0010; session-protocol.md:87 "Resultados de atividades nunca herdam essas exceções" |
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
    section: 3654-3672, 3428-3439, 4126-4350, 5152-5189, 6074-6080
    consulted: 2026-09-24
  - type: repo
    title: agent_orchestration.py — estados e arestas de atividade/recurso
    url: plugin/skills/grill-with-docs/scripts/grill_core/agent_orchestration.py
    version: 6.0.30 (HEAD 39380f7, com cherry-pick f1475f4 em 1393-1395)
    section: 45-49, 639-662, 917-930, 959-993, 1378, 1532-1557
    consulted: 2026-09-24
  - type: decision
    title: DQ-0006 (R-0005), DQ-0007 (adendo, msg_ff60609e12bb), DQ-0008..DQ-0011 — decisões humanas do coordenador, migradas de fix-continuidade-sem-checkpoint-d62bb2a5380d4409ace677fa741af28d
    url: DECISION-FRONTIER.md
    version: 2026-09-24
    section: DQ-0002, DQ-0005, DQ-0006, DQ-0007, DQ-0008, DQ-0009, DQ-0010, DQ-0011
    consulted: 2026-09-24
  - type: repo
    title: Revisão independente interview-reviewer-001 (APPROVED, 8 findings) do work item de origem
    url: .grill/work-items/fix-continuidade-sem-checkpoint-d62bb2a5380d4409ace677fa741af28d/agent-orchestration/activities/interview-reviewer-001.result.md
    version: sha256 2b5a62b0aac8c5afb85dc6445e7e156d00f1db08cec8c52c39a8c64051c44872
    section: Findings 1-8
    consulted: 2026-09-24
---
# ADR-0001 — Atividade órfã ou de sessão retida sai por fence autorizado; o resultado nunca é aceito e o sucessor reexecuta como attempt 2

## Contexto
O takeover exige quiescência: toda atividade `BOOTSTRAPPING|VERIFIED|DISPATCHED|RESULT_RECORDED` sem sessão `CLOSED` correlacionada ao resultado conta como ativa (grill_workspace.py:3654-3672) e recusa `TAKEOVER-WORK-ACTIVE` (4170-4174). Só workers `PREPARED` são herdados (3675-3681, session-protocol.md:85). No X7 a atividade `converge-final-author-x7-3` ficou `DISPATCHED` com recurso `REGISTERED`, o especialista terminou sem gravar resultado e o líder foi liberado (DQ-0005). Nenhum verbo alcança esse estado: `--diagnostic` exige o líder corrente (`@_gauntlet_authorized`, 3393) e `prepare-switch --released-source` só aquieta `RESULT_RECORDED` com release arquivado (3684-3709). O adendo DQ-0007 acrescenta a variante de sessão retida: `RESULT_RECORDED` com recurso `CLOSE_PENDING` e terminal retido pelo Orca (`retained/user_owned/user_takeover`, liveness `unverifiable`); o aceite recusa `SESSION-CLOSE-UNPROVEN` (agent_orchestration.py:972-975; agent_runtime.py:1223-1236) e `RESULT_RECORDED → FAILED` não é aresta válida (agent_orchestration.py:48).

**Segundo caso observado — o work item de origem desta decisão.** A variante retida foi observada ao vivo em `interview-author-001`/`ctx_2923e0218c89` do work item `fix-continuidade-sem-checkpoint-d62bb2a5380d4409ace677fa741af28d` (contexto `ctx-0c0155ef5a94`, líder `orca:ctx_ad48e72ddf4c`): dispatch `completed` com capability revogada, terminal retido, liveness `unverifiable`, atividade `RESULT_RECORDED` com `diagnostic_ref=None`, recurso `CLOSE_PENDING`. Quando o terminal do líder desconectou, o sucessor foi recusado por `gauntlet-context-takeover` com `TAKEOVER-WORK-ACTIVE` e `activity:interview-author-001` — o work item que decidiu esta rota ficou bloqueado pelo defeito que ela corrige, sem verbo que leve a atividade a estado terminal. Por decisão humana do coordenador (plano E), as decisões seladas migraram para este work item sem reabertura; o de origem será marcado `superseded` depois do ship, quando o verbo existir (BL-0001, FASE-002).

O protocolo já fixa o princípio: a prova de líder liberado só é herdada por `gauntlet-run-abandon`, e ainda assim com autorização humana exata para o run; "Resultados de atividades nunca herdam essas exceções" (session-protocol.md:87). O precedente valida `human-authorization/v1` com `scope == run_id` (attestation.py:773-781; grill_workspace.py:5174-5182).

## Decisão
Rota de **fence autorizado** (DQ-0006 opção A, estendida por DQ-0007): verbo novo preview-first com `--apply --expected-sha256`, que exige (1) prova terminal Orca do dispatch do especialista **e** do líder da atividade e (2) `human-authorization/v1` com `scope` vinculado a `work_id + context_id + activity_id` exatos. O fence leva a atividade a `FAILED` com `diagnostic_ref` apontando o receipt do fence e fecha o recurso de sessão com receipt correlacionado. O resultado gravado, quando existir, **não é aceito**: nenhum `acceptance_ref`, nenhum `accepted_by_context`, nenhum aceite posterior. O contexto sucessor, após o takeover, reexecuta o autor como attempt 2 (atividade nova). A variante de sessão retida entra no mesmo verbo. Decisões humanas complementares: autoridade derivada da observação do líder (DQ-0008 A: líder terminal → sucessor com prova do host; líder vivo → só o líder corrente exato; líder vivo e chamador diferente → `FENCE-LEADER-ACTIVE`); nova aresta `RESULT_RECORDED → FAILED` com `diagnostic_ref` obrigatório e percorrida só pelo fence (DQ-0009 A); attempt 2 como atividade nova com `activity_id` novo e `attempt=1`, vínculo no `intended_after` da operação de fence (DQ-0010 A); findings F1, F2 e F4 da revisão independente aplicados como correção obrigatória de HOW (DQ-0011 A).

## Opções e custos
Rótulos B/C conforme a rodada DQ-0006 do work item de origem; o texto das alternativas é reconstrução do autor a partir da evidência da fronteira — o líder confere contra a pergunta original.
- **A (escolhida): fence autorizado, resultado não aceito, attempt 2 no sucessor.** benefício: coerente com session-protocol.md:87 e com o precedente do run-abandon (mesma forma de autorização, mesma família de recusas), fail-closed em cada prova, sem mexer em takeover/prepare-switch; **custo:** verbo e códigos novos no contrato público, um humano no loop a cada órfã, e reexecução do autor (custo de tokens) mesmo quando um resultado já existe na variante 2.
- **B: quiescência automática por observação.** takeover ou prepare-switch aquietariam a órfã só com a prova terminal do especialista; benefício: zero fricção; **custo:** torna a exceção do run-abandon herdável por atividades, o que o protocolo proíbe (87); silêncio/expiry viram prova; sem rastro humano da decisão de descartar trabalho (Constituição: fail-closed sem waiver, rastreabilidade).
- **C: aceitar ou transferir o resultado gravado para o sucessor.** benefício: não perde o resultado da variante 2; **custo:** aceite sem prova de fechamento da sessão exata (`SESSION-CLOSE-UNPROVEN` existe para isso), resultado de contexto superseded herdado por contexto novo, e na variante 1 nem existe resultado; contradiz "sem aceitar nem reexecutar" do protocolo.

## Consequências
- Estado terminal novo alcançável por verbo: `DISPATCHED → FAILED` já é aresta válida (agent_orchestration.py:48); `RESULT_RECORDED → FAILED` passa a existir por DQ-0009 (um literal em `_ACTIVITY_EDGES`, `diagnostic_ref` obrigatório — `FAILED` já o exige em 784-785 —, guarda de CLI restrita ao fence, travada no validador de contrato).
- `_continuity_quiescence` deixa de contar a atividade fenced; o takeover passa a abrir sem tocar na regra de herança de workers `PREPARED`.
- O fence é registrado como operação `CONFIRMED` sob o contexto da atividade, com o fence do líder daquele contexto (agent_orchestration.py:1378), a autorização verbatim, os digests das duas observações e a prova de readiness do solicitante (F4) — mesma rastreabilidade do run-abandon (gauntlet_runs.py:3119-3126).
- `gauntlet-activity --phase accept` sobre a atividade fenced recusa `ACTIVITY-STATE-DIVERGENCE` (grill_workspace.py:6074-6075): a não-aceitação é estrutural, não convenção.
- Attempt 2 é atividade nova no contexto sucessor; o campo `attempt` é identidade write-once e o CLI grava 1 (agent_orchestration.py:1532; grill_workspace.py:5990) — por DQ-0010 o attempt 2 recebe `activity_id` novo (sufixo incrementado) com `attempt=1`, e o vínculo fica em `intended_after` (`subject_ids` + `successor`) da operação de fence.
- O work item de origem (`fix-continuidade-sem-checkpoint-d62bb2a5380d4409ace677fa741af28d`) é o primeiro consumidor do verbo: FASE-002 o cerca e o marca `superseded` depois do ship (BL-0001).
- Fora do escopo, por DQ-0002: SGD-37 (transcript > 16 MiB), SGD-38 (KeyError com `campaign` e head nulo), checkpoint automático. Nada muda em Constituição, WORKFLOW, `ESSENTIAL` ou registries.
- Bump de distribuição obrigatório nos oito pontos (CLAUDE.md, "Distribuição"): 6.0.30 → 6.0.31.

## Relações
- amends: none
- supersedes: fix-continuidade-sem-checkpoint-d62bb2a5380d4409ace677fa741af28d/ADR-0001 (mesma decisão, migrada sem reabertura; o ADR de origem recebe `superseded-by` na FASE-002)
- superseded-by: none
- exception: none
- backlog: SGD-37, SGD-38 (registrados em DQ-0002); SGD-39 (F8 da revisão independente, DQ-0011: `prepare-switch --released-source` grava `ACCEPTED` com `review_verdict=APPROVED` em grill_workspace.py:3936-3939 enquanto session-protocol.md:87 diz "sem aceitar nem reexecutar" — divergência doc/código registrada, não tratada aqui). Nenhum é BL deste work item.
```

## ROADMAP.md

```markdown
# ROADMAP

- execution-order: FASE-001, FASE-002

## FASE-001 — Fence autorizado de atividade órfã
- state: ready-for-specify
- objetivo: um work item com uma atividade de especialista órfã (`DISPATCHED`, sem resultado) ou de sessão retida (`RESULT_RECORDED`, recurso `CLOSE_PENDING`, terminal retido pelo Orca) — cujo líder terminou **ou** que ainda tem líder vivo (DQ-0008) — volta a admitir `gauntlet-context-takeover` por um verbo preview-first que exige prova terminal Orca do especialista, prova terminal do líder ou pedido do líder corrente exato, e autorização humana exata; o verbo leva a atividade a estado terminal não aceito, fecha o recurso com receipt e deixa o autor ser reexecutado como attempt 2 no contexto sucessor. Observável: no X7, `TAKEOVER-WORK-ACTIVE` some após o fence; no work item fix-continuidade-sem-checkpoint-d62bb2a5380d4409ace677fa741af28d, `interview-author-001` deixa de contar como ativa e o takeover pelo sucessor abre.
- scope-in: verbo novo com preview/apply e `--expected-sha256`; prova terminal do especialista e do líder pela mesma observação do takeover; prova de readiness do solicitante sucessor; `human-authorization/v1` com `scope = work_id + context_id + activity_id`; transição da atividade para `FAILED` com `diagnostic_ref` do receipt; fechamento do recurso de sessão com receipt correlacionado; operação `CONFIRMED` rastreável; os quatro testes negativos de DQ-0006 mais preview sem escrita, hash stale e replay idempotente; documentação do verbo no protocolo de sessão; bump nos oito pontos de distribuição.
- scope-out: SGD-37 (transcript do líder > 16 MiB); SGD-38 (KeyError do prepare-switch com `campaign` preenchido e head nulo); SGD-39 (prepare-switch grava `ACCEPTED` contra o protocolo); prevenção por checkpoint automático (T005 já cobre head nulo); aceitar, transferir ou reaproveitar o resultado gravado; fence de workers de run (já coberto por `gauntlet-run-abandon`); alterações em Constituição, WORKFLOW, `ESSENTIAL`, registries ou no Orca; mudança nas regras de herança do takeover; encerrar o work item de origem (FASE-002).
- context-refs: atividade órfã, sessão retida, fence autorizado, prova terminal Orca, autorização humana exata, takeover, quiescência, attempt 2, resultado não aceito
- ADRs: ADR-0001
- BLs: none
- depends-on: none
- specify-handoff: handoffs/FASE-001-SPECIFY-HANDOFF.md
- delivery-units: DU-001

## FASE-002 — Encerramento do work item de origem por fence autorizado
- state: planned
- objetivo: o work item fix-continuidade-sem-checkpoint-d62bb2a5380d4409ace677fa741af28d fica encerrado como `superseded`: sua atividade `interview-author-001` (sessão retida, dispatch `ctx_2923e0218c89`) é cercada pelo verbo entregue pela FASE-001 e publicado na 6.0.31, com autorização humana exata, sem aceite do resultado retido; o bundle de origem registra o encerramento apontando para este work item. Observável: `audit` do work item de origem devolve `MILESTONE-COMPLETE`; sua quiescência fica vazia; aceite tardio de `interview-author-001` recusa.
- scope-in: prévia e aplicação do fence sobre `interview-author-001` do work item de origem com prova terminal Orca de `ctx_2923e0218c89` e do líder `orca:ctx_ad48e72ddf4c` (ou pedido pelo líder corrente exato, se vivo); autorização exata com escopo daquele work item, daquele contexto e daquela atividade; marcação `superseded` da FASE-001 de origem, fechamento do milestone de origem e `superseded-by` no ADR-0001 de origem.
- scope-out: reexecutar o autor de origem como attempt 2 (as decisões já migraram para este work item); tocar o Store do X7; qualquer alteração de código ou de distribuição (entregue pela FASE-001); aceitar o resultado retido.
- context-refs: sessão retida, fence autorizado, prova terminal Orca, autorização humana exata, takeover, quiescência, resultado não aceito
- ADRs: ADR-0001
- BLs: BL-0001
- depends-on: FASE-001
- specify-handoff: handoffs/FASE-002-SPECIFY-HANDOFF.md
- delivery-units: DU-002

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
- **Líder sucessor**: sessão nova que precisa assumir o work item e é recusada por trabalho ativo de uma atividade sem dono. Quando o líder anterior está terminal, é o sucessor quem pede o fence, e a própria sessão dele é observada e provada antes de qualquer efeito (DQ-0008).
- **Humano autorizador**: quem decide descartar o trabalho da atividade e assina a autorização exata para este work item, este contexto e esta atividade (no adendo DQ-0007 a decisão chegou como mensagem do coordenador; é esse tipo de recibo que a autorização referencia).
- **Especialista órfão**: sessão de autor cujo dispatch já terminou; ou não gravou resultado (variante 1), ou gravou mas sua sessão ficou retida pelo Orca e nunca poderá provar fechamento (variante 2).
- **Líder corrente**: líder vivo que pede o fence de uma atividade própria de sessão retida; enquanto o líder está vivo, somente o líder corrente exato pode pedir (DQ-0008).

### Cenários
1. **Órfã (caso X7)**: atividade `DISPATCHED`, especialista terminado, líder liberado. Prévia lista a atividade, os dois dispatches e seus veredictos terminais, e o hash. Aplicação com o hash e a autorização exata: atividade termina não aceita, recurso de sessão é fechado com recibo, takeover passa a ser admitido, sucessor prepara attempt 2 como atividade nova.
2. **Sessão retida (caso `interview-author-001` do work item fix-continuidade-sem-checkpoint-d62bb2a5380d4409ace677fa741af28d)**: atividade com resultado gravado, sessão retida pelo Orca, dispatch terminado. Mesma rota; o resultado gravado permanece registrado, mas nunca é aceito nem herdado. Pedido pelo líder corrente exato quando o líder está vivo, ou por sucessor com prova terminal do líder (DQ-0008); a atividade chega a estado terminal não aceito (DQ-0009).
3. **Negativo — sem autorização**: prévia e aplicação recusam com o mesmo código; nada muda no estado.
4. **Negativo — autorização de outro contexto, atividade ou run**: recusa idêntica ao caso 3; nada muda.
5. **Negativo — líder vivo que não é o chamador**: o dispatch do líder da atividade ainda está ativo e o solicitante não é esse líder corrente exato; recusa própria; nada muda (DQ-0008).
6. **Negativo — especialista vivo**: o dispatch do especialista ainda está ativo; recusa própria; nada muda.
7. **Negativo — evidência inconclusiva**: observação ausente, ilegível, não correlacionada ou liveness sem veredicto terminal; recusa de prova não comprovada; nada muda. Inclui o sucessor cuja própria sessão não conclui a observação de prontidão.
8. **Hash stale / replay**: aplicação com hash divergente recusa; aplicação repetida com os mesmos inputs devolve reuso sem segundo efeito.
9. **Aceite tardio**: qualquer tentativa de aceitar a atividade encerrada é recusada.

### Critérios de aceite
- Prévia nunca escreve; o hash da prévia cobre atividade, contexto, solicitante, veredictos e referências das duas observações e a autorização.
- Os quatro negativos de DQ-0006 e o inconclusivo deixam o estado bit a bit igual.
- Após o fence no cenário 1, o takeover é admitido sem alterar a regra de herança de workers; após o fence no cenário 2, a atividade deixa de contar como ativa para takeover e prepare-switch.
- A atividade encerrada não possui aceite, e aceite posterior é recusado.
- A operação de fence fica rastreável ao work item, ao contexto, à atividade, ao solicitante, aos digests observados e à autorização verbatim.
- Attempt 2 nasce como atividade nova no contexto sucessor; nada do resultado encerrado migra.
- Versão do plugin incrementada nos oito pontos de distribuição; suíte de validadores do repositório verde nos três SOs, sem rede.

## WHY
- **Valor**: o X7 está preso: instalar 6.0.30 não destrava (DQ-0005), porque nenhum verbo alcança uma atividade `DISPATCHED` sem líder; a única saída seria editar o Store à mão, o que a Constituição trata como contorno. O work item de origem desta decisão, fix-continuidade-sem-checkpoint-d62bb2a5380d4409ace677fa741af28d, caiu no mesmo defeito: com o terminal do líder desconectado, o sucessor é recusado por `TAKEOVER-WORK-ACTIVE` por causa de `interview-author-001`, e o ciclo executor não pode começar lá. Este work item é a menor rota legítima para os dois casos.
- **Evidência**: leituras literais do Store do X7 pelo coordenador (DQ-0001, DQ-0005); estado vivo de `interview-author-001` observado no work item de origem (dispatch `completed`, capability revogada, terminal retido, liveness `unverifiable`, atividade `RESULT_RECORDED`, recurso `CLOSE_PENDING`), que reproduz a variante 2 no próprio repositório e bloqueou o takeover daquele work item; decisões humanas DQ-0002 (escopo A), DQ-0006 (opção A), DQ-0007 (adendo), DQ-0008 (autoridade), DQ-0009 (aresta), DQ-0010 (attempt 2) e DQ-0011 (findings da revisão), migradas sem reabertura.
- **Restrições**: autorização humana é obrigatória e exata (nunca genérica, nunca por flag); prova terminal vem do ambiente, nunca da alegação do chamador; silêncio e expiry não provam; o resultado da atividade encerrada nunca é aceito nem herdado; nada muda na Constituição, no WORKFLOW ou nos registries; fix é plan-only e termina em `PLAN_ONLY_STOP`.

> Não inclua headings/campos de stack, banco, framework, classes, componentes, implementação ou API interna. Este handoff cobre somente uma fase.

> Feature/fix handoffs remain plan-only. Incident hotfixes use HOTFIX.md and do not bypass constitutional safety.
```

## handoffs/FASE-002-SPECIFY-HANDOFF.md

```markdown
# FASE-002 — Encerramento do work item de origem por fence autorizado

- phase: FASE-002
- state: planned
- roadmap: ROADMAP.md#FASE-002
- context-refs: sessão retida, fence autorizado, prova terminal Orca, autorização humana exata, takeover, quiescência, resultado não aceito
- ADRs: ADR-0001
- BLs: BL-0001

## WHAT
- delivery-units: DU-002
- development-type: platform-devops

### Resultado
O work item fix-continuidade-sem-checkpoint-d62bb2a5380d4409ace677fa741af28d deixa de ser um bundle auto-bloqueado e passa a `superseded`, apontando para este work item como sucessor das suas decisões. Sua atividade `interview-author-001` (sessão retida) é encerrada pelo fence autorizado publicado na 6.0.31, sem aceite do resultado retido; o milestone de origem fecha.

### Atores
- **Líder GWD deste work item**: pede a prévia e a aplicação do fence sobre o work item de origem, depois registra o encerramento no bundle de origem.
- **Humano autorizador**: assina a autorização exata para o work item de origem, seu contexto `ctx-0c0155ef5a94` e a atividade `interview-author-001`.

### Cenários
1. **Fence do work item de origem**: prévia mostra `interview-author-001` (`RESULT_RECORDED`, recurso `CLOSE_PENDING`), o veredicto terminal do especialista `ctx_2923e0218c89`, o veredicto do líder `orca:ctx_ad48e72ddf4c` e o hash; aplicação com o hash e a autorização exata leva a atividade a estado terminal não aceito e fecha o recurso com recibo.
2. **Encerramento do bundle de origem**: a fase de origem passa a `superseded`, o milestone de origem fecha como completo e o ADR de origem aponta `superseded-by` para o ADR-0001 deste work item; a auditoria do bundle de origem devolve `MILESTONE-COMPLETE`.
3. **Negativo — aceite tardio**: qualquer tentativa de aceitar `interview-author-001` de origem depois do fence é recusada.
4. **Negativo — fence antes da 6.0.31**: sem o verbo instalado, nada é executado e o BL permanece aberto.

### Critérios de aceite
- A aplicação do fence devolve o veredicto de aplicado (ou de reuso no replay) com recibo e autorização verbatim rastreáveis ao work item de origem.
- A quiescência do work item de origem fica vazia; nenhuma atividade ativa resta.
- A auditoria do bundle de origem devolve `MILESTONE-COMPLETE` sem BL nem DQ material aberto.
- Nenhum byte fora dos bundles `.grill/` e do Store deste repositório muda.

## WHY
- **Valor**: o bundle de origem ficou preso pelo defeito que ele mesmo diagnosticou; deixá-lo `in-progress` para sempre é ruído em toda auditoria e status, e cercá-lo é o primeiro uso real do verbo, no próprio repositório.
- **Evidência**: recusa `TAKEOVER-WORK-ACTIVE` com `activity:interview-author-001` observada pelo coordenador; `interview-author-001` `RESULT_RECORDED` com recurso `CLOSE_PENDING`, dispatch `completed` e capability revogada; decisão humana do coordenador (plano E) de migrar e marcar `superseded` depois do ship.
- **Restrições**: depende da FASE-001 shipada e publicada como 6.0.31 (BL-0001); autorização humana exata e prova terminal Orca continuam obrigatórias; o resultado retido nunca é aceito nem reexecutado; sem edição manual do Store.

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
Linhas conferidas no HEAD `39380f7` (6.0.30 + cherry-pick `f1475f4`, que insere 3 linhas em `agent_orchestration.py:1393-1395`; tudo abaixo disso deslocou +3 em relação ao work item de origem). `grill_workspace.py`, `agent_runtime.py`, `attestation.py`, `store.py`, `gauntlet_runs.py` e `session-protocol.md` estão inalterados.

**Verbo.** `gauntlet-activity-fence ROOT --work-id ID --activity-id ID --session-ref REF --authorization PATH [--apply --expected-sha256 HASH]`, em `grill_workspace.py`, ao lado de `gauntlet_context_takeover_command` (4126-4350), reusando sua forma: mesmas checagens em preview e apply, apply só acrescenta o hash e a mutação CAS. Não decorado com `@_gauntlet_authorized` (3393): o líder da rota órfã está terminal e `require_authority` recusaria `LEADER-AUTHORITY-UNPROVEN`. `context_id`/`epoch` derivam da atividade no Store, nunca do chamador. Códigos KEBAB novos, um por recusa: `FENCE-ACTIVITY-NOT-FOUND`, `FENCE-ACTIVITY-STATE` (estado fora de `DISPATCHED|RESULT_RECORDED`), `FENCE-AUTHORIZATION-INVALID` (ausente, ilegível, malformada, não aprovada, escopo divergente — um código só, como `ABANDON-AUTHORIZATION-INVALID`, 5174-5182), `FENCE-NOT-OBSERVABLE`, `FENCE-SPECIALIST-ACTIVE`, `FENCE-SPECIALIST-UNPROVEN`, `FENCE-LEADER-ACTIVE`, `FENCE-LEADER-UNPROVEN`, `FENCE-INPUTS-STALE`, `FENCE-CAS-CONFLICT`; veredictos `FENCE-PREVIEW`, `FENCE-APPLIED`, `FENCE-REUSED`.

**Autoridade (DQ-0008, com F4).** Observar o dispatch do líder do contexto da atividade (`context.leader.session_ref`) por `_takeover_observation` (1565-1609). Três saídas: (a) líder **terminal** → o solicitante é o sucessor, e sua sessão é provada por `_session_readiness(root, context["runtime"], args.session_ref, work_id=args.work_id)` (1612-1656), a mesma chamada que o takeover faz em 4181; ela recusa `LEADER-AUTHORITY-UNPROVEN`/`STYLE-*` quando a sessão entrante não conclui, então ausência de prova nunca autoriza. `readiness["ref"]`, `readiness["sha256"]` e `readiness["incarnation"]` (1655-1656) entram em `evidence.requester` e em `intended_after.requester`. (b) líder **vivo** (`status ∈ {dispatched, running}`) → `args.session_ref` precisa ser igual a `context.leader.session_ref` e passar por `_require_current_leader` (1658-1670); chamador diferente → `FENCE-LEADER-ACTIVE`. (c) nem terminal nem vivo → `FENCE-LEADER-UNPROVEN`. Em (b) o solicitante é o próprio líder e `evidence.requester` recebe a observação de `_require_current_leader`.

**Provas exigidas (duas observações, mesma função; F1).** Reusar `_takeover_observation` sobre `observe_predecessor_termination` (agent_runtime.py:1249-1292) para o dispatch do especialista e para o do líder. **O especialista é observado por `"orca:" + resource["identity"]["owner_dispatch"]`**, na forma de `_released_activity_sessions` (3700): `owner_dispatch` é id nu no Store (`ctx_2923e0218c89` no work item de origem), `observe_predecessor_termination` só aceita `orca:ctx[-_]…` (agent_runtime.py:1268) e `_takeover_observation` faz `removeprefix("orca:")` (1593); sem o prefixo todo fence cairia em `not_observable`. Mapeamento idêntico ao takeover (4158-4166): `not_observable` → `FENCE-NOT-OBSERVABLE`; não terminal com `status ∈ {dispatched, running}` → `*-ACTIVE`; qualquer outro não terminal → `*-UNPROVEN`. Terminal = `status ∉ {dispatched, running}` ou `capabilityRevokedAt` não nulo ou liveness `exited` por `agent_status` (agent_runtime.py:1286-1291). Definição fail-closed de "especialista vivo", inclusive na variante 2: o dispatch ainda pode gravar resultado, isto é, `status ∈ {dispatched, running}` com `capabilityRevokedAt == null`. Na sessão retida o que se prova é o dispatch `completed` com capability revogada (observado em `ctx_2923e0218c89`); o processo do agente dentro do terminal retido é irrelevante, porque nenhum `gauntlet-activity` correlaciona outro `owner_dispatch` (6052-6055). Liveness `unverifiable` sozinha nunca decide: sem `status` terminal nem capability revogada → `FENCE-SPECIALIST-UNPROVEN`. Ambas as leituras vão para `evidence` (`observation_ref`, `observation_sha256`, `dispatch_status`, `liveness`) como no takeover (4195-4196).

**Autorização.** `load_checkpoint_attestation` (5340-5359) + `attestation._validate_human_authorization(bundle, scope)` (773-781), sem tocar na função: `scope` canônico `f"{work_id}:{context_id}:{activity_id}"` (ids não admitem `:`; agent_orchestration.py:40). Escopo de outro contexto, atividade ou run difere e cai em `HUMAN_AUTHORIZATION_SCOPE` → `FENCE-AUTHORIZATION-INVALID`. `receipt_ref` = recibo humano (na DQ-0007, a mensagem do coordenador). `content_sha256` é validado só na forma, como no precedente; endurecimento opcional (não exigido por DQ-0006): a prévia publica `authorization_content_sha256 = jcs({work_id, context_id, activity_id, observações})` e apply compara. Bundle gravado verbatim em `intended_after.authorization`, como `abandon_run` grava no run (gauntlet_runs.py:3119-3126).

**Hash da prévia (F4).** `expected = jcs_sha256({work_id, context_id, activity_id, activity_state, resource_id, to_session_ref: args.session_ref, specialist: {verdict, reference}, leader: {verdict, reference}, authorization: {scope, decision, authorized_by, receipt_ref, content_sha256}})` — `to_session_ref` entra como no takeover (4261), para que um `--apply` de outro solicitante recuse `FENCE-INPUTS-STALE`. Sem digest de resposta nem `snapshot.revision` (T018/T024, 4247-4259); a revisão é reconferida em `mutate`.

**Mutação (estado terminal + fechamento; F2).** Operação `kind="activity-fence"` (kind é string livre, agent_orchestration.py:639-643), `context_id` = contexto da atividade, `fence` = `contexts[ctx].leader.fence` (obrigatório, 1378), `subject_ids=[activity_id, session_resource_id]`, `input_sha256=expected`, `state="CONFIRMED"` (exige `observation_ref` e `result_sha256`, 651-652), `result_ref=observation_ref=f"activity-fence/{operation_id}.json"` (referência lógica, como `context-takeover/...` em 4286; nenhuma categoria nova em `RECEIPT_CATEGORIES`, store.py:100-111), `result_sha256=jcs({...evidence, authorization})`, `intended_after={reason: "fence", evidence, requester, authorization, successor: "attempt-2-in-successor-context"}`. Atividade: `state="FAILED"`, `diagnostic_ref=result_ref` (`FAILED` exige `diagnostic_ref`, 784-785; campo first-bound a partir de `None`, 1537-1539; aresta `DISPATCHED→FAILED` válida, 48; `RESULT_RECORDED→FAILED` por DQ-0009). Recurso: `evidence_manifest.receipts` recebe `{ref: "orca:" + owner_dispatch + ":fence", sha256: observation_sha256}` (append permitido, refs únicos, 1054-1058 e 1550-1553), `last_observation` idem (precisa constar em receipts, 1067-1068), `result_acceptance_ref` fica `None` (nullable, 1001-1002; nada foi aceito). Arestas de recurso (49, 1557): variante 2 é um salto `CLOSE_PENDING→CLOSED`; variante 1 exige dois (`REGISTERED→CLOSE_PENDING→CLOSED`), então o apply faz dois `store.transact` (store.py:1605-1630) com a mesma `idempotency_key`:
- salto 1: `mutate` guarda `document["revision"] == snapshot.revision` (padrão 4309-4310) e o estado esperado (atividade no estado da prévia, recurso `REGISTERED`, operação ausente); grava operação `CONFIRMED` + atividade `FAILED` + recurso `CLOSE_PENDING`.
- salto 2 — **não reusa `snapshot.revision`**: `transact` carimba `current.revision + 1` no salto 1 (store.py:1619-1623), então a guarda por revisão antiga cairia sempre em `FENCE-CAS-CONFLICT`. O salto 2 guarda **só por estado**: `operations[operation_id]` presente, `CONFIRMED` e com o mesmo `input_sha256`; atividade `FAILED` com `diagnostic_ref == result_ref`; recurso `CLOSE_PENDING` → fecha; recurso já `CLOSED` → no-op e `FENCE-REUSED`. Equivalente aceitável: reler `store.read_snapshot` (store.py:1340) entre os saltos e guardar pela revisão nova.
- replay completo: operação presente com o mesmo `input_sha256` e recurso `CLOSED` → `FENCE-REUSED` sem segundo evento; qualquer outra divergência → `FENCE-CAS-CONFLICT` (padrão 4341-4343).
- alternativa em um salto (F3, precedente não citado no work item de origem): `PRESERVED` é aresta válida a partir de `REGISTERED` **e** de `CLOSE_PENDING` (49); `_transferred_activity_sessions` + `mutate` do prepare-switch (3711-3750, 3940-3953) já levam `DISPATCHED`+`REGISTERED` a `FAILED` com `diagnostic_ref` lógico (`orca:<dispatch>:superseded-by:<id>`) e o recurso a `PRESERVED` com `preservation_reasons=["RESULT_NOT_DURABLE"]` e `operation_id`, num único `transact`. Elimina o salto 2, a janela de crash e o caso p5. Custo: o recurso aparece em `preserved_resources` do checkpoint (`_cleanup_checkpoint_projection`, 1869; usos 1942 e 3798) e em `retained` do takeover (4281-4282), e a prosa "fecha o recurso" (ROADMAP, handoff, DELIVERY-MAP, CONTEXT) viraria "preserva". Escolha do ciclo executor; este HOW fixa `CLOSED` por ser terminal e coerente com session-protocol.md:87.
`# ponytail:` dois saltos por causa da aresta; se o contrato ganhar `REGISTERED→CLOSED`, vira um.

**Interação com `_continuity_quiescence` (3654-3672).** Sem mudança: `FAILED` não está no conjunto ativo (3664) e o recurso `CLOSED` não é `UNKNOWN` (3668). Após o fence o takeover deixa de acusar `TAKEOVER-WORK-ACTIVE` sem tocar em `_takeover_prepared_workers` (3675-3681); `prepare-switch` deixa de acusar `CONTINUITY-ACTIVE-WORK` (3975) por essa atividade.

**Interação com `gauntlet-context-takeover` (4126-4350).** Ordem: fence → takeover preview → takeover apply. O `expected` do takeover não cobre atividades (4260-4263), mas `mutate` fixa `document["revision"]` (4309-4310): fence entre preview e apply do takeover → `TAKEOVER-CAS-CONFLICT`, nova prévia. `TAKEOVER-REUSED` (4147-4156) e `CONTINUITY-CHECKPOINT-MISSING` (4184-4187) inalterados; no X7 `campaign=None`, sem checkpoint exigido; no work item de origem também não há campanha. O contexto da atividade permanece `ACTIVE` com líder terminal até o takeover o superseder; um líder "ressuscitado" continua recusado por `observe()` (`LEADER-AUTHORITY-UNPROVEN`, agent_runtime.py:808-823).

**Attempt 2 no contexto sucessor.** Depois de `TAKEOVER-APPLIED`, o sucessor roda `gauntlet-activity --phase prepare|dispatch` com `activity_id` novo no `context_id` novo; `activity_id` é chave única do dicionário (`value["activity_id"] != activity_id` recusa, agent_orchestration.py:720-721) e `attempt` é identidade write-once gravada como 1 pelo CLI (5990; agent_orchestration.py:1532). O input manifest do attempt 2 não lista a atividade fenced em `required_activity_ids`/`author_activity_ids`. Por DQ-0010: `activity_id` novo por convenção (sufixo incrementado), `attempt=1`, vínculo em `intended_after` (`subject_ids` + `successor`) da operação de fence; sem mudança de CLI nem schema.

**Testes negativos (obrigação; F7).** A obrigação vem de DQ-0006 ("Testes negativos: sem autorização; autorização de outro contexto/atividade/run; líder vivo; especialista vivo") e da cláusula constitucional "Fail-closed sem waiver" (toda recusa deixa o Store igual). Nota de origem: o brief do coordenador citou uma "regra 11" do `CLAUDE.md` do projeto consumidor proxy-cm-ai (salvaguarda nova exige teste negativo); a fonte não está nos inputs e fica só como origem, não como âncora. Em `tests/validate_agent_orchestration_contract.py`, padrão de `test_context_takeover` (2257-2646): `takeover_show(dispatch_id, *, status, revoked, liveness)` (62), `guarded_run` (2281) interceptando só `worker-show` e roteando por `--dispatch`, `assert_refused_and_unwritten` (2297) comparando `content_sha256` do Store antes/depois em preview **e** apply. Casos: (n1) sem `--authorization`/arquivo ausente/ilegível/malformado/`decision != APPROVED` → `FENCE-AUTHORIZATION-INVALID`; (n2) escopo de outro `context_id`, outro `activity_id` e um `run_id` → `FENCE-AUTHORIZATION-INVALID`; (n3) líder vivo (`dispatched` + liveness `live/agent_status`) que não é o chamador → `FENCE-LEADER-ACTIVE`; (n3b) líder vivo que é o líder corrente exato e atividade retida → admitido (DQ-0008); (n3c) líder terminal e `--session-ref` cuja `_session_readiness` não conclui → recusa de readiness, nada escrito (F4); (n4) especialista `dispatched`/`running` + `live` → `FENCE-SPECIALIST-ACTIVE`; (n5) liveness `unverifiable` com `status=dispatched` e `capabilityRevokedAt=null` → `FENCE-SPECIALIST-UNPROVEN`; (n6) `not_observable` → `FENCE-NOT-OBSERVABLE`; (n7) hash stale, inclusive `--session-ref` diferente da prévia → `FENCE-INPUTS-STALE`; (n8) atividade `ACCEPTED`/`FAILED`/`VERIFIED` → `FENCE-ACTIVITY-STATE`. Positivos: (p1) X7-shape (`DISPATCHED` + `REGISTERED`, líder `completed`, especialista `completed` com capability revogada, especialista observado por `orca:<owner_dispatch>`) → `FENCE-PREVIEW`, `FENCE-APPLIED`, atividade `FAILED` com `diagnostic_ref`, recurso `CLOSED` com receipt, operação `CONFIRMED` com autorização verbatim e `requester`, depois `gauntlet-context-takeover` → `TAKEOVER-APPLIED`; (p2) forma retida (`RESULT_RECORDED` + `CLOSE_PENDING`, `retained/user_owned`, `unverifiable`) — pela aresta `RESULT_RECORDED → FAILED` (DQ-0009); (p3) replay → `FENCE-REUSED` sem segundo evento; (p4) `gauntlet-activity --phase accept` após fence → `ACTIVITY-STATE-DIVERGENCE` (6074-6075); (p5) apply interrompido entre os dois saltos e reaplicado → `CLOSED` (a guarda por estado do salto 2 é o que este caso prova). Contrato de arestas travado em `validate_agent_orchestration_contract.py` (DQ-0009 A), incluindo a recusa de `RESULT_RECORDED → FAILED` sem `diagnostic_ref` e fora do fence. Sem rede, sem `orca` real (transporte injetado), CI ubuntu/windows/macos, Python 3.10/3.13.

**Restrições.** Somente stdlib, Python ≥ 3.10. Nenhuma edição em `.specify/memory/constitution.md`, `WORKFLOW.md`, tuplas `ESSENTIAL` (`ensure_workflow`, `workflow_v3`, `workflow_v4`), registries/catálogos/snapshots de confiança. Nenhuma alteração em `SPECIALIST_PAIRS`, na policy `agent-orchestration.v1.json`, em `attestation.py`, em `agent_runtime.py` nem no schema do Store além da aresta `RESULT_RECORDED → FAILED` de DQ-0009. Hooks continuam read-only.

**Bump de distribuição (CLAUDE.md, "Distribuição").** Oito pontos, hoje `6.0.30`, alvo `6.0.31` (fix → PATCH, salvo bump intermediário): `plugin/.claude-plugin/plugin.json:3`, `plugin/.codex-plugin/plugin.json:3`, `.claude-plugin/marketplace.json:11`, `.agents/plugins/marketplace.json:7`, `tests/validate_distribution.py:8` (`VERSION`), `plugin/skills/grill-with-docs/SKILL.md:6` (`# Grill with Docs vX.Y.Z`), `plugin/skills/grill-with-docs/references/session-protocol.md:1` (`# Protocolo de sessão vX.Y.Z`), `README.md:3` (`**vX.Y.Z`). Documentação: o parágrafo de session-protocol.md:87 ganha o verbo, as duas provas, a prova de readiness do solicitante, a autorização exata e a frase de que o resultado fenced nunca é aceito; verbo listado onde o protocolo enumera `gauntlet-context-takeover`/`gauntlet-run-abandon` (85-89). `publish.yml` cria tag e Release no merge (Constituição: bump e release obrigatórios).

**Riscos e lock-in.**
- Códigos, veredictos e `kind="activity-fence"` viram contrato público travado por teste; renomear depois custa bump e migração de prosa.
- Colisão de vocabulário (F6): `fence` já é o inteiro de autoridade do líder (`leader.fence`, agent_orchestration.py:1378) e `release_proof=resource-fence` (agent_runtime.py:1042; session-protocol.md:87). `activity-fence`/`FENCE-*` são distintos por prefixo; renomear (`activity-close`, `orphan-fence`) é opção do executor, não bloqueia.
- `content_sha256` sem comparação (precedente) permite reutilizar a mesma autorização enquanto a tripla não mudar; o hash da prévia inclui a autorização e o solicitante, mas não amarra a autorização às observações. Mitigação opcional acima.
- Dois saltos de recurso na variante 1: janela de crash entre saltos deixa `FAILED` + `CLOSE_PENDING`; coberto por replay idempotente (p5). Não bloqueia takeover, pois `CLOSE_PENDING` não é `UNKNOWN`.
- O Store do X7 vive em outra máquina (EVIDENCE GAP, DQ-0001): rodar a prévia lá antes de qualquer apply; a prévia é read-only.
- Campos Orca `retained`/`user_takeover`/`missing_status` não são contrato versionado; a prova usa só `status`, `capabilityRevokedAt` e `liveness`, já consumidos pelo takeover. `observe_predecessor_termination` trata qualquer `status` fora de `{dispatched, running}` como terminal (agent_runtime.py:1287), inclusive um status novo do Orca; o fence herda esse comportamento do takeover.
- Lock-in de vocabulário: `scope` canônico com `:`; mudar o separador invalida autorizações já emitidas.
- Recurso fechado sem `result_acceptance_ref` continua `RESULT_NOT_DURABLE` em `cleanup_reasons` (agent_orchestration.py:1083); irrelevante após supersede (cleanup filtra pelo contexto corrente, 4273-4282), mas aparece em auditoria.

## FASE-002 — Encerramento do work item de origem por fence autorizado
- phase: FASE-002
- ADRs: ADR-0001
- BLs: BL-0001
- delivery-units: DU-002
- development-type: platform-devops

### HOW
**Pré-condição (BL-0001).** 6.0.31 publicada (tag imutável + GitHub Release pelo `publish.yml`) e instalada no harness do líder (`preflight` reportando a versão). Até lá a fase fica `planned`; depois do ship da FASE-001 o líder a marca `blocked` (o auditor exige BL open válido para `blocked` e recusa fase `ready` ligada a BL open, audit_decisions.py:740-745), e só promove a `ready-for-specify` ao resolver o BL.

**Sequência.** (1) `gauntlet-activity-fence ROOT --work-id fix-continuidade-sem-checkpoint-d62bb2a5380d4409ace677fa741af28d --activity-id interview-author-001 --session-ref <sessão do líder GWD> --authorization <bundle>` em preview: conferir `activity_state=RESULT_RECORDED`, recurso `CLOSE_PENDING`, especialista `ctx_2923e0218c89` terminal (dispatch `completed`, capability revogada), veredicto do líder `orca:ctx_ad48e72ddf4c` (terminal → o solicitante é provado por `_session_readiness`; vivo → só ele pode pedir). (2) Bundle `human-authorization/v1` com `scope = "fix-continuidade-sem-checkpoint-d62bb2a5380d4409ace677fa741af28d:ctx-0c0155ef5a94:interview-author-001"`, `receipt_ref` = recibo humano da autorização. (3) `--apply --expected-sha256` com o hash da prévia; replay devolve `FENCE-REUSED`. (4) Bundle de origem, editado pelo líder (não há verbo de supersede de work item no core; a marcação é do bundle, session-protocol.md:213): `ROADMAP.md` FASE-001 `state: superseded`; `state.json` `milestone_status=completed`, `status=complete`, `active_phase=null`, `audit_verdict=GO`; `docs/adr/ADR-0001.md` `status: superseded`, `superseded-by: fix-fence-autorizado-atividade-f831232ae30e4087adbaa988bc0f7b24/ADR-0001`; `audit` do bundle de origem devolve `MILESTONE-COMPLETE`. (5) `gauntlet-activity --phase accept` sobre a atividade cercada recusa `ACTIVITY-STATE-DIVERGENCE` (6074-6075) — evidência do critério "aceite tardio".

**Fora.** Takeover do contexto de origem só se algum verbo `@_gauntlet_authorized` for necessário lá (ver DQ proposta no resultado do autor); attempt 2 do autor de origem não é executado; nada em `plugin/**`; Store do X7 intocado.

> Mantenha um bloco por fase e referências ADR/BL exatamente equivalentes ao ROADMAP e ao handoff. Nunca registre `selected-handoff` aqui.
```

## DELIVERY-MAP.md

```markdown
# DELIVERY-MAP

decomposition-schema: v1

## MOD-001 — Continuidade do líder (core CLI)
- module-kind: platform
- responsibility: Levar atividades órfãs ou de sessão retida a estado terminal não aceito, sob prova terminal Orca, prova de readiness do solicitante e autorização humana exata, para que takeover e prepare-switch voltem a admitir o work item
- boundary: `grill_workspace.py` (verbo, admissão, mutação CAS), `grill_core/agent_orchestration.py` (aresta `RESULT_RECORDED → FAILED`, DQ-0009), `tests/validate_agent_orchestration_contract.py`, `references/session-protocol.md`, oito pontos de distribuição; sem tocar `attestation.py`, `agent_runtime.py`, policy, registries, Constituição ou WORKFLOW
- depends-on: none

### DU-001 — Verbo de fence autorizado
- development-type: platform-devops
- phase: FASE-001
- scope-in: verbo preview-first com `--apply --expected-sha256`; provas terminais do especialista (por `orca:<owner_dispatch>`) e do líder pela observação do takeover; readiness do solicitante sucessor por `_session_readiness`; `human-authorization/v1` com escopo `work_id + context_id + activity_id`; atividade `FAILED` com `diagnostic_ref`; recurso `CLOSED` com receipt; operação `CONFIRMED` com evidência, solicitante e autorização verbatim; testes negativos e positivos; parágrafo no protocolo de sessão; bump de versão 6.0.31
- scope-out: aceite, transferência ou reaproveitamento de resultado; fence de workers de run; SGD-37; SGD-38; SGD-39; checkpoint automático; mudanças no Orca, na policy ou nos registries; encerramento do work item de origem
- depends-on: none
- acceptance: `tests/run_validators.py` verde sem rede em ubuntu/windows/macos × Python 3.10/3.13; os quatro negativos de DQ-0006 mais inconclusivo, readiness do solicitante, stale e replay deixam o Store bit a bit igual; forma X7 fenced e em seguida `TAKEOVER-APPLIED`; forma retida fenced pela aresta nova; aceite tardio recusado; `validate_distribution.py` casando 6.0.31 nos oito pontos

## MOD-002 — Encerramento do work item de origem
- module-kind: cross-cutting
- responsibility: Levar o work item fix-continuidade-sem-checkpoint-d62bb2a5380d4409ace677fa741af28d a `superseded` com o verbo de MOD-001, sem aceitar nem reexecutar `interview-author-001`
- boundary: bundle `.grill/work-items/fix-continuidade-sem-checkpoint-d62bb2a5380d4409ace677fa741af28d/` (ROADMAP.md, state.json, docs/adr/ADR-0001.md) e o Store de orquestração deste repositório, somente pelos verbos públicos; nenhum byte em `plugin/**`
- depends-on: MOD-001

### DU-002 — Fence de `interview-author-001` de origem e supersede do bundle
- development-type: platform-devops
- phase: FASE-002
- scope-in: prévia e aplicação do fence sobre `interview-author-001` do work item de origem com autorização exata; marcação `superseded` da fase de origem, milestone de origem completo, `superseded-by` no ADR de origem
- scope-out: código e distribuição; Store do X7; attempt 2 do autor de origem; aceite do resultado retido
- depends-on: DU-001
- acceptance: fence devolve `FENCE-APPLIED` (ou `FENCE-REUSED` no replay) com receipt e autorização verbatim; quiescência do work item de origem vazia; `audit` do bundle de origem devolve `MILESTONE-COMPLETE`; `gauntlet-activity --phase accept` sobre a atividade cercada recusa `ACTIVITY-STATE-DIVERGENCE`

> IDs are stable within this work item. `module-kind` is one of `domain|platform|cross-cutting`; each DU has exactly one closed development type.
```

## DECISION-FRONTIER.md

```markdown
# DECISION FRONTIER

## DQ-0001 — O contexto do X7 no Store tem `campaign` preenchido junto de `checkpoint_head=null`?
- phase: FASE-001
- fingerprint: x7-store-context-campaign-vs-checkpoint-head
- impact: high
- state: resolved
- context-refs: quiescência, takeover
- artifacts: ROADMAP.md, handoffs/FASE-001-SPECIFY-HANDOFF.md
- depends-on: none
- final-ref: R-0002
- migrated-from: fix-continuidade-sem-checkpoint-d62bb2a5380d4409ace677fa741af28d/DQ-0001
- resolution: caso (1). Store do X7 (coordenador, saída literal `ACTIVE None False []`): contexto ACTIVE, `checkpoint_head=None`, `campaign` ausente, zero checkpoints. Na 6.0.30 a lacuna de checkpoint deixa de bloquear: takeover não exige head com `campaign` nulo (ws:4184) e prepare-switch projeta `cp-init` (T005). O defeito `campaign` preenchido + head nulo (KeyError ws:3891) não é o estado do X7; fica como achado lateral.
- evidence: 6.0.30 `gauntlet_context_takeover_command` só exige `checkpoint_head` quando `context.campaign` não é nulo (grill_workspace.py:4184-4187); `gauntlet_prepare_switch_command` projeta `cp-init-*` quando o head é nulo (T005, 3860-3873), mas com `campaign` preenchido lê `item["checkpoints"][cp-init]` do snapshot antes de existir e cai em `CONTINUITY-STATE-DIVERGENCE` (3888-3893). O código atual só grava `campaign` na mesma transação que grava `checkpoint_head` (1992-1997, 3916-3920, 4325). A falha do X7 foi observada na 6.0.25, anterior ao T005/takeover (0e95746, v6.0.28). EVIDENCE GAP: Store do X7 em outra máquina.

## DQ-0002 — Qual o escopo da correção entre as três candidatas (recuperação autorizada, prevenção, transcript > 16 MiB)?
- phase: FASE-001
- fingerprint: fix-scope-recovery-prevention-transcript
- impact: high
- state: resolved
- context-refs: fence autorizado, atividade órfã
- artifacts: docs/adr/, ROADMAP.md, PLAN-CONTEXT.md
- depends-on: DQ-0001
- final-ref: R-0004
- migrated-from: fix-continuidade-sem-checkpoint-d62bb2a5380d4409ace677fa741af28d/DQ-0002
- resolution: decisão humana (coordenador, opção A): escopo = somente a rota de recuperação da atividade órfã (DISPATCHED com especialista encerrado e líder liberado). Transcript > 16 MiB -> SGD-37; KeyError do prepare-switch com campaign e head nulo -> SGD-38. Prevenção por checkpoint automático descartada: T005 já cobre head nulo.

## DQ-0003 — A projeção do checkpoint a partir do `state.json` exige autorização humana exata e conferência das atestações aceitas?
- phase: FASE-001
- fingerprint: derived-checkpoint-human-authorization
- impact: high
- state: out-of-scope
- context-refs: autorização humana exata
- artifacts: docs/adr/, PLAN-CONTEXT.md
- depends-on: DQ-0002
- final-ref: R-0004
- migrated-from: fix-continuidade-sem-checkpoint-d62bb2a5380d4409ace677fa741af28d/DQ-0003
- resolution: checkpoint projetado não é mais o gap (T005 na 6.0.28+, X7 com campaign nulo); a questão de autorização migra para DQ-0006.
- evidence: `_initial_continuity_checkpoint` copia `development` do `state.json` sem comparar com atividades/aceites do Store (grill_workspace.py:3808-3823). O precedente `gauntlet-run-abandon` valida `human-authorization/v1` com `scope == run_id` (attestation.py:191-193, 773-781).

## DQ-0004 — Como tratar transcript do líder corrente acima de 16 MiB?
- phase: FASE-001
- fingerprint: leader-transcript-over-16mib
- impact: medium
- state: out-of-scope
- context-refs: prova terminal Orca
- artifacts: docs/adr/, PLAN-CONTEXT.md
- depends-on: DQ-0002
- final-ref: R-0004
- migrated-from: fix-continuidade-sem-checkpoint-d62bb2a5380d4409ace677fa741af28d/DQ-0004
- resolution: fora do escopo por DQ-0002; registrado como SGD-37 com gatilho.
- evidence: o limite só incide no transcript da sessão corrente via `_session_readiness`/`project_leader_presentation` quando o Orca devolve conteúdo recortado (agent_runtime.py:603, 760, 1113-1114); `observe`/`observe_released` do líder liberado não leem transcript.

## DQ-0005 — Quais atividades/recursos do contexto X7 estão em voo (autor x7-3 com resultado não aceito, revisor ctx_8c7cb66ad5d3 ocioso)?
- phase: FASE-001
- fingerprint: x7-inflight-activities-block-takeover
- impact: high
- state: resolved
- context-refs: quiescência, atividade órfã, takeover
- artifacts: ROADMAP.md, docs/adr/
- depends-on: DQ-0001
- final-ref: R-0003
- migrated-from: fix-continuidade-sem-checkpoint-d62bb2a5380d4409ace677fa741af28d/DQ-0005
- resolution: bloqueio real. Store do X7 (coordenador, saída literal): `A converge-final-author-x7-3 author DISPATCHED ctx-3d2202b3201b converge REGISTERED ctx_822340e6d1d1` e `R session-1b989c4a052f0b3550a2e811 session REGISTERED`; revisor ctx_8c7cb66ad5d3 não tem atividade em voo no Store. O resultado do autor nunca foi gravado (DISPATCHED, não RESULT_RECORDED). Na 6.0.30: takeover recusa `TAKEOVER-WORK-ACTIVE`; prepare-switch `--released-source` recusa `CONTINUITY-ACTIVE-WORK` (só aquieta RESULT_RECORDED de autor liberado). Instalar 6.0.30 não destrava o X7; o gap é atividade DISPATCHED órfã com líder liberado.
- evidence: `_continuity_quiescence` (ws:3654-3672) conta como ativa toda atividade BOOTSTRAPPING/VERIFIED/DISPATCHED/RESULT_RECORDED cuja sessão não esteja CLOSED com `result_acceptance_ref`; takeover recusa `TAKEOVER-WORK-ACTIVE` (ws:4169-4174) e só herda workers PREPARED; prepare-switch `--released-source` só aquieta resultado de autor com sessão Orca liberada (ws:3690-3714), fechando sem aceitar. EVIDENCE GAP: estados no Store do X7.

## DQ-0006 — Qual o destino de uma atividade DISPATCHED órfã (especialista encerrado, líder liberado) para liberar a sucessão?
- phase: FASE-001
- fingerprint: orphan-dispatched-activity-disposition
- impact: high
- state: resolved
- context-refs: atividade órfã, takeover, autorização humana exata
- artifacts: docs/adr/, PLAN-CONTEXT.md, handoffs/FASE-001-SPECIFY-HANDOFF.md
- depends-on: DQ-0002, DQ-0005
- final-ref: R-0005
- migrated-from: fix-continuidade-sem-checkpoint-d62bb2a5380d4409ace677fa741af28d/DQ-0006
- resolution: decisão humana (coordenador, opção A): fence autorizado por verbo novo preview-first (`--apply --expected-sha256`), exigindo (1) prova Orca de dispatch terminal do especialista E do líder e (2) `human-authorization/v1` vinculado a work_id + context_id + activity_id exatos. O resultado não é aceito; o sucessor reexecuta o autor como attempt 2. Testes negativos: sem autorização; autorização de outro contexto/atividade/run; líder vivo; especialista vivo.
- evidence: protocolo de sessão: "Resultados de atividades nunca herdam essas exceções" (references/session-protocol.md:87); precedente `gauntlet-run-abandon` com `human-authorization/v1` e `scope == run_id` (attestation.py:191-193, 773-781); takeover herda só workers PREPARED (ws:4169-4174).

## DQ-0007 — A variante `RESULT_RECORDED` com sessão retida ou `CLOSE_PENDING` entra no escopo do fence?
- phase: FASE-001
- fingerprint: retained-session-result-recorded-in-scope
- impact: high
- state: resolved
- context-refs: sessão retida, fence autorizado, resultado não aceito
- artifacts: docs/adr/ADR-0001.md, ROADMAP.md, PLAN-CONTEXT.md, handoffs/FASE-001-SPECIFY-HANDOFF.md, DELIVERY-MAP.md, CONTEXT.md
- depends-on: DQ-0006
- final-ref: R-0006
- migrated-from: fix-continuidade-sem-checkpoint-d62bb2a5380d4409ace677fa741af28d/DQ-0007
- resolution: decisão humana (coordenador, msg_ff60609e12bb): entra no escopo. O fence autorizado cobre `DISPATCHED` órfã e `RESULT_RECORDED` com sessão não liberada; mantém não-aceite do resultado, autorização exata work_id+context_id+activity_id, prova terminal Orca e testes negativos. No work item de origem (fix-continuidade-sem-checkpoint-d62bb2a5380d4409ace677fa741af28d) foi entregue ao autor como adendo (`agent-orchestration/activities/interview-author-002.payload-addendum.md` daquele bundle) e registrado na fronteira de origem após o aceite de interview-author-002 para preservar seu `input_sha256`.
- evidence: `interview-author-001` do work item de origem (dispatch ctx_2923e0218c89) ficou `RESULT_RECORDED` com recurso `CLOSE_PENDING`; Orca `releaseState=retained`, `ownershipState=user_owned`, `retainedReason=user_takeover`, liveness `unverifiable`; aceite recusou `SESSION-CLOSE-UNPROVEN` (agent_orchestration.py `accept_activity`; agent_runtime.py:1222-1233). A mesma atividade bloqueou depois o takeover do work item de origem com `TAKEOVER-WORK-ACTIVE`.

## DQ-0008 — Quem tem autoridade para pedir o fence quando o líder da atividade está vivo (variante de sessão retida)?
- phase: FASE-001
- fingerprint: fence-authority-live-leader
- impact: high
- state: resolved
- context-refs: fence autorizado, sessão retida, takeover
- artifacts: docs/adr/ADR-0001.md, PLAN-CONTEXT.md, handoffs/FASE-001-SPECIFY-HANDOFF.md
- depends-on: DQ-0006, DQ-0007
- final-ref: R-0007
- migrated-from: fix-continuidade-sem-checkpoint-d62bb2a5380d4409ace677fa741af28d/DQ-0008
- resolution: decisão humana (coordenador, opção A): um verbo só, autoridade derivada da observação do líder. Líder terminal: aceita sucessor com prova do host. Líder vivo: só o líder corrente exato (`_require_current_leader`). Líder vivo e chamador diferente: `FENCE-LEADER-ACTIVE`. O teste negativo vira "líder vivo que não é o chamador".
- evidence: proposta de interview-author-002 do work item de origem (result.md daquele bundle, "DQs propostas"); `_require_current_leader` (grill_workspace.py:1658-1671); negativo "líder vivo" decidido em DQ-0006 para a variante órfã.

## DQ-0009 — Como levar `RESULT_RECORDED` a estado terminal não aceito, dado que `RESULT_RECORDED → FAILED` não é aresta válida?
- phase: FASE-001
- fingerprint: result-recorded-terminal-edge
- impact: high
- state: resolved
- context-refs: sessão retida, resultado não aceito, quiescência
- artifacts: docs/adr/ADR-0001.md, PLAN-CONTEXT.md, DELIVERY-MAP.md
- depends-on: DQ-0007
- final-ref: R-0008
- migrated-from: fix-continuidade-sem-checkpoint-d62bb2a5380d4409ace677fa741af28d/DQ-0009
- resolution: decisão humana (coordenador, opção A): nova aresta `RESULT_RECORDED → FAILED` (um literal em `_ACTIVITY_EDGES`); `diagnostic_ref` obrigatório nessa aresta; guarda do CLI permite só ao fence percorrê-la; validador de contrato trava.
- evidence: `_ACTIVITY_EDGES["RESULT_RECORDED"] == {"RESULT_RECORDED", "ACCEPTED"}` (agent_orchestration.py:48), aplicado em `validate_transition` (1538; no HEAD 39380f7, 1541).

## DQ-0010 — Como identificar o attempt 2 no contexto sucessor?
- phase: FASE-001
- fingerprint: attempt-2-identity
- impact: medium
- state: resolved
- context-refs: attempt 2
- artifacts: PLAN-CONTEXT.md, CONTEXT.md
- depends-on: DQ-0006
- final-ref: R-0009
- migrated-from: fix-continuidade-sem-checkpoint-d62bb2a5380d4409ace677fa741af28d/DQ-0010
- resolution: decisão humana (coordenador, opção A): attempt 2 = atividade NOVA com `activity_id` novo por convenção (sufixo incrementado) e `attempt=1`; vínculo com a atividade cercada no `intended_after` da operação de fence (`subject_ids` + `successor`). Sem mudança de CLI nem schema.
- evidence: `activity_id` é chave única (agent_orchestration.py:720); `attempt` write-once (1529; no HEAD 39380f7, 1532) e o CLI grava 1 (grill_workspace.py:5990).

## DQ-0011 — Qual o destino dos 8 findings menores da revisão independente (interview-reviewer-001, APPROVED)?
- phase: FASE-001
- fingerprint: interview-review-findings-disposition
- impact: medium
- state: resolved
- context-refs: fence autorizado, prova terminal Orca, attempt 2
- artifacts: .grill/work-items/fix-continuidade-sem-checkpoint-d62bb2a5380d4409ace677fa741af28d/agent-orchestration/activities/interview-reviewer-001.result.md
- depends-on: DQ-0006, DQ-0007, DQ-0008, DQ-0009, DQ-0010
- final-ref: R-0010
- migrated-from: fix-continuidade-sem-checkpoint-d62bb2a5380d4409ace677fa741af28d/DQ-0011
- resolution: decisão humana (coordenador, opção A): os artefatos revisados do work item de origem não são tocados. `agent-orchestration/activities/interview-reviewer-001.result.md` daquele bundle (sha256 2b5a62b0aac8c5afb85dc6445e7e156d00f1db08cec8c52c39a8c64051c44872) é insumo obrigatório do ciclo executor. A etapa plan aplica F1 (prefixo `orca:` sobre `owner_dispatch`), F2 (guarda de revisão do segundo transact, ou `PRESERVED` em um salto) e F4 (mecanismo `_session_readiness` e registro do solicitante) como correção obrigatória, com autor xhigh e revisor high próprios. F8 (prepare-switch grava `ACCEPTED` contra session-protocol.md:87) vira SGD-39. F3, F5, F6 e F7 ficam como insumo, sem obrigação. Registrado como DQ porque o auditor só aceita o evento lifecycle `phase-turn` (audit_decisions.py:48).
- evidence: revisão `interview-reviewer-001` ACCEPTED/APPROVED no Store do work item de origem (rev 3259); findings com file:line no resultado persistido; SGD-39 aberto no backlog `SGD`. Nesta migração, por ordem do coordenador, F1/F2/F4 estão aplicados em PLAN-CONTEXT.md, F5 em ROADMAP.md e no handoff da FASE-001, F6 em CONTEXT.md, F7 em PLAN-CONTEXT.md e F8 nas Relações do ADR-0001.

> Estados: open | resolved | deferred | split | blocked | out-of-scope. Não duplique fingerprints abertos.
```

## DECISION-BACKLOG.md

```markdown
# DECISION-BACKLOG

## BL-0001 — Marcar o work item de origem como superseded depois do ship da 6.0.31
- state: open
- phase: FASE-002
- owner: líder GWD deste work item (contexto ctx-146fb68d0d6e)
- decision: quando e como o work item fix-continuidade-sem-checkpoint-d62bb2a5380d4409ace677fa741af28d é encerrado como `superseded`: cercar sua atividade `interview-author-001` (sessão retida, dispatch ctx_2923e0218c89, contexto ctx-0c0155ef5a94, líder orca:ctx_ad48e72ddf4c) pelo verbo de fence autorizado publicado na 6.0.31, com autorização humana exata, e fechar o milestone de origem apontando para este work item; o resultado retido nunca é aceito
- trigger: release 6.0.31 publicada (tag imutável e GitHub Release criadas pelo publish.yml no merge para main) e plugin 6.0.31 instalado no harness do líder
- evidence-needed: `gh release view` da 6.0.31 com a tag ancorada no commit do ship; `preflight` do líder reportando o plugin 6.0.31; prévia do fence sobre o work item de origem com especialista terminal (ctx_2923e0218c89: dispatch completed, capability revogada) e veredicto do líder orca:ctx_ad48e72ddf4c; recibo humano (`receipt_ref`) da autorização com scope `fix-continuidade-sem-checkpoint-d62bb2a5380d4409ace677fa741af28d:ctx-0c0155ef5a94:interview-author-001`
- next-action: depois do ship da FASE-001, o líder marca FASE-002 `blocked` até o gatilho; ao cumprir o gatilho, registra este BL como `resolved` com a evidência acima, promove FASE-002 a `ready-for-specify` e executa handoffs/FASE-002-SPECIFY-HANDOFF.md
- resolution: none

> Estados: `open | resolved | superseded`; `resolved` e `superseded` são terminais. Todo BL pertence a exatamente uma fase e deve ser referenciado no ROADMAP, handoff e PLAN-CONTEXT. Não fabrique um BL apenas para preencher o template.
```

## CONSTITUTION-CHECK.md

Proposta de preenchimento; o líder confere cada evidência antes de gravar. `<líder>` = `session_ref` do líder do contexto `ctx-146fb68d0d6e` no Store (não está nos meus inputs).

````markdown
# Constitution Check

<!-- grill-constitution-check:start -->
```json
{
  "clauses": [
    {
      "evidence": [
        "DECISION-FRONTIER.md",
        "docs/adr/ADR-0001.md#Contexto",
        "PLAN-CONTEXT.md",
        "agent-orchestration/activities/interview-author-001.input.json",
        "agent-orchestration/activities/interview-author-001.result.md",
        ".grill/work-items/fix-continuidade-sem-checkpoint-d62bb2a5380d4409ace677fa741af28d/DECISION-FRONTIER.md",
        ".grill/work-items/fix-continuidade-sem-checkpoint-d62bb2a5380d4409ace677fa741af28d/ROUND-LOG.jsonl"
      ],
      "heading": "Evidência antes de afirmação",
      "id": "evid-ncia-antes-de-afirma-o",
      "justification": "As onze DQs migradas mantêm a evidência original (leituras literais do Store do X7 pelo coordenador; file:line da 6.0.30) e ganharam `migrated-from` apontando o work item de origem. Toda citação file:line herdada foi reconferida no HEAD 39380f7, incluindo o deslocamento +3 em agent_orchestration.py após o cherry-pick f1475f4. O autor conferiu os 27 sha256 do input manifest. A variante retida foi observada ao vivo no work item de origem (interview-author-001/ctx_2923e0218c89, SESSION-CLOSE-UNPROVEN e depois TAKEOVER-WORK-ACTIVE).",
      "status": "PASS"
    },
    {
      "evidence": [
        "WORK-ITEM.json",
        "state.json"
      ],
      "heading": "Work item isolado e ownership",
      "id": "work-item-isolado-e-ownership",
      "justification": "Work item fix criado por init com identidade collision-resistant fix-fence-autorizado-atividade-f831232ae30e4087adbaa988bc0f7b24 (base_commit 39380f7, branch cadugevaerd/fix-leader), contexto ctx-146fb68d0d6e com líder <líder>. O work item de origem não foi tocado: a migração copia decisões seladas e o encerramento dele é fase própria (FASE-002, BL-0001), depois do ship.",
      "status": "PASS"
    },
    {
      "evidence": [
        "ROADMAP.md#FASE-001 — Fence autorizado de atividade órfã",
        "handoffs/FASE-001-SPECIFY-HANDOFF.md#WHY"
      ],
      "heading": "Feature/fix plan-only",
      "id": "feature-fix-plan-only",
      "justification": "Nenhum byte fora de .grill/ foi alterado nesta sessão: `git status --porcelain` só lista o bundle deste work item como untracked; plugin/**, tests/ e docs estão intocados. A sessão termina em PLAN_ONLY_STOP; implementação e ship ficam para o ciclo executor.",
      "status": "PASS"
    },
    {
      "evidence": [
        "state.json",
        "handoffs/FASE-001-SPECIFY-HANDOFF.md"
      ],
      "heading": "Sequência obrigatória do desenvolvimento",
      "id": "sequ-ncia-obrigat-ria-do-desenvolvimento",
      "justification": "state.json mantém os onze passos pending, com current_step=specify e workflow_version=v4. O handoff é o insumo da etapa specify e não autoriza saltos; o ciclo executor segue specify → ... → ship.",
      "status": "PASS"
    },
    {
      "evidence": [
        "state.json"
      ],
      "heading": "Verify/review antes de ship",
      "id": "verify-review-antes-de-ship",
      "justification": "Não há ship nesta sessão plan-only; verify, review e ship estão pending. A obrigação vale no ciclo executor, e o DU-001 lista a suíte e o validador de distribuição como aceite.",
      "status": "NOT-APPLICABLE"
    },
    {
      "evidence": [
        "docs/adr/ADR-0001.md#Decisão",
        "PLAN-CONTEXT.md",
        "DECISION-FRONTIER.md#DQ-0006 — Qual o destino de uma atividade DISPATCHED órfã (especialista encerrado, líder liberado) para liberar a sucessão?"
      ],
      "heading": "Fail-closed sem waiver",
      "id": "fail-closed-sem-waiver",
      "justification": "A rota decidida é fail-closed: exige prova terminal Orca, prova de readiness do solicitante e autorização humana exata, e toda recusa deixa o Store igual (obrigação dos testes negativos ancorada em DQ-0006 e nesta cláusula). A recusa TAKEOVER-WORK-ACTIVE do work item de origem não foi contornada: nenhum Store foi editado à mão e a saída é um work item novo com as mesmas decisões, mais uma fase que cerca o de origem pelo verbo quando ele existir.",
      "status": "PASS"
    },
    {
      "evidence": [
        "DECISION-FRONTIER.md",
        "DELIVERY-MAP.md",
        "DECISION-BACKLOG.md",
        "agent-orchestration/activities/interview-author-001.input.json",
        "agent-orchestration/activities/interview-author-001.result.md"
      ],
      "heading": "Rastreabilidade",
      "id": "rastreabilidade",
      "justification": "Cada DQ traz `migrated-from: <work item de origem>/DQ-NNNN` e o final-ref original. MOD-001/DU-001 ligam a FASE-001 ao ADR-0001; MOD-002/DU-002 ligam a FASE-002 ao BL-0001. A atividade de autor tem input manifest com sha256 (27 arquivos), observação Orca e resultado persistido. SGD-37, SGD-38 e SGD-39 existem no backlog SGD.",
      "status": "PASS"
    },
    {
      "evidence": [
        "agent-orchestration/activities/interview-author-001.observation.json"
      ],
      "heading": "Tier de modelo e esforço do worker Orca",
      "id": "tier-de-modelo-e-esfor-o-do-worker-orca",
      "justification": "O worker de autoria (arquitetura) foi lançado com --model fable --effort xhigh, tier forte e esforço alto; a observação normalizada registra requested_model=fable, requested_effort=xhigh, effective_model=fable, effective_effort=xhigh, resolved_model_id=fable. Nenhum --terminal foi reutilizado.",
      "status": "PASS"
    },
    {
      "evidence": [
        "git status --porcelain: nenhum caminho sob plugin/** modificado por este work item",
        "PLAN-CONTEXT.md"
      ],
      "heading": "Bump obrigatório do plugin",
      "id": "bump-obrigat-rio-do-plugin",
      "justification": "Nenhum byte de plugin/** foi alterado neste work item plan-only. O PLAN-CONTEXT registra a obrigação de bump patch 6.0.30 → 6.0.31 nos oito pontos de versão, com as linhas atuais, como pré-requisito do merge no ciclo executor.",
      "status": "NOT-APPLICABLE"
    },
    {
      "evidence": [
        "PLAN-CONTEXT.md",
        "DECISION-BACKLOG.md"
      ],
      "heading": "Release obrigatória por versão",
      "id": "release-obrigat-ria-por-vers-o",
      "justification": "Nenhuma versão é publicada por esta sessão. A release da 6.0.31 é criada pelo publish.yml no merge para main do ciclo executor, ancorada na tag; a existência dessa release é o gatilho do BL-0001.",
      "status": "NOT-APPLICABLE"
    },
    {
      "evidence": [
        ".specify/memory/constitution.md"
      ],
      "heading": "Governance",
      "id": "governance",
      "justification": "A Constituição 2.1.0 (sha256 54d5522b…7569) foi lida e preservada byte a byte; WORK-ITEM.json e state.json selam o mesmo hash. Nenhuma emenda, waiver ou ADR contra ela; hooks usados só como contexto read-only.",
      "status": "PASS"
    }
  ],
  "constitution_sha256": "54d5522b18e43efa05311dbf13ed79694b79ccfcb01509384b3572b2d5667569",
  "constitution_state": "present"
}
```
<!-- grill-constitution-check:end -->
````

## Aplicação de F1/F2/F4/F5

- **F1 (prefixo `orca:`)** — PLAN-CONTEXT FASE-001, parágrafo "Provas exigidas": o especialista é observado por `"orca:" + resource["identity"]["owner_dispatch"]`, forma de `_released_activity_sessions` (grill_workspace.py:3700); justificativa com `observe_predecessor_termination` (agent_runtime.py:1268) e `removeprefix` (grill_workspace.py:1593). Também no DU-001 (`scope-in`) e no caso p1 dos testes.
- **F2 (guarda do segundo salto)** — PLAN-CONTEXT FASE-001, parágrafo "Mutação": salto 2 guarda **só por estado** (operação `CONFIRMED` com mesmo `input_sha256`, atividade `FAILED`, recurso `CLOSE_PENDING`), com a causa citada (`transact` carimba `current.revision + 1`, store.py:1619-1623); equivalente aceitável = reler `read_snapshot` (store.py:1340). A alternativa `PRESERVED` em um salto está registrada com o precedente F3 (`_transferred_activity_sessions` 3711-3750; mutate 3940-3953), custos e a decisão de manter `CLOSED` neste HOW. p5 passa a ser o teste que prova a guarda.
- **F4 (prova do host do sucessor)** — PLAN-CONTEXT FASE-001, parágrafos "Autoridade" e "Hash da prévia": líder terminal → `_session_readiness(root, context["runtime"], args.session_ref, work_id=...)` (grill_workspace.py:1612-1656; mesma chamada do takeover em 4181); `readiness["ref"/"sha256"/"incarnation"]` em `evidence.requester` e `intended_after.requester`; `to_session_ref` no hash da prévia (como 4261). Refletido no handoff (ator "Líder sucessor", cenário 7, critérios "solicitante"), no ADR (Consequências) e no DU-001; caso n3c e n7 nos testes.
- **F5 (líder vivo ou terminal)** — ROADMAP FASE-001 `objetivo`: "cujo líder terminou **ou** que ainda tem líder vivo (DQ-0008)"; handoff cenário 2: "Pedido pelo líder corrente exato quando o líder está vivo, ou por sucessor com prova terminal do líder (DQ-0008)"; ator "Líder corrente" reescrito sem "só na variante 2".
- **F6 (opcional)** — CONTEXT.md, linha "fence autorizado", cell "Termos a evitar": nota de desambiguação contra `leader.fence` (agent_orchestration.py:1378) e `release_proof=resource-fence` (agent_runtime.py:1042; session-protocol.md:87). PLAN-CONTEXT "Riscos e lock-in" menciona a colisão.
- **F7 (opcional)** — PLAN-CONTEXT "Testes negativos": obrigação ancorada em DQ-0006 e na cláusula "Fail-closed sem waiver"; "regra 11" do proxy-cm-ai rebaixada a nota de origem.
- **F8** — ADR-0001 "Relações → backlog": SGD-39 (existe, `open`, título "prepare-switch --released-source grava ACCEPTED contra session-protocol.md:87"), sem tratamento.
- **Nit do revisor** — handoff FASE-001, último critério: "suíte de validadores do repositório verde nos três SOs, sem rede". DELIVERY-MAP mantém `tests/run_validators.py` (não é handoff).
- **Reconferência de linhas** — deslocamentos aplicados: agent_orchestration.py 1529→1532, 1532-1536→1537-1539, 1538→1541, 1545-1551→1550-1553, 1554→1557, 1522→1525; testes 2234→2257, 2258→2281, 2274→2297. Corrigidas citações imprecisas herdadas: takeover 4126-4345→4126-4350, run-abandon 5153-5195→5152-5189, 5175-5186→5174-5182, 3684-3714→3684-3709, `_takeover_observation` 1565-1610→1565-1609, `_require_current_leader` 1658-1671→1658-1670, mapeamento 4157-4166→4158-4166, hash 4249-4262→4247-4263, guardas 4304-4316→4309-4318, agent_runtime 1222-1233→1223-1236, 972-977→972-975. Na DECISION-FRONTIER as citações originais foram mantidas (evidência original), com o número no HEAD entre parênteses onde o cherry-pick deslocou (DQ-0009, DQ-0010).
- **Segundo caso no ADR** — parágrafo "Segundo caso observado" no Contexto; Consequências e Relações (`supersedes`) apontam o work item de origem.
- **FASE-002/BL-0001/DU-002** — a fase existe porque o auditor recusa BL órfão (audit_decisions.py:564-566) e fase `ready` ligada a BL open (740-741), conferido. `validate_decomposition` exige que **toda** fase do ROADMAP tenha os mesmos DUs no DELIVERY-MAP, no handoff e no PLAN-CONTEXT (`phases != expected` → divergência), por isso DU-002/MOD-002 e o bloco FASE-002 no PLAN-CONTEXT; os handoffs não citam DU da outra fase (o auditor coleta todo `DU-\d{3}` do texto).
- **Verificação** — os dez artefatos foram materializados numa cópia do bundle do NOVO em scratchpad (fora do repositório) e submetidos a `plugin/skills/grill-with-docs/scripts/audit_decisions.py <cópia> --project-root <repo> --json` (read-only): `{"code": "OK", "selected_handoff": "handoffs/FASE-001-SPECIFY-HANDOFF.md", "selected_phase": "FASE-001", "verdict": "GO"}`, exit 0. Simulação pós-ship na mesma cópia: FASE-001 `complete` + FASE-002 `blocked` + BL-0001 `open` → `{"code": "EXTERNAL-BLOCKER", "findings": ["dependência externa legítima: BL-0001"], "verdict": "BLOCKED"}`, exit 2; BL-0001 `resolved` + FASE-002 `ready-for-specify` → `GO` selecionando `handoffs/FASE-002-SPECIFY-HANDOFF.md`, exit 0. O JSON do CONSTITUTION-CHECK parseia com 11 cláusulas (`PASS`/`NOT-APPLICABLE`).

### Notas ao líder (não são DQs)
1. `ROUND-LOG.jsonl` do NOVO tem só a linha R-0001 de init. Os `final-ref` migrados (R-0002..R-0010) apontam rodadas do bundle de origem; o auditor não cruza `final-ref` com o ROUND-LOG, mas para rastreabilidade local vale espelhar as linhas R-0002..R-0010 do bundle de origem verbatim (todas com `question_id` existente aqui).
2. `ADRs: ADR-0001` na FASE-002 e `development-type: platform-devops` no DU-002 são escolhas minhas (a fase aplica exatamente aquela decisão; o vocabulário do auditor não tem tipo "operacional"). `documentation` seria a alternativa; trocar exige trocar nos três lugares (DELIVERY-MAP, handoff, PLAN-CONTEXT).
3. `supersedes:` no ADR-0001 aponta o ADR de origem já agora; o `superseded-by` do lado de origem só é gravado na FASE-002. Se preferir simetria estrita, deixe `supersedes: none` até a FASE-002.
4. O campo `<líder>` no CONSTITUTION-CHECK precisa do `session_ref` do líder do contexto `ctx-146fb68d0d6e`, que não está nos meus inputs.

## DQs propostas

### DQ proposta A — O contexto de origem no Store precisa ser assumido (takeover) e liberado depois do fence, ou basta o fence mais a marcação `superseded` no bundle?
- **Pergunta atômica**: após `FENCE-APPLIED` sobre `interview-author-001` do work item de origem, o contexto `ctx-0c0155ef5a94` (líder `orca:ctx_ad48e72ddf4c`, terminal) fica `ACTIVE` no Store para sempre, sem líder vivo. Isso é aceitável para um work item `superseded`?
- **Evidência**: a marcação `superseded` é edição do bundle (`ROADMAP.md`, `state.json`, ADR) e não passa pelo Store (session-protocol.md:213); o takeover só é necessário para verbos `@_gauntlet_authorized` (grill_workspace.py:3393). Todo work item abandonado hoje deixa o mesmo resíduo; nenhum verbo público "encerra" um contexto sem sucessor.
- **Opções**: (A) só fence + bundle; o contexto de origem fica `ACTIVE` com líder terminal, como qualquer work item abandonado. (B) fence → `gauntlet-context-takeover` pelo líder deste work item → bundle; o contexto de origem vira `SUPERSEDED` no Store e o sucessor fica `ACTIVE` sem trabalho. (C) adiar: registrar como item SGD lateral ("verbo de encerramento de contexto sem sucessor").
- **Recomendação**: A. É o menor diff correto e não cria um contexto sucessor vazio para manter; B só se `status`/`preflight` passarem a acusar o contexto de origem como ruído, e nesse caso C é a rota certa em vez de takeover ad hoc.

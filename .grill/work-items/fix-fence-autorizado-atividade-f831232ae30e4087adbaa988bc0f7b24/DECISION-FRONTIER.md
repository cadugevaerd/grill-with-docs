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

## DQ-0012 — Depois do fence sobre o work item de origem, o contexto ctx-0c0155ef5a94 precisa de takeover e liberação, ou basta o fence mais a marcação superseded no bundle?
- phase: FASE-002
- fingerprint: origin-context-after-fence
- impact: low
- state: resolved
- context-refs: fence autorizado, takeover
- artifacts: PLAN-CONTEXT.md, handoffs/FASE-002-SPECIFY-HANDOFF.md
- depends-on: DQ-0006, DQ-0008
- final-ref: R-0011
- resolution: decisão do coordenador sob o goal (opção A; o humano pode reverter, afeta só a FASE-002 pós-ship): só fence + marcação `superseded` no bundle de origem. O contexto `ctx-0c0155ef5a94` (líder `orca:ctx_ad48e72ddf4c`, terminal) fica `ACTIVE` no Store com líder terminal, como qualquer work item abandonado. Sem takeover ad hoc nem sucessor vazio.
- evidence: DQ proposta A de `interview-author-001` (agent-orchestration/activities/interview-author-001.result.md, seção "DQs propostas"): a marcação `superseded` é edição do bundle e não passa pelo Store; takeover só é exigido por verbos `@_gauntlet_authorized`; nenhum verbo público encerra contexto sem sucessor.

> Estados: open | resolved | deferred | split | blocked | out-of-scope. Não duplique fingerprints abertos.

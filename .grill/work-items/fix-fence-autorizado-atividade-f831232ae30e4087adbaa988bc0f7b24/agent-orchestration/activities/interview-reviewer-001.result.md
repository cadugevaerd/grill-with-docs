VERDICT: APPROVED

# Revisão — interview-reviewer-001 (REVISOR, claude/fable/high, requested == effective)

- work item: `fix-fence-autorizado-atividade-f831232ae30e4087adbaa988bc0f7b24` (NOVO), contexto `ctx-146fb68d0d6e`, fence 1, dispatch `ctx_4f1fedf1f5bd`
- fonte: `fix-continuidade-sem-checkpoint-d62bb2a5380d4409ace677fa741af28d` (ANTIGO), contexto `ctx-0c0155ef5a94`, líder `orca:ctx_ad48e72ddf4c`
- worktree `/home/carlosaraujo/orca/workspaces/grill-with-docs/fix-leader`, HEAD `39380f7`; `git status --porcelain` só lista o bundle do NOVO como untracked
- payload lido por inteiro: sha256 `907e6dc340d0dee6feaa776ce81da3b6505daf524a0994a9b2431d05fa22833d` (confere)
- input manifest: 28/28 sha256 conferidos, zero divergência
- nada escrito em `.grill/` nem em `.specify/reports/`
- `audit` read-only executado: `{"code":"OK","selected_handoff":"handoffs/FASE-001-SPECIFY-HANDOFF.md","selected_phase":"FASE-001","verdict":"GO"}`, 11 cláusulas, exit 0

## 0. Edições do líder sobre o resultado do autor — exatamente as declaradas

Diff programático entre cada bloco de `interview-author-001.result.md` e o artefato persistido:

- `CONTEXT.md`, `docs/adr/ADR-0001.md`, `ROADMAP.md`, `handoffs/FASE-001-SPECIFY-HANDOFF.md`, `handoffs/FASE-002-SPECIFY-HANDOFF.md`, `PLAN-CONTEXT.md`, `DELIVERY-MAP.md`, `DECISION-BACKLOG.md`: byte a byte idênticos.
- `DECISION-FRONTIER.md`: única diferença é o bloco DQ-0012 (linhas 145-156) acrescentado.
- `CONSTITUTION-CHECK.md`: única diferença é `<líder>` → `orca:ctx_bf15a89923e5` (linha 29); confere com o Store (contexto `ctx-146fb68d0d6e`, leader `orca:ctx_bf15a89923e5`, fence 1).
- `ROUND-LOG.jsonl`: linhas 1-10 idênticas ao ANTIGO (`diff` limpo); linha 11 = R-0011/DQ-0012.

Nenhuma outra edição.

## 1. Fidelidade às decisões — OK

Comparei DQ-0001..DQ-0011 do NOVO contra o ANTIGO campo a campo. `resolution` e `evidence` são idênticos em todas, salvo: `migrated-from` acrescentado; `context-refs` remapeados para o glossário do NOVO; caminhos e "work item corrente" reescritos como "work item de origem"; DQ-0009/DQ-0010 ganham "(no HEAD 39380f7, N)" ao lado da linha original; DQ-0011 ganha uma frase de evidência dizendo onde F1/F2/F4/F5/F6/F7/F8 foram aplicados. Nada reaberto, ampliado, estreitado ou omitido:

- resultado nunca aceito: handoff-001:15,25,32,38; ADR:55,61,67; CONTEXT:15; DELIVERY-MAP:15,29; FASE-002:15,36.
- autorização exata `work_id + context_id + activity_id`: PLAN-CONTEXT:19; CONTEXT:11; ROADMAP:8; BL-0001:9 (scope literal).
- prova terminal Orca: PLAN-CONTEXT:17; CONTEXT:10; handoff-001:30 (inconclusivo).
- DQ-0008 autoridade derivada do líder: PLAN-CONTEXT:15 (a/b/c); handoff-001:18,21,25,28; ROADMAP:7.
- DQ-0009 aresta `RESULT_RECORDED → FAILED` só pelo fence: ADR:64; PLAN-CONTEXT:23,36,38; DELIVERY-MAP:8.
- DQ-0010 attempt 2 = atividade nova, `attempt=1`, vínculo em `intended_after`: PLAN-CONTEXT:34; ADR:68; CONTEXT:14.
- SGD-37/38/39 fora de escopo: ROADMAP:9; ADR:70,78; DELIVERY-MAP:15. Os três existem `open` no backlog `SGD` (conferido por `backlogctl`).
- DQ-0011: F1/F2/F4 aplicados no HOW já na migração, com autor xhigh (observation: `fable/xhigh`) e revisor high (esta atividade) — cumpre "autor xhigh e revisor high próprios" sem reabrir.
- DQ-0012: registrada como "decisão do coordenador sob o goal", não como decisão humana; R-0011 usa `coordinator:decision` (os demais `coordinator:human-decision`). Rotulagem honesta; impacto `low`, só FASE-002 pós-ship, reversível. Não é decisão nova tomada pelo autor.

Observação sobre a "reexecução como attempt 2" (DQ-0006) no ANTIGO: a FASE-002 não reexecuta o autor de origem porque as decisões já migraram; o `interview-author-001` do NOVO é, na prática, a reautoria. Não contradiz DQ-0006 (o que ela veda é aceitar/herdar o resultado cercado).

## 2. Findings obrigatórios F1, F2, F4 e F5 — aplicados, sem brecha fail-open

- **F1** — PLAN-CONTEXT:17: especialista observado por `"orca:" + resource["identity"]["owner_dispatch"]`. Conferido: `observe_predecessor_termination` só aceita `orca:ctx[-_]…` (agent_runtime.py:1268), `_takeover_observation` faz `removeprefix("orca:")` (grill_workspace.py:1593), `_released_activity_sessions` compõe `"orca:" + dispatch` (3700). No Store, `owner_dispatch` é id nu (`ctx_2923e0218c89`). Também no DU-001 (DELIVERY-MAP:14) e no p1.
- **F2** — PLAN-CONTEXT:23-26: salto 2 guarda só por estado, com a causa correta (`transact` recusa revisão divergente e carimba `current.revision + 1`, store.py:1619-1624). Equivalente `read_snapshot` (1340) citado. Alternativa `PRESERVED` em um salto registrada com o precedente F3 (`_transferred_activity_sessions` 3711-3750; mutate 3940-3953; `PRESERVED` alcançável de `REGISTERED` e `CLOSE_PENDING`, agent_orchestration.py:49). Ver Finding 1 e 6 sobre precisão de ordem, não sobre fail-open.
- **F4** — PLAN-CONTEXT:15,21: líder terminal → `_session_readiness(root, context["runtime"], args.session_ref, work_id=...)` (1612-1655), mesma chamada do takeover (4181); ela recusa `LEADER-AUTHORITY-UNPROVEN`/`STYLE-*` quando não conclui (1632, 1641-1653), então ausência de prova nunca autoriza. `readiness["ref"/"sha256"/"incarnation"]` (1654-1655) em `evidence.requester` e `intended_after.requester`; `to_session_ref` no hash como no takeover (4261). Refletido em handoff-001:18,30,35,39, ADR:66, DELIVERY-MAP:14, casos n3c/n7.
- **F5** — ROADMAP:7 "cujo líder terminou **ou** que ainda tem líder vivo (DQ-0008)"; handoff-001:25 "pedido pelo líder corrente exato quando o líder está vivo, ou por sucessor com prova terminal do líder"; ator "Líder corrente" (handoff-001:21) sem "só na variante 2".

Fail-open: nenhuma. O fence exige mais que o takeover (takeover: predecessor terminal + readiness; fence: especialista terminal + líder terminal-ou-chamador-exato + readiness + `human-authorization/v1` com escopo exato). Silêncio/`unverifiable` sem `status` terminal nem capability revogada → `indeterminate` (agent_runtime.py:1286-1291) → `FENCE-SPECIALIST-UNPROVEN`/`FENCE-LEADER-UNPROVEN`.

## 3. Correção técnica do HOW contra o HEAD 39380f7 — OK, com correções menores

Premissas conferidas no código (todas as citações file:line de PLAN-CONTEXT, ADR-0001, CONTEXT e DECISION-FRONTIER batem; desvio ≤ 1 linha onde há desvio):

- Cherry-pick `f1475f4` insere exatamente 3 linhas em agent_orchestration.py:1393-1395 (`git show --stat`); deslocamento +3 aplicado corretamente: `attempt` write-once 1532, first-bound 1537-1539, `validate_transition` 1541, receipts 1550-1553, arestas de recurso 1557, `CONFIRMED` imutável 1525. Testes: `test_context_takeover` 2257 (termina em 2646; próximo `def` em 2647), `guarded_run` 2281, `assert_refused_and_unwritten` 2297, `takeover_show(dispatch_id, *, status, revoked, liveness)` 62.
- Arestas (48-49): `DISPATCHED→FAILED` válida; `RESULT_RECORDED→FAILED` ausente (DQ-0009); `REGISTERED→CLOSE_PENDING→CLOSED` e `CLOSE_PENDING→CLOSED` válidas.
- `FAILED` com `result_ref` preenchido (variante 2) é válido: 762 exige só a tripla `result_ref/result_sha256/output_manifest` coerente; 770 não inclui `FAILED`; 784-785 exige `diagnostic_ref`. `diagnostic_ref` é `_text` (755) — referência lógica aceita, como `orca:<dispatch>:superseded-by:<id>` do prepare-switch (3952-3953).
- Recurso `CLOSED` com `result_acceptance_ref=None` é válido: nullable (1002-1003), nenhuma exigência por estado em `_resource` (996-1070), nenhum cruzamento atividade/recurso em `validate_block` (1424-1460) além de contexto e kind. Receipt `{ref, sha256}` (`_ref`, ref único 1058); `last_observation` precisa constar em receipts (1067-1068). No ANTIGO os receipts atuais são `['orca:ctx_2923e0218c89']`, então `orca:ctx_2923e0218c89:fence` é único.
- Operação: `kind` string livre (643); `fence == contexts[ctx].leader.fence` (1378); `CONFIRMED` exige `observation_ref` e `result_sha256` (651-652); idempotência por identidade `(kind, context_id, subject_ids, input_sha256)` (1379-1381); `continuity_ref` só exige kind `continuity-switch` para sucessores (1385-1387), então um kind novo não colide. `_ID` (40) não admite `:` — `scope` canônico não ambíguo. `FREE_REF_RE` (attestation.py:134) aceita `msg_…` em `receipt_ref`.
- `_continuity_quiescence` (3654-3672): `FAILED` fora do conjunto ativo (3664); só `UNKNOWN` conta como sessão desconhecida (3668); `CLOSE_PENDING` entre saltos não bloqueia. `_takeover_prepared_workers` intocado (3675-3681). Takeover: REUSED 4148-4156, mapeamento 4158-4166, quiescência 4170-4174, readiness 4181, checkpoint só com `campaign` (4184-4187), hash 4260-4263, guarda de revisão 4309-4310, CAS 4341-4343.
- `gauntlet-activity` é `@_gauntlet_authorized` (5952-5953); `accept` fora de `DISPATCHED|RESULT_RECORDED` → `ACTIVITY-STATE-DIVERGENCE` (6074-6075); `--diagnostic` só em `DISPATCHED` (6078-6080); `attempt=1` (5990); correlação de `owner_dispatch` (6052-6055). `accept_activity` do core recusa fora de `RESULT_RECORDED` (964-965) — não-aceite estrutural.
- Precedente run-abandon: `load_checkpoint_attestation` (5340-5359, caminho relativo sem symlink) + `_validate_human_authorization(bundle, scope)` (773-781) + código único `ABANDON-AUTHORIZATION-INVALID` (5174-5183); `abandon_run` grava o bundle verbatim (gauntlet_runs.py:3119-3126).
- Store vivo (rev 3282): NOVO `interview-author-001` `ACCEPTED`, recurso `CLOSED` com `result_acceptance_ref`; `interview-reviewer-001` `DISPATCHED` (esta sessão, owner `ctx_4f1fedf1f5bd`). ANTIGO `interview-author-001` `RESULT_RECORDED`, `diagnostic_ref=None`, recurso `CLOSE_PENDING`, owner `ctx_2923e0218c89`; `interview-author-002` e `interview-reviewer-001` `ACCEPTED`; contexto `ctx-0c0155ef5a94` `ACTIVE`, líder `orca:ctx_ad48e72ddf4c` estado `ACTIVE`. Nenhum revisor referencia `interview-author-001` em `author_activity_ids`, então o fence não quebra `_reviewer_authors` (399-421).
- Premissa "líder do ANTIGO é terminal" (DQ-0012, BL-0001, FASE-002): sustentada indiretamente — o takeover recusou `TAKEOVER-WORK-ACTIVE` (4174), que só é alcançado depois da observação do líder devolver `terminal` (4158-4166). Caso (a) do HOW é, portanto, o esperado na FASE-002; a prévia read-only confirma antes de qualquer apply.
- Distribuição: os oito pontos estão em `6.0.30` exatamente nas linhas de PLAN-CONTEXT:40.

### Finding 1 — menor — ordem das checagens: replay (p3) e retomada (p5) partem de atividade já `FAILED`
- Evidência: PLAN-CONTEXT:13 fixa `FENCE-ACTIVITY-STATE` para estado fora de `DISPATCHED|RESULT_RECORDED`; PLAN-CONTEXT:26 exige `FENCE-REUSED` no replay e :24-26/p5 exigem retomar o salto 2 com a atividade já `FAILED`. O hash da prévia (:21) inclui `activity_state`, então no replay o `expected` recalculado difere do da primeira aplicação → `FENCE-INPUTS-STALE`. Sem ordem explícita, o executor que implementar na ordem do texto reprova p3 e p5. O takeover resolve isso checando `TAKEOVER-REUSED` antes de tudo (4148-4156), sem comparar hash. Além disso o HOW não define como `operation_id` é cunhado, e o salto 2 / o replay precisam localizar a operação a partir de `(work_id, activity_id)`.
- Correção: em PLAN-CONTEXT:13/23, (i) `operation_id = "fence-" + sha256(canonical({"context": context_id, "activity": activity_id}))[:24]` (determinístico, sem `expected`, para ser reencontrável); (ii) primeira checagem, antes de estado/observações/hash: operação presente com esse id, `kind="activity-fence"`, `CONFIRMED` → se recurso `CLOSED` devolve `FENCE-REUSED`; se recurso `CLOSE_PENDING` e atividade `FAILED` com `diagnostic_ref == result_ref` → executa só o salto 2 (p5); se `input_sha256` divergente → `FENCE-CAS-CONFLICT`; (iii) só então `FENCE-ACTIVITY-STATE`. Não muda decisão nem abre brecha: o replay só reusa o que já está `CONFIRMED`.

### Finding 2 — menor — evidência de "aceite tardio" na FASE-002 inalcançável sem takeover (DQ-0012 A)
- Evidência: DELIVERY-MAP:31 (aceite do DU-002) e PLAN-CONTEXT:62 passo (5) exigem `gauntlet-activity --phase accept` sobre a atividade cercada do ANTIGO devolvendo `ACTIVITY-STATE-DIVERGENCE`. `gauntlet-activity` é `@_gauntlet_authorized` (5952): o decorator chama `require_authority` (3441-3444) e `_require_current_leader` (3459) sobre o contexto `ctx-0c0155ef5a94`, cujo líder `orca:ctx_ad48e72ddf4c` é terminal; a recusa vem como `LEADER-AUTHORITY-UNPROVEN` antes de chegar a 6074-6075. DQ-0012 A veda o takeover ad hoc do ANTIGO, então o código `ACTIVITY-STATE-DIVERGENCE` não é observável lá. O handoff FASE-002:24 e o critério :30 dizem só "é recusada", o que continua verdadeiro.
- Correção: DELIVERY-MAP:31 e PLAN-CONTEXT:62(5): "aceite tardio recusado (`LEADER-AUTHORITY-UNPROVEN` sem takeover; a recusa estrutural `ACTIVITY-STATE-DIVERGENCE` é comprovada pelo p4 da FASE-001 e por `accept_activity`, agent_orchestration.py:964-965)". Não é decisão nova: é o efeito direto de DQ-0012 A sobre o critério de aceite.

### Finding 3 — menor — DQ-0012 não está refletida nos artefatos que ela lista
- Evidência: DQ-0012 (DECISION-FRONTIER:151) lista `artifacts: PLAN-CONTEXT.md, handoffs/FASE-002-SPECIFY-HANDOFF.md`. PLAN-CONTEXT:64 ainda diz "ver DQ proposta no resultado do autor" e mantém a condicional "takeover do contexto de origem só se algum verbo `@_gauntlet_authorized` for necessário lá", que deixa o takeover ad hoc em aberto; DQ-0012 A diz "sem takeover ad hoc nem sucessor vazio" (a opção C do autor — item SGD lateral — é o caminho se um verbo autorizado se tornar necessário). O handoff FASE-002 não menciona DQ-0012.
- Correção: PLAN-CONTEXT:64 → "Por DQ-0012 (A): sem takeover do contexto de origem; se um verbo `@_gauntlet_authorized` se mostrar necessário lá, abrir item SGD lateral (opção C), não takeover ad hoc". Handoff FASE-002 WHY/Restrições: citar DQ-0012.

### Finding 4 — menor — forma da operação omite chaves obrigatórias do contrato
- Evidência: PLAN-CONTEXT:23 descreve a operação sem `expected_before`, `error` e sem o valor de `idempotency_key`; `_operation` exige o conjunto completo (agent_orchestration.py:641-642) e `expected_before` é `_json` (657). O texto manda "reusar a forma" do takeover (4292-4301), que traz todas, então o executor tende a acertar.
- Correção: acrescentar em :23 `expected_before={"context_id", "activity_id", "activity_state", "resource_id", "resource_state"}`, `idempotency_key=operation_id`, `error=None`.

### Finding 5 — menor — glossário × objetivo da FASE-001 sobre "órfã com líder vivo"
- Evidência: CONTEXT:7 define "atividade órfã" com "cujo líder de origem também terminou"; ROADMAP:7 (F5) aplica "cujo líder terminou **ou** que ainda tem líder vivo" às duas variantes, inclusive à órfã. Pelo glossário, "órfã com líder vivo" é contradição em termos. DQ-0008 é geral ("um verbo só, autoridade derivada da observação do líder"), então o alcance está correto; só a palavra está apertada.
- Correção: CONTEXT:7, nota na definição: "para a autoridade do fence vale DQ-0008 em qualquer variante; 'órfã' descreve o caso X7, não limita o verbo". Ou ROADMAP:7 "uma atividade `DISPATCHED` sem resultado ou de sessão retida … cujo líder terminou ou …".

### Finding 6 — menor — "no-op" do salto 2 dentro de `mutate` ainda gera evento
- Evidência: PLAN-CONTEXT:25 diz "recurso já `CLOSED` → no-op e `FENCE-REUSED`" dentro da guarda do salto 2; PLAN-CONTEXT:26 exige "sem segundo evento". `transact` sempre carimba `current.revision + 1` e escreve (store.py:1624-1631) quando `mutate` retorna, mesmo sem mudança.
- Correção: decidir `FENCE-REUSED` a partir do snapshot lido antes do `transact` (Finding 1, item ii); dentro de `mutate`, recurso já `CLOSED` → `raise store.StoreError(STATE_DIVERGENCE, …)` mapeado para `FENCE-REUSED` (ou `FENCE-CAS-CONFLICT` se `input_sha256` divergir), nunca `return document` sem mudança.

### Nits (não findings)
- PLAN-CONTEXT:23 cita "nullable, 1001-1002" — é 1002-1003; "carimba `current.revision + 1` (store.py:1619-1623)" — a checagem é 1619-1623, o carimbo é 1624.
- FASE-002 handoff:22 nomeia estados do Store (`RESULT_RECORDED`, `CLOSE_PENDING`) e ids de dispatch. É evidência observada, não implementação; mesmo critério aceito na revisão anterior (handoff-001:45). Não bloqueia.
- PLAN-CONTEXT:62 passo (4) edita `state.json` do ANTIGO à mão (`audit_verdict=GO`). É a prática documentada no rodapé do ROADMAP e em session-protocol.md:213 e o ANTIGO não tem checkpoint que sele `state_sha256`; registro só para o executor.

## 4. Separação WHAT/WHY × HOW — OK
Handoff FASE-001: sem stack, classes, verbos de CLI ou API interna; o nit da revisão anterior (`tests/run_validators.py`) foi trocado por "suíte de validadores do repositório" (handoff-001:41). Handoff FASE-002: sem HOW; cita só ids observados e códigos de veredicto genéricos ("aplicado", "reuso"). O HOW inteiro vive em PLAN-CONTEXT.

## 5. Coerência entre artefatos — OK
- FASE-001: `ADRs: ADR-0001`, `BLs: none`, DU-001, `platform-devops` idênticos em ROADMAP:11-12,15, handoff-001:7-8,11-12, PLAN-CONTEXT:5-8, DELIVERY-MAP:11-13.
- FASE-002: `ADRs: ADR-0001`, `BLs: BL-0001`, DU-002, `platform-devops` idênticos em ROADMAP:23-24,27, handoff-002:7-8,11-12, PLAN-CONTEXT:54-57, DELIVERY-MAP:25-27. BL-0001 `phase: FASE-002`, `open`; FASE-002 `planned` → sem "ready ligada a BL open" (audit_decisions.py:740-741); fase existe porque o auditor recusa BL órfão (564-566).
- `execution-order: FASE-001, FASE-002`; `depends-on: FASE-001` em FASE-002; só a primeira fase `ready-for-specify`.
- `context-refs`: ROADMAP:10 e handoff-001:6 = 9 termos = 9 linhas do glossário (CONTEXT:7-15); FASE-002 = 7 termos, subconjunto.
- Testes negativos exigidos por DQ-0006: handoff-001:26-29 e PLAN-CONTEXT:36 n1-n4; inconclusivo/readiness/stale/replay/aceite tardio em handoff-001:30-32, DELIVERY-MAP:17, PLAN-CONTEXT:36 (n3c, n5-n8, p3-p5).
- DELIVERY-MAP:8 boundary exclui `attestation.py`/`agent_runtime.py`, coerente com PLAN-CONTEXT:19 ("sem tocar na função") e :38.
- ADR "Relações": `supersedes` aponta o ADR de origem já agora (assimetria declarada pelo autor em "Notas ao líder" 3; aceitável); `backlog` lista SGD-37/38/39.

## 6. Constituição — OK
Cada PASS/NOT-APPLICABLE conferido contra evidência real:
- `constitution_sha256` `54d5522b…7569` = manifest = `WORK-ITEM.json.immutable.constitution.sha256` = `state.json.constitution.sha256`; Constituição 2.1.0 com 11 cláusulas, mesmas 11 do check.
- "Evidência antes de afirmação": input manifest do autor tem 27 arquivos (justificativa diz 27); citações reconferidas por mim no HEAD.
- "Work item isolado": `WORK-ITEM.json` `type=fix`, `base_commit 39380f7…`, `branch cadugevaerd/fix-leader`; Store: `ctx-146fb68d0d6e`, líder `orca:ctx_bf15a89923e5`.
- "Feature/fix plan-only": `git status --porcelain` só `?? .grill/work-items/fix-fence-…/`.
- "Sequência obrigatória": `state.json` 11 passos `pending`, `current_step=specify`, `active_phase=FASE-001`.
- "Fail-closed": nenhuma edição manual de Store; rota é work item novo + FASE-002 pelo verbo.
- "Rastreabilidade": `migrated-from` em DQ-0001..0011; SGD-37/38/39 `open` no backlog `SGD` (conferido).
- "Tier de modelo": `interview-author-001.observation.json` `fable/xhigh` requested == effective, `resolved_model_id=fable`; revisor `fable/high` idem.
- NOT-APPLICABLE em verify/review, bump e release: justificativas honestas; PLAN-CONTEXT:40 registra os oito pontos e a Release pelo `publish.yml`.
- "Governance": Constituição intocada (hash igual no manifest).

## DQs propostas
Nenhuma. Findings 1-6 são precisão de HOW ou de critério de aceite derivada de decisões já seladas (DQ-0006, DQ-0008, DQ-0009, DQ-0012); nenhuma exige decisão humana nova.

## Veredicto
`APPROVED`. Seis findings menores; nenhum contradiz decisão humana, nenhum abre brecha fail-open, nenhum é premissa falsa contra o HEAD. Findings 1 e 2 valem corrigir em PLAN-CONTEXT/DELIVERY-MAP antes do `specify`, porque o executor tropeça neles em p3/p5 e no aceite do DU-002.

VERDICT: APPROVED

# Revisão independente — plan-reviewer-002 (REVISOR, fable/high, etapa plan, work item fix-fence-autorizado-atividade-f831232ae30e4087adbaa988bc0f7b24)

- payload lido por inteiro: sha256 `d1866afe4638f9b5e7700ae2567e2dd708304c38a9b5beea8b5808afdb118530` (confere)
- input manifest `plan-reviewer-002.input.json`: 27/27 sha256 conferidos, zero divergência
- worktree `/home/carlosaraujo/orca/workspaces/grill-with-docs/fix-leader`, HEAD `0eadd3a` (commit da correção de `plan-author-002`). `git diff --stat 39380f7 HEAD -- plugin tests` vazio: os cinco módulos e os dois validadores são idênticos ao `39380f7`/`4cad807`/`ad42a65`. Toda citação file:line abaixo foi reconferida neste HEAD.
- `git diff 4cad807 HEAD -- specs/034-*`: 5 arquivos, +40/−33; cada hunk mapeado a um dos Findings 1–6 ou aos nits do payload de `plan-author-002` (tabela na seção 0). Fora de `specs/034-*` o diff toca só `.grill/`.
- nada escrito em `.grill/`, `.specify/reports/` nem no repositório; relatório só neste scratchpad
- convenções: `ws` = `plugin/skills/grill-with-docs/scripts/grill_workspace.py`; `ao` = `grill_core/agent_orchestration.py`; `ar` = `grill_core/agent_runtime.py`; `att` = `grill_core/attestation.py`; `st` = `grill_core/store.py`; `gr` = `grill_core/gauntlet_runs.py`; `T` = `tests/validate_agent_orchestration_contract.py`; `F` = `specs/034-fence-autorizado-atividade`

## Resumo

Nenhum finding bloqueante. As seis correções de `plan-reviewer-001` estão aplicadas onde o autor declara, nada fora delas mudou, e a revisão completa (não só o delta) não encontra premissa falsa que altere decisão, brecha fail-open sobre o descarte, corrida com segundo efeito, nem contradição com a spec ou com DQ-0001..DQ-0014. Sobrevivem cinco findings menores: um teste (n9) planejado sobre o mecanismo errado, duas premissas falsas na prosa de R7 (cleanup não move recurso de sessão; `preserved_resources` do checkpoint só projeta workers), uma declaração de "exceção a FR-013" que a análise cruzada vai ler como inconsistência spec/plano, e a retomada do salto 2 escrevendo sem reobservar o solicitante. Nenhum exige DQ.

## 0. Delta 4cad807 → HEAD — cada hunk tem dono

| Arquivo | Hunk | Finding/nit do payload |
|---|---|---|
| contract:8 | hash recalculado × hash da operação; `intended_after.requester.ref` | F1 |
| contract:10 | flag omitida → `FENCE-AUTHORIZATION-INVALID`; não `required` | F2 |
| contract:13 | "só para o mesmo solicitante" | F1 |
| contract:14 | exceção do `FENCE-CAS-CONFLICT` pós-salto 1 | F4 |
| contract:17 | mesmo solicitante; outro → `FENCE-ACTIVITY-STATE` | F1 |
| contract:20 | cleanup não reconhece; `attempt-2-as-new-activity`; contexto do attempt 2 | F3, F6 |
| data-model:23, :38, :58, :66, :84-87 | `SESSION-CLOSE-UNPROVEN`; `successor`; DQ-0013; flag omitida; transições | F3, F6, nit, F2, F1/F4 |
| plan:9, :39, :45, :79 | reexecução por forma; HEAD e contagem de manifests; DQ-0013/0014; `n1..n9` | F6, F6, F3, F5 |
| quickstart:3 | casos novos | F1–F5 |
| research:3, R1, R2, R5, R7, R8, R9, R10, R11, DQs | conforme relatório do autor | F1–F6, nits |

Nenhum hunk sem finding correspondente. Decisão de saltos intacta (`CLOSED`, salto derivado do estado). DQ-0001..DQ-0014: nenhuma reaberta, ampliada ou estreitada; DQ-0013 (A) e DQ-0014 (A) refletidas em R5/R8/contrato/data-model/plan.

## 1. Fidelidade — OK

FR-001..FR-015 conferidas uma a uma contra R1..R12, data-model e contrato (mesma tabela de `plan-reviewer-001` §1, reconferida; sem divergência nova). Pontos que a rodada de correção tocou:

- FR-003: flag omitida, arquivo ausente, ilegível (`ws:5349-5350`), malformado (`5351-5352`), não-objeto (`5357-5358`), symlink (`5354-5355`), caminho absoluto (`5343-5344`), `EVIDENCE-MISSING` (`ws:356-357`) e toda falha de `_validate_human_authorization` (`att:773-781`) são `CliFailure`/`AttestationError` e colapsam num código só, como `ws:5174-5183`. Literal.
- FR-012 + US4 AS1 ("mesmos insumos → reuso"): o solicitante é insumo (entra no hash, R6), então outro `--session-ref` não é "mesmos insumos"; `FENCE-ACTIVITY-STATE` para ele é coerente com a spec e com `TAKEOVER-REUSED` (`ws:4151`).
- FR-013: ver Finding 3 — o plano declara uma exceção que, lida pelo que o código faz, não é exceção.
- FR-005 na retomada: ver Finding 4.

## 2. Findings obrigatórios — resolvidos (reconferido)

- interview-reviewer-001 (NOVO) 1, 4, 6: R2 (ordem; `operation_id` sem `expected`; `_fence_recorded` antes de estado/hash), data-model (chaves de `ao:641` completas, `expected_before` `_json` `ao:657`), R7 (salto 2 levanta, nunca `return document`; `st:1616-1631`). Corretos.
- specify-reviewer-002 F2: R3/R4(c)/R4(a); n3c, n5, n5b, n5c. Coberto.
- Origem F1 (`"orca:" + owner_dispatch`: `ws:3700`, `ar:1268`, `ws:1593`), F2 (guarda só por estado no salto 2; `st:1619-1624`), F4 (`_session_readiness` `ws:1612-1656` como em `4181`; `to_session_ref` no hash como `4261`; `requester` em `evidence`/`intended_after`). Mantidos.
- plan-reviewer-001 Findings 1–6: aplicados (seção 0). A nota de `plan-author-002` sobre o Finding 1 está certa: pela ordem de R2 o par `(FAILED, CLOSE_PENDING)` com solicitante divergente cai em `FENCE-ACTIVITY-STATE` no passo 3, não em `FENCE-INPUTS-STALE`.

## 3. Correção técnica contra o HEAD — OK, com premissas falsas de prosa (Finding 2)

Conferido literalmente:

- Arestas `ao:48-49`; `validate_transition` uma vez por `transact` (`st:1627`; `ao:1541`, `1557`) → dois saltos obrigatórios na forma órfã; `CLOSED` terminal.
- Atividade `FAILED` com `result_ref` preenchido válida (`ao:762-763`, `770-771`, `780-781`, `784-785`); first-bound `1537-1539` (`diagnostic_ref` de `None`); identidade `1532-1536`.
- Recurso: receipt único `1054-1059`; `last_observation` em receipts `1066-1068`; `operation_id` nullable `1002-1003` e existente em `operations` `1442` (mesmo `transact`); `result_acceptance_ref` nulo aceito; identidade `1542-1546`; receipts antigos preservados `1550-1553`.
- Operação: `ao:641-658`; `fence == leader.fence` `1378` (takeover não altera o fence do contexto superseded, `ws:4319-4320`); idempotência `1379-1381`; `CONFIRMED` imutável `1525`; `continuity_ref` só exige `continuity-switch` para sucessores `1385-1387`.
- `_reviewer_authors` (`ao:399-421`, `1447-1460`): revisor com recurso exige autores `ACCEPTED` — um revisor só ganha recurso em `VERIFIED`, então nenhum revisor com sessão referencia atividade `DISPATCHED|RESULT_RECORDED`. Estrutural; o fence não invalida o documento por esse caminho.
- Provas: `_takeover_observation` `ws:1565-1609` (LEADER-ADAPTER-UNSUPPORTED em `1579` → `indeterminate` via `ar:1284-1285`); `observe_predecessor_termination` `ar:1249-1292` (regex `1268`, terminal `1286-1291`); mapeamento `ws:4159-4166`. R4(b) é duplamente provado: `status ∈ {dispatched, running}` sem revogação pela observação de takeover, depois `LeaderBoundary.observe()` estrito (`ar:812-823`) por `_require_current_leader` (`ws:1658-1671`). `source_sha256` do `observe()` é estável entre leituras (`ar:835-836`), então a comparação com `context.leader.observation_sha256` funciona.
- Autorização: `ws:5340-5359`; `att:773-781`; `SHA256_RE` `att:130`; `FREE_REF_RE` `134`; `_ID` `ao:40` e `WORK_ID_RE` `st:142` sem `:`.
- Hash: `st:375-376`; sem `snapshot.revision` (motivo `ws:4253-4259`).
- Quiescência `ws:3654-3672`; workers `PREPARED` `3675-3681`; takeover `4126-4351` (REUSED `4148-4156`, readiness `4181`, campanha `4184-4187`, guarda `4309-4310`, CAS `4340-4343`); `gauntlet-activity` `5952`, accept `6074-6075`, `--diagnostic` `6078-6080`, `record` `6097-6106`, `attempt=1` `5990`, correlação `6052-6055`; `accept_activity` `ao:964-965`; prepare-switch `ws:3934-3939` (ACCEPTED), `3944-3953` (FAILED só de DISPATCHED), `3974-3976`.
- Cleanup `ws:4354-4478`: sessão é **relatório sem mutação** (`4450-4455`); `closed` `4452`; veredicto `4474-4478`; único chamador a tabela `7214` (mais o `__name__` em `3447`). `_cleanup_checkpoint_projection` `1869-1881` → `gr:487-506` projeta **só workers de run**. Confirma R8/DQ-0014 A: efeito de relatório, nada bloqueia.
- Parser `7131-7136`; `7081`; `7134`; dispatch `7212`; `canonical` `237`; `_gauntlet_authorized` `3393`, `3441-3444`, `3447-3450`.
- Seams: `takeover_show` `T:62-77`; `offline_leader` `tests/orchestration_fixture.py:89-105` (`boundary` deriva o dispatch do próprio `session_ref`, `55-58` — serve qualquer `orca:ctx-…`); `command` `108-119` não injeta `--session-ref` no verbo novo; `guarded_run` `T:2281-2292`; `assert_refused_and_unwritten` `2297-2307`; seed `1245-1266`; `2348-2353`; `2508-2511`; CAS `2620-2637`; REUSED `2640-2645`; `_session_readiness` mockada `263`; store contract `31-34`, `288-290`.
- Concorrência (dois solicitantes A e B): A grava o salto 1; B cai na guarda de revisão do salto 1 (`4309-4310` como padrão) → `StoreError` → releitura → `_fence_recorded(B)` vê requester A ≠ B → recusa (`FENCE-CAS-CONFLICT` no `except`, com o payload de Finding 4), sem escrever. Um efeito, nunca dois. Ver Finding 3 sobre a rotulagem.

## 4. Um salto × dois saltos (R7) — correto

`REGISTERED → CLOSED` não é aresta (`ao:49`); `PRESERVED` tem saídas; FR-008 e a entidade "Recibo de fechamento" dizem "fechada". `CLOSED` em dois `transact` na órfã e um na retida é a leitura coerente com a spec sem tocar `_RESOURCE_EDGES`. O intermediário `(FAILED, CLOSE_PENDING)` + operação `CONFIRMED` não viola invariante de Store (`ao:1424-1460`) nem de quiescência (`ws:3664`, `3668`). Testável por p5. A única imprecisão é de rationale (Finding 2b).

## 5. Testes — planejados, determinísticos, sem rede; um caso sobre o mecanismo errado (Finding 1)

Exigidos e presentes: sem autorização (n1, inclusive flag omitida), outro alvo (n2, n2d), líder vivo que não é o chamador (n3), especialista vivo (n4), indeterminado do especialista (n5, n5c), do líder (n5b), do sucessor (n3c), hash stale (n7), replay (p3, p3b), aceite tardio (p4), positivos das duas formas (p1, p2, p2b), retomada (p5). Pares fora das duas formas (n8, n8b). Todos pelos seams existentes. Aresta nova travada em `tests/validate_orchestrator_store_contract.py`.

## 6. Particionabilidade — OK

Nó A (`ao` + `validate_orchestrator_store_contract.py`), nó B (`ws` + `T`), nó C (`session-protocol.md`, `SKILL.md`, 4 manifests, `validate_distribution.py`, `README.md`, `CHANGELOG.md`): disjuntos. B depende de A em execução (p2 usa a aresta), resolvido pela ordem de fases. Lembrete para `tasks`: nenhum token com `/` fora de path de grant nas linhas de tarefa (`CLAUDE.md`, Project Learnings).

## 7. Constituição e distribuição — OK

Constituição 2.1.0, sha256 `54d5522b…7569` = manifest; 11 cláusulas (`constitution.md:34-66`) = 11 linhas da tabela, cada uma com evidência real. Bump: os oito pontos estão em `6.0.30` nas linhas citadas (`plugin/.claude-plugin/plugin.json:3`, `plugin/.codex-plugin/plugin.json:3`, `.claude-plugin/marketplace.json:11`, `.agents/plugins/marketplace.json:7`, `tests/validate_distribution.py:8`, `SKILL.md:6`, `session-protocol.md:1`, `README.md:3`); `## 6.0.30` em `CHANGELOG.md:3`; `validate_distribution.py:41-43` exige `## 6.0.31`. Nono arquivo corretamente declarado. Único desvio editorial: plan:39 cita HEAD `ad42a65`; o HEAD corrente é `0eadd3a`, código idêntico.

## Findings

### Finding 1 — menor — n9 espera `FENCE-CAS-CONFLICT` de uma escrita interposta entre prévia e apply, mas a guarda de revisão não cobre essa janela
- **Evidência**: R11 n9: "`store.transact` interposto entre prévia e apply (escrita real no Store ou `read_snapshot` stale, como o caso `TAKEOVER-CAS-CONFLICT` em 2620-2637) → `FENCE-CAS-CONFLICT`". No padrão do takeover que R7 reusa, o `snapshot` guardado em `mutate` é o lido **na própria invocação do apply** (`ws:4140`, guarda em `4309-4310`), não o da prévia. Uma escrita real entre prévia e apply que não toque atividade/recurso passa: o apply relê, o hash confere e devolve `FENCE-APPLIED`. Se a escrita tocar o par, a recusa vem por `FENCE-ACTIVITY-STATE` (passo 3) ou `FENCE-INPUTS-STALE` (passo 7), nunca por CAS. É por isso que `T:2620-2637` simula com `read_snapshot` devolvendo revisão stale, não com escrita real. Um executor que implemente a variante "escrita real" reprova a asserção.
- **Correção**: em R11 n9 e quickstart:3, fixar a única forma válida: mock de `read_snapshot` com `revision - 1` (seam de `T:2630-2633`) → `FENCE-CAS-CONFLICT` na guarda do salto 1, Store igual. Registrar que escrita interposta entre prévia e apply é coberta por n7 (hash) e n8/n8b (estado). Sem decisão nova.

### Finding 2 — menor — duas premissas falsas na prosa de R7 (não alteram a decisão)
- **(a) Evidência**: R7 salto 2 e contract:14 dizem que o recurso pode ser "movido por outro verbo entre os saltos — `CLOSE_PENDING → PRESERVED|UNKNOWN` pelo cleanup do mesmo líder". `gauntlet_cleanup_command` **não muta recurso de sessão**: só reporta (`ws:4450-4455`, "No session-close transport is wired here"); não há `transact` sobre `resources` no comando. Os únicos escritores de estado de recurso de sessão em `ws` são `gauntlet-activity` (`REGISTERED → CLOSE_PENDING` `6104`, `CLOSE_PENDING → CLOSED` `6147`, ambos exigem atividade `DISPATCHED|RESULT_RECORDED`, `6074-6075`) e `gauntlet-prepare-switch` (`→ CLOSED` `3934` só de `RESULT_RECORDED` com release; `→ PRESERVED` `3950` só de `DISPATCHED`+`REGISTERED`). Nenhum verbo escreve `UNKNOWN` em recurso. Depois do salto 1 a atividade é `FAILED`, então nenhum verbo do core alcança o recurso. A divergência real que produz o payload de Finding 4 é a corrida de dois solicitantes no salto 1 (seção 3) ou crash/edição externa.
- **(b) Evidência**: R7 Rationale (e PLAN-CONTEXT:27, de onde veio) diz que um recurso `PRESERVED` "aparece em `preserved_resources` do checkpoint (`_cleanup_checkpoint_projection` 1869; usos 1942 e 3798)". `_cleanup_checkpoint_projection` (`ws:1869-1881`) chama `gauntlet_runs.cleanup_projection` (`gr:487-506`), que só percorre `runs[*].workers` — recursos de sessão nunca entram. Um recurso `PRESERVED` aparece só em `retained` do takeover/resume (`ws:4064`, `4281-4282`), que é o argumento correto e suficiente.
- **Correção**: R7 salto 2: "nenhum verbo do core move um recurso `CLOSE_PENDING` cuja atividade está `FAILED`; a divergência vem de corrida no salto 1 (outro solicitante), crash ou edição externa". R7 Rationale: trocar `preserved_resources` por `retained` (`4281-4282`). contract:14: "movido por outro verbo" → "divergente por corrida, crash ou edição externa". p5 (variante `PRESERVED` semeada por `transact`) continua válido como teste da guarda.

### Finding 3 — menor — o plano declara "a única exceção a FR-013"; pelo código não há exceção, e a declaração vira inconsistência spec/plano em `analyze`
- **Evidência**: R7, contract:14 e data-model:84 dizem que `FENCE-CAS-CONFLICT` pós-salto 1 é "a única recusa do verbo com estado alterado, a única em que FR-013 não vale". A recusa em si não escreve nada: o `StoreError` sai de dentro de `mutate` antes de `stamp`/`_write_document` (`st:1616-1631`), e a releitura é read-only. O estado difere do pré-apply só pelo salto 1, que **aplicou com sucesso**. Nos dois cenários alcançáveis (Finding 2a): o perdedor da corrida não escreveu byte algum (FR-013 vale para ele); no próprio processo, o salto 1 é um efeito aplicado sob prova completa, e o payload o reporta. FR-013 é MUST na spec; um plano que afirma "FR-013 não vale aqui" será lido por `speckit-analyze` como contradição.
- **Correção**: reescrever nos três lugares: "toda recusa escreve zero bytes; `FENCE-CAS-CONFLICT` pós-salto 1 reporta em `activity_state`/`resource_state`/`operation_id` o efeito já aplicado pelo salto 1 (próprio ou do solicitante vencedor), e a saída é a retomada". Precisão adicional para o executor: no `except` do salto 1, `_fence_recorded` com solicitante divergente mapeia para `FENCE-CAS-CONFLICT` (R7 só nomeia "forma de replay → REUSED; outra → CAS-CONFLICT", e R2 define esse caso como "segue para o passo 3", que não existe no `except`).

### Finding 4 — menor — a retomada executa o salto 2 sem reobservar o solicitante
- **Evidência**: R2 passo 2: com operação presente, mesmo solicitante (comparação de string com `intended_after.requester.ref`) e recurso `CLOSE_PENDING`, "apply com hash igual executa só o salto 2", sem passar pelos passos 5-6. `--session-ref` é alegação do chamador; nenhum verbo prova identidade do chamador, mas todos os que escrevem observam a sessão alegada (`@_gauntlet_authorized` `3458-3459`; takeover `4181`; o próprio fence nos passos 5-6). FR-005: "o sucessor pode pedir se a própria sessão for observada e provada". Não é fail-open sobre o descarte (operação `CONFIRMED` e imutável, atividade já `FAILED`; o efeito é só `CLOSE_PENDING → CLOSED`, o desfecho autorizado), e o precedente `TAKEOVER-REUSED` compara string do mesmo jeito — mas é read-only. `plan-reviewer-001` Finding 1 apontou exatamente "escrita sem prova do chamador"; a correção (mesmo solicitante) restringe quem pode, não prova quem é.
- **Correção**: na retomada, antes do salto 2, reexecutar só a prova do solicitante conforme `intended_after.requester.role`: `successor` → `_session_readiness(root, context["runtime"], args.session_ref, work_id=...)`; `current-leader` → `_require_current_leader(root, work_id, context, args.session_ref)`. Uma observação, mesmos seams (offline_leader serve). Replay (`FENCE-REUSED`) permanece read-only e sem observação. Não reabre DQ-P3 (continua "mesmo solicitante"); é FR-005 aplicada ao único caminho que escreve sem prova.

### Finding 5 — nit — `owner_dispatch` nulo não "cai naturalmente em `not_observable`"
- **Evidência**: R3: "`owner_dispatch` nulo (permitido em 1020-1025) cai naturalmente em `not_observable`". `"orca:" + None` levanta `TypeError` antes de chegar a `observe_predecessor_termination` (que só devolve `not_observable` para não-string, `ar:1268`). `_released_activity_sessions` guarda com `isinstance(dispatch, str)` (`ws:3697`).
- **Correção**: R3: compor `session_ref = "orca:" + od if isinstance(od, str) else None`, que o adapter então classifica como `not_observable` → `FENCE-NOT-OBSERVABLE` (n6).

### Nits (não findings)
- research R4/R6: `_session_readiness` termina em `ws:1656` (retorno em `1655-1656`), não `1655`; `_require_current_leader` `1658-1671`. Desvio de uma linha.
- plan:39 e research:3 citam HEAD `ad42a65`; o HEAD é `0eadd3a` (código idêntico).
- PLAN-CONTEXT (fora do grant, do líder) ficou atrás do plano em quatro pontos: `:13` recusa por estado da atividade (plano recusa por par); `:21` hash sem `resource_state`; `:23` `successor: "attempt-2-in-successor-context"`; `:25` "recurso já `CLOSED` → no-op e `FENCE-REUSED`" (superado por interview-reviewer-001 Finding 6). O plano "detalha e corrige" o HOW por contrato do payload; registro só para o líder decidir se sincroniza.
- Na forma retida o sucessor precisa de `ORCA_TERMINAL_HANDLE` para as duas observações e a readiness; sem ele tudo é `*-UNPROVEN`. Já coberto por n5c; só lembrete para quickstart:6 (FASE-002 live).

## DQs propostas

Nenhuma. Findings 1–5 são precisão de HOW ou de prosa derivada de decisões já seladas (DQ-0006, DQ-0008, DQ-0009, DQ-0013, DQ-0014); nenhum exige decisão humana nova.

## Veredicto

`APPROVED`. Cinco findings menores; nenhum contradiz decisão humana, nenhum abre brecha fail-open sobre o descarte, nenhum é premissa falsa que mude a decisão. Findings 1 e 3 valem corrigir antes de `tasks`: o primeiro porque vira uma tarefa de teste que reprova como escrita; o segundo porque é texto que `analyze` vai acusar como contradição de FR-013.

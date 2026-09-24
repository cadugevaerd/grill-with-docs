VERDICT: APPROVED

# Revisão independente — plan-reviewer-003 (REVISOR, fable/high, etapa plan, work item fix-fence-autorizado-atividade-f831232ae30e4087adbaa988bc0f7b24)

- payload lido por inteiro: sha256 `f16d404e144be6df5538adde5e69067caf129e4c88643c8ebfa89898a449d529` (confere)
- input manifest `plan-reviewer-003.input.json`: 30/30 sha256 conferidos, zero divergência
- worktree `/home/carlosaraujo/orca/workspaces/grill-with-docs/fix-leader`, HEAD `38d6917` (commit da correção de `plan-author-003`). `git diff --stat 39380f7 HEAD -- plugin tests` vazio: os cinco módulos e os dois validadores são idênticos ao `39380f7`/`4cad807`/`0eadd3a`/`2fc26a0`. Toda citação file:line abaixo foi reconferida neste HEAD.
- `git diff 2fc26a0 38d6917`: fora de `.grill/` toca só os cinco arquivos do grant (`+21/−21`); cada hunk mapeado a um finding ou nit do payload de `plan-author-003` (seção 0). Nada mais mudou.
- nada escrito em `.grill/`, `.specify/reports/` nem no repositório; relatório só neste scratchpad
- convenções: `ws` = `plugin/skills/grill-with-docs/scripts/grill_workspace.py`; `ao` = `grill_core/agent_orchestration.py`; `ar` = `grill_core/agent_runtime.py`; `att` = `grill_core/attestation.py`; `st` = `grill_core/store.py`; `gr` = `grill_core/gauntlet_runs.py`; `T` = `tests/validate_agent_orchestration_contract.py`; `F` = `specs/034-fence-autorizado-atividade`

## Resumo

Nenhum finding bloqueante. As cinco correções de `plan-reviewer-002` e os nits estão aplicados onde o autor declara, nenhuma abriu lacuna, e a revisão completa (não só o delta) não encontra premissa falsa que altere decisão, brecha fail-open sobre o descarte, corrida com segundo efeito, nem contradição com a spec ou com DQ-0001..DQ-0014. Sobrevive **um finding menor** que as duas revisões anteriores deixaram passar: os casos n5/n5b descrevem um shape de observação (`status=dispatched`, `capabilityRevokedAt=null`, liveness `unverifiable`) que, pelo mapeamento do próprio plano (R3/R4b, idêntico ao takeover), produz `*-ACTIVE`, não `*-UNPROVEN`. É contradição interna do plano, resolvida por trocar o shape do teste; não é DQ. Mais três nits de prosa.

## 0. Delta 2fc26a0 → 38d6917 — cada hunk tem dono

| Arquivo | Hunk | Finding/nit de plan-reviewer-002 |
|---|---|---|
| contract:13 | retomada reexecuta a prova do solicitante | F4 |
| contract:14 | "escreve zero bytes"; corrida/crash/edição externa; nenhum verbo move `CLOSE_PENDING` de atividade `FAILED`; `except` → `FENCE-CAS-CONFLICT` | F2a, F3 |
| contract:17 | prova reexecutada (sucessor → readiness; líder → reobservação); replay read-only | F4 |
| data-model:48 | `1658-1670` → `1658-1671` | nit |
| data-model:84 | "toda recusa escreve zero bytes" | F3 |
| data-model:86 | retomada com prova por `role` | F4 |
| plan:25 | retomada só prova do solicitante; replay não observa | F4 |
| plan:39 | HEAD `2fc26a0`; 32 arquivos (conferido: 32) | nit |
| plan:79 | `n1..n10` | F4 |
| quickstart:3 | `read_snapshot` stale (`revision - 1`); retomada sem prova | F1, F4 |
| research:3 | HEAD e revisores | nit |
| research R2 | prova por `role` na retomada; `except` → `FENCE-CAS-CONFLICT` | F4, F3 |
| research R3 | `"orca:" + od if isinstance(od, str) else None` | F5 |
| research R4(b) | `1658-1671` | nit |
| research R7 salto 1 | `except` com solicitante divergente → `FENCE-CAS-CONFLICT` | F3 |
| research R7 salto 2 | nenhum verbo move o recurso; zero bytes; retomada | F2a, F3 |
| research R7 Rationale e Alternatives | `retained` (4064, 4281-4282); `_cleanup_checkpoint_projection` projeta só workers | F2b |
| research R11 | n9 pelo seam de revisão; n10; p5 com prova reexecutada | F1, F4 |

Nenhum hunk sem finding correspondente. Decisão de saltos intacta (`CLOSED`, salto derivado do estado). DQ-0001..DQ-0014: nenhuma reaberta, ampliada ou estreitada. O nit de `_session_readiness` foi corretamente **não** aplicado: a função vai de `ws:1612` a `1655` (`return` em 1654-1655; 1656-1657 vazias; `_require_current_leader` em 1658-1671). O revisor anterior estava uma linha fora; o autor, certo.

## 1. Fidelidade — OK

FR-001..FR-015 conferidas uma a uma contra R1..R12, data-model e contrato (mesma tabela de `plan-reviewer-001` §1, reconferida). Pontos tocados pela rodada 003:

- FR-005 na retomada: a prova do solicitante volta a existir no único caminho que escrevia sem ela (R2 passo 2; `_session_readiness` `ws:1612-1655` ou `_require_current_leader` `ws:1658-1671`). Fechado.
- FR-013: sem afirmação de exceção em lugar nenhum (`grep -n 'FR-013' F/*` só em plan:44 e R2/R7 no sentido correto). `FENCE-CAS-CONFLICT` sai de dentro de `mutate` antes de `stamp`/`_write_document` (`st:1616-1631`); a recusa não escreve.
- Edge case spec:80 ("veredicto indeterminado: sem status terminal, sem revogação e sem liveness conclusiva → prova não comprovada") × AS4 spec:58 ("dispatch ainda ativo → recusa própria"): o plano resolve o overlap pela definição de R3 ("vivo" = `status ∈ {dispatched, running}` com `capabilityRevokedAt == null`) e pelo mapeamento do takeover. É a leitura correta e fail-closed (as duas recusam sem escrever), mas os casos n5/n5b contradizem essa própria resolução — Finding 1.

## 2. Findings obrigatórios — resolvidos (reconferido)

- interview-reviewer-001 (NOVO) 1, 4, 6: R2 (ordem; `operation_id` determinístico sem `expected`; `_fence_recorded` antes de estado/hash), data-model (chaves obrigatórias de `ao:641` completas; `expected_before` `_json` `ao:657`), R7 (salto 2 levanta `StoreError`, nunca `return document`; `st:1624-1631`). Corretos.
- specify-reviewer-002 F2: R3/R4(c)/R4(a); n3c, n5c cobrem o indeterminado do sucessor e do especialista sem handle; n5/n5b precisam do shape certo (Finding 1).
- Origem F1 (`"orca:" + owner_dispatch`: `ws:3700`, `ar:1267-1268`, `ws:1593`; guarda `isinstance` `ws:3697`), F2 (guarda só por estado no salto 2; `st:1619-1624`), F4 (`_session_readiness` como em `ws:4181`; `to_session_ref` no hash como `ws:4261`; `requester` em `evidence`/`intended_after`). Mantidos.
- plan-reviewer-001 Findings 1–6 e plan-reviewer-002 Findings 1–5: aplicados (seção 0 e relatório de `plan-author-003`).

## 3. Correção técnica contra o HEAD — OK

Conferido literalmente (desvio zero nas linhas tocadas):

- Arestas `ao:48-49`; `validate_transition` uma vez por `transact` (`st:1627`; `ao:1541`, `1557`) → dois saltos obrigatórios na forma órfã; `CLOSED` terminal.
- Atividade `FAILED` com `result_ref` preenchido válida (`ao:762-763`, `770-771`, `780-781`, `784-785`); first-bound `1537-1539`; identidade `1532`.
- Recurso: receipt único `1054-1058`; `last_observation` em receipts `1066-1068`; `operation_id` nullable `1002-1003` e existente em `operations` `1442`; `owner_dispatch` nulo permitido `1020-1025`; identidade `1542-1546`; receipts antigos preservados `1550-1553`.
- Operação: `ao:639-658`; `fence == leader.fence` `1378` (o takeover não altera `leader.fence` do contexto superseded, `ws:4319-4320`); idempotência `1379-1381`; `CONFIRMED` imutável `1525`; `continuity_ref` só exige `continuity-switch` `1385-1387`.
- **Escritores reais de estado de recurso de sessão em `ws`** (grep): `3934` (`CLOSED`, prepare-switch), `3950` (`PRESERVED`, prepare-switch), `6104` (`CLOSE_PENDING`, activity record), `6147` (`close_session_resource` → `CLOSED`). Nenhum escreve `UNKNOWN`. Escritores de `FAILED`: `3952` (prepare-switch, só de `DISPATCHED`) e `6083` (`--diagnostic`, só de `DISPATCHED`, `6078-6080`). Confirma R7 (Finding 2a) e R9.
- `gauntlet_cleanup_command` `ws:4354-4478`: sessão é relatório sem `transact` (`4450-4455`); `closed` `4452`; veredicto `4474-4478`; chamadores: só a tabela `7214` e o `__name__` em `3447`. `_cleanup_checkpoint_projection` `1869-1881` → `gr:487-506` só workers. Confirma R8/DQ-0014 A.
- Provas: `_takeover_observation` `ws:1565-1609` (`LEADER-ADAPTER-UNSUPPORTED` em `1579` → `indeterminate` via `ar:1284-1285`; `status` só quando `dispatch.id == dispatch_id` e string, `1600-1602`); `observe_predecessor_termination` `ar:1249-1292` (regex `1267-1268`, `not_observable` para não-string sem chamar `read`; terminal `1286-1291`); mapeamento `ws:4159-4166`. R4(b) duplamente provado: `status ∈ {dispatched, running}` pela observação de takeover, depois `LeaderBoundary.observe()` estrito (`ar:812-823`) por `_require_current_leader`; `source_sha256` estável (`ar:835-836`).
- `_validate_orchestration_transition` (`st:1102-1125`) só exige contexto observado quando `_ORCHESTRATION_AUTHORITY` está setado pelo `@_gauntlet_authorized`; o fence, não decorado como o takeover, transaciona sem essa prova — coerente com R1 e com o precedente.
- Autorização: `ws:5340-5359`; arquivo ausente → `EVIDENCE-MISSING` (`ws:356-357`) re-levantado e absorvido no código único; `att:773-781`; `SHA256_RE` `att:130`; `FREE_REF_RE` `134`; `_ID` `ao:40` e `WORK_ID_RE` `st:142` sem `:`.
- Hash: `st:375-376`; sem `snapshot.revision` (motivo `ws:4253-4259`).
- Quiescência `ws:3654-3672` (`3664`, `3668`); workers `PREPARED` `3675-3681`; `_released_activity_sessions` só `RESULT_RECORDED` autor (`3690-3697`) e `_transferred_activity_sessions` só `DISPATCHED`+`REGISTERED` (`3717-3720`) → a atividade cercada não entra em nenhum; takeover `4126-4351` (REUSED `4148-4156`, readiness `4181`, campanha `4184-4187`, guarda `4309-4310`, CAS `4340-4343`, `retained` `4281-4282`); `gauntlet-activity` `5952`, accept `6074-6075`, `--diagnostic` `6078-6080`, `record` `6097-6106`, `attempt=1` `5990`, correlação `6052-6055`; `accept_activity` `ao:964-965`; prepare-switch `3934-3939`, `3944-3953`, `3974-3976`.
- Parser `7131-7136`; `7081`; `7134`; dispatch `7212`; `canonical` `237`; `_gauntlet_authorized` `3393`, `3441-3444`, `3447-3450`.
- Seams: `takeover_show` `T:62-77`; `offline_leader` `tests/orchestration_fixture.py:89-105` (`boundary` `55-58` deriva o dispatch do próprio `session_ref`); `command` `108-119` não injeta `--session-ref` no verbo novo; `guarded_run` `T:2281-2292`; `assert_refused_and_unwritten` `2297-2307`; seed `1245-1266`; `2348-2353`; `2508-2511`; CAS por `read_snapshot` stale `2626-2637`; REUSED `2640-2645`; `_session_readiness` mockada `263`; store contract `31-34`, `288-290` (`ORCHESTRATOR_INVALID` é o código de `_invalid` em `st:1125`, o mesmo que embrulha `validate_transition`).
- Concorrência (A e B): A grava o salto 1; B cai na guarda de revisão → `StoreError` → releitura → `_fence_recorded(B)` vê requester A ≠ B → `FENCE-CAS-CONFLICT` no `except`, sem escrever. Um efeito, nunca dois. Salto 2 concorrente: `CLOSE_PENDING → CLOSED` só uma vez; o segundo levanta e é `FENCE-REUSED`.

## 4. Um salto × dois saltos (R7) — correto

`REGISTERED → CLOSED` não é aresta (`ao:49`); `PRESERVED` tem saídas; FR-008 diz "fechada". `CLOSED` em dois `transact` na órfã e um na retida é a leitura coerente sem tocar `_RESOURCE_EDGES`. O intermediário `(FAILED, CLOSE_PENDING)` + operação `CONFIRMED` não viola invariante de Store (`ao:1424-1460`) nem de quiescência (`ws:3664`, `3668`), não bloqueia takeover nem switch, e é reportado pelo cleanup do sucessor apenas como `RESOURCE-RETAINED-ELSEWHERE` (`ws:4439-4443`) — ver nit (c). Testável por p5 e n10.

## 5. Testes — planejados, determinísticos, sem rede; um par de casos com o shape errado (Finding 1)

Exigidos e presentes: sem autorização (n1, inclusive flag omitida), outro alvo (n2, n2d), líder vivo que não é o chamador (n3), especialista vivo (n4), indeterminado do especialista (n5 — shape a corrigir; n5c correto), do líder (n5b — shape a corrigir), do sucessor (n3c), hash stale (n7), replay (p3, p3b), aceite tardio (p4), positivos das duas formas (p1, p2, p2b), retomada (p5, n10). Pares fora das duas formas (n8, n8b). CAS só pelo seam de revisão (n9). Todos pelos seams existentes. Aresta nova travada em `tests/validate_orchestrator_store_contract.py`.

## 6. Particionabilidade — OK

Nó A (`ao` + `validate_orchestrator_store_contract.py`), nó B (`ws` + `T`), nó C (`session-protocol.md`, `SKILL.md`, 4 manifests, `validate_distribution.py`, `README.md`, `CHANGELOG.md`): disjuntos. B depende de A em execução (p2 usa a aresta), resolvido pela ordem de fases. Lembrete para `tasks`: nenhum token com `/` fora de path de grant nas linhas de tarefa (`CLAUDE.md`, Project Learnings).

## 7. Constituição e distribuição — OK

Constituição 2.1.0, sha256 `54d5522b…7569` = manifest; 10 princípios (`constitution.md:34-63`) + Governance (`64-66`) = 11 linhas da tabela, cada uma com evidência real. Bump: os oito pontos estão em `6.0.30` nas linhas citadas (`plugin/.claude-plugin/plugin.json:3`, `plugin/.codex-plugin/plugin.json:3`, `.claude-plugin/marketplace.json:11`, `.agents/plugins/marketplace.json:7`, `tests/validate_distribution.py:8`, `SKILL.md:6`, `session-protocol.md:1`, `README.md:3`); `## 6.0.30` em `CHANGELOG.md:3`; `validate_distribution.py:41-43` exige `## 6.0.31`. Nono arquivo corretamente declarado. `session-protocol.md:87` diz literalmente "o recurso `CLOSE_PENDING` é então fechado com receipt correlacionado", como R7 cita.

## Findings

### Finding 1 — menor — n5 e n5b esperam `*-UNPROVEN` de um shape que o mapeamento do plano classifica como `*-ACTIVE`
- **Evidência**: R11 n5: "especialista `status=dispatched`, `capabilityRevokedAt=null`, liveness `unverifiable` → `FENCE-SPECIALIST-UNPROVEN`"; n5b: "líder idem → `FENCE-LEADER-UNPROVEN`". R3 define "especialista vivo" exatamente como `status ∈ {dispatched, running}` com `capabilityRevokedAt == null`, e fixa "mapeamento idêntico ao takeover (4159-4166): não terminal com `status ∈ {dispatched, running}` → `*-ACTIVE`; qualquer outro não terminal → `*-UNPROVEN`". R4(b) idem para o líder. Pelo código: `observe_predecessor_termination` devolve `indeterminate` para esse shape (`ar:1286-1291`), `_takeover_observation` extrai `status="dispatched"` (`ws:1602-1604`) e o CLI mapeia `status in {"dispatched", "running"}` → `*-ACTIVE` (`ws:4163-4165`). O takeover, precedente que R3 invoca, testa o inconclusivo de liveness com `status=None` (`T:2516`: `takeover_show(old_dispatch, status=None, liveness={"verdict": "unverifiable"})` → `TAKEOVER-EVIDENCE-UNPROVEN`) e o vivo com `status="dispatched"` (`T:2505` → `TAKEOVER-LEADER-ACTIVE`). Um executor que implemente R3 e escreva n5/n5b como estão reprova os dois casos; um que force `UNPROVEN` para esse shape diverge do takeover e faz "vivo" depender de liveness, contra R3. `*-UNPROVEN` só é alcançável com `status` ausente, não string, de dispatch não correlacionado, resposta ilegível ou sem handle — os shapes de `T:2508-2516`.
- **Por que é menor**: as duas saídas recusam sem escrever (FR-004, FR-013 intactos); é contradição interna entre a definição (R3/R4b) e a lista de testes (R11), sem decisão nova.
- **Correção**: em R11 (e quickstart:3), n5 → "especialista com `status` ausente e liveness `unverifiable` (`T:2516`), ou dispatch não correlacionado (`T:2514`), ou resposta ilegível (`T:2512`) → `FENCE-SPECIALIST-UNPROVEN`"; n5b idem para o líder → `FENCE-LEADER-UNPROVEN`. Acrescentar em R3 uma frase que feche o overlap entre spec:80 e spec:58: "`status ∈ {dispatched, running}` sem revogação é **ativo** (`*-ACTIVE`) qualquer que seja a liveness; 'sem status terminal' do edge case da spec cobre `status` ausente, ilegível ou não correlacionado, que é o indeterminado". Opcional: um n5d com `status=dispatched` + `unverifiable` → `FENCE-SPECIALIST-ACTIVE`, travando a distinção.

### Nits (não findings)
- (a) R7 Rationale e Alternatives dizem que o recurso `PRESERVED` "aparece em `retained` do resume e do takeover (4064, 4281-4282)". `retained` é a variável local; a chave pública do payload é `preserved_resources` (`ws:4070`, `4121`, `4348`; `T:2615` assere `projected["preserved_resources"]`). Dizer "`retained` (chave `preserved_resources` do payload)". A correção do Finding 2b de plan-reviewer-002 estava certa quanto ao checkpoint, mas apagou a única menção ao nome que o executor vai ver.
- (b) plan:35 cita "11 cláusulas, `constitution.md:34-62`"; os princípios vão de 34 a 63 e Governance está em 64-66. Faixa correta: `34-66`.
- (c) R7/R2 não dizem o que sobra quando o solicitante do salto 1 morre entre os saltos e é **substituído** por outra sessão: por DQ-P3 (A), o novo solicitante não retoma (`FENCE-ACTIVITY-STATE`), o takeover não é bloqueado (`CLOSE_PENDING` não é `UNKNOWN`), e o recurso fica `(FAILED, CLOSE_PENDING)` sem verbo que o feche; o cleanup do sucessor o lista como `RESOURCE-RETAINED-ELSEWHERE` com veredicto `PRESERVED`, exit 2 (`ws:4439-4443`, `4475`), efeito de relatório como o de DQ-0014. Uma frase em R7 ("Janela de crash") basta; não é decisão nova, é consequência já aceita em DQ-P3 (A).
- (d) PLAN-CONTEXT (fora do grant, do líder) continua atrás do plano nos quatro pontos já listados por plan-reviewer-002 (`:13`, `:21`, `:23`, `:25`) e carrega o mesmo shape de n5 (`:36`). Registro para o líder.

## DQs propostas

Nenhuma. O Finding 1 é precisão de teste derivada de definição já fixada em R3/R4 e do precedente do takeover; os nits são prosa. Nenhuma DQ-0001..DQ-0014 reaberta, ampliada ou estreitada.

## Veredicto

`APPROVED`. Um finding menor e três nits; nenhum contradiz decisão humana, nenhum abre brecha fail-open sobre o descarte, nenhum é premissa falsa que mude a decisão de saltos. O Finding 1 é insumo obrigatório do autor de `tasks`: os casos n5/n5b devem nascer com o shape de `T:2512-2516`, não com `status=dispatched`.

VERDICT: APPROVED

# Revisão independente — plan-reviewer-001 (REVISOR, fable/high, etapa plan, work item fix-fence-autorizado-atividade-f831232ae30e4087adbaa988bc0f7b24)

- payload lido por inteiro: sha256 `d15e774de4fd6167ec59e8dcbda8b4d433655dd386e868090824c2ad68ec2c32` (confere)
- input manifest: 24/24 sha256 conferidos, zero divergência
- worktree `/home/carlosaraujo/orca/workspaces/grill-with-docs/fix-leader`, HEAD `4cad807` (commit do plano + DQ-0013). Os cinco módulos e os dois validadores do manifest têm os mesmos sha256 que o plano cita para `9dd8df6`/`39380f7`; `git diff --stat 9dd8df6 HEAD` toca só `specs/034-*` e `.grill/`. Toda citação file:line abaixo foi reconferida neste HEAD.
- nada escrito em `.grill/`, `.specify/reports/` nem no repositório; relatório só neste scratchpad
- convenções: `ws` = `plugin/skills/grill-with-docs/scripts/grill_workspace.py`; `ao` = `grill_core/agent_orchestration.py`; `ar` = `grill_core/agent_runtime.py`; `att` = `grill_core/attestation.py`; `st` = `grill_core/store.py`; `T` = `tests/validate_agent_orchestration_contract.py`; `F` = `specs/034-fence-autorizado-atividade`; `W` = bundle do work item

## Resumo

Nenhum finding bloqueante. Nenhuma premissa falsa contra o HEAD, nenhuma brecha fail-open, nenhum caminho em que a mesma operação produza dois efeitos. Os Findings obrigatórios (interview-reviewer-001 NOVO 1, 4, 6; specify-reviewer-002 F2; origem F1/F2/F4) estão resolvidos onde o autor diz. A decisão dois saltos → `CLOSED` é correta pelas arestas reais e coerente com FR-008. Sobrevivem seis findings menores (precisão de contrato, um efeito colateral de relatório no `gauntlet-cleanup` não declarado, e lacunas pequenas na lista de testes) e duas DQs propostas, nenhuma exigindo reabrir DQ-0001..DQ-0013.

## 1. Fidelidade à spec e às DQs — OK

FR-001..FR-015 → plano, uma a uma:

| FR | Onde | Evidência |
|---|---|---|
| FR-001 verbo único, prévia por padrão | research R1; contract:4-8 | forma do takeover `ws:4130-4134` |
| FR-002 prévia não escreve; conteúdo do hash | R6; data-model "Hash da prévia" | cobre atividade, contexto, solicitante (`to_session_ref`), veredictos + referências das duas observações, autorização |
| FR-003 autorização exata, mesmo código para ausência e alvo divergente | R5 | `att:773-781`; `_ID` `ao:40` e `WORK_ID_RE` `st:142` não admitem `:` — separador não ambíguo (ver Finding 2 sobre `required=True`) |
| FR-004 prova do ambiente | R3 | `_takeover_observation` `ws:1565-1609` sobre `observe_predecessor_termination` `ar:1249-1292`; `unverifiable` sozinha → `indeterminate` (`ar:1286-1291`) |
| FR-005 autoridade pelo líder | R4 (a)/(b)/(c) | `_session_readiness` `ws:1612-1655`; `_require_current_leader` `ws:1658-1670` |
| FR-006 duas formas | R2 passo 3 | `(DISPATCHED, REGISTERED)` por `ao:887-911`+`933-939`; `(RESULT_RECORDED, CLOSE_PENDING)` por `ws:6097-6106` |
| FR-007 terminal não aceito | R7, R8, data-model | `FAILED` exige `diagnostic_ref` `ao:784-785`; `accept_activity` recusa fora de `RESULT_RECORDED` `ao:964-965`; CLI `ws:6074-6075` |
| FR-008 sessão fechada com recibo | R7 | `CLOSED` terminal `ao:49`; receipt `orca:<owner_dispatch>:fence` com `last_observation` em receipts (`ao:1067-1069`) |
| FR-009 não conta como ativo; herança inalterada | R8 | `ws:3664`, `3668`, `3675-3681` intocados |
| FR-010 rastreabilidade | data-model "Operação" | `subject_ids`, `evidence` com digests, `requester`, `authorization` verbatim |
| FR-011 attempt 2 novo | R10 | `ao:720-721` chave única; `attempt` write-once `ao:1532`; CLI grava 1 `ws:5990` |
| FR-012 reuso / stale | R2 passo 2, R6 | replay antes do hash, como `ws:4148-4156` |
| FR-013 recusa sem efeito | R2 ordem fixa; todas as recusas antes do `transact` | ver Finding 4 sobre a janela entre saltos |
| FR-014 bump 8 pontos | R12 | os oito estão em `6.0.30` exatamente nas linhas citadas; `tests/validate_distribution.py:41-43` exige `## 6.0.31` no `CHANGELOG.md` (nono arquivo, corretamente declarado) |
| FR-015 nada em Constituição/WORKFLOW/registries | plan "Constraints" | `attestation.py` e `agent_runtime.py` fora do diff |

DQ-0006/0007/0008/0009/0010/0012/0013: nenhuma reaberta, ampliada ou estreitada. DQ-0013 (A) está refletida em R5 e data-model ("só forma"); R5/data-model ainda chamam isso de "DQ-P1" porque foram escritos antes da decisão — anotação editorial do líder, não finding.

## 2. Findings obrigatórios — resolvidos

- **interview-reviewer-001 (NOVO) Finding 1** (ordem; `operation_id` determinístico; replay/retomada antes de estado/hash): R2 passos 1-7 e `_fence_recorded`; contract:13,17. O `operation_id` sem `expected` é reencontrável; replay só reusa `CONFIRMED` imutável (`ao:1525`). Correto.
- **Finding 4** (forma completa da operação): data-model tabela — `expected_before` (`_json`, `ao:657`), `idempotency_key = operation_id`, `error = None`, `observation_ref = result_ref`; `CONFIRMED` exige `observation_ref` e `result_sha256` (`ao:651-652`). Conjunto obrigatório de `ao:641` coberto integralmente.
- **Finding 6** (nenhum no-op em `mutate`): R7 salto 2 — recurso já `CLOSED` → `raise StoreError(STATE_DIVERGENCE)`; CLI relê e classifica. Correto: `transact` carimba `current.revision + 1` e escreve sempre que `mutate` retorna (`st:1624-1631`).
- **Findings 2, 3, 5**: registrados em R13 como fora desta fase. Correto (tocam FASE-002/glossário).
- **specify-reviewer-002 F2** (indeterminado do especialista, do líder e do sucessor): R3 (`*-UNPROVEN`), R4(c) `FENCE-LEADER-UNPROVEN`, R4(a) readiness recusa quando não conclui; testes n3c, n5, n5b, n5c. Coberto.
- **Origem F1**: `"orca:" + owner_dispatch` — `ws:3700` compõe assim, `ar:1268` só aceita `orca:ctx[-_]…`, `ws:1593` faz `removeprefix`. Confere. **F2**: salto 2 guarda só por estado; causa correta (`st:1619-1624`). Confere. **F4**: `_session_readiness` como em `ws:4181`; `to_session_ref` no hash como `ws:4261`; `requester` em `evidence` e `intended_after`. Confere.

## 3. Correção técnica contra o HEAD — OK

Conferido literalmente (desvio ≤ 1 linha onde há):
- Arestas `ao:48-49`: `DISPATCHED→FAILED` válida; `RESULT_RECORDED→FAILED` ausente; `REGISTERED→CLOSE_PENDING→CLOSED` e `CLOSE_PENDING→CLOSED` válidas; `REGISTERED→CLOSED` inválida → dois saltos são obrigatórios na forma órfã. `_validate_orchestration_transition` roda uma vez por `transact` (`st:1627`).
- Digests: `_ref` exige `sha256` em `_HEX` (`ao:81-83`, `201-206`); `observe_predecessor_termination` produz `hashlib.sha256(raw).hexdigest()` (`ar:69-70`, `1277`) e `store.jcs_sha256` idem (`st:375-376`) — receipt do fence, `input_sha256` e `result_sha256` validam.
- `FAILED` com `result_ref` preenchido: `ao:763` só exige tripla coerente; `771` exclui `FAILED`; `779` exclui `FAILED`. Válido.
- Recurso `CLOSED` com `result_acceptance_ref=None`: nullable `ao:1002-1003`; nenhum cruzamento em `validate_block` `ao:1424-1460`. Válido (mas ver Finding 3).
- Operação: `fence == contexts[ctx].leader.fence` (`ao:1378`) — o takeover não altera `leader.fence` do contexto superseded, então a operação continua válida depois. `resource.operation_id` precisa existir em `operations` (`ao:1443`): gravado no mesmo `transact`. `idempotency` `ao:1379-1381`.
- Quiescência `ws:3654-3672`: `FAILED` fora de `3664`; só `UNKNOWN` conta em `3668`; `CLOSE_PENDING` entre saltos não bloqueia takeover nem `prepare-switch`.
- Takeover `ws:4126-4350`: REUSED `4148-4156`, mapeamento `4159-4166`, quiescência `4170-4174`, readiness `4181`, checkpoint só com campanha `4184-4187`, guarda de revisão `4309-4310`, CAS `4340-4343`. Fence entre prévia e apply do takeover → `TAKEOVER-CAS-CONFLICT`, como R8 diz.
- `gauntlet-activity` `@_gauntlet_authorized` `ws:5952`; `accept` fora de `DISPATCHED|RESULT_RECORDED` → `ACTIVITY-STATE-DIVERGENCE` `6074-6075`; `--diagnostic` só de `DISPATCHED` `6078-6080`; `record` grava `CLOSE_PENDING` `6099-6104`.
- Precedente run-abandon `ws:5174-5183`; `load_checkpoint_attestation` `5340-5359`; arquivo ausente → `safe_read_regular_fd` levanta `CliFailure(EVIDENCE-MISSING)` (`ws:356-357`), absorvido no código único. `abandon_run` grava bundle verbatim (`gauntlet_runs.py:3155`).
- `_reviewer_authors` `ao:399-421`: um revisor com sessão exige autor `ACCEPTED`; como nenhum revisor é despachado antes do aceite do autor, nenhum revisor referencia uma atividade `DISPATCHED|RESULT_RECORDED` — o fence não invalida o documento por esse caminho. Estrutural.
- Seams de teste: `takeover_show` `T:62-77`; `offline_leader` `tests/orchestration_fixture.py:89-105` (serve qualquer `orca:ctx…`); `command` `113-116` não injeta `--session-ref` no verbo novo (correto: testes passam explícito); `guarded_run` `T:2281-2292` (closure local; a "extensão" é um novo closure no teste novo); `assert_refused_and_unwritten` `T:2297-2307`; seed `T:1245-1266`; `_session_readiness` mockada `T:263`; `ORCA_TERMINAL_HANDLE` ausente `T:2508-2511`.
- Concorrência: salto 1 guardado por `document["revision"]`; o perdedor cai em `StoreError` → releitura → `FENCE-REUSED` (replay) ou `FENCE-CAS-CONFLICT`. Salto 2 concorrente: `CLOSE_PENDING→CLOSED` só uma vez; o segundo levanta e é classificado como `FENCE-REUSED`. Um efeito, nunca dois. Confere.

## 4. Um salto × dois saltos (R7) — correto

`PRESERVED` não é terminal (`ao:49` tem saídas), aparece em `retained` do takeover (`ws:4281-4282`) e em `preserved_resources`; FR-008 e a entidade "Recibo de fechamento de sessão" dizem "fechada". `CLOSED` é a única leitura coerente com a spec sem alterar `_RESOURCE_EDGES` (vedado pelo PLAN-CONTEXT). Estado intermediário `(FAILED, CLOSE_PENDING)` + operação `CONFIRMED` não viola nenhum invariante do Store nem da quiescência. O custo (retomada p5) está corretamente classificado como detalhe de implementação, já que a spec aprovada removeu o cenário de aplicação interrompida (specify-reviewer-001 F1). Ver Finding 4 para a única imprecisão residual.

## 5. Testes — planejados, determinísticos, sem rede (com lacunas menores, Finding 5)

Negativos exigidos: sem autorização (n1), outro alvo (n2), líder vivo que não é o chamador (n3), especialista vivo (n4), indeterminado do especialista (n5), do líder (n5b), do sucessor (n3c), hash stale (n7), replay (p3), aceite tardio (p4). Positivos: p1 (órfã + takeover), p2 (retida, líder vivo), p2b (retida, sucessor), p5 (retomada). Todos via seams existentes; `takeover_show` produz as formas `completed`/revogado/`unverifiable`. Aresta nova travada em `tests/validate_orchestrator_store_contract.py` (fixtures `31-34`, `invalid` `288-290` conferidos).

## 6. Particionabilidade — OK

Nó A (`ao` + `validate_orchestrator_store_contract.py`), nó B (`ws` + `T`), nó C (docs + 9 arquivos de versão): disjuntos; B depende de A só em tempo de execução (p2 usa a aresta), o que a ordem de fases resolve. Lembrete para o autor de `tasks` (Project Learnings do `CLAUDE.md`): as linhas de tarefa não podem carregar tokens com `/` que não sejam paths de grant.

## 7. Constituição e distribuição — OK

Constituição 2.1.0, sha256 `54d5522b…7569` igual ao manifest; 10 princípios + Governance = 11 linhas da tabela, todas com evidência real. "Tier de modelo": tier derivado do nó do DAG, coerente com a cláusula. Bump: 8 pontos + `CHANGELOG.md` (`## 6.0.30` na linha 3 hoje). Único desvio editorial: o plano cita HEAD `9dd8df6`; o HEAD corrente é `4cad807` com código idêntico.

## Findings

### Finding 1 — menor — replay e retomada não verificam o solicitante; contract:8 afirma o contrário para a retomada
- **Evidência**: R2 passo 2 devolve `FENCE-REUSED` (exit 0) para qualquer `--session-ref` e sem reler a autorização, e na retomada publica `expected_sha256 = operation["input_sha256"]` para qualquer solicitante; contract:8 diz "um `--apply` de outro `--session-ref` também é stale, porque o solicitante integra o hash" — verdadeiro só quando o hash é recalculado (passo 7), falso na retomada, onde o hash vem da operação. O precedente `TAKEOVER-REUSED` exige `context.leader.session_ref == args.session_ref` (`ws:4148`). Efeito: replay não escreve (inofensivo); retomada escreve só o fechamento de um recurso cuja operação já está `CONFIRMED` e autorizada — não é fail-open sobre o descarte, mas é escrita sem prova do chamador.
- **Correção**: em `_fence_recorded`, exigir `args.session_ref == operation["intended_after"]["requester"]["ref"]`; divergente → segue para o passo 3 (replay cai em `FENCE-ACTIVITY-STATE`; retomada em `FENCE-INPUTS-STALE`). Ajustar contract:8 e :17 para dizer isso. Custo: uma comparação e um caso de teste (p3 com `--session-ref` diferente).

### Finding 2 — menor — `--authorization required=True` faz "ausência" sair como erro de argparse, não como `FENCE-AUTHORIZATION-INVALID`
- **Evidência**: R1/R5 fixam `required=True` (precedente `ws:7081`); FR-003 diz "Ausência e alvo divergente MUST recusar com o mesmo código"; US3 AS1 "sem autorização → prévia e aplicação recusam com o mesmo código". Argparse devolve exit 2 sem payload (`CLAUDE.md`, Project Learnings), e o contrato só cobre arquivo ausente/inválido.
- **Correção**: `--authorization` sem `required`, default `None` → `FENCE-AUTHORIZATION-INVALID` antes de `load_checkpoint_attestation`. Uma linha; satisfaz FR-003 literalmente e n1 ganha o caso "flag omitida". Se o executor preferir manter o precedente, contract:10 deve dizer explicitamente que a flag omitida é erro de uso, não recusa do contrato.

### Finding 3 — menor — `gauntlet-cleanup` passa a reportar o recurso cercado como `SESSION-CLOSE-UNPROVEN` no contexto vivo; efeito não declarado
- **Evidência**: `ws:4452` define `closed = state in {CLOSED, REMOVED} and bool(result_acceptance_ref)`; o recurso cercado fica `CLOSED` com `result_acceptance_ref=None` (data-model, "Recurso de sessão"). Na forma retida com líder vivo (US2 AS1, p2) o contexto continua corrente, então todo `gauntlet-cleanup --context-id` desse contexto lista o recurso com `verdict: UNKNOWN`, `code: SESSION-CLOSE-UNPROVEN` (`4453-4455`) e o veredicto geral vira `UNKNOWN`, exit 2 (`4474-4478`), para sempre. R7/R8 só tratam o cleanup na forma órfã ("filtra pelo contexto corrente, 4273-4282"), que não se aplica aqui. Nenhum outro verbo consome o veredicto do cleanup (único chamador é a tabela de dispatch, `ws:7214`; o checkpoint projeta só workers, `ws:1869-1881`), e a quiescência olha o estado do recurso, não o relatório — logo não bloqueia takeover, switch, phase-turn ou ship. É inconsistência de auditoria: o Store diz "fechado com receipt do fence" e o cleanup diz "fechamento não comprovado".
- **Correção**: (i) declarar em R8, contract:19-20 e p2 que, na forma com líder vivo, o cleanup reporta esse recurso como `SESSION-CLOSE-UNPROVEN` sem bloquear nada, com asserção no teste; ou (ii) tratar como DQ-P2 abaixo, se o líder quiser que o cleanup reconheça o fence.

### Finding 4 — menor — R7 não diz o que o CLI devolve quando o salto 2 falha por divergência real depois do salto 1 ter sido gravado
- **Evidência**: R7 cobre "recurso já `CLOSED` → `FENCE-REUSED`" e "qualquer outra divergência → `StoreError`" → `FENCE-CAS-CONFLICT`. Nesse segundo caso o salto 1 já está commitado (atividade `FAILED`, operação `CONFIRMED`) e a resposta é uma recusa com estado alterado — a única situação do plano em que FR-013 ("bit a bit igual") não vale. Na prática só é alcançável se outro verbo mover o recurso `CLOSE_PENDING → PRESERVED|UNKNOWN` entre os saltos (cleanup do mesmo líder, forma órfã com líder vivo), ou por crash; a spec removeu o cenário interrompido de propósito.
- **Correção**: em R7 e contract:14, fixar que `FENCE-CAS-CONFLICT` emitido depois do salto 1 carrega `activity_state`, `resource_state` e `operation_id` no payload, e que a retomada (R2) é o caminho de saída; e que p5 cobre também esse payload. Sem decisão nova: é precisão de contrato.

### Finding 5 — menor — lacunas na lista de testes
- **Evidência**: (a) n2 lista `scope` de outro `context_id`, `activity_id` e um `run_id`, mas não outro `work_id` (FR-003 vincula ao work item também). (b) n8 varia só o estado da atividade; R2 passo 3 recusa por **par** — faltam `(RESULT_RECORDED, REGISTERED)`, `(DISPATCHED, CLOSE_PENDING)` e `(RESULT_RECORDED, CLOSED)`, que são exatamente as formas que o CLI *não* produz e que o fence promete recusar. (c) Não há caso de `FENCE-CAS-CONFLICT` por escrita entre prévia e apply (o takeover tem um em `T:2620-2637`); o edge case de concorrência da spec fica sem teste direto. (d) p3 não fixa o comportamento com `--session-ref` diferente (Finding 1).
- **Correção**: acrescentar n2d (`work_id` divergente), n8b (três pares), n9 (`transact` interposto entre prévia e apply → `FENCE-CAS-CONFLICT`, Store igual ao estado interposto) e p3b. Todos com os seams já citados.

### Finding 6 — menor — imprecisões de prosa
- **Evidência**: R9 "nenhum outro verbo escreve `FAILED`" — `gauntlet-prepare-switch` escreve `FAILED` de `DISPATCHED` em `ws:3952-3953`; o que é verdadeiro é "nenhum outro caminho percorre `RESULT_RECORDED → FAILED`". `intended_after.successor = "attempt-2-in-successor-context"` (data-model, R10) é inexato na forma com líder vivo, onde o attempt 2 nasce no **mesmo** contexto. plan:39 cita HEAD `9dd8df6` (hoje `4cad807`, código idêntico).
- **Correção**: reescrever a frase de R9; `successor: "attempt-2-as-new-activity"` (ou registrar o `context_id` corrente no momento do apply, sem prometer sucessor); atualizar o HEAD citado.

### Nits (não findings)
- R5/data-model ainda dizem "DQ-P1" onde já vale DQ-0013 (A); anotação do líder.
- Na forma órfã com líder vivo, `gauntlet-activity --phase accept --diagnostic` (`ws:6078-6083`) já leva `DISPATCHED → FAILED` sem autorização humana; o fence é redundante ali (não errado: exige mais e fecha o recurso).

## DQs propostas

### DQ-P2 — O `gauntlet-cleanup` deve reconhecer o receipt do fence como fechamento comprovado?
- **Pergunta atômica**: em `ws:4452`, um recurso `CLOSED` cujo `operation_id` aponta uma operação `activity-fence` `CONFIRMED` conta como fechado (`REUSED`), ou continua `SESSION-CLOSE-UNPROVEN` por não ter `result_acceptance_ref`?
- **Opções**: (A) sem mudança nesta versão; declarar o efeito (Finding 3, correção i) e deixar o cleanup honesto sobre "nenhum aceite" — menor diff, sem tocar um verbo fora do escopo do DU-001. (B) `closed = state in {CLOSED, REMOVED} and (result_acceptance_ref or fence_confirmed(resource))` — o cleanup do contexto vivo volta a `CLEANED`; custo: toca `gauntlet_cleanup_command`, exige teste próprio e amplia o scope-in do DU-001 ("verbo de fence").
- **Recomendação**: A nesta versão. O cleanup de sessão é relatório sem transporte (`ws:4449-4450`) e nada o consome; B é aditiva e pode entrar em item SGD com o gatilho "líder vivo precisa de `CLEANED` no contexto após um fence".

### DQ-P3 (só se o líder discordar da correção do Finding 1) — Retomada do salto 2 exige o mesmo solicitante?
- **Pergunta atômica**: a retomada de `(FAILED, CLOSE_PENDING)` só é admitida ao `requester.ref` gravado na operação, ou a qualquer sessão que apresente o `input_sha256` publicado pela prévia?
- **Opções**: (A) mesmo solicitante (Finding 1) — um sucessor novo não completa o salto 2, mas o takeover não é bloqueado por `CLOSE_PENDING`, e o recurso fica visível em `preserved_resources`/`retained` do takeover como hoje. (B) qualquer sessão, reexecutando ao menos a autorização (passo 4) antes do salto 2 — completa o fechamento após crash do solicitante, ao custo de uma leitura local.
- **Recomendação**: A (mesma forma do `TAKEOVER-REUSED`); B se o líder quiser que crash do sucessor entre saltos seja recuperável por outra sessão.

## Veredicto

`APPROVED`. Seis findings menores; nenhum contradiz decisão humana, nenhum abre brecha fail-open, nenhum é premissa falsa contra o HEAD `4cad807`. Findings 1 e 3 valem corrigir no plano antes de `tasks`, porque são contrato público (prosa do `contracts/activity-fence.md`) que o executor vai travar por teste.

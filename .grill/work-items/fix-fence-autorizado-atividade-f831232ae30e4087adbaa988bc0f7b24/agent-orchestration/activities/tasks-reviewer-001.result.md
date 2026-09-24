VERDICT: APPROVED

# Revisão independente — tasks-reviewer-001 (REVISOR, fable/high, etapa tasks, work item fix-fence-autorizado-atividade-f831232ae30e4087adbaa988bc0f7b24)

- payload lido por inteiro: sha256 `af14e6d3e1c5c53b76e81b648e0778f0116afb5b090684f7722a85da4f2e713d` (confere)
- input manifest `tasks-reviewer-001.input.json`: 25/25 sha256 conferidos, zero divergência
- worktree `/home/carlosaraujo/orca/workspaces/grill-with-docs/fix-leader`, HEAD `4e34d8a` (commit do `tasks.md`); `git diff --stat 39380f7 HEAD -- plugin tests` vazio, então toda citação file:line de código vale neste HEAD. O `tasks.md` (linha 17) cita HEAD `a5ee1da`; o delta `a5ee1da..4e34d8a` é só o próprio `tasks.md`.
- `tasks.md` sha256 `c298d8219d9e650e3e5c43650ae7a42f72a674407b6fbf6021b65cc7116424c6` (igual ao manifest e ao relatório do autor); `tasks_semantic_sha256` do parser do core devolve o mesmo valor.
- nada escrito em `.grill/`, `.specify/reports/` nem no repositório; relatório só neste scratchpad
- convenções: `ws` = `plugin/skills/grill-with-docs/scripts/grill_workspace.py`; `ao` = `grill_core/agent_orchestration.py`; `st` = `grill_core/store.py`; `att` = `grill_core/attestation.py`; `ar` = `grill_core/agent_runtime.py`; `T` = `tests/validate_agent_orchestration_contract.py`; `F` = `specs/034-fence-autorizado-atividade`; `tasks` = `F/tasks.md`

## Resumo

Nenhum finding bloqueante. O `tasks.md` cumpre o contrato `task-files/v1` pelo parser do próprio core (executado em memória, sem escrever DAG): 8 tarefas, 6 despacháveis, 2 read-only, 0 deferred, 3 nós (`p01-a`, `p02-a`, `p02-b`), Phase 3 sem nó, `PARTITION-DEGRADED` só por causa das read-only. Cobertura FR-001..FR-015, US1..US4, SC-001..SC-005 e a matriz R11 inteira estão atribuídas. Os insumos obrigatórios (plan-reviewer-003 Finding 1 e nits (a)/(c); checklist-reviewer-001 Findings 1–5; CHK036–038) entraram nas tarefas certas. Todas as citações file:line que conferi batem no HEAD. Sobrevivem dois findings menores de executabilidade (closures do teste de takeover que não são reutilizáveis; forma do caso n7) e três nits de prosa. Nenhuma DQ nova.

## 1. Contrato `task-files/v1` — OK (parser do core)

`grill_core.partition.parse_task_files` + `partition_task_files(text, feature="034-fence-autorizado-atividade", root=".")`:

| Item | Resultado |
|---|---|
| marcador `<!-- grill-task-files:v1 -->` | tasks:1, exatamente uma ocorrência |
| `Files:` JSON de uma linha logo após cada tarefa | T001..T008, todas parseadas (tasks:32, 44, 47, 50, 53, 56, 68, 70) |
| `Result:` único por tarefa despachável, presente em `Files:`, path `specs/034-fence-autorizado-atividade/implement/<id>.tasks.json` | T001..T006 (tasks:33, 45, 48, 51, 54, 57); `TASK-RESULT-UNDECLARED` não disparou |
| read-only com `Files: []` e sem `Result:` | T007, T008 (tasks:68, 70) |
| glob / diretório / traversal / fora do escopo | nenhum; `normalize_task_path` e `_validate_leaf(root=".")` aceitaram os 21 paths distintos; `implement/` inexistente é permitido (retorno em `FileNotFoundError`, partition.py:436) |
| evidência reservada ao líder num worker | nenhuma: `_dag_scope_violation` (gauntlet_runs.py:740-757) só rejeita `.grill` e `.specify/reports`; `deferred_to_leader == []` |
| raiz (`README.md`, `CHANGELOG.md`) e dot-dirs (`.claude-plugin/`, `.agents/plugins/`) | aceitos pelo parser; coerente com o payload do autor ("Raiz, arquivo novo e prefixo ./ valem") |
| tokens com `/` na descrição | irrelevantes sob v1: `TaskFilesTask` "deliberately has no description grant" (partition.py:107) e `partition_task_files` usa só `task.files` (604-606); `human-authorization/v1` em T005 e os paths de T008 não viram grant |
| fases estritamente ordenadas, tarefa fora de fase | OK (Phase 1, 2, 3; `_PHASE_RE` partition.py:73) |
| múltiplos `[USn]` numa tarefa | `_MARKER_RE` (74) aceita; T002 → `('US1','US2','US3')`, T004 → 4 stories |

Nós emitidos (arquivos disjuntos entre nós da mesma fase):

- `p01-a` (Phase 1, T001): `ao`, `tests/validate_orchestrator_store_contract.py`, `implement/T001.tasks.json`; `depends_on: []`
- `p02-a` (Phase 2, T002+T003+T004): `ws`, `T`, três results; `depends_on: [p01-a]`
- `p02-b` (Phase 2, T005+T006): 4 manifests, `tests/validate_distribution.py`, `SKILL.md`, `session-protocol.md`, `README.md`, `CHANGELOG.md`, dois results; `depends_on: [p01-a]`
- Phase 3: `node_ids: []`, `read_only_tasks: [T007, T008]`

`max_workers` 2. Nada em `p02-a` cruza com `p02-b`.

## 2. Cobertura — OK

- **FR-001..FR-015**: tabela de rastreabilidade (tasks:107-123) mapeia os quinze; conferi cada linha contra a descrição da tarefa citada. FR-014 → T006 + T008 (validate_distribution); FR-015 → T008 por diff explícito contra constituição, `WORKFLOW.md`, `assets/`, `attestation.py`, `agent_runtime.py`, `workflow_versions.py` (tasks:69).
- **US1..US4**: US1 (T002-T004: p1, p3), US2 (T001, T004: p2, p2b, p4), US3 (T002-T004: matriz negativa), US4 (T004: p3, p5, n7, n9, n10) — tasks:100-103.
- **SC-001..SC-005**: tasks:124-128.
- **R11 completo** (research.md:80-82): n1, n2, n2d, n8, n8b, n0 → T002 (tasks:43); n3, n3c, n4, n5, n5b, n5c, n5d, n6, n7, pv1, pv2 → T003 (tasks:46); p1, p2, p2b, p3, p3b, p4, p5, p6, n9, n10 → T004 (tasks:49). Nenhum caso de R11 ficou sem tarefa; o caso de retomada com prova do solicitante é n10 + p5 (T004).
- **Bump, nove arquivos**: T006 (tasks:55-56) nomeia os oito pontos de `CLAUDE.md` mais `CHANGELOG.md`, com linha; conferido no HEAD: `plugin/.claude-plugin/plugin.json:3`, `plugin/.codex-plugin/plugin.json:3`, `.claude-plugin/marketplace.json:11`, `.agents/plugins/marketplace.json:7`, `tests/validate_distribution.py:8` (`VERSION = "6.0.30"`), `SKILL.md:6`, `session-protocol.md:1`, `README.md:3`, `CHANGELOG.md:3` (`## 6.0.30`); `validate_distribution.py:41-43` exige exatamente um `## <VERSION>`. `grep 6.0.30` nesses nove arquivos devolve exatamente 9 ocorrências, uma por arquivo, nas linhas citadas.

## 3. Insumos obrigatórios — incorporados onde cada um toca

| Insumo | Onde entrou | Conferido |
|---|---|---|
| plan-reviewer-003 Finding 1 (shape de n5/n5b) | T003: n5 e n5b com os shapes de `T:2512/2514/2516` e a frase "NUNCA com `status` `dispatched`"; n5d (`dispatched`+`unverifiable` → `*-ACTIVE`) como trava | tasks:46; `T:2512-2516` batem (illegible, uncorrelated, `status=None` + `unverifiable`) |
| plan-reviewer-003 nit (a) (`preserved_resources`) | T004 p1 assere ausência do recurso cercado em `preserved_resources` (`ws:4070, 4121, 4348`) | tasks:49; `ws:4281-4282` filtra `CLOSED`/`REMOVED`, então a asserção é verdadeira por construção |
| plan-reviewer-003 nit (c) (solicitante substituído entre saltos) | T004 p3b: `FENCE-ACTIVITY-STATE` para outro `--session-ref` na retomada; takeover por outra sessão admitido em prévia (`ws:3668`) | tasks:49 |
| plan-reviewer-003 nits (b), (d) | fora do grant (prosa de plan/PLAN-CONTEXT); registrados em tasks:133 | correto não incorporar |
| checklist-reviewer-001 Finding 1 (FR-014/FR-015 sem SC) | T006 + T008 e tabela de rastreabilidade | tasks:55, 69, 122-123 |
| Finding 2 (SC-002 não exaustivo) | matriz derivada de R11; `assert_refused_and_unwritten` em prévia E apply em T002/T003/T004; "Independent test criteria" chama SC-002 de amostra | tasks:43, 46, 49, 102 |
| Finding 3 (Store pós-salto 1 em p5) | T004 p5 variante pós-salto 1: Store igual ao pós-salto 1, payload com `activity_state`/`resource_state`/`operation_id` | tasks:49 |
| Finding 4 (prepare-switch após fence) | T004 p6 com fallback `_continuity_quiescence` (`ws:3654-3672`) | tasks:49 |
| Finding 5 (nove arquivos nomeados) | T006 | tasks:55 |
| CHK036 (retomada mesmo solicitante + prova por `role`) | T002 passo 2, T004 retomada, p5, n10, p3b | tasks:43, 49 |
| CHK037 (paridade prévia/apply) | T002 ("Prévia e apply executam as mesmas checagens na mesma ordem; apply só acrescenta o hash e a mutação") | tasks:43 |
| CHK038 (ids lidos do Store) | T002 passo 1 ("lidos da atividade e do contexto no Store, nunca do chamador") | tasks:43 |

## 4. Executabilidade e citações — OK, com dois findings menores

Citações reconferidas literalmente no HEAD `4e34d8a` (desvio zero):

- `ws`: 237 (`canonical`), 1565-1609 (`_takeover_observation`; `removeprefix` 1593; extração de `status`/`liveness` 1600-1609), 1612-1655 (`_session_readiness`, `return` 1654-1655), 1658-1671 (`_require_current_leader`), 3393 (`_gauntlet_authorized`), 3441-3444 (`LEADER-AUTHORITY-UNPROVEN`), 3447-3450 (`administrative_recovery`), 3654-3672 (quiescência; 3664 conjunto ativo; 3668 `UNKNOWN`), 3675-3681, 3697 (guarda `isinstance`), 3700, 3934, 3950-3953, 3974-3976, 4070/4121/4348 (`preserved_resources`), 4126-4351 (takeover; 4130-4134 docstring de paridade; 4137-4138; 4140-4143; 4148-4156 REUSED; 4159-4166 mapeamento; 4181; 4184-4187; 4247-4270 hash/STALE; 4281-4282; 4300-4343 `mutate`/`transact`; 4309-4310; 4317-4318; 4340-4343), 4439-4443, 4450-4455, 4474-4478, 5152-5183 (`run-abandon`; 5174-5183 autorização), 5340-5359, 5952, 5990, 6052-6055, 6074-6083, 6094, 6097-6106, 6147, 7081, 7131-7136, 7212.
- `ao`: 40, 48 (`_ACTIVITY_EDGES["RESULT_RECORDED"] == {"RESULT_RECORDED", "ACCEPTED"}` hoje), 49, 639-662, 720, 762, 770, 784-785, 796/841/858/887/933/942, 887-911 (`session_resource` → `REGISTERED`), 933-939, 964-965, 1002-1003, 1020-1025, 1054-1058, 1066-1068, 1082-1083, 1378-1381, 1442, 1525, 1532, 1537-1539 (first-bound, inclui `diagnostic_ref`), 1541, 1550-1553, 1557.
- `st`: 121 (`STATE_DIVERGENCE`), 142, 375-376, 1605-1631 (`transact`; 1624 carimba `revision + 1`; 1626-1627 validações). `att`: 130, 134, 191-193, 773-781. `ar`: 812-823, 1042, 1249-1292 (1267-1268 regex; 1273 `worker-show --dispatch`; 1284-1285; 1286-1291).
- `T`: 62-77 (`takeover_show`), 263 (`_session_readiness` mockada), 275/1303/2385 (prepare-switch offline), 983-996, 1245-1266 (seed), 1257-1260, 2257-2646 (`test_context_takeover`; 2281-2292 `guarded_run`; 2297-2307 `assert_refused_and_unwritten`; 2348-2353; 2505; 2508-2511; 2512/2514/2516; 2615; 2626-2637; 2640-2645). `tests/orchestration_fixture.py`: 55-58, 89-119. `tests/validate_orchestrator_store_contract.py`: 31-34, 288-290.
- Docs: `session-protocol.md:1, 85, 87`; `SKILL.md:6, 94`; manifests e `README.md:3`, `CHANGELOG.md:3`; constituição sha256 `54d5522b…7569` igual ao selado.

Ordem dentro dos nós é implementável: T001 sozinho; T002 → T003 → T004 acrescentam passos 1-4, 5-7 e mutação/retomada sobre a mesma função, cada fatia com os próprios casos de teste; T005 → T006 com o bump por último para `validate_distribution.py` fechar. Checkpoints de fase são comandos concretos (tasks:35, 59, 72).

## 5. Particionabilidade — OK

Confirmado pelo parser (seção 1). T002-T004 conflitam em `ws` + `T` → um nó; T005/T006 conflitam em `SKILL.md` + `session-protocol.md` → um nó; B e C disjuntos. Nenhuma tarefa da Phase 2 depende de arquivo de outro nó da mesma fase: C não lê nada de B (T006 valida só os nove arquivos do próprio grant). Barreira Phase 1 → 2 é real (p2/p2b percorrem a aresta de T001). Phase 3 read-only por último é a colocação correta: em `partition_task_files` (partition.py:606-611 no HEAD; o autor citou a mesma faixa) `previous = phase_nodes` é atribuído mesmo quando a fase não tem nó, então uma fase só read-only **no meio** zeraria `depends_on` da fase seguinte — observação sobre o core, fora deste grant (ver Observações).

## 6. Fidelidade — OK

Nada amplia, estreita ou contradiz spec, plan, research, data-model, contrato ou DQ-0001..DQ-0014:

- DQ-0006/DQ-0008 (verbo único, autoridade pela observação do líder): T002/T003 literais a R1/R4.
- DQ-0009 (aresta): T001 é um literal, não derivado; `diagnostic_ref` obrigatório vem de `ao:784-785`; guardas de CLI (`ws:6078-6080`, `3952-3953`) citadas, p4 fixa que só o fence percorre.
- DQ-0010 (attempt 2): `successor: "attempt-2-as-new-activity"` em T004; nenhuma mudança de CLI/schema.
- DQ-0013 A: T002 "`content_sha256` só na forma".
- DQ-0014 A: T004 p2 assere `SESSION-CLOSE-UNPROVEN`, `UNKNOWN`, exit 2, Store intacto; T005 documenta a ressalva.
- Hash da prévia (dm:74), forma da operação (dm:29-46), receipt `:fence` e `last_observation` (dm:20-22), dois saltos/um salto (R7), retomada só com prova (R2), replay read-only (R2): T003/T004 reproduzem chave a chave.
- FR-013 × pós-salto 1: T004 p5 trata como a única saída com efeito próprio já gravado, exatamente como checklist-reviewer-001 Finding 3 prescreveu; não reabre a spec.
- FR-015: T008 e o grant por nó; `attestation.py`, `agent_runtime.py`, `assets/`, `workflow_versions.py` fora de todo `Files:`.

## Findings

### Finding 1 — menor (executabilidade) — T002 manda "estender" `guarded_run` e reaproveitar `assert_refused_and_unwritten`, mas ambos são closures locais de `test_context_takeover`
- **Evidência**: tasks:43 ("`guarded_run` estendido para receber um mapa `{dispatch_id: raw}` …"; "`assert_refused_and_unwritten` para o fence …"). Em `T`, `spawn`, `takeover`, `guarded_run`, `observing` e `assert_refused_and_unwritten` são definidos dentro do `with` de `test_context_takeover` (`T:2264-2307`, indentação de método), não no módulo nem na classe. `test_activity_fence` é um método novo (R11) e não enxerga essas funções. O checkpoint do nó B exige "nenhum caso existente editado para passar" (tasks:59).
- **Por que é menor**: um worker atento define os próprios helpers "no molde de" 2281-2307, e o texto já usa essa fórmula para o invocador (`fence` "no molde do invocador `takeover`"). Mas "estendido" convida a editar a closure do takeover, o que toca um caso existente sem necessidade.
- **Correção sugerida**: em T002, trocar por "definir em `test_activity_fence` os próprios `guarded_run` (roteado por `--dispatch`), `observing` e `assert_refused_and_unwritten`, no molde das closures de `test_context_takeover` (`T:2281-2307`), sem editar o teste existente"; ou, se preferir compartilhar, "içar as três closures para o nível do módulo mantendo o comportamento e a assinatura, sem alterar asserções de `test_context_takeover`". Qualquer das duas mantém o grant.

### Finding 2 — menor (executabilidade) — T003 n7 "apply com o hash da prévia mas `--session-ref` diferente → `FENCE-INPUTS-STALE`" só vale na forma com líder terminal
- **Evidência**: tasks:46 (n7) não nomeia a forma. Pela ordem fixada na própria T003 (passo 6 antes do passo 7) e por R2/R4(b), com líder **vivo** um `--session-ref` diferente do líder recusa `FENCE-LEADER-ACTIVE` no passo 6, antes do hash; `FENCE-INPUTS-STALE` por `to_session_ref` só é alcançável com líder terminal, onde `_session_readiness` da sessão nova passa (fixture `offline_leader` serve qualquer `orca:ctx-…`, `tests/orchestration_fixture.py:55-58, 89-105`) e o hash recalculado difere (`ws:4261` como precedente). Contrato linha 8 e R6 dizem o mesmo sem nomear a forma.
- **Por que é menor**: as duas saídas recusam sem escrever (FR-013); o worker que escolher o shape de pv2 (líder vivo) vê `FENCE-LEADER-ACTIVE`, entende e troca. Custa uma iteração, não abre brecha.
- **Correção sugerida**: em n7, "na forma órfã com líder terminal (shape de pv1): apply com hash de 64 zeros, e apply com o hash da prévia mas `--session-ref` diferente, recusam `FENCE-INPUTS-STALE`"; opcionalmente registrar que na forma com líder vivo o mesmo desvio de `--session-ref` já é n3 (`FENCE-LEADER-ACTIVE`).

### Nits (não findings)
- (a) T006 (tasks:55) diz "nenhum outro byte desses arquivos muda", mas T005, no mesmo nó e antes, acrescenta um parágrafo em `session-protocol.md` e uma frase em `SKILL.md`. Lido por tarefa está certo; para o worker do nó C, "além do parágrafo e da frase de T005" evita a dúvida.
- (b) T008 (tasks:69) diz "`git diff --stat` da base do work item até o HEAD corrente" sem fixar a base. É tarefa aceita pelo líder, que conhece a base; um SHA (ou "merge-base com `main`") tornaria o registro reproduzível por terceiros.
- (c) tasks:17 cita HEAD `a5ee1da`; o `tasks.md` foi commitado em `4e34d8a`. Código de `plugin/` e `tests/` idêntico (diff vazio), então nenhuma citação muda; só registro.

## Observações para o líder (fora do grant desta etapa)

- **Core, `partition.py:606-611`**: `previous = phase_nodes` incondicional. Fase composta só de tarefas read-only/deferred no meio do documento faz os nós da fase seguinte nascerem com `depends_on: []`, perdendo a barreira. Não afeta este `tasks.md` (Phase 3 é a última). O autor já registrou; candidato a item de backlog `SGD`, não a DQ desta entrega.
- Prévia da retomada (T002/R2) devolve `FENCE-PREVIEW` com `resume: true` **sem** reexecutar a prova do solicitante; só o apply a reexecuta. É o desenho de R2 aprovado por plan-reviewer-003 (CHK037 lido como "apply só acrescenta hash e mutação" sobre o caminho normal). Tasks são fiéis; registro apenas porque `analyze` pode confrontar com CHK037.

## DQs propostas

Nenhuma. Os dois findings são precisão de instrução ao worker, derivados de código e seams já existentes (`T:2264-2307`; R2/R4/R6); os nits são prosa. Nenhuma DQ-0001..DQ-0014 reaberta, ampliada ou estreitada.

## Veredicto

`APPROVED`. Contrato v1 provado pelo parser do core, cobertura e insumos completos, citações batendo no HEAD, partição em três nós disjuntos com Phase 3 read-only na posição correta. Dois findings menores e três nits para o autor aplicar em rodada leve ou para o líder anotar no aceite; nenhum faria `partition` recusar, o worker falhar de forma irreparável ou abrir brecha.

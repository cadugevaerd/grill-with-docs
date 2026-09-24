VERDICT: APPROVED

# Revisão — interview-reviewer-001 (REVISOR, claude/fable/high, requested == effective)

- work item: `fix-continuidade-sem-checkpoint-d62bb2a5380d4409ace677fa741af28d` (W), plugin 6.0.30, worktree `/home/carlosaraujo/orca/workspaces/grill-with-docs/fix-leader`
- activity: `interview-reviewer-001`, context `ctx-0c0155ef5a94`, fence 1, dispatch `ctx_a8d0c8866a4a`
- payload lido por inteiro: `agent-orchestration/activities/interview-reviewer-001.payload.md` sha256 `e38c84eaa5eb927e2129ce944dbb98688dee2e9762d33fa8f5fb975be5f6150c`
- input manifest: 18/18 sha256 conferidos, zero divergência
- nada escrito em `.grill/` nem em `.specify/reports/`

## Escopo da verificação

Comparei `interview-author-002.result.md` com os artefatos persistidos. As edições do líder são exatamente as declaradas: DQ-0008 (handoff:21,28; PLAN-CONTEXT:11,27; ADR:47), DQ-0009 (ADR:47,56; PLAN-CONTEXT:19,27,29; DELIVERY-MAP:8), DQ-0010 (ADR:60; PLAN-CONTEXT:25), citação da "regra 11" (PLAN-CONTEXT:27) e `CONSTITUTION-CHECK.md` preenchido. Nenhuma outra diferença de conteúdo.

Conferi no código 6.0.30 (worktree, hashes do manifest) toda citação file:line de PLAN-CONTEXT, ADR-0001, CONTEXT e DECISION-FRONTIER. Todas batem, com desvio ≤ 3 linhas onde há desvio. Evidência viva: Store rev 3257, `interview-author-001` `RESULT_RECORDED` com `diagnostic_ref=None` e recurso `CLOSE_PENDING` (owner `ctx_2923e0218c89`, receipts `['orca:ctx_2923e0218c89']`); `interview-author-002` `ACCEPTED`; SGD-37 e SGD-38 existem no backlog `SGD`; `git status` só tem o bundle untracked; os oito pontos de distribuição estão em `6.0.30` nas linhas citadas.

## 1. Fidelidade às decisões humanas — OK

- DQ-0001/0002/0005: escopo = rota de recuperação; SGD-37/38 e checkpoint automático fora (ROADMAP:9, ADR:61, DELIVERY-MAP:15, PLAN-CONTEXT:29). Sem ampliação.
- DQ-0006: resultado nunca aceito (handoff:15,25,32,38; ADR:47,59; CONTEXT:15); autorização exata `work_id + context_id + activity_id` (PLAN-CONTEXT:15; CONTEXT:11); prova terminal Orca do especialista **e** do líder (PLAN-CONTEXT:13); os quatro negativos presentes (handoff:26-29; PLAN-CONTEXT:27 n1-n4).
- DQ-0007: variante retida em todos os artefatos listados na fronteira (ROADMAP:7, handoff:20,25, PLAN-CONTEXT:13,19, ADR:42,47, DELIVERY-MAP:7, CONTEXT:8).
- DQ-0008: autoridade derivada da observação do líder; negativo virou "líder vivo que não é o chamador" (handoff:28; PLAN-CONTEXT:11,27 n3/n3b; ADR:47).
- DQ-0009: aresta `RESULT_RECORDED → FAILED` só pelo fence, `diagnostic_ref` obrigatório, validador trava (ADR:56; PLAN-CONTEXT:19,27,29; DELIVERY-MAP:8). Consistente com agent_orchestration.py:784-785, que já exige `diagnostic_ref` em todo `FAILED`.
- DQ-0010: attempt 2 = atividade nova, `activity_id` novo, `attempt=1`, vínculo em `intended_after` (PLAN-CONTEXT:25; ADR:60; CONTEXT:14).
- Nenhum artefato contradiz, amplia ou omite decisão. Findings 2 e 3 abaixo são imprecisões de redação, não contradições.

## 2. Correção técnica do HOW — OK, com correções menores

Premissas confirmadas no código:
- `observe_predecessor_termination` (agent_runtime.py:1249-1292): `terminal` = `status ∉ {dispatched, running}` **ou** `capabilityRevokedAt` não nulo **ou** liveness `exited/agent_status` (1286-1290). A definição de CONTEXT:10 e a de "especialista vivo" em PLAN-CONTEXT:13 são exatamente essa função. A variante 2 observada (`completed` + capability revogada + liveness `unverifiable`) é `terminal`; liveness `unverifiable` com `dispatched` e capability nula é `indeterminate` → `FENCE-SPECIALIST-UNPROVEN`. Fail-closed.
- `_takeover_observation` (grill_workspace.py:1565-1609) devolve `status`/`liveness` só se `dispatch.id` correlaciona; mapeamento do takeover em 4159-4166.
- `_continuity_quiescence` (3654-3672): `FAILED` fora do conjunto ativo (3664); só `UNKNOWN` conta como sessão desconhecida (3668). `CLOSED` e `CLOSE_PENDING` não bloqueiam. Takeover herda só `PREPARED` (3675-3681, 4170-4174).
- Arestas (agent_orchestration.py:48-49): `DISPATCHED→FAILED` válida; `RESULT_RECORDED→FAILED` ausente (DQ-0009); `REGISTERED→CLOSE_PENDING→CLOSED` e `CLOSE_PENDING→CLOSED` válidas. `diagnostic_ref` first-bound (1534-1536) e hoje `None` em `interview-author-001`. `result_ref` em `FAILED` não viola invariante (762, 770-771, 780-781). Receipts append-only com `ref` único (1545-1550, 1058); `last_observation` precisa estar em receipts (1067). Operação: `kind` livre, `fence` = fence do líder do contexto (643, 1378), `CONFIRMED` exige `observation_ref` e `result_sha256` (651), `idempotency_key` colide só com identidade diferente (1379-1381), `CONFIRMED` imutável (1522).
- `_ID` (agent_orchestration.py:40) não admite `:` — o `scope` canônico `work_id:context_id:activity_id` é não ambíguo.
- `_validate_human_authorization(value, step_id)` (attestation.py:773-781): `_exact_keys`, `scope == step_id`, `decision == APPROVED`, `FREE_REF_RE` em `authorized_by`/`receipt_ref`, `SHA256_RE` em `content_sha256` (só forma). `load_checkpoint_attestation` (5340-5359). Precedente `gauntlet-run-abandon` 5152-5189 com código único `ABANDON-AUTHORIZATION-INVALID`.
- `gauntlet-activity` é `@_gauntlet_authorized` (5952-5953); `--diagnostic` só em `DISPATCHED` (6078-6080); `accept` fora de `DISPATCHED|RESULT_RECORDED` → `ACTIVITY-STATE-DIVERGENCE` (6074-6075); `attempt=1` fixo (5990); correlação de `owner_dispatch` (6052-6055).
- Testes: `test_context_takeover` (2234), `guarded_run` (2258), `assert_refused_and_unwritten` (2274), `takeover_show(dispatch_id, *, status, revoked, liveness)` (62) existem e suportam fixtures com capability revogada.
- Distribuição: oito pontos em `6.0.30` exatamente nas linhas de PLAN-CONTEXT:31.

### Finding 1 — menor — prefixo `orca:` ausente na observação do especialista
- Evidência: PLAN-CONTEXT:13 manda reusar `_takeover_observation` "para o dispatch do especialista (`resource.identity.owner_dispatch`)". `observe_predecessor_termination` exige `session_ref` casando `orca:ctx[-_]…` (agent_runtime.py:1268) e `_takeover_observation` faz `removeprefix("orca:")` (1593). `identity.owner_dispatch` é id nu (Store: `ctx_2923e0218c89`); `_released_activity_sessions` compõe `"orca:" + dispatch` (grill_workspace.py:3700).
- Efeito: sem o prefixo, todo fence cai em `not_observable` → `FENCE-NOT-OBSERVABLE`. Fail-closed, não fail-open; o executor tropeça no primeiro positivo.
- Correção: em PLAN-CONTEXT:13, "sobre `'orca:' + resource.identity.owner_dispatch` (forma de `_released_activity_sessions`, 3700)".

### Finding 2 — menor — guarda de revisão no segundo salto da variante 1
- Evidência: PLAN-CONTEXT:19 prescreve dois `store.transact` com a mesma `idempotency_key` e "guarda de revisão e de estado dentro de `mutate` como no takeover (4304-4316)". A guarda do takeover compara `document["revision"]` com `snapshot.revision` lido fora do lock (4309). O primeiro `transact` incrementa a revisão; o segundo, guardado contra o mesmo `snapshot.revision`, cai sempre em `FENCE-CAS-CONFLICT`.
- Correção: dizer explicitamente que o segundo salto reobserva o Store (novo `read_snapshot`) ou guarda só por estado (`operation_id` presente e `CONFIRMED`, recurso `CLOSE_PENDING`, atividade `FAILED`). Alternativa em Finding 3.

### Finding 3 — menor — precedente omitido e simplificação disponível
- Evidência: `_transferred_activity_sessions` + `mutate` de prepare-switch (grill_workspace.py:3711-3750, 3940-3953) já leva `DISPATCHED`+`REGISTERED` a `FAILED` com `diagnostic_ref` lógico (`orca:<dispatch>:superseded-by:<id>`) e o recurso a `PRESERVED` em um salto, com `preservation_reasons=["RESULT_NOT_DURABLE"]` e `operation_id`. Não cobre o X7 (exige retry `ACCEPTED` no mesmo terminal físico, mesmo contexto, sob `@_gauntlet_authorized`), então "nenhum verbo alcança" (ADR:42) continua verdadeiro. Mas é o precedente de forma mais próximo da mutação proposta e não é citado.
- Simplificação (HOW, sem decisão humana envolvida): `PRESERVED` é aresta válida a partir de `REGISTERED` **e** de `CLOSE_PENDING` (agent_orchestration.py:49), o que faria as duas variantes num único `transact`, eliminando p5, a janela de crash (PLAN-CONTEXT:36) e o `# ponytail:` de PLAN-CONTEXT:19. Custo: `PRESERVED` aparece em `preserved_resources` do checkpoint (`_cleanup_checkpoint_projection`, 1942/3798) e na projeção `retained` do takeover (4281-4282), e a prosa "fecha o recurso" (ROADMAP:8, handoff:24, DELIVERY-MAP:14) viraria "preserva". Manter `CLOSED` é igualmente correto pelas arestas; a escolha é do ciclo executor. Registrar o precedente em PLAN-CONTEXT:19 em qualquer caso.

### Finding 4 — menor — prova do host do sucessor não tem mecanismo nem registro
- Evidência: DQ-0008 (DECISION-FRONTIER:95) diz "Líder terminal: aceita sucessor com prova do host". PLAN-CONTEXT:11 repete a frase mas não nomeia o mecanismo; o takeover usa `_session_readiness(root, runtime, session_ref, work_id)` (4181) para observar a sessão entrante. `intended_after` (PLAN-CONTEXT:19) e o hash da prévia (PLAN-CONTEXT:17) não registram quem pediu o fence; o critério "rastreável ao work item, contexto, atividade, digests e autorização" (handoff:39) omite o solicitante.
- Efeito: sem prova do host qualquer string em `--session-ref` é aceita na rota órfã. A autorização humana continua sendo o gate, então não é fail-open, mas é decisão humana sem HOW.
- Correção: PLAN-CONTEXT:11 → "líder terminal → `_session_readiness` sobre `--session-ref` (4181); `readiness.ref/sha256` entram em `evidence.requester` e em `intended_after`". Hash da prévia pode incluir `to_session_ref` como no takeover (4261).

### Finding 5 — menor — objetivo do ROADMAP e cenário 2 do handoff estreitam DQ-0008
- ROADMAP:7: "um work item **cujo líder terminou** com uma atividade … órfã ou de sessão retida". Na variante 2 deste repositório o líder `orca:ctx_ad48e72ddf4c` está `ACTIVE` (Store), e DQ-0008 cobre exatamente esse caso. O observável "no work item corrente, `interview-author-001` deixa de contar como ativa" acontece com líder vivo.
- handoff:25: "Pedido pelo líder corrente exato (DQ-0008)" lê como regra; DQ-0008 permite sucessor com líder terminal também na variante 2.
- Correção: ROADMAP:7 "cujo líder terminou **ou** que ainda tem líder vivo"; handoff:25 "pedido pelo líder corrente exato quando o líder está vivo, ou por sucessor com prova terminal do líder (DQ-0008)".

### Finding 6 — menor — colisão de vocabulário "fence"
- Evidência: `fence` já é (a) o inteiro de autoridade do líder (`leader.fence`, agent_orchestration.py:1378; payload `fence=1`) e (b) `release_proof=resource-fence` do release estrito do líder (agent_runtime.py:1042; session-protocol.md:87 "o fence registra `release_proof=resource-fence`"). O work item cunha (c) "fence autorizado", `kind="activity-fence"`, `FENCE-*`.
- Correção: CONTEXT:9 "termos a evitar"/nota de desambiguação; PLAN-CONTEXT:34 (lock-in) mencionar a colisão. Renomear (`activity-close`, `orphan-fence`) é opção do executor; não bloqueia.

### Finding 7 — menor — citação inverificável da "regra 11"
- Evidência: PLAN-CONTEXT:27 cita "regra 11 do `CLAUDE.md` do projeto consumidor proxy-cm-ai, citada no brief do coordenador". Não está no input manifest; o autor registrou não a ter localizado (result.md:296). SGD-37 confirma que X7 = proxy-cm-ai, então a origem é plausível, mas o revisor não pode conferir.
- Correção: manter a origem como nota e ancorar a obrigação em fonte dos inputs: DQ-0006 ("Testes negativos: …", DECISION-FRONTIER:71) e a cláusula "Fail-closed sem waiver" da Constituição.

### Finding 8 — menor — divergência doc/código apontada pelo autor não foi registrada
- Evidência: session-protocol.md:87 diz que o fechamento por release ocorre "sem aceitar nem reexecutar o resultado"; `gauntlet_prepare_switch_command` grava `ACCEPTED`, `review_verdict=APPROVED`, `acceptance_ref=result_ref` (grill_workspace.py:3936-3939). O autor sinalizou (result.md:297); nenhum artefato, BL ou item SGD registra.
- Efeito: ADR-0001 invoca o princípio de :87 como base da opção A; o código vigente já o contraria na rota de release. Não muda a decisão, mas fica sem rastro.
- Correção: item SGD lateral (como SGD-37/38) ou nota em ADR "Relações → backlog". Fora do escopo deste fix por DQ-0002.

### Observação (não é finding do plano)
`observe_predecessor_termination` classifica como `terminal` qualquer `status` fora de `{dispatched, running}` (1287), inclusive um status novo do Orca que não seja terminal. O fence herda o comportamento do takeover; PLAN-CONTEXT:38 já limita a prova a `status`/`capabilityRevokedAt`/`liveness`. Registro só para o ciclo executor conhecer.

## 3. Separação WHAT/WHY × HOW — OK
Handoff sem stack, classes ou API interna. Termos Orca em handoff:45 (`completed`, capability revogada, liveness `unverifiable`) são evidência observada, não implementação. Único nit: handoff:41 nomeia `tests/run_validators.py`; "suíte de validadores do repositório verde nos três SOs sem rede" seria mais puro. Não bloqueia.

## 4. Coerência entre artefatos — OK
- ADRs `ADR-0001`, BLs `none`, DU-001, `development-type: platform-devops` idênticos em ROADMAP:11-12,15, handoff:7-8,11-12, PLAN-CONTEXT:5-8, DELIVERY-MAP:11-13.
- `context-refs` (ROADMAP:10, handoff:6) = 9 termos = 9 linhas do glossário (CONTEXT:7-15).
- Testes negativos exigidos por DQ-0006 presentes em handoff:26-29 e PLAN-CONTEXT:27; inconclusivo, stale, replay e aceite tardio em handoff:30-32 e DELIVERY-MAP:17.
- DELIVERY-MAP:8 cita agent_orchestration.py só pela aresta de DQ-0009; PLAN-CONTEXT:29 idem. Boundary exclui `attestation.py`/`agent_runtime.py`, coerente com PLAN-CONTEXT:15 ("sem tocar na função").
- Nit: CONTEXT:14 ("attempt 2") cita só DQ-0006; poderia citar DQ-0010, que fixa a convenção de `activity_id`.

## 5. Constituição — OK
Cada PASS/NOT-APPLICABLE conferido contra evidência real:
- `constitution_sha256` = `54d5522b…7569` = manifest e `state.json`/`WORK-ITEM.json`.
- "Feature/fix plan-only": `git status --porcelain` só `?? .grill/work-items/fix-continuidade-…/`; SGD-37 e SGD-38 existem no backlog `SGD` com origem DQ-0002.
- "Sequência obrigatória": `state.json` com 11 passos `pending`, `current_step=specify`.
- "Rastreabilidade": R-0002..R-0009 no ROUND-LOG; `interview-author-002` `ACCEPTED` no Store (rev atual 3257 ≥ 3244 citada).
- "Tier de modelo": `interview-author-001/002.observation.json` com `effective_model=fable`, `effective_effort=xhigh`, `resolved_model_id=fable`; revisor a `fable/high` (fora do check, correto para revisão).
- NOT-APPLICABLE em verify/review, bump e release: justificativas honestas; PLAN-CONTEXT:31 registra a obrigação de bump 6.0.31 e `publish.yml`.

## DQs propostas
Nenhuma. Não encontrei decisão material fora das já resolvidas; Findings 3 e 6 são escolhas de HOW do ciclo executor, não decisões humanas.

## Veredicto
`APPROVED`. Oito findings, todos menores; nenhum contradiz decisão humana nem abre brecha fail-open. Findings 1, 2 e 4 são os que valem corrigir em PLAN-CONTEXT antes do `specify`, porque o executor tropeça neles no primeiro teste positivo.

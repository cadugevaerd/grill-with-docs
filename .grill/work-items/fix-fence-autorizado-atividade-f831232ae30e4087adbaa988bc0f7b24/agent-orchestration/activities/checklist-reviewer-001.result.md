VERDICT: APPROVED

# Revisão independente — checklist-reviewer-001 (REVISOR, fable/high, etapa checklist, work item fix-fence-autorizado-atividade-f831232ae30e4087adbaa988bc0f7b24)

- payload lido por inteiro: sha256 `b5446e42b0c6a43ae174c391cb760bf939630457c6a23fd84247069164d687af` (confere)
- input manifest `checklist-reviewer-001.input.json`: 12/12 sha256 conferidos, zero divergência
- worktree `/home/carlosaraujo/orca/workspaces/grill-with-docs/fix-leader`, HEAD `4dda791`; `git diff --stat 816618c 4dda791` toca só `F/checklists/release-gate.md` (+66). Artefatos de plan idênticos aos atestados por `plan-reviewer-003`.
- nada escrito em `.grill/`, `.specify/reports/` nem no repositório; relatório só neste scratchpad
- convenções: `F` = `specs/034-fence-autorizado-atividade`; `spec` = `F/spec.md`; `plan` = `F/plan.md`; `R` = `F/research.md`; `dm` = `F/data-model.md`; `qs` = `F/quickstart.md`; `ct` = `F/contracts/activity-fence.md`; `DF` = `DECISION-FRONTIER.md`; `pr3` = `plan-reviewer-003.result.md`; `ws` = `grill_workspace.py`

## Resumo

35 CHKs avaliados. 33 PASS, 2 FAIL menores (CHK018, CHK019), nenhum bloqueante: nenhuma lacuna faria o executor implementar errado ou abrir brecha, porque a regra exaustiva (FR-013, R11 n1..n10) existe e é a fonte que `tasks` deve usar. O checklist cobre os oito riscos do domínio pedidos; falta um item de alto risco sobre a **retomada do salto 2** (o único caminho que já escreveu sem prova, plan-reviewer-002 F4) e dois de risco médio. Nenhum CHK testa implementação em vez de requisito. Nenhuma DQ nova.

## Tabela CHK

| CHK | Veredicto | Evidência |
|---|---|---|
| CHK001 | PASS | ct:9 "Formas admitidas: `(DISPATCHED, REGISTERED)` e `(RESULT_RECORDED, CLOSE_PENDING)`"; dm:9, dm:19; spec:94 (FR-006) em nível de negócio |
| CHK002 | PASS | spec:91-93 (FR-003 autorização, FR-004 especialista, FR-005 líder + sessão do sucessor); ct:10-13 enumera as quatro provas e a ordem |
| CHK003 | PASS | spec:90 (FR-002) lista as classes; dm:74 fecha o conjunto literal (`work_id, context_id, activity_id, activity_state, resource_id, resource_state, to_session_ref, specialist{verdict,reference}, leader{verdict,reference}, authorization{5 chaves}`); R6 explica exclusões (digest de resposta, `snapshot.revision`) |
| CHK004 | PASS | spec:98 (FR-010); dm:27-48: `context_id`, `subject_ids=[activity_id, resource_id]`, `requester`, `evidence.*.observation_sha256`, `authorization` verbatim; work item = documento do Store onde a operação vive e `scope` da autorização (dm:55) |
| CHK005 | PASS | spec:96 (FR-008); dm:19-22 (`CLOSED`, receipt `orca:<owner_dispatch>:fence`, `operation_id`); dm:82-83 transições das duas formas; ct:18 |
| CHK006 | PASS | plan:29 "9 arquivos de versão (8 pontos + CHANGELOG.md)"; plan:82-90 lista os nove com linha; plan:47; R12; `tests/validate_distribution.py:41-43` exige `## 6.0.31`. Nota: spec:102 (FR-014) diz "oito pontos" — ver Finding 5 |
| CHK007 | PASS | spec:91 (FR-003); ct:10 `scope == "<work_id>:<context_id>:<activity_id>"` e `decision == APPROVED`; dm:52-58; R5 (`:` não ambíguo, `_ID` `ao:40`) |
| CHK008 | PASS | R5 "Alternatives" → DQ-0013 (A); R:108-112 (DQ-P1 selada); dm:58 "só forma (R5; DQ-0013, opção A; SGD-40)"; DF:157-167 `state: resolved` |
| CHK009 | PASS | ct:11 terminal = `status ∉ {dispatched, running}` ∨ `capabilityRevokedAt` não nulo ∨ liveness `exited`; R3 vivo = `status ∈ {dispatched, running}` com `capabilityRevokedAt == null`; indeterminado = residual; `not_observable` como quarta saída (ct:14, R13). Critério objetivo existe. O parêntese de spec:80 sobrepõe "vivo" e "indeterminado" no shape `dispatched`+`null`+`unverifiable`; é o pr3 Finding 1, fechado pela frase em R3 que ele prescreve — não repetido como FAIL (ver Findings, nota) |
| CHK010 | PASS | spec:93 (FR-005 "derivar da observação do líder"); ct:11 "do ambiente e nunca do chamador"; R4(a)(b)(c) |
| CHK011 | PASS | spec:95 (FR-007); dm:9 `state = FAILED`; dm:10 `diagnostic_ref = activity-fence/<operation_id>.json`; dm:38 `intended_after.reason = "activity-fence"` |
| CHK012 | PASS | plan:17 artefato = `.git/grill/orchestrator.json`; plan:27 "toda recusa deixa o Store bit a bit igual"; R11 `assert_refused_and_unwritten` compara `content_sha256` antes/depois em prévia e apply |
| CHK013 | PASS | spec:91 (FR-003) e spec:55-56 (US3 AS1/AS2 "recusa idêntica"); ct:10 enumera flag omitida, ausente, ilegível, malformado, não aprovado, outro work item/contexto/atividade/run → `FENCE-AUTHORIZATION-INVALID`; R5 (`required` ausente no parser) |
| CHK014 | PASS | spec:101 (FR-013); ct:14 "Toda recusa … escreve zero bytes; `FENCE-CAS-CONFLICT` pós-salto 1 … reporta o efeito já aplicado pelo salto 1 (próprio ou do solicitante vencedor)"; dm:84; R7 salto 2. Consistentes entre si; a tensão com a letra de FR-013 no caso "próprio" está declarada — ver Finding 3 |
| CHK015 | PASS | spec:93 (FR-005), spec:39-40 (US2 AS1/AS2), spec:57 (US3 AS3); ct:12; R4; R11 n3 (`FENCE-LEADER-ACTIVE`), n3c (readiness do sucessor), p2, p2b; DF:93-104 (DQ-0008) |
| CHK016 | PASS | spec:97 (FR-009), spec:83; ct:19 "não altera … a regra de herança de workers `PREPARED` do takeover"; R8 "sem tocar `_takeover_prepared_workers` (3675-3681)" |
| CHK017 | PASS | spec:99 (FR-011); dm:38 `successor: "attempt-2-as-new-activity"` + `subject_ids`; R10 (`activity_id` novo, `attempt=1`, mesmo contexto quando líder vivo); ct:20; DF:119-130 (DQ-0010) |
| CHK018 | FAIL (menor) | FR-001..FR-013 têm AS/SC (US1-US4, SC-001..SC-004). **FR-015** (spec:103) não tem cenário nem SC. **FR-014** (spec:102) só indiretamente por SC-005 (suíte verde inclui `validate_distribution.py`) e qs:5. Ver Finding 1 |
| CHK019 | FAIL (menor) | SC-002 (spec:118) enumera seis negativos; faltam: estado fora das duas formas (spec:78; n8/n8b), revisão stale/CAS (n9), solicitante divergente em replay/retomada (p3b), `decision != APPROVED` (spec:79), não observável (n6). FR-013 é a regra exaustiva. Ver Finding 2 |
| CHK020 | PASS | spec:121 (SC-005 "três sistemas operacionais da matriz de integração, sem rede"); plan:21 nomeia ubuntu/windows/macos × 3.10/3.13 |
| CHK021 | PASS | spec:55 (AS1 sem autorização), :56 (AS2 outro alvo), :57 (AS3 líder vivo não solicitante), :58 (AS4 especialista vivo); DF:77 (DQ-0006) |
| CHK022 | PASS | spec:59 (US3 AS5, "inclusive a da própria sessão do sucessor"); spec:80; separação por sujeito em R11: n5 (especialista), n5b (líder), n3c (sucessor), n5c (sem handle) — shape de n5/n5b a corrigir por pr3 F1 |
| CHK023 | PASS | spec:73-74 (US4 AS1 reuso sem segundo evento; AS2 recusa sem efeito); ct:8, ct:17; R2 passo 2 |
| CHK024 | PASS | spec:95 (FR-007), spec:119 (SC-003 "qualquer rota"); ct:19 `ACTIVITY-STATE-DIVERGENCE`; dm:87; R8: `gauntlet-activity --phase accept` (`ws:6074-6075`) e `accept_activity` (`ao:964-965`); rota `prepare-switch --released-source` não alcança `FAILED` (`_released_activity_sessions` só `RESULT_RECORDED`, R1 alternatives, pr3 §3) |
| CHK025 | PASS | spec:97 (FR-009 "nem para a troca de runtime"), spec:82, spec:35 (US2 Independent Test); ct:20; R8 (`CONTINUITY-ACTIVE-WORK` 3974-3976 deixa de acusar). Requisito coberto; falta caso de teste em R11 — ver Finding 4 |
| CHK026 | PASS | ct:9 "Formas admitidas"; R2 passo 3 → `FENCE-ACTIVITY-STATE`; R11 n8b (três pares semeados direto) |
| CHK027 | PASS | spec:81; R7 salto 1 (`StoreError` → releitura → `_fence_recorded` sob outro solicitante → `FENCE-CAS-CONFLICT`) e salto 2 (`CLOSE_PENDING → CLOSED` uma vez; segundo → `FENCE-REUSED`); pr3 §3 traça A/B |
| CHK028 | PASS | R3 `"orca:" + od if isinstance(od, str) else None` → `not_observable` → `FENCE-NOT-OBSERVABLE`; R11 n6; dm:67 |
| CHK029 | PASS | ct:20; R8; dm:23; DF:169-179 (DQ-0014 A, SGD-41); R11 p2 fixa `SESSION-CLOSE-UNPROVEN`, exit 2, Store intacto |
| CHK030 | PASS | plan:19 (seams `takeover_show`, `guarded_run`, `assert_refused_and_unwritten`), plan:21 ("sem rede e sem `orca` real"); R11 (`offline_leader`, mocks de `_session_readiness` e `read_snapshot`) |
| CHK031 | PASS | plan:13 "Python >=3.10, somente biblioteca padrão"; plan:15 "nenhuma nova" |
| CHK032 | PASS | plan:25 "duas observações do host por fence … mais uma de readiness quando o líder terminou; a retomada faz só a prova do solicitante e o replay não observa" |
| CHK033 | PASS | spec:125 (sinais: status, revogação, liveness; "leitura que não traz nenhum … é indeterminada"); spec:92 (FR-004); ct:11 |
| CHK034 | PASS | spec:127-129 (FASE-002, SGD-37/38/39, DQ-0002); SGD-40/41 nasceram no plan (após a spec selada): plan:45, R5, R8, DF DQ-0013/DQ-0014 |
| CHK035 | PASS | spec:103 (FR-015); plan:27 amplia para `ESSENTIAL`, `attestation.py`, `agent_runtime.py`, policy; ct:19; verificável pelo grant por nó (plan:72-91) e por diff — ver Finding 1 |

## Avaliação do checklist em si

**Cobertura dos riscos do domínio**: fail-closed (CHK013/014/026/033), autoridade (CHK007/010/015), idempotência (CHK023/027), não-aceite (CHK011/024), quiescência (CHK025/029), rastreabilidade (CHK004/017), distribuição (CHK006), suíte offline (CHK020/030). Todos cobertos.

**Itens que testam implementação**: nenhum. CHK028 e CHK032 são os mais próximos do código, mas perguntam por desfecho e custo declarados, não por como implementar.

**Itens de alto risco ausentes** (recomendo acrescentar; todos já PASSam pelos artefatos atuais, então é registro de cobertura, não trabalho novo):

- **CHK036 (alto) — Retomada do salto 2**: "A retomada sobre `(FAILED, CLOSE_PENDING)` está restrita ao mesmo solicitante da operação gravada, reexecuta a prova dele conforme `requester.role` antes de escrever, e tem desfecho definido para solicitante diferente?" Evidência: ct:13, ct:17; R2 passo 2; dm:86; R11 n10/p3b/p5. Motivo: é o único caminho que já escreveu sem prova (plan-reviewer-002 F4); a spec não tem cenário (specify-reviewer-001 F1); sem CHK, `analyze` não tem gancho para exigir tarefa e teste.
- **CHK037 (médio) — Paridade prévia/apply**: "Está exigido que a prévia execute exatamente as checagens do apply, na mesma ordem, com o apply só acrescentando hash e mutação?" Evidência: ct:7, ct:13; R1; plan:93. Motivo: prévia mais fraca que o apply produz hash "válido" de um estado que o apply recusa, ou o inverso.
- **CHK038 (médio) — Fronteira de confiança dos identificadores**: "`context_id`, `epoch`, `fence` e `resource_id` são lidos do Store e nunca do chamador, inclusive o `context_id` do `scope` da autorização?" Evidência: ct:9; dm:55, dm:64. Motivo: se o chamador pudesse fornecer `context_id`, a autorização exata seria contornável.

## Findings

Todos menores. Nenhum exige editar `spec.md` (re-atestação em cascata); todos são insumo para `tasks`/`analyze`.

### Finding 1 — menor — CHK018: FR-015 sem cenário/SC; FR-014 só indireto
- **Evidência**: spec:102-103; SCs em spec:117-121 não citam bump nem proibições; qs:5 cobre o bump; nada cobre FR-015 além de plan:27 (declaração).
- **Por que é menor**: FR-015 é estruturalmente imposto pelo grant de arquivos por nó (plan:72-91; `partition` recusa fora do grant com `GRANT-SCOPE-VIOLATION`) e o `verify` faz diff hygiene. FR-014 é imposto por `validate_distribution.py`, que está em SC-005.
- **Correção (em tasks/analyze)**: mapear FR-014 → tarefa do nó C + `python3 tests/validate_distribution.py`; FR-015 → nota de rastreabilidade "verificado pelo grant do DAG e por `git diff --stat` contra `.specify/memory/constitution.md`, `WORKFLOW.md`, `plugin/skills/grill-with-docs/assets/`, `grill_core/attestation.py`, `grill_core/agent_runtime.py`, `agent-orchestration.v1.json`". Sem tarefa nova de código.

### Finding 2 — menor — CHK019: SC-002 não é exaustivo
- **Evidência**: spec:118 lista seis negativos; faltam estado fora das formas (spec:78), CAS/revisão stale, solicitante divergente no replay/retomada, `decision != APPROVED` (spec:79) e não observável. R11 testa todos com `assert_refused_and_unwritten` (n1..n10, p3b).
- **Por que é menor**: FR-013 ("toda recusa") é a regra exaustiva; SC-002 é amostra.
- **Correção (em tasks)**: derivar a matriz negativa de R11 (n1, n2, n2d, n3, n3c, n4, n5, n5b, n5c, n6, n7, n8, n8b, n9, n10, p3b), não de SC-002, e exigir `assert_refused_and_unwritten` em prévia **e** apply para cada um; `analyze` não deve tratar SC-002 como lista fechada.

### Finding 3 — menor — CHK014: letra de FR-013 × `FENCE-CAS-CONFLICT` após salto 1 próprio
- **Evidência**: spec:101 "toda recusa MUST deixar o estado bit a bit igual ao anterior"; ct:14 admite "efeito já aplicado pelo salto 1 (**próprio** ou do solicitante vencedor)". Na forma órfã, uma invocação do mesmo solicitante que grava o salto 1 e falha no salto 2 devolve código de recusa com o Store diferente do pré-invocação.
- **Por que é menor**: o salto 1 é `transact` concluído e íntegro; a recusa em si não escreve; há retomada determinística (R2/p5); pr3 §1 já aceitou a leitura "a recusa não escreve".
- **Correção (em tasks/analyze)**: o teste p5 variante pós-salto 1 deve asserir Store == estado pós-salto 1 e payload (`activity_state`, `resource_state`, `operation_id`), **não** "idêntico ao anterior"; `analyze` deve reconhecer ct:14 como exceção declarada de FR-013, não como inconsistência. Opcional em ct:14: uma frase "única saída do verbo com código de recusa e efeito próprio já gravado".

### Finding 4 — menor — CHK025: sem caso de teste para `prepare-switch` após fence
- **Evidência**: spec:35 (US2 Independent Test: "deixa de contar como ativa para a tomada e para a troca de runtime"); R8 afirma por leitura de código (3974-3976); R11 p1 cobre só takeover; nenhum caso de R11 invoca `gauntlet-prepare-switch` (grep vazio em R11); a suíte já tem 12 usos offline do verbo em `tests/validate_agent_orchestration_contract.py` (ex.: :275), então o seam existe.
- **Correção (em tasks)**: caso p6 — forma retida com líder vivo, após `FENCE-APPLIED`, `gauntlet-prepare-switch` em prévia não devolve `CONTINUITY-ACTIVE-WORK` pela atividade cercada. Se o fixture exigir mais setup que o valor, asserir ao menos que `_continuity_quiescence` não a lista.

### Finding 5 — menor — CHK006: FR-014 diz "oito pontos"; o gate exige nove arquivos
- **Evidência**: spec:102 "oito pontos de distribuição"; `tests/validate_distribution.py:41-43` exige `## 6.0.31` em `CHANGELOG.md`; plan:29 e R12 já corrigem para nove.
- **Por que é menor**: o validador é a verdade e o plano já lista o nono arquivo no nó C.
- **Correção (em tasks)**: a tarefa do nó C nomeia os nove arquivos explicitamente; nenhuma edição na spec.

### Nota — pr3 Finding 1 (shape de n5/n5b) não repetido
Não reprova CHK009: o critério objetivo existe em ct:11 e R3. A origem do overlap é o parêntese de spec:80 ("sem status terminal" inclui `status=dispatched`), que R3 deve fechar com a frase prescrita por pr3. `tasks` deve nascer com n5/n5b no shape de `T:2512-2516` (status ausente / não correlacionado / ilegível) e, opcionalmente, n5d (`dispatched` + `unverifiable` → `*-ACTIVE`). Insumo obrigatório, já registrado.

## DQs propostas

Nenhuma. Os findings são precisão de rastreabilidade e de matriz de teste, derivados de regras já fixadas (FR-013, R2, R11) e de decisões seladas (DQ-0006..DQ-0014). Nenhuma DQ reaberta, ampliada ou estreitada.

## Veredicto

`APPROVED`. 33 PASS, 2 FAIL menores (CHK018, CHK019), nenhum bloqueante. Recomendo acrescentar CHK036 (retomada), CHK037 (paridade prévia/apply) e CHK038 (ids do Store) antes de `tasks`, e levar os Findings 1–5 mais o pr3 Finding 1 como insumo obrigatório de `tasks`.

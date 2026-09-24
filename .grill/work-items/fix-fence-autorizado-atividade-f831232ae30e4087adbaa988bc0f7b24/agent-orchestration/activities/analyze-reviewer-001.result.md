VERDICT: APPROVED

# Revisão independente — analyze-reviewer-001 (REVISOR, fable/high, etapa analyze, work item fix-fence-autorizado-atividade-f831232ae30e4087adbaa988bc0f7b24)

- payload lido por inteiro: sha256 `fdd9dc05a9aebe4f0a0a5dd26ef6a0789873b12076a0f4110f2e33d898fd7705` (confere)
- input manifest `analyze-reviewer-001.input.json`: 14/14 sha256 conferidos, zero divergência
- worktree `/home/carlosaraujo/orca/workspaces/grill-with-docs/fix-leader`, HEAD `3d71305`; `git diff --stat 39380f7 HEAD -- plugin tests` vazio, então toda citação file:line de código vale neste HEAD
- partição reproduzida em memória pelo parser do core (`grill_core.partition.partition_task_files`, sem escrever): resultado idêntico ao relatado em `analysis.md:3`
- nada escrito em `.grill/`, `.specify/reports/` nem no repositório; `git status --porcelain` só mostra os três artefatos de dispatch do coordenador
- convenções: `ws` = `plugin/skills/grill-with-docs/scripts/grill_workspace.py`; `ao` = `grill_core/agent_orchestration.py`; `ar` = `grill_core/agent_runtime.py`; `T` = `tests/validate_agent_orchestration_contract.py`; `F` = `specs/034-fence-autorizado-atividade`

## Resumo

`F/analysis.md` está correto e suficiente para seguir ao `partition`. Os sete achados existem, têm a severidade certa e nenhum CRITICAL ou HIGH foi rebaixado ou omitido: cobertura 20/20 conferida requisito a requisito, Constituição com o hash selado, sem contradição spec/plan/tasks que mude código ou grant, sem critério não testável, ordem de dependências implementável. As recomendações de U1, U2 e I2 como esclarecimento no brief dos workers bastam: nenhuma altera contrato, `Files:` ou asserção, então reescrever o `tasks.md` atestado custaria a cascata de re-atestação sem ganho. Sobrevive um achado de completude que o líder não listou (MEDIUM, mesma classe de U2, resolvido no brief do nó B) e quatro notas LOW. Nenhuma DQ nova.

## 1. O relatório é correto? — SIM

Cada achado reconferido no HEAD:

| ID | Confere? | Evidência |
|---|---|---|
| U1 MEDIUM | Sim | `spawn`, `takeover`, `guarded_run`, `observing`, `assert_refused_and_unwritten` são closures dentro do `with` de `test_context_takeover` (`T:2264-2307`), invisíveis a um método novo. Severidade certa: "estender" convida a editar caso existente, contra o checkpoint `tasks.md:59`. |
| U2 MEDIUM | Sim | Ordem fixada em `tasks.md:46` (passo 6 antes do 7) e contrato linha 13. Com líder vivo, `--session-ref` diferente cai em `FENCE-LEADER-ACTIVE` antes do hash; `FENCE-INPUTS-STALE` por `to_session_ref` só é alcançável com líder terminal, onde `_session_readiness` da sessão nova passa (`offline_leader`, `tests/orchestration_fixture.py:89-105`) e o hash difere (`ws:4261` como precedente). |
| I1 LOW | Sim | `spec.md:102` "oito"; `tests/validate_distribution.py:41-43` exige exatamente um `## <VERSION>` no `CHANGELOG.md`; `grep 6.0.30` nos nove arquivos devolve nove ocorrências, uma por arquivo, nas linhas de `tasks.md:55`. Sem ação, correto. |
| I2 LOW | Sim | `tasks.md:55` "nenhum outro byte" × `tasks.md:52` (T005 escreve nos mesmos dois arquivos, mesmo nó, antes). Brief do nó C resolve. |
| A1 LOW | Sim | `WORK-ITEM.json` `base_commit` = `39380f7fc3147d9766f277e3474e845f1dd6c9b3` (commit existe). Observação: `git merge-base main HEAD` = `32c4954`, diferente; a base do work item é a referência certa para FR-015 e hoje o diff `39380f7..HEAD -- plugin tests` é vazio. |
| D1 LOW | Sim | `research.md:83` cita "DQ-0008 (n3/n3b)"; n3b não existe em `research.md:81-82` nem em `tasks.md`; tasks acrescentam n0, n5d, p6, pv1, pv2. Sem ação, correto. |
| C1 LOW | Sim no mérito | Prévia da retomada devolve `FENCE-PREVIEW` com `resume: true` sem reprovar o solicitante (`research.md:15`; `tasks.md:43`); só o apply reprova. Desenho de R2 aprovado. **Citação errada**: ver Finding 2. |

Omissões CRITICAL/HIGH procuradas e não encontradas:

- **Requisito sem tarefa**: tabela de cobertura (`analysis.md:21-39`) conferida contra `tasks.md:107-128` e as descrições; FR-001..FR-015, SC-001..SC-005 têm tarefa. FR-011 não exige código (research R10) e fica em T004 (`successor`) + T005 (prosa) — correto.
- **Constituição**: sha256 `54d5522b18e43efa05311dbf13ed79694b79ccfcb01509384b3572b2d5667569` igual ao selado (`plan.md:35`); nenhum `Files:` toca `.specify/`, `WORKFLOW.md`, `assets/`, `attestation.py`, `agent_runtime.py`, `workflow_versions.py`; bump e release cobertos por T006 e `publish.yml`.
- **Contradição spec/plan/tasks com efeito em código**: nenhuma. A aresta (`ao:48`), `diagnostic_ref` obrigatório (`ao:784-785`), `result_ref` válido em `FAILED` (`ao:762, 770`), arestas de recurso (`ao:49`), first-bound (`ao:1537-1539`), `transact` carimbando revisão (`store.py:1624`) e a guarda `proposed.revision == current.revision` (`store.py:1619-1623`) batem com R7/R9 e T001/T004. Validador de recurso (`ao:996-1088`) não exige `result_acceptance_ref` em `CLOSED`, então o recurso cercado é válido.
- **Critério não testável**: SC-005 (matriz) é conferido no PR, declarado em T007 — aceitável para `PLAN_ONLY_STOP`.
- **Ordem de dependências**: Phase 3 é a última; `partition.py:600-612` atribui `previous = phase_nodes` incondicionalmente, então uma fase read-only no meio zeraria a barreira seguinte — não é o caso deste `tasks.md`.

## 2. O relatório é completo? — Com um achado a mais (MEDIUM) e notas LOW

### Finding 1 — MEDIUM (Inconsistency; não bloqueante) — `research.md` R11 dá a n5/n5b a forma que R3 e T003 classificam como `*-ACTIVE`
- **Evidência**: `research.md:81` "(n5) especialista `status=dispatched`, `capabilityRevokedAt=null`, liveness `unverifiable` → `FENCE-SPECIALIST-UNPROVEN`; (n5b) líder idem → `FENCE-LEADER-UNPROVEN`". `research.md:26` (R3): "não terminal com `status ∈ {dispatched, running}` → `*-ACTIVE`" e "'Especialista vivo' = `status ∈ {dispatched, running}` com `capabilityRevokedAt == null`". `tasks.md:46` n5/n5b usam os shapes de `T:2512/2514/2516` "NUNCA com `status` `dispatched`" e n5d trava `dispatched` + `unverifiable` → `FENCE-SPECIALIST-ACTIVE`. Código: `ar:1286-1291` devolve `indeterminate` para esse shape e `ws:1600-1609` extrai `status="dispatched"`, que o mapeamento do takeover (`ws:4159-4166`, copiado em T003) manda para `*-ACTIVE`.
- **Por que MEDIUM e não HIGH**: `tasks.md` governa o worker e já está certo (plan-reviewer-003 Finding 1 aplicado em T003). Mas `tasks.md:102` remete a "matriz negativa é a de research R11", e `research.md` não foi corrigida na mesma rodada: um worker não-frontier que abrir R11 para "ver a forma de n5" implementa o shape errado, vê `FENCE-SPECIALIST-ACTIVE`, e o risco real é ele "consertar" o mapeamento do verbo para fazer n5 passar — o que quebraria n5d e a definição de vivo. Mesma classe de U2 (custa uma iteração ou induz erro), mesma severidade.
- **Correção sugerida**: no brief do nó B: "Shapes de n5/n5b são os de `T:2512/2514/2516` (ilegível, não correlacionado, `status` ausente + `unverifiable`), como escrito em T003; a linha de R11 em `research.md:81` está desatualizada para n5/n5b — `dispatched` + `unverifiable` é n5d e recusa `*-ACTIVE`." Não exige reescrever `tasks.md` nem `research.md` antes do `partition`.

### Finding 2 — LOW (Citação do relatório) — `analysis.md:15` localiza C1 em `checklists/release-gate.md CHK037`, mas o arquivo termina em CHK035
- **Evidência**: `F/checklists/release-gate.md:11-65` vai de CHK001 a CHK035. CHK036–CHK038 existem só como sugestão de checklist-reviewer-001, registrada em `tasks.md:135` ("o arquivo de checklist fica fora deste grant").
- **Correção sugerida**: trocar a localização por "tasks.md:135 (CHK037 sugerido por checklist-reviewer-001)". Não muda mérito nem severidade de C1.

### Finding 3 — LOW (Terminology) — `plan.md` carrega listas desatualizadas de seams e casos
- **Evidência**: `plan.md:19` apresenta `takeover_show`, `guarded_run`, `assert_refused_and_unwritten` como seams reutilizáveis (só `takeover_show` é de módulo, `T:62`); `plan.md:79` "n1..n10, p1..p5" omite n0, n2d, n3c, n5b, n5c, n5d, n8b, p2b, p3b, p6, pv1, pv2.
- **Correção sugerida**: nenhuma; subsumido por U1 e D1 ("a lista de tasks.md governa"). Registro para o brief: "a lista de casos é a de `tasks.md`, não a de `plan.md:79`".

### Finding 4 — LOW (Terminology) — Contrato linha 13 omite a checagem de recurso do passo 1
- **Evidência**: `contracts/activity-fence.md:13` fixa "replay/retomada → estado da atividade → autorização → …", mas `tasks.md:43` passo 1 (e `research.md:14`) recusam `FENCE-ACTIVITY-STATE` para recurso ausente ou `kind != session` **antes** do replay. Desfecho idêntico: sem recurso `CLOSED`/`CLOSE_PENDING` não há forma de replay nem de retomada, então a ordem não altera nenhum veredicto.
- **Correção sugerida**: nenhuma.

### Finding 5 — LOW (Registro) — FR-013 × `FENCE-CAS-CONFLICT` pós-salto 1 é desvio já adjudicado, não listado
- **Evidência**: `spec.md:101` (FR-013) "toda recusa deixa o estado bit a bit igual ao anterior"; `tasks.md:49` p5 variante pós-salto 1: "Store fica igual ao estado pós-salto 1, não ao anterior à primeira invocação, que é a única saída do verbo com código de recusa e efeito próprio já gravado". Adjudicado por checklist-reviewer-001 Finding 3, research R7 (`research.md:55`) e contrato linha 14 ("`FENCE-CAS-CONFLICT` pós-salto 1 … reporta o efeito já aplicado pelo salto 1"). A recusa em si escreve zero bytes; o efeito é do salto 1.
- **Correção sugerida**: nenhuma; só registrar em "Constitution/Consistency" do relatório como desvio aceito, para o `verify` não reabrir.

Conferências sem achado: contagens (`analysis.md:47-52`: 15 FR + 5 SC, 8 tarefas, 6 despacháveis, 2 read-only, 1 ambiguidade) batem; cobertura 100% reconferida; R11 completo por tarefa (`tasks.md:43, 46, 49`); casos p2/p2b percorrem a aresta de T001, barreira real; `FENCE-REUSED` e retomada exigem `session_ref == intended_after.requester.ref` em R2, contrato 17, data-model 85-86 e T002/T004 — consistente; hash da prévia (`data-model.md:74`) igual em R6 e T003; `transact` exige `document["revision"]` inalterado em `mutate` (`store.py:1619-1623`), o que T004 respeita nos dois saltos.

## 3. As recomendações bastam? — SIM

- **U1**: "definir em `test_activity_fence` os próprios helpers no molde de `T:2281-2307`, sem editar `test_context_takeover`" é a opção certa das duas que tasks-reviewer-001 ofereceu: içar as closures ao módulo moveria código de um caso existente, contra o checkpoint `tasks.md:59`. A instrução é executável por worker não-frontier porque as três closures cabem em ~30 linhas e o único ajuste é `guarded_run` receber `{dispatch_id: raw}` e escolher pelo token após `--dispatch` em `cmd` (`ar:1273`).
- **U2**: "n7 usa a forma órfã com líder terminal (shape de pv1)" fecha a ambiguidade; com líder vivo o desvio de solicitante já é n3.
- **I2**: "além do parágrafo e da frase de T005" basta.
- **Nenhum exige corrigir `tasks.md` antes do `partition`**: nenhum dos três muda `Files:`, `Result:`, asserção ou código do verbo; `tasks_semantic_sha256` `c298d821…424c6` continua válido e uma reescrita obrigaria re-atestar tasks e refazer este analyze.
- **Acréscimo**: Finding 1 entra no mesmo brief do nó B, com a mesma forma (esclarecimento, sem editar artefato atestado).

## 4. Partição — coerente

Reproduzida em memória (`partition_task_files(text, feature="034-fence-autorizado-atividade", root=".")`): `PARTITION-DEGRADED` (só por T007/T008 read-only), `max_workers` 2, `deferred_to_leader` e `unmapped` vazios:

- `p01-a` (Phase 1, T001): `ao`, `tests/validate_orchestrator_store_contract.py`, `implement/T001.tasks.json`; `depends_on: []`.
- `p02-a` (Phase 2, T002+T003+T004): `ws`, `T`, três results; `depends_on: [p01-a]`.
- `p02-b` (Phase 2, T005+T006): quatro manifests, `tests/validate_distribution.py`, `SKILL.md`, `session-protocol.md`, `README.md`, `CHANGELOG.md`, dois results; `depends_on: [p01-a]`.
- Phase 3: `node_ids: []`, `read_only_tasks: [T007, T008]`.

`files` de cada nó = união exata dos `Files:` declarados (`tasks.md:32, 44, 47, 50, 53, 56`); nenhum path cruza entre `p02-a` e `p02-b`; a barreira Phase 1 → 2 é real (p2/p2b percorrem a aresta de T001); nenhum token com `/` da descrição virou grant (contrato v1, `partition.py:107`).

## DQs propostas

Nenhuma. Os cinco findings são precisão de instrução ou de citação, derivados de artefatos já selados e de código no HEAD; nenhuma DQ-0001..DQ-0014 é reaberta, ampliada ou estreitada.

## Veredicto

`APPROVED`. O relatório do líder é correto no que afirma e suficiente para o `partition`; as recomendações no brief bastam para um worker não-frontier. Acrescentar ao brief do nó B o esclarecimento do Finding 1 (shape de n5/n5b: T003 governa, R11 de `research.md` está desatualizada) e corrigir a citação de C1 (Finding 2) no aceite do líder. Nada bloqueia; nenhum achado CRITICAL ou HIGH foi omitido.

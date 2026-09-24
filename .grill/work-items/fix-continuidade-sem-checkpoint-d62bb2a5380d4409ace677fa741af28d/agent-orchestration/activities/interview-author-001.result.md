# interview-author-001 — propostas de artefatos (AUTOR fable/xhigh)

- work item: `fix-continuidade-sem-checkpoint-d62bb2a5380d4409ace677fa741af28d`
- worktree: `/home/carlosaraujo/orca/workspaces/grill-with-docs/fix-leader` (branch `cadugevaerd/fix-leader`, plugin 6.0.30, HEAD `32c4954`)
- activity: `interview-author-001`, context `ctx-0c0155ef5a94`, fence 1, `write_files=[]`
- input manifest: 15/15 sha256 conferidos (`interview-author-001.input.json`); payload `c9d7d8ca…6632` conferido
- decisões humanas respeitadas: DQ-0002 R-0004 (escopo = só rota de recuperação; SGD-37/SGD-38 fora) e DQ-0006 R-0005 (opção A: fence autorizado, resultado não aceito, attempt 2)
- toda linha:coluna citada foi lida nesta sessão em `plugin/skills/grill-with-docs/scripts/` salvo indicação

---

## CONTEXT.md

```markdown
# CONTEXT

## Glossário

| Termo canônico | Definição | Termos a evitar | Evidência |
|---|---|---|---|
| atividade órfã | Atividade `DISPATCHED` cujo especialista já encerrou sem que o resultado fosse gravado (`result_ref` nulo) e cujo líder também já foi encerrado/liberado pelo Orca. Nenhum verbo atual a tira do caminho: quiescência a conta como ativa e o takeover recusa `TAKEOVER-WORK-ACTIVE`. | atividade travada, dispatch morto, zumbi | `grill_workspace.py:3654-3672`, `:4169-4174`; caso X7 (DECISION-FRONTIER DQ-0005: `converge-final-author-x7-3 author DISPATCHED … session REGISTERED`) |
| fence autorizado | Ato explícito, preview-first e com hash esperado, que encerra uma atividade órfã como `FAILED` e fecha seu recurso de sessão com receipt, mediante prova terminal Orca do especialista e do líder mais autorização humana exata. Não aceita nem reexecuta o resultado. | abandono automático, limpeza, kill | ADR-0001; precedente `gauntlet-run-abandon` (`grill_workspace.py:5153-5185`, `grill_core/attestation.py:191-193, 773-781`) |
| prova terminal Orca | Observação nativa do Orca (`worker-show`) de que um dispatch exato encerrou: para o líder, `status` fora de `dispatched\|running`, capability revogada ou liveness `exited` (mesmo padrão do takeover); para o especialista, release exato do recurso com identidade de dez campos igual à registrada (mesmo padrão do prepare-switch). Silêncio, `indeterminate` ou identidade divergente não provam nada. | sessão fechada, timeout, lease vencido | `grill_core/agent_runtime.py:1249-1292` (`observe_predecessor_termination`), `:839-1050` (`observe_released`); `grill_workspace.py:1565-1611`, `:3683-3710` |
| autorização humana exata | Documento `human-authorization/v1` de seis chaves cujo `scope` casa exatamente com o work item, o contexto e a atividade a cercar; `decision=APPROVED`. Escopo de outro contexto, atividade ou run é recusado. É a mesma forma que `ship` e `gauntlet-run-abandon` já validam. | flag de confirmação, `--force`, aprovação verbal | `grill_core/attestation.py:191-193` (chaves), `:773-781` (validação); `tests/validate_gauntlet_converge_contract.py:339-352` |
| takeover | `gauntlet-context-takeover`: uma sessão nova assume o work item quando o Orca prova que o líder anterior encerrou; herda só workers `PREPARED` e recusa qualquer atividade em voo. É o passo seguinte ao fence autorizado. | adoção, rebind, resume | `grill_workspace.py:4126-4345`; `references/session-protocol.md:81` |
| quiescência | Estado em que nenhuma atividade está em `BOOTSTRAPPING\|VERIFIED\|DISPATCHED\|RESULT_RECORDED` sem sessão fechada por aceite, nenhum recurso de sessão está `UNKNOWN` e nenhum worker está ativo. Só observação terminal explícita aquieta; silêncio e expiry são ignorados. | inatividade, idle, sem heartbeat | `grill_workspace.py:3654-3672` (`_continuity_quiescence`) |
| attempt 2 | Nova atividade de autor, no contexto sucessor, com o mesmo input manifest e `attempt=2`, criada depois do fence e do takeover. O resultado da atividade órfã nunca entra nela; não é reexecução do mesmo id. | retry, reaproveitar resultado, reabrir atividade | `grill_core/agent_orchestration.py:797-810` (`new_activity` já aceita `attempt>=1`), `:1529-1533` (identidade imutável inclui `attempt`); `references/session-protocol.md:87` |

> Somente linguagem ubíqua; decisões e tarefas vivem em ADR/BL/ROADMAP.
```

---

## docs/adr/ADR-0001.md

```markdown
---
managed-by: grill-with-docs/v1
id: ADR-0001
title: Atividade DISPATCHED órfã sai do caminho só por fence autorizado; o resultado não é aceito e o sucessor reexecuta como attempt 2
status: accepted
evidence-status: verified
sources:
  - type: repo
    title: grill_workspace.py — _continuity_quiescence, takeover e prepare-switch --released-source
    url: plugin/skills/grill-with-docs/scripts/grill_workspace.py
    version: 6.0.30
    section: 3654-3672 (quiescência), 3683-3710 (released sessions), 3928-3953 (fechamento/superseded), 4126-4345 (takeover), 3428-3437 (única exceção do decorator), 5153-5185 (run-abandon)
    consulted: 2026-09-24
  - type: repo
    title: attestation.py — human-authorization/v1
    url: plugin/skills/grill-with-docs/scripts/grill_core/attestation.py
    version: 6.0.30
    section: 191-193 (chaves), 773-781 (_validate_human_authorization, scope exato)
    consulted: 2026-09-24
  - type: repo
    title: agent_runtime.py — provas terminais do Orca
    url: plugin/skills/grill-with-docs/scripts/grill_core/agent_runtime.py
    version: 6.0.30
    section: 839-1050 (observe_released, release_proof archive|resource-fence), 1249-1292 (observe_predecessor_termination)
    consulted: 2026-09-24
  - type: repo
    title: agent_orchestration.py — máquina de estados de atividade e recurso
    url: plugin/skills/grill-with-docs/scripts/grill_core/agent_orchestration.py
    version: 6.0.30
    section: 45-49 (estados e arestas), 784 (FAILED exige diagnostic_ref), 1538 e 1554 (arestas verificadas por commit)
    consulted: 2026-09-24
  - type: repo
    title: Protocolo de sessão — cleanup e continuidade
    url: plugin/skills/grill-with-docs/references/session-protocol.md
    version: 6.0.30
    section: linha 87 ("Resultados de atividades nunca herdam essas exceções")
    consulted: 2026-09-24
  - type: decision
    title: DECISION-FRONTIER DQ-0005 e DQ-0006 (R-0003, R-0005) — leitura do Store do X7 e decisão humana opção A
    url: DECISION-FRONTIER.md
    version: R-0005
    section: DQ-0005 evidence; DQ-0006 resolution
    consulted: 2026-09-24
---
# ADR-0001 — Atividade DISPATCHED órfã sai do caminho só por fence autorizado; o resultado não é aceito e o sucessor reexecuta como attempt 2

## Contexto
No caso X7 (proxy-cm-ai, plugin 6.0.25, líder Codex) o Store registra a atividade `converge-final-author-x7-3` em `DISPATCHED` com recurso de sessão `REGISTERED`, especialista já encerrado e líder já liberado pelo Orca (DQ-0005, saída literal do coordenador). Nenhum verbo da 6.0.30 remove essa atividade do caminho da sucessão:

- `_continuity_quiescence` conta como ativa toda atividade `BOOTSTRAPPING|VERIFIED|DISPATCHED|RESULT_RECORDED` cuja sessão não esteja `CLOSED` por aceite (`grill_workspace.py:3654-3672`);
- `gauntlet-context-takeover` herda apenas workers `PREPARED` e recusa o resto com `TAKEOVER-WORK-ACTIVE` (`:4169-4174`);
- `gauntlet-prepare-switch --released-source` só aquieta atividade de autor em `RESULT_RECORDED` com release arquivado (`:3683-3710`), e só fecha o recurso já em `CLOSE_PENDING` (`:3928-3935`); a única saída para `DISPATCHED` órfã exige um retry já `ACCEPTED` no mesmo terminal (`:3711-3753`), que aqui não existe;
- o decorator de autoridade abre uma única exceção para líder liberado, exclusiva de `gauntlet-run-abandon`, que por sua vez exige `human-authorization/v1` com `scope == run_id` (`:3428-3437`, `:5153-5185`; `attestation.py:773-781`). O protocolo é explícito: "Resultados de atividades nunca herdam essas exceções" (`session-protocol.md:87`).

Instalar a 6.0.30 não destrava o X7 (DQ-0005). O escopo do fix é apenas essa rota de recuperação (DQ-0002, opção A humana); transcript > 16 MiB e o `KeyError` de `campaign` com head nulo ficaram em SGD-37 e SGD-38.

## Decisão
Existe um verbo novo, preview-first e com `--apply --expected-sha256`, que executa um **fence autorizado** sobre uma atividade órfã exata. Ele só aplica quando as três provas coexistem, todas relidas no apply:

1. **prova terminal Orca do líder** registrado no contexto corrente, com o mesmo padrão do takeover (`observe_predecessor_termination`: `status` fora de `dispatched|running`, capability revogada ou liveness `exited`);
2. **prova terminal Orca do especialista**: release exato do recurso de sessão, com identidade de dez campos igual à registrada no Store, pelo mesmo `observe_released` que o prepare-switch usa; aceita release arquivado ou fence de recurso (`release_proof=archive|resource-fence`), porque nenhum resultado será lido;
3. **autorização humana exata**: `human-authorization/v1` cujo `scope` casa exatamente com `work_id`, `context_id` e `activity_id` da atividade cercada, validada pelo mesmo `_validate_human_authorization` do `ship` e do `run-abandon`.

Efeito: a atividade vai para `FAILED` com `diagnostic_ref` apontando a operação de fence; o recurso de sessão é fechado (`CLOSED`) com receipt correlacionado ao release observado; a operação fica registrada com o documento de autorização gravado literalmente, como o `run-abandon` já faz com `abandon_authorization`. **O resultado da atividade órfã não é aceito, não é lido e não é reexecutado sob o mesmo id**: depois do takeover, o contexto sucessor cria uma nova atividade de autor com o mesmo input manifest e `attempt=2`.

Nada muda em Constituição, `WORKFLOW.md`, tuplas `ESSENTIAL`, registries ou no schema do Store: estados, arestas e chaves existentes bastam (`DISPATCHED → FAILED` e `REGISTERED → CLOSE_PENDING → CLOSED` já são arestas válidas).

## Opções e custos
- **A (escolhida, decisão humana R-0005): fence autorizado por verbo novo.** benefício: rota única, auditável e fail-closed, coerente com o único precedente que remove trabalho ativo (`run-abandon`) e com o princípio de que resultados nunca herdam exceções; **custo:** exige humano no laço e mais um verbo público, mais um formato de `scope` a documentar.
- **B (rejeitada): aquietar automaticamente a atividade `DISPATCHED` quando o Orca prova o release do especialista**, estendendo `_released_activity_sessions` sem autorização humana. benefício: zero fricção; **custo:** o core passaria a descartar trabalho de agente por conta própria, sem registro de quem decidiu; contraria o precedente `run-abandon` e a cláusula "Fail-closed sem waiver". A prova de release diz que o processo morreu, não que o trabalho pode ser abandonado.
- **C (rejeitada): tornar o takeover tolerante à atividade órfã**, herdando-a ou ignorando-a como faz com workers `PREPARED`. benefício: nenhum verbo novo; **custo:** a exceção do takeover é deliberadamente restrita a workers exatamente `PREPARED` (`session-protocol.md:81`); abrir para atividades em voo apagaria a diferença entre "nada rodou" e "rodou e ninguém sabe o que saiu", e o contexto sucessor nasceria com uma atividade cuja sessão ninguém fechou.

## Consequências
- O X7 e todo caso igual têm caminho: fence autorizado → `gauntlet-context-takeover` → attempt 2 no contexto sucessor.
- `_continuity_quiescence`, takeover e prepare-switch não mudam de semântica; a atividade deixa de contar porque `FAILED` já não é estado ativo. Cleanup passa a ver o recurso como fechado porque `CLOSED` com referência não nula é o predicado que ele já usa.
- Custo de reversão alto: o verbo grava operação `CONFIRMED` e autorização literal no Store; um Store com fences aplicados só é legível por versões que aceitem essa operação. Por isso a decisão é ADR e não detalhe de plano.
- Testes negativos obrigatórios (DQ-0006): sem autorização; autorização de outro contexto, atividade ou run; líder vivo; especialista vivo. Cada recusa deixa o Store byte a byte igual.
- Fora do escopo e intactos: SGD-37, SGD-38, prevenção por checkpoint automático (T005 já cobre head nulo).

## Relações
- amends: none
- supersedes: none
- superseded-by: none
- exception: none
- backlog: SGD-37, SGD-38 (fora do escopo, gatilhos registrados)
```

---

## ROADMAP.md

```markdown
# ROADMAP

- execution-order: FASE-001

## FASE-001 — Fence autorizado de atividade órfã para liberar a sucessão
- state: ready-for-specify
- objetivo: um work item com atividade órfã (especialista encerrado, líder liberado, resultado nunca gravado) volta a ser sucedível: com prova terminal Orca dos dois dispatches e autorização humana exata, a atividade é encerrada como falha e seu recurso de sessão é fechado com receipt, o takeover passa e o contexto sucessor reexecuta o autor como attempt 2, sem aceitar o resultado órfão
- scope-in: verbo novo preview-first com hash esperado; provas terminais Orca do especialista e do líder; autorização humana exata por work item, contexto e atividade; estado terminal da atividade e fechamento do recurso de sessão com receipt; attempt 2 no contexto sucessor; testes negativos (sem autorização; autorização de outro contexto/atividade/run; líder vivo; especialista vivo); bump de distribuição
- scope-out: transcript do líder acima de 16 MiB (SGD-37); `KeyError` do prepare-switch com campanha preenchida e cabeça de checkpoint nula (SGD-38); prevenção por checkpoint automático (já coberta por T005); qualquer aceite ou reexecução do resultado da atividade órfã; mudança em Constituição, WORKFLOW, ESSENTIAL, registries ou schema do Store
- context-refs: atividade órfã, fence autorizado, prova terminal Orca, autorização humana exata, takeover, quiescência, attempt 2
- ADRs: ADR-0001
- BLs: none
- depends-on: none
- specify-handoff: handoffs/FASE-001-SPECIFY-HANDOFF.md
- delivery-units: DU-001

> Estados: `planned | ready-for-specify | blocked | complete | superseded`. `complete` e `superseded` são terminais. `execution-order` é explícita, topológica e independente dos números de fase. Cada fase tem um handoff exclusivo; somente a primeira incompleta pode ficar `ready-for-specify`. Se todas forem terminais e não houver BL/DQ material aberto, grave `milestone_status=completed`, `state.status=complete`, `active_phase=null` e `audit_verdict=GO`; a auditoria retorna `MILESTONE-COMPLETE`.

## Delivery First
Feature/fix phases are plan-only. Hotfix-fast incidents are tracked in the work-item HOTFIX.md and reconciled after ship.
```

---

## handoffs/FASE-001-SPECIFY-HANDOFF.md

```markdown
# FASE-001 — Fence autorizado de atividade órfã para liberar a sucessão

- phase: FASE-001
- state: ready-for-specify
- roadmap: ROADMAP.md#FASE-001
- context-refs: atividade órfã, fence autorizado, prova terminal Orca, autorização humana exata, takeover, quiescência, attempt 2
- ADRs: ADR-0001
- BLs: none

## WHAT
- delivery-units: DU-001
- development-type: platform-devops

**Resultado observável.** Um work item preso por uma atividade órfã volta a ser sucedível. Quem conduz a sucessão pede uma prévia do fence, confere o que será encerrado e o hash esperado, e aplica com a autorização humana em mãos. Depois do fence, a atividade aparece como falha com referência à operação, o recurso de sessão aparece fechado com receipt, a quiescência não a conta mais, o takeover passa e o contexto sucessor cria a atividade de autor de novo como attempt 2. O resultado da atividade órfã nunca é aceito nem lido.

**Atores.**
- *Líder sucessor*: a sessão nova que precisa assumir o work item e hoje recebe recusa por trabalho ativo.
- *Humano autorizador*: quem assina a autorização exata para aquele work item, contexto e atividade, e responde pelo descarte do trabalho órfão.
- *Especialista órfão*: o dispatch de autor ou revisor que encerrou sem gravar resultado; não age mais, só é observado.

**Cenários.**
1. Atividade em voo, especialista comprovadamente encerrado, líder comprovadamente encerrado, autorização exata presente: a prévia mostra atividade, recurso e hash; o apply com o mesmo hash encerra a atividade como falha, fecha o recurso com receipt e registra a autorização literalmente. O takeover seguinte é aceito e o sucessor abre o attempt 2.
2. **Sem autorização** (ausente, ilegível, malformada ou não aprovada): recusa nomeada; nada é escrito.
3. **Autorização de outro contexto, de outra atividade ou de outro run/work item**: recusa nomeada por escopo divergente; nada é escrito.
4. **Líder vivo** (dispatch ainda despachado ou em execução): recusa nomeada; nada é escrito. Ausência de resposta ou resposta ambígua do host também recusa, com código distinto de "vivo".
5. **Especialista vivo**: recusa nomeada; nada é escrito. Release não comprovado ou identidade do recurso divergente da registrada também recusa.
6. Prévia e apply divergem porque algo mudou entre eles: o apply recusa por entradas obsoletas e pede nova prévia.
7. Repetição do mesmo fence já aplicado: resposta idempotente, sem segundo efeito; um fence interrompido antes de confirmar é concluído pela repetição do mesmo comando.
8. Atividade que não é órfã (resultado já gravado, atividade de verificação determinística, recurso já fechado): recusa nomeada como não elegível.

**Escopo excluído.** Transcript do líder acima de 16 MiB (SGD-37); falha do prepare-switch com campanha preenchida e cabeça de checkpoint nula (SGD-38); prevenção por checkpoint automático, já coberta; aceitar, reler ou reexecutar sob o mesmo id o resultado da atividade órfã; qualquer mudança em Constituição, WORKFLOW, ESSENTIAL, registries ou schema do Store.

**Critérios de aceite.**
- Os oito cenários cobertos por validação automatizada offline, sem Orca real, rede ou processo externo, usando os seams de observação já existentes na suíte.
- Em toda recusa o Store permanece byte a byte igual ao anterior.
- A prévia e o apply chegam ao mesmo veredito para as mesmas entradas; o apply exige o hash da prévia.
- Depois do fence, a quiescência não lista a atividade, o takeover é aceito quando nada mais está ativo e o cleanup vê o recurso como fechado.
- Nenhum código de recusa existente muda de significado; o fence tem códigos próprios.
- Suíte completa em exit 0 e versão do plugin incrementada nos oito pontos que o validador de distribuição fixa, antes do merge.
- Evidência de origem: o estado do X7 (contexto ativo, cabeça de checkpoint nula, campanha ausente, atividade `converge-final-author-x7-3` em voo com sessão registrada) é reproduzido em fixture e sai do bloqueio pelo caminho fence → takeover.

## WHY

**Valor.** Um work item cujo especialista morreu no meio de uma atividade e cujo líder também caiu fica preso para sempre: a sucessão exige quiescência, e a única exceção existente serve apenas a runs do Gauntlet. Foi o que aconteceu no X7 (proxy-cm-ai, plugin 6.0.25, líder Codex), e instalar a 6.0.30 não resolve.

**Evidência.** Leitura literal do Store do X7 pelo coordenador (DQ-0001, DQ-0005): contexto ativo, cabeça de checkpoint nula, campanha ausente, atividade de autor em voo com recurso de sessão registrado e revisor sem atividade em voo. Na 6.0.30 a quiescência conta essa atividade como ativa, o takeover recusa por trabalho ativo e o prepare-switch com origem liberada só aquieta resultado já gravado. O protocolo de sessão diz, na letra, que resultados de atividades nunca herdam as exceções de continuidade.

**Restrições.** Fail-closed sem waiver: a autorização é prova humana exata mais prova terminal do host, nunca flag nem silêncio. O resultado órfão não é aceito: o caminho correto é attempt 2 no contexto sucessor. Somente biblioteca padrão, sem rede, sem processo novo; nenhum checkpoint, DAG, receipt ou operação histórica é reescrito. A entrega altera `plugin/**`, logo exige bump antes do merge; a leitura proposta é patch (6.0.30 → 6.0.31) e fica como assunção a confirmar no ciclo executor.

> Não inclua headings/campos de stack, banco, framework, classes, componentes, implementação ou API interna. Este handoff cobre somente uma fase.

> Feature/fix handoffs remain plan-only. Incident hotfixes use HOTFIX.md and do not bypass constitutional safety.
```

---

## PLAN-CONTEXT.md

```markdown
# PLAN-CONTEXT

## FASE-001 — Fence autorizado de atividade órfã para liberar a sucessão
- phase: FASE-001
- ADRs: ADR-0001
- BLs: none
- delivery-units: DU-001
- development-type: platform-devops

### HOW

Todos os caminhos abaixo são relativos a `plugin/skills/grill-with-docs/scripts/`; linhas conferidas na 6.0.30 (HEAD `32c4954`).

**1. Verbo novo `gauntlet-activity-fence`** (parser ao lado de `gauntlet-context-takeover`, `grill_workspace.py:7131`):
`gauntlet-activity-fence ROOT --work-id ID --activity-id AID --session-ref REF --authorization PATH [--apply --expected-sha256 HASH]`.
Não recebe `@_gauntlet_authorized`: o chamador é o líder sucessor, que ainda não é o líder corrente, e a única exceção do decorator é exclusiva de `gauntlet-run-abandon` (`:3428-3437`; protocolo, `session-protocol.md:87`). A autoridade do verbo é a mesma do takeover (`gauntlet_context_takeover_command`, `:4126-4345`): prova do host, não pedido do chamador. Preview e apply executam exatamente as mesmas verificações; o apply só acrescenta o CAS com hash (`:4130-4136`).

**2. Elegibilidade** (`FENCE-NOT-ELIGIBLE` caso contrário): item em `agent_orchestration.work_items`; contexto corrente `ACTIVE|QUIESCING` (`:4145-4148`); atividade em `DISPATCHED`, `activity_type in {author, reviewer}`, `result_ref` nulo; recurso `session_resource_id` com `kind=session`, `state=REGISTERED`, `activity_id` igual e `identity.owner_dispatch` string — o mesmo filtro de `_transferred_activity_sessions` (`:3711-3720`), sem exigir sucessor aceito. Atividade `deterministic_check` não tem dispatch e não é elegível.

**3. Prova terminal do líder** — reutilizar `_takeover_observation(root, context["runtime"], context["leader"]["session_ref"])` (`:1565-1611`): `not_observable` → `FENCE-NOT-OBSERVABLE`; `status in {dispatched, running}` → `FENCE-LEADER-ACTIVE`; qualquer outro não-terminal → `FENCE-EVIDENCE-UNPROVEN`. Mesmo padrão e mesma dívida do takeover (SGD-36 m3: predicado terminal permissivo, não ampliado aqui).

**4. Prova terminal do especialista** — dois passos sobre `"orca:" + identity["owner_dispatch"]`: (a) `agent_runtime.observe_predecessor_termination` (`agent_runtime.py:1249-1292`) para separar vivo de inconclusivo: `status in {dispatched, running}` → `FENCE-SPECIALIST-ACTIVE`; (b) `_leader_boundary(root, identity["provider"], ref, work_id).observe_released(allow_unarchived_stopped=True)` (`:1547-1562`; `agent_runtime.py:839-1050`) e igualdade dos dez campos de identidade com `resource["identity"]`, exatamente como `_released_activity_sessions` faz em `:3702-3710`. Falha ou divergência → `FENCE-EVIDENCE-UNPROVEN`. `allow_unarchived_stopped=True` é deliberado: o fence não lê resultado, então release por `resource-fence` basta; o prepare-switch exige arquivo porque aceita o resultado.

**5. Autorização humana exata** — `load_checkpoint_attestation(root, args.authorization)` (`:5340-5360`) e `attestation._validate_human_authorization(bundle, scope)` (`attestation.py:773-781`) com `scope = f"{work_id}:{context_id}:{activity_id}"` (separador `:`; ids não contêm `:`; evitar `/` porque o partition trata token com barra como grant, ver CLAUDE.md Project Learnings). Toda falha — ausente, ilegível, malformada, escopo divergente, não aprovada — é um único código público `FENCE-AUTHORIZATION-INVALID`, espelhando `ABANDON-AUTHORIZATION-INVALID` (`:5171-5185`). Convenção recomendada para o arquivo: `.grill/work-items/<work_id>/receipts/activity-fence-<activity_id>.json`, escrito pelo humano/líder, nunca pelo core.

**6. Sessão chamadora** — `--session-ref` obrigatório e observado por `_session_readiness(root, context["runtime"], args.session_ref, work_id=...)` (`:1612-1660`), como o takeover faz em `:4177` (T016: ausência de prova nunca autoriza). A observação entra na operação como `applied_by`; o verbo não instala líder.

**7. Hash da prévia** — `store.jcs_sha256({work_id, context_id, activity_id, resource_id, leader: {verdict, reference}, specialist: {source_ref, release_proof, incarnation}, authorization_sha256: jcs(bundle)})`. Digerir decisões, não bytes voláteis do `worker-show` (lição T018, `:4226-4231`); `snapshot.revision` fica fora (T024, `:4232-4239`). Preview → `FENCE-PREVIEW` com `expected_sha256` e o resumo das provas; apply com hash divergente → `FENCE-INPUTS-STALE`.

**8. Apply: uma operação, dois commits CAS.** As arestas são verificadas por commit (`agent_orchestration.py:1538`, `:1554`) e `REGISTERED → CLOSED` não é aresta direta (`:49`), logo:
- `operation_id = "fence-" + sha256(canonical({context_id, activity_id, authorization_sha256}))[:24]`; registro em `operations` com `kind="activity-fence"`, `fence=context["leader"]["fence"]`, `subject_ids=[activity_id, resource_id]`, `input_sha256=expected`, `expected_before={activity: DISPATCHED, resource: REGISTERED, leader_session_ref}`, `intended_after={reason: "orphan-fence", authorization: <bundle literal>, leader_evidence, specialist_evidence, applied_by, successor_attempt: 2}` (chaves exigidas em `agent_orchestration.py:639-652`; bundle literal como `abandon_run` faz em `gauntlet_runs.py:3105-3160`).
- **Commit 1 (INTENT):** operação `INTENT`; atividade `DISPATCHED → FAILED` com `diagnostic_ref = f"orca:{owner_dispatch}:fenced-by:{operation_id}"` (mesma forma sintética de `:3952`; `FAILED` exige `diagnostic_ref`, `agent_orchestration.py:784`); recurso `REGISTERED → CLOSE_PENDING`, `operation_id` preenchido, receipt `{ref: source_ref + ":release", sha256: source_sha256}` acrescentado a `evidence_manifest.receipts` (forma de `:3929-3931`).
- **Commit 2 (CONFIRMED):** recurso `CLOSE_PENDING → CLOSED`, `last_observation = <release ref>`, `result_acceptance_ref = "fence:" + operation_id`; operação `CONFIRMED` com `result_ref = f"activity-fence/{operation_id}.json"`, `result_sha256 = jcs({...})`, `observation_ref = <release source_ref>` (forma do takeover, `:4258-4275`).
- Guarda de revisão dentro de cada `mutate` (T017, `:4287-4292`) e recheck de `expected_before`; divergência → `FENCE-CAS-CONFLICT`. Operação já `CONFIRMED` com mesma `idempotency_key` → `FENCE-REUSED`. Operação `INTENT` deixada por interrupção → a repetição do mesmo comando executa só o commit 2 (mesma operação, mesmo id; `session-protocol.md:19`). Nenhum receipt/evento novo fora do Store: a operação confirmada e o receipt no recurso são a evidência.

**9. Efeitos nos verbos existentes, sem alterar seu código:** `_continuity_quiescence` (`:3654-3672`) deixa de listar a atividade porque `FAILED` não está no conjunto ativo; `gauntlet-context-takeover` passa em `:4169-4174` se nada mais estiver ativo; `gauntlet-prepare-switch --released-source` idem. `gauntlet-cleanup` vê o recurso como fechado porque o predicado é `CLOSED|REMOVED` com `result_acceptance_ref` não nulo (`:4452-4455`); o checkpoint sucessor não o carrega em `preserved_resources` (`:4064-4065`).

**10. Attempt 2 no contexto sucessor** — `gauntlet-activity --phase prepare` ganha `--attempt N` (int ≥ 1, default 1), substituindo o literal `attempt=1` em `:5990`; `new_activity` já valida `attempt >= 1` (`agent_orchestration.py:797-810`). O sucessor usa **novo** `--activity-id` (a identidade da atividade é imutável e inclui `attempt` e `context_id`, `:1529-1533`; `prepare_activity` só aceita `DECLARED|BOOTSTRAPPING`, `:283-297`) e o **mesmo** input manifest, logo o mesmo `input_sha256`. Nenhum campo novo no schema da atividade; a ligação com a atividade cercada é a operação `activity-fence` (`subject_ids`) e o `diagnostic_ref`.

**11. Testes negativos obrigatórios** (DQ-0006; "regra 11" do payload do líder) em `tests/validate_agent_orchestration_contract.py`, com o padrão de store mockado de `:374-400` e o seam `native_show` de `tests/orchestration_fixture.py:29-46` estendido com uma forma "released" para o especialista; bundle de seis chaves como `tests/validate_gauntlet_converge_contract.py:339-352`:
- positivo: preview e apply concordam; pós-estado `FAILED` + `CLOSED`; takeover em seguida devolve `TAKEOVER-PREVIEW`;
- sem `--authorization`, arquivo ausente, JSON inválido, `decision != APPROVED` → `FENCE-AUTHORIZATION-INVALID`;
- `scope` de outra atividade, de outro contexto e de outro work item → `FENCE-AUTHORIZATION-INVALID`;
- líder `dispatched|running` → `FENCE-LEADER-ACTIVE`; host inconclusivo → `FENCE-EVIDENCE-UNPROVEN`;
- especialista `dispatched|running` → `FENCE-SPECIALIST-ACTIVE`; identidade divergente → `FENCE-EVIDENCE-UNPROVEN`;
- hash divergente → `FENCE-INPUTS-STALE`; replay → `FENCE-REUSED`; atividade `RESULT_RECORDED` ou `deterministic_check` → `FENCE-NOT-ELIGIBLE`;
- em toda recusa, `store.read_snapshot(root).content_sha256` antes == depois (padrão de `:372`);
- fixture do X7: contexto `ACTIVE`, `checkpoint_head=None`, `campaign=None`, atividade `DISPATCHED`, recurso `REGISTERED`; `--attempt 2` aceito em `prepare` no contexto sucessor. Fixture derivada de saída real do Orca, não do código (memória do projeto: fixture mais limpa que a realidade).

**12. Documentação e distribuição:** parágrafo novo em `references/session-protocol.md` logo após a linha 87, nomeando o verbo, as três provas, o não-aceite e o attempt 2; nada em WORKFLOW.md, `ESSENTIAL`, registries, catálogos, Constituição ou assets de workflow. Bump 6.0.30 → 6.0.31 nos oito pontos de `CLAUDE.md` "Distribuição" (dois manifests do plugin, dois marketplaces, `VERSION` do validador, headings de `SKILL.md`, `session-protocol.md` e `README.md`); `python3 tests/run_validators.py` em exit 0 antes e depois (contar pelo marcador `==>`).

**13. Restrições:** somente stdlib; nenhum subprocesso além do transporte Orca já existente (`_leader_boundary`, `:1547-1562`, exige `ORCA_TERMINAL_HANDLE`, senão `LEADER-ADAPTER-UNSUPPORTED`); nenhum byte fora do Store escrito pelo core; nenhum código público existente muda de string; nenhum checkpoint, DAG, receipt ou operação histórica é reescrito.

**14. Riscos e lock-in:**
- `result_acceptance_ref` passa a admitir um valor `fence:<op>` em recurso cuja atividade não tem resultado aceito. É o campo que cleanup (`:4452`) e quiescência (`:3663`) já leem como "fechado com referência"; trocar de campo seria mudança de schema em todo Store. Documentar no protocolo.
- O formato de `scope` (`work_id:context_id:activity_id`) vira contrato para quem assina autorizações; mudar depois invalida bundles guardados.
- A prova do líder é de grau takeover (mais fraca que release); é paridade deliberada com o verbo que vem a seguir. Se o líder estiver `QUIESCING/RELEASING`, a prova ainda vale.
- Dois commits deixam janela `INTENT`; a reconciliação é a repetição do mesmo comando, nunca um segundo `operation_id`.
- Verbo depende do Orca CLI na máquina; sem ele, recusa nomeada, nunca fence "cego".
- Fixture do especialista liberado precisa de `worker-show` real capturado; sem isso o teste positivo prova o código, não o Orca.
```

---

## DELIVERY-MAP.md

```markdown
# DELIVERY-MAP

decomposition-schema: v1

## MOD-001 — Continuidade de contexto: recuperação autorizada de atividade órfã
- module-kind: platform
- responsibility: Decidir quando uma atividade em voo cujo especialista e líder já encerraram pode sair do caminho da sucessão, exigir as provas e a autorização humana exata, registrar o fence e permitir o attempt 2 no contexto sucessor
- boundary: `plugin/skills/grill-with-docs/scripts/grill_workspace.py` (verbo novo, parser, `--attempt` no `gauntlet-activity`); leitura de `grill_core/agent_runtime.py`, `grill_core/attestation.py` e `grill_core/agent_orchestration.py` sem alteração de schema; contratos em `tests/validate_agent_orchestration_contract.py` e `tests/orchestration_fixture.py`; `references/session-protocol.md` e os oito pontos de versão
- depends-on: none

### DU-001 — Fence autorizado, fechamento com receipt e attempt 2
- development-type: platform-devops
- phase: FASE-001
- scope-in: verbo `gauntlet-activity-fence` preview-first com `--apply --expected-sha256`; prova terminal Orca do líder (grau takeover) e do especialista (release exato com identidade igual); `human-authorization/v1` com escopo `work_id:context_id:activity_id`; atividade `FAILED` com `diagnostic_ref` e recurso `CLOSED` com receipt em dois commits CAS; operação `activity-fence` com autorização literal; `--attempt` no `gauntlet-activity prepare`; testes positivo e negativos com Store imutável em recusa; parágrafo no protocolo; bump 6.0.31
- scope-out: SGD-37 (transcript > 16 MiB); SGD-38 (`KeyError` com campanha preenchida e head nulo); prevenção por checkpoint automático; aceite, leitura ou reexecução do resultado órfão; mudança em Constituição, WORKFLOW, ESSENTIAL, registries, catálogos ou schema do Store; alteração de `_continuity_quiescence`, takeover ou prepare-switch
- depends-on: none
- acceptance: fixture do X7 sai do bloqueio por fence → `TAKEOVER-PREVIEW`; os quatro negativos exigidos e os demais listados no PLAN-CONTEXT recusam com código próprio e Store byte a byte igual; preview e apply concordam; `gauntlet-cleanup` vê o recurso como fechado; `python3 tests/run_validators.py` em exit 0; nenhum código público existente muda de string; versão 6.0.31 nos oito pontos e `tests/validate_distribution.py` em exit 0

> IDs are stable within this work item. `module-kind` is one of `domain|platform|cross-cutting`; each DU has exactly one closed development type.
```

---

## DQs propostas

Nenhuma decisão material nova ficou descoberta pelas decisões humanas R-0004 e R-0005; o HOW acima resolve só detalhes de engenharia dentro da opção A. Registro três notas que **não** são DQ, para o líder decidir se viram texto ou ficam como estão:

1. **Alternativas B/C do ADR-0001** foram reconstruídas a partir do código (aquietar automático sem humano; takeover tolerante), porque `DECISION-FRONTIER.md` e `ROUND-LOG.jsonl` registram só a opção A escolhida. Se as opções apresentadas ao humano em R-0005 tinham outro enunciado, o líder substitui os dois parágrafos de "Opções e custos"; a decisão e as consequências não mudam.
2. **"regra 11"** citada no payload não foi localizada em `SKILL.md`, `references/*.md`, Constituição ou `CLAUDE.md`; o item 11 do HOW cumpre a exigência de testes negativos e nomeia a origem como "payload do líder". Se houver fonte canônica, basta trocar a citação.
3. **SemVer do bump**: verbo público novo e flag nova são compatíveis para trás; propus **patch** (6.0.30 → 6.0.31) por paridade com os fixes anteriores (takeover entrou como patch, `fix-continuity-context` handoff), marcado como assunção a confirmar no ciclo executor. Se o líder ler como MINOR (6.1.0), só os oito pontos mudam.

Verificação de formato: os seis blocos acima foram materializados numa cópia temporária do bundle no scratchpad (`bundle-check/`, fora de `.grill/`) e submetidos a `python3 plugin/skills/grill-with-docs/scripts/audit_decisions.py <cópia> --project-root . --json`: `verdict=GO`, `selected-phase=FASE-001`, 0 findings, 0 blockers, exit 0. Os 15 arquivos do input manifest continuam com os sha256 originais e `git status` mostra só o bundle untracked pré-existente.

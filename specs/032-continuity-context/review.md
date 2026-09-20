## Review Report

**Verdict: REQUEST CHANGES**

Source fingerprint: tree `7f5ded772d5ac7203566206085e78b97d15681de6e8e42387ab6854ca315cc3e` / work `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` / plan `a8b9e5b66683ed8128b790e954d4dce3b241eceeba5dd30aff16a1b5cc142dfa`

Casa exatamente com o registrado em `converge.md` (rodada 2) e `verify.md`. Evidência fresca nos dois gates anteriores: Converge `CONVERGED`, Verify `PASS`.

Três revisores read-only, um por dimensão, todos com acesso ao diff `73a90bd..a9a561c`: correção de runtime, qualidade de testes, arquitetura/legibilidade/segurança. Os achados C1 e I1 foram reverificados diretamente pelo coordenador antes de entrarem neste relatório.

---

### O padrão que atravessa os achados

Os três achados mais graves têm a mesma assinatura: **`gauntlet-context-takeover` diverge do irmão `gauntlet-context-resume` exatamente nas garantias**, e não no que entrega. O resume observa a sessão entrante, trava a revisão do store e projeta os recursos do contexto que encerra. A tomada não faz nenhuma das três coisas.

E há uma razão única para isso ter atravessado 1488 testes verdes: **o `mutate()` real do verbo não é exercido por teste algum**. Os casos de takeover em `validate_orchestrator_store_contract.py` chamam `store.transact` com a fixture `CONTEXT_TAKEOVER`, que reimplementa o `mutate()` à mão; o caso do CLI em `validate_agent_orchestration_contract.py` aplica a tomada mas só verifica `state` e `session_ref` do contexto novo, nunca os campos de observação, e nunca executa um comando autorizado como o líder novo.

É o padrão de fixture mais limpa que a realidade, já registrado na memória deste projeto, agora na sua forma mais cara: a fixture não só é mais limpa, ela **é** o objeto sob teste.

---

### Critical Issues

#### C1 — A tomada instala um líder sem observação, e o contexto sucessor nasce inutilizável

`plugin/skills/grill-with-docs/scripts/grill_workspace.py:3739-3741`

O contexto novo é gravado com `"incarnation": None, "observation_ref": None, "observation_sha256": None`. O ambiente prova que o predecessor morreu, mas ninguém observa a sessão **entrante**: o `--session-ref` de quem pede entra no store apenas na palavra dele.

Cenário de falha, verificado:

1. `TAKEOVER-APPLIED` grava o contexto novo como `current_context_id`, estado `ACTIVE`.
2. Qualquer comando com `@_gauntlet_authorized` passa por `_require_current_leader` (`:1629-1632`), que compara `observation_ref`, `observation_sha256` e `incarnation` contra uma observação fresca. `None` nunca casa → `LEADER-AUTHORITY-UNPROVEN`.
3. **14 comandos** carregam esse decorador — entre eles `gauntlet-wave-declare`, `gauntlet-worker-declare`, `gauntlet-converge`, `gauntlet-progress-record`.
4. Não há saída: `TAKEOVER-REUSED` faz short-circuit antes de qualquer escrita, e `gauntlet-context-resume` exige `source.state == "RELEASED"` com operação `APPLIED` (`:3596-3601`), enquanto a tomada deixa `SUPERSEDED`/`CONFIRMED`.

O verbo criado para destravar um work item preso entrega um contexto preso de outra forma, no exato cenário que ele existe para resolver.

O caminho irmão faz certo: `continuity_resume_command` grava `observation_ref`, `observation_sha256` e `incarnation` a partir do `readiness` da sessão entrante (`:3608-3610`).

**Correção**: antes do `mutate`, observar a sessão entrante com `_session_readiness(root, context["runtime"], args.session_ref, work_id=args.work_id)` e gravar os três campos (mais `presentation`) a partir dela, recusando se a observação não concluir. Acrescentar o teste que falta: aplicar a tomada e então executar um comando autorizado como o líder novo.

---

### Important Issues

#### I1 — `mutate` da tomada sem guarda de revisão

`grill_workspace.py:3722-3729`

Todo o veredito — observação, `_continuity_quiescence` (`:3672`), `checkpoint_head` (`:3681`), `bridge` (`:3684-3687`) — é computado a partir do `snapshot` lido em `:3643`, **fora** do lock. O `mutate` revalida só identidade de contexto.

Cenário: na revisão R a quiescência retorna vazia; entre `:3672` e `store.transact` um worker transiciona `DECLARED → PREPARING`, store vai a R+1; o `mutate` roda sobre R+1 e nenhuma checagem dele olha workers. Commit passa. Resultado: `TAKEOVER-APPLIED` onde `TAKEOVER-WORK-ACTIVE` deveria ter disparado, e o líder novo assume sobre worker vivo. A mesma janela vale para `checkpoint_head` mover e para a campanha.

**Correção**: uma linha, idêntica à do resume (`:3588`) — `if document["revision"] != snapshot.revision: raise store.StoreError(store.STATE_DIVERGENCE, ...)`. Cobre quiescência, head e campanha de uma vez.

#### I2 — `expected_sha256` digere a resposta viva e pode tornar `--apply` inalcançável

`grill_workspace.py:3693-3699`, com `observation["digest"]` vindo de `agent_runtime.py:1044`

`expected` inclui o `observation` inteiro, e `digest` é o sha256 dos **bytes crus** da resposta de `worker-show`. Prévia e aplicação são duas invocações separadas do CLI, cada uma com sua própria leitura. Qualquer campo volátil na resposta do coordenador — carimbo de tempo de projeção, liveness recomputada — muda o digest, e o apply recusa com `TAKEOVER-INPUTS-STALE` sem que nada tenha mudado no store. O código de recusa passa a mentir sobre a causa.

O teste não pega porque serve a **mesma** resposta canned nas duas chamadas, byte a byte (`validate_agent_orchestration_contract.py:1169-1173`).

**Correção**: digerir a decisão, não a resposta — `{"verdict": observation["verdict"], "reference": observation["reference"]}`, mais `"revision": snapshot.revision`, que é o que o resume usa. O `digest` continua gravado em `evidence` como prova de sucessão, que é o papel dele.

#### I3 — Recursos do predecessor ficam órfãos, sem verbo que os alcance

`grill_workspace.py:3730-3745` vs `grill_core/agent_orchestration.py:1561-1568`

O `mutate` marca o contexto anterior como `SUPERSEDED` mas não projeta `preserved_resources` nem obrigações de cleanup. `require_authority` exige contexto corrente **e** `ACTIVE`, então `gauntlet-cleanup --context-id <antigo>` recusa com `LEADER-AUTHORITY-UNPROVEN` para sempre. Recursos `kind: session` em `REGISTERED` ficam no store indefinidamente.

**Correção**: espelhar o resume (`:3567-3571`) — computar `retained` e `reconcile` e devolvê-los no payload de `TAKEOVER-APPLIED`, para o sucessor reconciliar sob a própria autoridade.

#### I4 — Os casos de takeover no store testam a fixture, não o produto

`tests/validate_orchestrator_store_contract.py:58` e os três casos em `:497`, `:521`, `:533`

`CONTEXT_TAKEOVER` reimplementa à mão o `mutate()` de `gauntlet_context_takeover_command`. Nenhum dos três chama o CLI. Reverter o `mutate()` real inteiro deixa os três verdes.

Divergências já presentes entre fixture e produto: o real copia `worktree_identity` e `presentation` para o sucessor, a fixture não; o real inclui `checkpoint_id` em `expected_before` sempre, a fixture só com campanha; o real inclui `to_runtime` em `intended_after`, a fixture não; o real tem quatro guardas que a fixture não tem.

**Correção**: manter os casos do store como aceitação de shape do `validate_block` — é o que o comentário deles já declara — mas mover a prova de comportamento para o caso do CLI, asserindo após `--apply` o contexto e a operação reais.

#### I5 — O caso de concorrência não exercita concorrência

`tests/validate_orchestrator_store_contract.py:533`

`store.transact` serializa tudo sob `orchestrator_lock`. Não há CAS perdedor: a segunda thread entra no lock depois do commit da primeira e quem levanta `STATE_DIVERGENCE` é o guard da **própria fixture**. Barrier e `ThreadPoolExecutor` são cerimônia; duas chamadas sequenciais dariam idêntico.

**Correção**: as duas threads chamarem o CLI com o mesmo `expected_sha256`, asserindo que o perdedor recebe `TAKEOVER-CAS-CONFLICT` — o código real. Ou, se a intenção é só o store, renomear para o que o caso de fato prova e chamar sequencial.

#### I6 — Checkpoint sintetizado testado num schema que o produto não emite

`tests/validate_orchestrator_store_contract.py:553`

Usa `ORCHESTRATION_CHECKPOINT` (v1), enquanto `_initial_continuity_checkpoint` emite v2 (`grill_workspace.py:3357`). Além disso, `assertEqual` compara a fixture com os literais que a própria fixture acabou de escrever — tautologia. Há drift de tipo: a fixture usa `development_sequence: {}`, o real emite lista.

**Correção**: trocar para `ORCHESTRATION_CHECKPOINT_V2` e, para a parte de resumabilidade, ler o checkpoint que o `gauntlet-prepare-switch` gravou em vez de construir um à mão.

#### I7 — Cobertura deslocada na troca do prepare-switch

`tests/validate_agent_orchestration_contract.py:274` e `:1071`

A única asserção removida em toda a entrega, e a troca é legítima: FR-006 mudou o comportamento. Mas o ramo de recusa passou a viver só num caso que **stuba `store.read_snapshot`** com um documento que o `validate_block` recusa persistir por qualquer escrita legítima — o próprio docstring admite. `CONTINUITY-CHECKPOINT-MISSING` do prepare-switch passou a ser testado contra estado inalcançável em produção.

O caminho novo só assere `(0, "QUIESCING")`: não verifica que o checkpoint sintetizado foi gravado, que é v2, que `checkpoint_head` aponta para ele, nem que os digests batem.

**Correção**: após o `QUIESCING`, ler o snapshot e asserir `checkpoint_head`, `schema == CHECKPOINT_SCHEMA_V2`, `previous_checkpoint_id is None` e os dois digests contra suas fontes.

---

### Minor Issues

| # | Local | Achado |
|---|---|---|
| M1 | `agent_orchestration.py:28-32` | Comentário afirma que a emissão ainda usa v1 "porque o validador fixa v1". Falso desde T015: os dois emissores usam v2 e o validador foi reescrito. Risco concreto: alguém "corrigir" a emissão de volta. Apontado por dois revisores independentes |
| M2 | `grill_workspace.py:3721,3732` | `leader_advance` avança um passo só: o contexto vai a `SUPERSEDED` mas o líder congela em `RELEASING`, e nenhum verbo volta lá. Como o predecessor está comprovadamente terminal, mapear direto a `RELEASED` |
| M3 | `grill_workspace.py:1543-1548` | `captured["raw"]` é sobrescrito a cada `read()`. Funciona porque há uma leitura só; acumular e recusar extração lateral com mais de uma |
| M4 | `tests/validate_orchestrator_store_contract.py:513-518` | Nenhum teste assere que o `state.json` sobrevive ao takeover (FR-005 ponta a ponta). Minor porque o `mutate()` é estruturalmente incapaz de tocar aquele arquivo. Correção de uma linha: comparar os bytes antes e depois do `--apply` |
| M5 | `tests/validate_checkpoint_contract.py:131` | `CommittedCheckpointContract` herda a classe inteira, então `test_checkpoint_emission_uses_v2_schema` roda duas vezes. Sem dano; pré-existente |
| M6 | `grill_workspace.py:3296-3298` | `DECLARED` fora do conjunto de atividade ativa e recursos pendentes fora de `unknown`. Contido na tomada, mas a mesma função serve o `prepare-switch`, onde o contexto segue vivo. Pré-existente |

---

### Test Quality

O que está **bom**, e merece registro porque é a parte que funcionou:

- o helper `takeover_show()` corrigido tornou os casos genuinamente sensíveis: revertendo `_takeover_observation` para ler o nível de topo, quebram as asserções de `dispatch_status` e `liveness` nos três subTests terminais e o caso de `TAKEOVER-LEADER-ACTIVE` degrada para `TAKEOVER-EVIDENCE-UNPROVEN`;
- cada código de recusa tem caso que o distingue — toda asserção é `assertEqual((status, code), (2, <código exato>))`, nenhum caso aceita "qualquer recusa";
- `test_checkpoint_emission_uses_v2_schema` prova emissão pelo produto: invoca o CLI por subprocess e correlaciona os dois digests com suas fontes no store;
- nenhuma asserção existente foi afrouxada. O diff é `+438/-2`, e as duas deleções são a constante de versão e a asserção trocada por FR-006.

O que está **ruim** é o conjunto I4–I7, já detalhado: a cobertura do verbo novo mede a fixture, não o produto.

### Runtime Correctness

Fora de C1, I1, I2 e I3, verificado e limpo:

- **Fail-closed preservado.** Nenhum caminho autoriza sem prova. `observe_predecessor_termination` nunca levanta: colapsa em `indeterminate`. `not_observable` e todo veredito diferente de `terminal` recusam. Falha de transporte vira `indeterminate` e recusa.
- **`except Exception` amplo**: não engole nada que devesse propagar — envolve só o parse de bytes já em memória, e o resultado `None` é fail-closed. `except agent_runtime.RuntimeError` seria mais honesto, mas não é defeito.
- **Invariantes de transição**: a época sempre cresce; regressão viraria `TAKEOVER-CAS-CONFLICT` sem traceback; tomada dupla concorrente recusa corretamente; `TAKEOVER-REUSED` está antes da observação e retorna sem `transact` — não reobserva nem reescreve.
- **Migração v1→v2**: nenhum leitor espera as chaves antigas num documento recém-emitido. As ocorrências remanescentes de `workflow_sha256`/`constitution_sha256` pertencem ao digest do `WORKFLOW.md` na admissão, domínio distinto. A cadeia é consistente: `previous_checkpoint_id` é agnóstico de schema e `checkpoint_sha256` é recomputado sobre o próprio documento, então um v2 encadeado sobre um v1 valida. `_continuity_checkpoint` faz `deepcopy` do head e preserva o schema dele, então o checkpoint de troca nunca muda de versão no meio.

### Architecture

Direção de dependência **preservada**: `grill_core/*` continua sem importar `grill_workspace`, e `observe_predecessor_termination` recebe `read` injetado em vez de tocar disco.

Sobre o ponto levantado pelo converge — `_takeover_observation` chamando `agent_runtime._object`, helper privado: o veredito dos revisores, que endosso, é que **promover `_object` a nome público resolveria o sintoma errado**. A causa é que `observe_predecessor_termination` já calcula `status` e `liveness` internamente e os descarta, obrigando o CLI a recapturar o `stdout` por canal lateral e reparsear. A forma correta é a função devolver `{"verdict", "reference", "digest", "dispatch_status", "liveness"}`, o que elimina de uma vez o reparse, o canal lateral `captured` e o acoplamento ao nome privado. Enquanto isso, chamar `_object` é aceitável e não bloqueia.

Débito técnico registrado, a fazer junto com as correções acima porque tocam a mesma fronteira:

- a closure `read` de `_takeover_observation` (`:1526-1547`) é cópia quase verbatim da de `_leader_boundary` (`:1508-1522`), com o parâmetro `runtime` recebido e **nunca usado** — resíduo da cópia. Extrair uma leitura comum; com a mudança acima, `_takeover_observation` desaparece inteira;
- o dicionário de checkpoint de ~25 chaves vive em dois pontos de emissão, e o rename v1→v2 teve de ser aplicado à mão nos dois. O risco não é hipotético: errar um deixaria o store com schemas misturados, que `_checkpoint` aceita sem ruído. Um construtor único em `grill_core` é lógica pura e cabe no critério que rege `triage.py`;
- a tabela decisória do takeover é lógica pura sobre uma observação já lida, e pertence a `grill_core` pelo mesmo critério. Fazer junto com o item acima, não em rodada separada.

### Security

Verificado e limpo:

- **sem injeção**: o ref do predecessor passa por `re.fullmatch(r"orca:ctx[-_][A-Za-z0-9_-]+")` antes de virar `dispatch_id`, e `subprocess.run` recebe lista de argv, sem shell;
- **timeout presente** nos dois caminhos de leitura;
- **sem escrita fora do caminho esperado**: o verbo não escreve arquivo algum, só o store;
- **ausência de `@_gauntlet_authorized` no verbo novo é correta por desenho** — a sessão entrante não é o líder corrente, e exigir o fence tornaria o verbo impossível. A autorização vem da observação do ambiente, do compare-and-swap e da época;
- **paridade prévia/aplicação**: a prévia levanta as mesmas recusas do apply.

A ressalva de confiança está em C1: hoje o `--session-ref` entrante é aceito sem observação. A correção de C1 fecha isso.

### Performance

Nenhum achado. O verbo faz uma leitura de transporte com timeout, uma transação de store e nenhum laço sobre coleção que cresça com o número de work items.

---

### Constitution References

Nenhum conflito constitucional descoberto. C1 é defeito funcional, não violação de cláusula: o fail-closed constitucional está preservado, já que o caminho falho **recusa** em vez de autorizar indevidamente.

---

### Final Recommendation

**REQUEST CHANGES.**

Obrigatório antes do ship:

1. **C1** — observar a sessão entrante e gravar os três campos de observação, mais o teste que executa um comando autorizado como o líder novo;
2. **I1** — guarda de revisão no `mutate`;
3. **I2** — digerir a decisão em vez dos bytes da resposta viva;
4. **I3** — devolver `retained` e `reconcile` no payload da tomada;
5. **I4–I7** — mover a prova de comportamento do takeover para o caminho que exerce o `mutate()` real, corrigir o schema do caso do checkpoint sintetizado e completar as asserções do prepare-switch;
6. **M1** — corrigir o comentário que contradiz o código, porque ele convida a reverter T015.

Recomendado na mesma rodada, por tocarem a mesma fronteira: `observe_predecessor_termination` devolver `dispatch_status` e `liveness` (elimina reparse, canal lateral e acoplamento a nome privado), extração da leitura comum e remoção do parâmetro morto.

Registráveis como débito: construtor único do checkpoint, mudança da tabela decisória para `grill_core`, M2–M6.

Próximo passo: corrigir, rodar `/speckit.converge`, depois `verify` e `review` de novo.

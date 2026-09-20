## Review Report — R1

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

---

## Review Report — R2

**Verdict: REQUEST CHANGES**

Source fingerprint: tree `fb14944628e0b1d23a7c804b92e64343f42251b113085f5a1433a97e05606b3f` / work `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` / plan `bf2b427c65cbe335332313d74a836514488b7e5c896291828e92242e0d1526ea`

Casa com `converge.md` (rodada 4) e `verify.md` (R2). Evidência fresca: Converge `CONVERGED`, Verify `PASS`.

Três revisores read-only, com mandato explícito de caçar **defeito novo introduzido pela correção**, não de reconferir o que a rodada 4 já verificou fechado. Os achados R2-1, R2-2 e R2-4 foram reverificados diretamente pelo coordenador.

### O que a Phase 7 fechou de verdade

Registro primeiro o que funcionou, porque é substancial. O Critical do R1 está morto, e a cobertura que o deixou passar foi corrigida de fato, não de forma:

- o caso novo executa `gauntlet-step-enter` com o `--session-ref` da sessão entrante e exige saída 0. A cadeia foi verificada: o verbo é `@_gauntlet_authorized`, o decorador chama `_session_readiness` e depois `_require_current_leader`, que levanta `LEADER-AUTHORITY-UNPROVEN` na divergência. Com os três campos nulos, reprova sempre;
- a sensibilidade foi confirmada por reversão temporária, e o caso reprova **mesmo com as asserções de campo removidas**, deixando só o comando;
- as asserções não são vácuas: `presentation["session_identity"]` carrega `owner_dispatch`, que diverge entre predecessor e sessão entrante;
- os casos do store que permanecem sobre fixture ficaram honestos no nome e no cabeçalho, que declara "None of them would fail if mutate() were reverted";
- nada foi afrouxado. As 33 remoções são o bloco de threads e o checkpoint v1; o diff **aperta** em dois pontos.

### Um erro do coordenador, registrado

A rodada 4 do converge deu **G6 por fechado indevidamente**, e quem o pegou foi o revisor de correção. Verifiquei que `preserved_resources` e `operations_to_reconcile` passaram a ser devolvidos; não verifiquei que alguém os consome. Não consome. Presença de código não é cumprimento de requisito, e a lição vale além deste caso.

---

### Important Issues

#### R2-1 — `worktree_identity` é herdada sem reverificação, e o T021 congelou isso como contrato

`grill_workspace.py:3774` · `tests/validate_agent_orchestration_contract.py:1236`

A tomada copia `source["worktree_identity"]` sem conferir nada. O irmão `continuity_resume_command` (`:3544-3546`) chama `_continuity_identity` e recusa com `CONTINUITY-STATE-DIVERGENCE` quando a identidade viva diverge da selada — e essa identidade inclui `branch` e `phase` (`:3282-3290`).

Cenário: o predecessor roda `prepare-switch`, carimba a identidade e fica `QUIESCING`. A sessão morre. O humano troca de branch na worktree, que é o comportamento normal depois de uma sessão morrer. A sessão nova roda a tomada; `LeaderBoundary.observe` garante `terminal.worktreePath == root`, mas **não olha branch**. O sucessor herda uma identidade que mente sobre a árvore viva, e todo `continuity-resume` posterior bate em divergência **para sempre**, porque não existe verbo de re-carimbo no core.

O agravante é a escolha de onde verificar: a tomada é justamente o caminho de recuperação, onde o ambiente tem a maior chance de ter derivado, e é o único que não verifica. A Phase 7 não criou a herança, mas T021 a transformou em asserção de contrato, o que a congela.

**Correção** (~4 linhas, o helper já existe): antes do cálculo de `expected`, derivar a identidade viva com `_continuity_identity`, recusar com um código próprio quando divergir da carimbada, e gravar a identidade derivada no sucessor em vez da cópia. O efeito colateral — a tomada passa a recusar em HEAD destacado — é o mesmo que o resume já aceita.

#### R2-2 — G6 não fecha: `preserved_resources` é relatório sem consumidor, e o cleanup do sucessor reporta sucesso falso

`grill_workspace.py:3721-3724` e `:3788` · `:3850-3864` · `grill_core/agent_orchestration.py:966`, `:1563-1569`

O comentário de T019 diz que os recursos são entregues ao sucessor "to be reconciled under its own authority". Não há caminho no core que os reconcilie. Os dois únicos consumidores filtram pelo contexto **corrente**:

- `gauntlet_cleanup_command:3850` pula todo recurso cujo `origin_context_id` difira do contexto corrente. Depois da tomada, o corrente é o sucessor e todo recurso retido tem a origem no contexto `SUPERSEDED`;
- o caminho de aceitação depende de `accept_activity`, que recusa `CONTEXT-FENCED` quando a atividade pertence a outro contexto.

E o desfecho é pior que a inércia: com `results == []`, o `verdict` em `:3862` avalia `any()` sobre lista vazia e cai em **`CLEANED`, exit 0**. O sucessor recebe sucesso enquanto o recurso segue aberto no store. O defeito que o R1 descreveu continua inteiro, agora com um relatório que sugere o contrário.

Nota de escopo: o `CLEANED` sobre lista vazia é **pré-existente**, não introduzido pela Phase 7.

**Correção**: uma das duas, explicitamente escolhida. (a) fazer o `cleanup` aceitar recursos cuja origem esteja na cadeia `predecessor_context_id` do contexto corrente — o `continuity_ref` já dá a cadeia auditável; ou (b) reabrir G6, corrigir o comentário e o `converge.md` para "projetado para auditoria; reconciliação não implementada", e registrar o resto como trabalho próprio. Em qualquer dos dois, `verdict` com `results == []` no ramo selecionado não pode ser `CLEANED`.

#### R2-3 — `snapshot.revision` no digest anula o objetivo de T018 e é redundante com a guarda de T017

`grill_workspace.py:3705-3708` vs `:3749-3750`

T018 tirou a `observation` inteira do `expected` porque o digest dos bytes vivos era volátil entre as duas invocações. Pôs no lugar `snapshot.revision`, que é a revisão **global** do documento único: `transact` carimba `current.revision + 1` no documento todo, não por work item. Qualquer escrita no store, de qualquer work item, invalida a prévia.

E existe um gerador rotineiro dessa escrita: o próprio `@_gauntlet_authorized` faz `store.transact` sempre que a apresentação observada diverge da persistida (`:3227-3233`).

Cenário: o operador roda a prévia; antes do apply roda qualquer verbo autorizado, ou outra sessão toca outro work item; a revisão sobe; o apply recusa `TAKEOVER-INPUTS-STALE` sem que nada da decisão tenha mudado. `TAKEOVER-INPUTS-STALE` volta a mentir sobre a causa — exatamente o que T018 existia para corrigir.

A redundância é o ponto: a guarda de `:3749` já garante, **sob o lock**, que o store não se moveu entre a leitura e o commit. Ela é estritamente mais forte e mais precisa.

**Correção**: remover `"revision": snapshot.revision` do `expected`. A segurança fica intacta. O resume tem o mesmo padrão, mas paridade não é justificativa.

#### R2-4 — T019 entrou sem nenhuma asserção

`grill_workspace.py:3721-3726` e `:3777-3778`

Nenhum teste assere `preserved_resources` ou `operations_to_reconcile`. Reverter as duas compreensões para `{}`, ou remover as chaves do retorno, passa verde nos 1488 testes. É o mesmo padrão que deixou o Critical do R1 atravessar a suíte — agora na correção do próprio achado que o R1 levantou.

**Correção**: no laço terminal de `test_context_takeover`, registrar um recurso e uma operação em estado retido antes do `--apply` e asserir que o payload os contém.

#### R2-5 — T017 entrou sem teste; `TAKEOVER-CAS-CONFLICT` não é exercido

`grill_workspace.py:3749-3752`

O código de recusa só aparece num comentário que explica por que o caso antigo foi removido. O irmão `CONTINUITY-CAS-CONFLICT` tem caso próprio. A renomeação do caso falso de concorrência estava certa, mas o buraco ficou aberto.

**Correção**: o padrão já existe no arquivo — `mock.patch.object(store_module, "read_snapshot", ...)` com uma revisão defasada faz o `mutate` levantar e o CLI devolver o código real.

#### R2-6 — O teste do store importa um helper privado do CLI que toca disco

`tests/validate_orchestrator_store_contract.py:579`

A troca em si foi boa: o caso anterior era tautológico. Mas `_initial_continuity_checkpoint` chama `_cleanup_checkpoint_projection(root, work_id)` (`grill_workspace.py:3354`), que **lê disco**. O contrato do store passou a exercitar I/O do CLI e a travar um helper privado de outro módulo como API de facto — o mesmo pecado de `agent_runtime._object`.

**Correção**: mover o emissor para `grill_core/agent_orchestration.py`, recebendo as obrigações de limpeza já lidas pela fronteira do CLI; o teste passa a importar só `grill_core`.

#### R2-7 — O cabeçalho da fixture omite uma divergência de tipo

`tests/validate_orchestrator_store_contract.py:49-70`, `:73`, `:544-545`

O cabeçalho lista corretamente quase todas as divergências, inclusive as da Phase 7. Falta uma: `evidence["liveness"]` é a string `'exited'` na fixture e asserida como literal, enquanto o produto grava `dict` com `verdict` e `source`, ou `None`. `agent_orchestration.py` não valida `liveness`, então o `validate_block` aceita e o teste congela um formato que emissor nenhum produz.

É o mesmo gênero de fixture mais limpa que a realidade que originou o Critical, dentro do próprio cabeçalho que existe para documentar essas divergências.

---

### Minor Issues

| # | Local | Achado |
|---|---|---|
| m1 | `grill_workspace.py:3697`, `:3757` | `operation_id` e `new_context_id` derivam da `observation` inteira, com `digest` volátil, mas `expected` não cobre mais esses bytes — dois apply com o mesmo `expected_sha256` geram ids diferentes e a guarda anti-duplo-write nunca dispara. Derivar de `expected`, que já é determinístico |
| m2 | `grill_workspace.py:3709-3710` | A prévia paga o custo de `readiness` e descarta: não devolve `presentation` nem o que será preservado, enquanto o resume devolve. Uma linha |
| m3 | `contracts/context-takeover.md:9` | A prévia agora pode recusar com códigos fora da família `TAKEOVER-*` (`LEADER-ADAPTER-*`, `STYLE-*`), vindos da observação da sessão entrante. O contrato só cita `TAKEOVER-*` |
| m4 | `grill_workspace.py:3629-3790` | A função está com 162 linhas, contra 106 do resume. Abaixo do teto de 200, mas acima do limiar prático. Corte sugerido de ~27 linhas: projeção para o core, bridge e operação em helpers |
| m5 | `tests/validate_orchestrator_store_contract.py:69` | Comentário morto: "used here to drive the concurrent-takeover test below", removido no mesmo commit |
| m6 | `tests/validate_agent_orchestration_contract.py:1204-1206` | `incarnation` é constante na fixture, então a asserção de igualdade não distingue; quem carrega a prova é `observation_ref`/`observation_sha256`. Vale um comentário |
| m7 | `tests/validate_orchestrator_store_contract.py:585-589` | O emissor é chamado com `state={}`, o que prova o default e não a projeção do estado corrente |

---

### Test Quality

Corrigida de verdade, com as duas lacunas de R2-4 e R2-5. O ganho real é que a prova de comportamento migrou para o caminho que exerce o produto, e a sensibilidade passou a ser verificada por reversão em vez de presumida. As ressalvas estão nos achados acima.

### Runtime Correctness

Verificado e limpo fora dos achados:

- **fail-closed íntegro** nos quatro caminhos novos. Nenhum autoriza sem prova, nenhum mascara recusa. A guarda de revisão inclusive tornou seguros acessos diretos que antes podiam levantar `KeyError`;
- **a prévia sem efeito colateral**: nada escreve no store nem em disco, e o teste confere `content_sha256` inalterado nos dois modos;
- **a prévia pode recusar onde antes passava, e isso é correto** — o apply correspondente instalava um líder que todo comando autorizado rejeitava depois. A prévia mentia antes;
- **`retained` e `reconcile` são consistentes no commit** graças à guarda; o payload é pré-tomada, mas equivale ao pós, porque a operação de sucessão nasce `CONFIRMED` e cai fora do filtro;
- **nenhum consumidor assume a apresentação do predecessor**; a mudança conserta o único que comparava.

### Architecture

Direção de dependência preservada no produto: `grill_core` continua sem importar `grill_workspace`. A contaminação está no teste (R2-6).

Sobre a convergência entre a tomada e o resume, o veredito é que **só um dos quatro blocos deve virar abstração comum**: a projeção de recursos, que é lógica pura, sem disco e sem `grill_workspace`, e cabe no critério de `triage.py`. Os outros três não devem convergir, e isso é decisão e não preguiça: o `expected` do resume digere o `readiness` e o da tomada deliberadamente não, por causa de T018. Uma função compartilhada de digest forçaria as duas semânticas a se alinharem, e o alinhamento errado é o bug de T018 de volta. A diferença deve ser comentada nos dois lados, não escondida atrás de um helper.

Débito registrado, não bloqueante: `observe_predecessor_termination` devolver `dispatch_status` e `liveness`; extração da leitura comum e remoção do parâmetro morto; construtor único do checkpoint; tabela decisória para `grill_core`.

### Security

Sem regressão, e a mudança de autorização foi auditada a fundo:

- **a sessão entrante não forja a prontidão.** `LeaderBoundary.observe` correlaciona dispatch, worker, terminal, recurso de terminal e projeção entre si, exige que o handle do terminal seja o do processo chamador, que o caminho da worktree seja a raiz, que a liveness venha de `agent_status`, que a capacidade não esteja revogada, e reobserva ao final. Do chamador vem só o `session_ref`, que seleciona um dispatch — não afirma nada;
- **auto-tomada é impossível**: exige o predecessor terminal e a entrante viva ao mesmo tempo;
- **`preserved_resources` não expõe nada indevido**: sai só no apply, quando a sessão já é líder e lê o store de qualquer modo;
- ressalva **pré-existente**, não desta entrega: `ORCA_CLI_COMMAND` permite apontar o adapter para um binário arbitrário, o que vale para toda verificação de líder do projeto.

### Performance

Nenhum laço cresce com o número de work items. O custo novo é de transporte: a prévia passou de uma leitura para quatro a seis subprocessos com timeout de 20s cada, porque `_session_readiness` faz `observe`, `worker-read` e `observe` de novo. Prévia mais apply ficam em oito a doze, com pior caso teórico na casa dos 200s. É o preço da prévia honesta e vale a pena, mas fica registrado o teto.

---

### Constitution References

Nenhum conflito constitucional descoberto. R2-1 e R2-2 são defeitos funcionais; o fail-closed constitucional está preservado, porque os caminhos falhos recusam ou inertizam, nunca autorizam indevidamente.

---

### Final Recommendation

**REQUEST CHANGES.**

Obrigatório antes do ship:

1. **R2-1** — derivar e verificar a identidade viva na tomada, gravando a derivada no sucessor. O dano hoje é irrecuperável sem editar o store à mão, e o diff é pequeno;
2. **R2-2** — decidir explicitamente entre reconciliar de verdade ou reabrir G6 e corrigir o registro. A terceira via, deixar como está, não existe: o comentário e o `converge.md` afirmam o que o código não faz. Em qualquer caso, `CLEANED` sobre lista vazia precisa deixar de ser sucesso;
3. **R2-3** — remover `snapshot.revision` do digest;
4. **R2-4** e **R2-5** — cobrir T019 e T017, que entraram sem teste;
5. **R2-6** e **R2-7** — mover o emissor para o core e completar o cabeçalho da fixture.

Registráveis como débito: m1 a m7 e os quatro itens de arquitetura já listados.

Próximo passo: corrigir, rodar `/speckit.converge`, depois `verify` e `review` de novo.

---

## Review Report — R3

**Verdict: REQUEST CHANGES**

Source fingerprint: tree `3c9790ce7164e66488bdf2fa0badcb47d24579d4520c4cf2a39b6a8d3dc70106` / work `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` / plan `4cbd57c9960a4a70dff68e939125c308eafab6216cff10f013a567d1e58514ad`

Casa com `converge.md` (rodada 6) e `verify.md` (R3). Converge `CONVERGED`, Verify `PASS`.

**Escopo desta rodada**: duas dimensões, correção de runtime e qualidade de cobertura. Arquitetura, segurança e performance **não** foram reexaminadas de forma independente, porque o diff da Phase 8 não move fronteira de módulo nem superfície de autorização — as mudanças são duas guardas, uma remoção de campo de digest, um comentário e casos de teste. Os achados dessas dimensões no R2 foram endereçados ou registrados como débito. É decisão de escopo, e fica declarada.

### A frase que resume a rodada

Do revisor de correção: *"O problema da Phase 8 é o sentido oposto: fecha demais, não de menos."*

As duas guardas que a Phase 8 acrescentou para impedir estados ruins passaram a impedir também estados legítimos — e ambas de forma **permanente**, porque o core não tem verbo de re-carimbo nem de reconciliação. O remédio virou veneno nos dois casos.

---

### Critical Issues

#### R3-1 — `phase` dentro da identidade comparada torna a tomada impossível no caso normal

`grill_workspace.py:3716-3721`, com `:3289`

`_continuity_identity` inclui `phase`, derivada de `state["active_phase"]` ou, na falta dela, de `development.current_step`. **Ambas avançam durante a vida de um contexto**: `current_step` a cada etapa do WORKFLOW, `active_phase` a cada fase do roadmap fechada.

Cenário: o contexto é criado por `continuity-resume` em `implement-parallel` e a identidade carimbada fixa `phase="implement-parallel"`. O ciclo progride para `converge`. A sessão morre. A tomada deriva `phase="converge"`, compara com o carimbo, diverge, e recusa com `TAKEOVER-IDENTITY-DIVERGENT`. **Permanentemente**: o campo só é reescrito por uma tomada bem-sucedida, e não há verbo de re-selagem.

O contraste com o resume é o ponto: o resume aplica a mesma comparação, mas a janela entre o carimbo do `prepare-switch` e o resume é quiescente por construção — o contexto está `QUIESCING` e ninguém avança etapa. Na tomada, a janela é a vida inteira da sessão. **O mesmo predicado é aperto num caso e veneno no outro.**

Medição no repositório: metade dos work items presentes não tem `active_phase` e cai no fallback para `current_step`, que muda a cada etapa.

**Correção**: comparar apenas o subconjunto invariante — `project_id`, `work_id`, `du`, `git_common_dir`, `real_path` e, se permanecer, `branch`. `phase` continua gravada na identidade derivada, porque o schema exige as sete chaves, mas deixa de ser predicado de recusa.

---

### Important Issues

#### R3-2 — A guarda não cura o defeito que o próprio comentário dela promete curar

`grill_workspace.py:3700-3721`

O comentário de T023 motiva a guarda com o cenário: a sessão morre, alguém troca de branch, o sucessor herda identidade que mente, e *toda retomada posterior é recusada para sempre*. Mas `branch` está **dentro** do conjunto comparado. Nesse exato cenário a tomada agora recusa.

Antes o deadlock acontecia no `prepare-switch`; agora acontece na tomada. **Mudou de lugar, não desapareceu.** O re-carimbo só ocorre no ramo `sealed is None`, que não é o cenário descrito.

**Correção**: decidir explicitamente. Ou `branch` é re-carimbável na tomada — e então sai do predicado junto com `phase`, que é a leitura coerente com a tomada ser o caminho de recuperação —, ou o comentário para de prometer uma cura que o código não entrega e o core ganha um verbo de re-selagem. A terceira via, manter os dois, deixa o único remédio sendo editar o store à mão.

#### R3-3 — `candidates` conta não-candidatos e bloqueia a limpeza legítima do sucessor

`grill_workspace.py:3886-3916`

O `candidates += 1` está antes de **todos** os filtros, inclusive o que compara `origin_context_id`. Conta, portanto, recursos de **outros** contextos e recursos sem `activity_id`.

Cenário, que é exatamente o do commit que introduziu a guarda: a tomada acontece; o contexto anterior fica `SUPERSEDED` com um recurso aberto; o mesmo commit declara, em T026, que reconciliar esse recurso **não é implementado**. O sucessor não possui recurso algum. `gauntlet-cleanup --context-id <sucessor>` conta 1 candidato — o recurso do predecessor —, produz zero resultados, e recusa. **Para sempre**, porque aquele recurso nunca pode ser fechado. O sucessor perde a limpeza do próprio contexto por causa de um recurso que não pode tocar.

**Esta falha é de instrução minha, não do worker.** Eu devolvi a primeira versão da guarda por estar larga demais e pedi que contasse "candidatos antes dos filtros". O worker seguiu ao pé da letra. A instrução é que estava errada: "antes dos filtros" inclui o filtro de contexto, que é justamente o que deveria filtrar. A guarda que pedi para eliminar um sucesso falso criou um bloqueio permanente na direção oposta.

**Correção**: o buraco original é de **relato**, não de autorização. Contar apenas o que a seleção deveria ter alcançado e, para o resto, relatar em vez de recusar — devolver os recursos retidos noutro contexto no payload e deixar o veredito sair de `CLEANED` quando existirem. O chamador deixa de ler sucesso sobre recurso ainda preso, sem travar a limpeza do contexto corrente.

#### R3-4 — A guarda de `candidates` não tem teste nenhum

`grill_workspace.py:3914`

Verificado por execução: substituindo a guarda por `pass` numa cópia do repositório, a suíte inteira passa. A correção de T025 entrou **exatamente no padrão que as duas rodadas anteriores pegaram** — correção sem asserção que a sustente.

O único `RESOURCE-IDENTITY-DIVERGENT` testado hoje usa o seletor `--activity-id` e é recusado bem antes, pelo check de posse da atividade; nunca alcança o contador.

**Correção**: dois casos curtos, no arquivo que já tem a fixture pronta — candidatos sem alcance recusando, e zero candidatos seguindo como sucesso. Sem o segundo, a guarda poderia ser alargada de volta para `selected and not results` sem reprovar nada.

#### R3-5 — Um comentário promete cobertura que não existe

`tests/validate_orchestrator_store_contract.py:596`

O caso renomeado removeu a asserção sobre `development_sequence`, `current_step`, `accepted_outputs` e `accepted_executions`, e o comentário afirma que isso é exercido via `gauntlet-prepare-switch` no contrato de orquestração. **Não é**: o caso do CLI assere schema, identificadores, ausência de predecessor e os dois digests — nada sobre o estado projetado.

E o campo é permissivo: `validate_block` aceita `dict` **ou** `list` em `development_sequence`, então um emissor que regredisse ao formato antigo sob schema novo passaria na suíte inteira.

**Correção**: uma linha no caso do CLI, sobre o checkpoint lido de volta do snapshot.

---

### Minor Issues

| # | Local | Achado |
|---|---|---|
| m1 | `grill_workspace.py:3715-3716` | A tomada passou a depender de git vivo e de disco justamente no caminho de recuperação: HEAD destacado, stash com untracked (que muda `project_id`, defeito já registrado na memória do projeto) e bundle ausente viram recusas novas. Mitiga junto com R3-1 e R3-2, tirando `phase` e `branch` do predicado |
| m2 | `grill_workspace.py:3717-3721` | `sealed is None` aceita árvore que o predecessor nunca usou: o contexto inicial nasce sem carimbo, e o único pino é `LeaderBoundary` exigir que a worktree seja a raiz — o que prova onde a **nova** sessão roda, não onde o predecessor rodava. Estreito e sem remédio barato; registrar como limitação |
| m3 | `grill_workspace.py:3694` vs `:3808` | O `campaign_bridge` ainda usa a cópia do predecessor enquanto o contexto sucessor grava a derivada. Quando `sealed is None`, o mesmo registro de operação carrega duas afirmações diferentes sobre a mesma sucessão. Inerte — nada compara as duas —, mas é inconsistência de auditoria. Correção de uma linha: derivar antes do bloco do bridge |
| m4 | `tests/validate_orchestrator_store_contract.py:611` | `assertRaises(store.StoreError)` sem asserir o código. Verificado que hoje a recusa é a certa, mas qualquer divergência futura manteria o caso verde pelo motivo errado |
| m5 | `tests/validate_orchestrator_store_contract.py:86` | `liveness: None`, que o produto devolve quando a resposta não traz liveness, não tem caso. É a outra metade do tipo real |

---

### Test Quality

A cobertura de T027 é **boa, e é o modelo do que faltava** nas rodadas anteriores:

- `work-projection` semeia o que deve entrar e o que **não** deve, e assere por igualdade exata dos dicionários, de modo que a ausência é verificada e não só a presença. A reversão que remove os filtros foi executada e reprova;
- `work-cas` acerta o seam: o patch incide no ponto de leitura fora do lock, a prévia é computada antes, e há asserção de que o store não se moveu. Verificado por execução que, sem a guarda, a tomada **aplica** — logo a recusa vem do caminho verdadeiro e não de um acidente;
- a troca de `liveness` para mapa eliminou a divergência de tipo em vez de documentá-la, e a asserção literal correspondente foi atualizada. Ganho líquido.

As falhas são R3-4 e R3-5: a guarda de T025 sem teste, e uma asserção perdida cuja substituta foi prometida em comentário mas não existe.

### Runtime Correctness

Fora dos achados, verificado e limpo:

- **gravar a identidade derivada no sucessor é seguro**: nenhum leitor a jusante compara a identidade do sucessor com a do checkpoint selado; resume e `prepare-switch` re-derivam ao vivo;
- **a remoção de `snapshot.revision` do digest não reabre janela**: todo fato do apply é re-derivado na própria invocação, sob a guarda de revisão. Ressalva de texto, não de código: o comentário diz que a guarda é "estritamente mais forte" que o campo removido, mas ela cobre **intervalo diferente** — leitura até commit do apply, não prévia até apply. A conclusão se sustenta porque tudo é re-derivado, não porque uma guarda subsuma a outra;
- **fail-closed íntegro**: todo caminho novo sai por recusa com código próprio, e arquivo ausente vira recusa e não traceback.

---

### Constitution References

Nenhum conflito constitucional descoberto. R3-1 e R3-3 são defeitos funcionais de disponibilidade, não de segurança: os caminhos falhos **recusam**, nunca autorizam indevidamente.

---

### Final Recommendation

**REQUEST CHANGES.**

Obrigatório antes do ship:

1. **R3-1** — tirar `phase` do predicado de comparação;
2. **R3-2** — decidir sobre `branch`: sai do predicado, ou o comentário para de prometer a cura e o core ganha re-selagem. Não manter as duas coisas;
3. **R3-3** — contar como candidato só o que a seleção deveria alcançar, e relatar o resto em vez de recusar;
4. **R3-4** — cobrir a guarda nos dois lados: candidatos sem alcance recusando, zero candidatos seguindo como sucesso;
5. **R3-5** — a asserção de uma linha sobre o estado projetado.

Registráveis como débito: m1 a m5, mais os itens já listados em R1 e R2.

Próximo passo: corrigir, rodar `/speckit.converge`, depois `verify` e `review` de novo.

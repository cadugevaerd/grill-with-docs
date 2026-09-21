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

---

## Review Report — R4

**Verdict: REQUEST CHANGES**

Source fingerprint: tree `0273d47dec3e312f96965eb4c0c68c30db4c1321bc9dc02aa8d05671fce4d7bc` / work `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` / plan `429ec68db32c0072f5cba1b12d36067ee102b4dcbb84d66b5fc046df60564c37`

Casa com `converge.md` (rodada 8) e `verify.md` (R4). Converge `CONVERGED`, Verify `PASS`.

Duas dimensões revisadas, correção de runtime e qualidade de cobertura, ambas com mandato de caçar defeito **novo**. Os dois Critical foram reverificados pelo coordenador. O revisor de cobertura rodou todos os experimentos em cópia de scratchpad, sem tocar o repositório.

### O padrão, agora inequívoco

Quatro rodadas, quatro `REQUEST CHANGES`, e a mesma forma em todas: **a correção fecha o caso que examinou e abre o vizinho**.

| Rodada | O que a correção anterior fez |
|---|---|
| R1 | O verbo entregava contexto inutilizável |
| R2 | A correção fez a tomada *parecer* com o resume sem herdar as garantias dele |
| R3 | As guardas novas fechavam demais, criando bloqueio permanente |
| R4 | A reabertura fechou o ramo por contexto e deixou o ramo por atividade quebrado |

A raiz é comum aos dois Critical desta rodada: **`gauntlet_context_takeover_command` e `gauntlet_cleanup_command` vêm sendo corrigidos isoladamente, sem tratar os irmãos que compartilham a mesma lógica**. O predicado mudou na tomada mas não no `prepare-switch` nem no `continuity-resume`; o filtro mudou no ramo de contexto mas não no de atividade.

---

### Critical Issues

#### R4-1 — O filtro de contexto rebaixa também o ramo por atividade

`grill_workspace.py:3903-3918`, com o filtro de seletor em `:3920`

O `retained.append` acontece **antes** de qualquer discriminação por seletor. O filtro de `activity_id` só aparece duas linhas depois. Verificado no código.

Cenário: depois da tomada, o sucessor aceita um especialista e chama `gauntlet-cleanup --context-id <sucessor> --epoch N --activity-id A`. Todos os recursos de `A` fecham corretamente. Existe um recurso `session` aberto do predecessor. Hoje: `retained` não-vazio rebaixa o veredito para `PRESERVED`, exit 2. Antes da Phase 9: exit 0.

E é **permanente**, porque T026 declara que reconciliar recurso do predecessor não é implementado. O ramo por atividade vira bloqueio eterno depois de qualquer tomada.

Nenhum teste cobre a combinação: o caso novo exercita só o ramo por contexto, e o caso pré-existente exercita `--activity-id` sem recurso alheio.

**Correção**: escopar a coleta de `retained` ao seletor — só coletar quando não houver atividade selecionada, ou exigir que o recurso pertença à atividade pedida.

#### R4-2 — A guarda de identidade da tomada não tem cobertura de nenhum lado

`grill_workspace.py:3730-3732`

`grep -rn "TAKEOVER-IDENTITY-DIVERGENT" tests/` devolve **zero ocorrências**; confirmado pelo coordenador. O revisor apagou o `raise` inteiro numa cópia — guarda deletada, não relaxada — e a suíte fechou 37/37 verde.

A distinção que importa: o caso `work-restamp` cobre o lado da **aceitação**. As quatro reversões relatadas provam que a guarda não pode ser **alargada de volta**; não provam que ela **existe**. Com o `raise` removido, uma tomada com `project_id`, `real_path` ou `git_common_dir` divergentes é aceita e carimba o sucessor com identidade de outra árvore, sem nada reprovar.

É o mesmo padrão que a própria Phase 9 nomeia no docstring do caso de limpeza — "os dois lados importam" — aplicado ali e esquecido aqui, justamente na guarda que T030 editou.

**Correção**: um caso irmão do `work-restamp`, no mesmo método, movendo um campo **estrutural** em vez de fase e branch. O mais barato é reescrever `real_path` no carimbo do contexto selado, direto no store, e exigir a recusa mais a verificação de que nada foi escrito.

---

### Important Issues

#### R4-3 — Correção assimétrica: `phase` e `branch` saem do predicado da tomada mas continuam sendo gravados e comparados pelos irmãos

`grill_workspace.py:3730` e `:3821`, contra `:3400` e `:3545`

A gravação está íntegra — a derivada é gravada incondicionalmente, inclusive quando não há carimbo prévio, e o único caminho sem regravação é a repetição idêntica, que é correto.

O que sobra: o sucessor sai da tomada carimbado com a fase daquele instante. Na **primeira virada de etapa** — vida normal do work item — `prepare-switch` compara a identidade inteira e recusa para sempre, porque o `setdefault` só carimba quando ausente e nunca recarimba. O defeito é pré-existente nos irmãos, mas a Phase 9 o tornou o caminho dominante: antes, a tomada recusava antes de chegar lá.

**Correção**: aplicar a mesma tupla estrutural nos dois irmãos, ou tirar fase e branch de `_continuity_identity` e mantê-los como campos informativos fora da identidade comparada.

#### R4-4 — Cinco campos estruturais não distinguem árvore recriada no mesmo caminho

`grill_workspace.py:3730`

`git_common_dir` é **compartilhado** entre worktrees do mesmo repositório, e `project_id` é hash dos root commits, idêntico em clone e em qualquer worktree. Sobra `real_path` como único discriminador, e nenhum dos cinco ancora conteúdo.

Cenário: a sessão morre; alguém faz `git worktree remove` e `git worktree add` no mesmo caminho, a partir de outro commit. Os cinco batem, a tomada aceita, e o sucessor herda campanha, resultados aceitos e ponto de retomada de uma árvore cujo conteúdo não existe mais. Antes, `branch` pegava o caso comum. Clone puro segue coberto, porque `real_path` difere.

**Correção**: acrescentar uma âncora de árvore que não se mova em operação normal — o diretório git **por worktree**, que é distinto por worktree ao contrário do comum. Commit base não serve, porque avança em commit normal.

#### R4-5 — `project_id` ainda vira com stash, e o bloqueio cai onde a tomada existe para curar

`grill_core/store.py:568` com `grill_workspace.py:3730`

`project_identity` deriva os root commits de `git rev-list --max-parents=0 --all`, e `--all` inclui `refs/stash`; `git stash push -u` cria commit sem pai, o `project_id` muda, e a tomada recusa permanentemente.

A ironia é o ponto: **guardar a árvore suja antes de assumir a sessão é o gesto natural do fluxo de recuperação**. Este defeito já está registrado como aprendizado do projeto, em outro contexto; agora ele alcança a tomada.

**Correção**: trocar `--all` por `--branches --tags --remotes`. É mudança de alcance global e re-deriva `project_id` de campanha já selada, então é decisão consciente, não ajuste local.

#### R4-6 — A asserção de estado projetado cobre só um dos dois emissores

`tests/validate_agent_orchestration_contract.py:306-311`, contra `grill_workspace.py:1879`

A asserção nova lê o checkpoint **inicial**. O comando de checkpoint tem um emissor paralelo com a mesma linha, e nenhum teste o observa. Verificado por execução: regredindo **só** esse emissor ao formato de mapa, os três validadores fecham verdes, porque a validação aceita mapa ou lista.

É o mesmo buraco do R3-5, num emissor que a Phase 9 não olhou.

**Correção**: replicar as quatro asserções sobre o checkpoint emitido pelo verbo de checkpoint, contra o estado vivo.

#### R4-7 — `work-restamp` move a árvore fora do `try`

`tests/validate_agent_orchestration_contract.py:1358-1362`

O `git checkout -b` e a reescrita do `state.json` acontecem **antes** do `try`, então o `finally` não os protege. Se a escrita levantar depois do checkout, a branch criada fica ativa no root da fixture pelo resto do método, e os casos seguintes derivam identidade de uma árvore que nenhum deles declarou — falha em cascata com causa não óbvia, ou aprovação por acidente.

**Correção**: abrir o `try` logo depois de capturar a branch original, com o checkout e a escrita dentro dele. Deslocamento de uma linha.

---

### Minor Issues

| # | Local | Achado |
|---|---|---|
| n1 | `grill_workspace.py:3947` | `UNKNOWN` é achatado quando vem de `retained`: a precedência só varre `results`, então recurso alheio em estado indeterminado sai rotulado `PRESERVED`. Exit é 2 nos dois casos, sem falso sucesso, mas o topo afirma "preservado" sobre estado que o protocolo trata como diferente |
| n2 | `references/session-protocol.md:103` | `RESOURCE-RETAINED-ELSEWHERE` e o campo `retained` **não existem no protocolo**. O leader recebe código sem regra, e como o protocolo manda não converter preservação em aprovação, a leitura padrão vira bloqueio. Vocabulário novo precisa entrar na tabela dizendo que não bloqueia a ação do contexto corrente |
| n3 | `grill_workspace.py:3694` | O bridge da campanha ainda carimba a identidade **selada** do predecessor, que T030 acabou de julgar obsoleta, enquanto o sucessor recebe a derivada. Depois de T030 as duas divergem por construção. Inerte hoje, mas o ledger registra identidade sabidamente falsa; o irmão `prepare-switch` passa a derivada |
| n4 | `tests/validate_agent_orchestration_contract.py:1387` | O `finally` restaura com `check=True`: se o corpo falhar e a restauração também, o erro do `finally` substitui a asserção que de fato quebrou |
| n5 | mesmo bloco | O `state.json` não é restaurado. Inócuo hoje; vira vazamento quando alguém acrescentar ao método um caso que itere os work items da fixture |
| n6 | `grill_workspace.py:3889` | O ramo de run da guarda de candidatos nunca é exercitado: os quatro cenários usam campanha vazia. As reversões reprovaram porque o `raise` é compartilhado, não porque o ramo esteja coberto |
| n7 | `grill_workspace.py:3913` | Só `CLOSED` é testado; tirar `REMOVED` do conjunto de estados fechados não reprova nada |

---

### Test Quality

**O que ficou bom, e é substancial:**

- a guarda de limpeza tem os **dois lados**, e cada um dos três mutantes testados é pego por um cenário específico. É o oposto do que as três rodadas anteriores acharam;
- `retained` é comparado por **igualdade exata de lista**, com verificação explícita de que o payload não carrega código de recusa — separando "relatado" de "recusado" sem frouxidão;
- `work-restamp` **move a árvore viva** em vez de mockar a derivação. É o que faz a reversão do predicado reprovar de verdade; um mock teria dado a mesma cor com muito menos prova;
- a asserção de estado projetado **lê o estado vivo de volta**, em vez de repetir o literal que o emissor escreveu — a correção certa para o defeito das rodadas anteriores;
- nenhum caso existente foi afrouxado: o diff é `+128/−0`, sem uma linha removida.

**O que falta** é R4-2, R4-6, R4-7 e os Minor n4 a n7.

### Runtime Correctness

Fora dos achados, verificado e limpo:

- **fail-closed íntegro**: a comparação recusa com campo ausente ou nulo, o schema garante as sete chaves, e a derivação recusa em HEAD destacado antes de qualquer comparação. No comando de limpeza, deixar de recusar sobre recurso alheio é decisão deliberada, e o caminho de sucesso ficou **mais estreito**, não mais largo — saída zero só sai com `CLEANED`;
- **precedência correta** entre os três vereditos para o que vem de `results`, e `CLEANED` exige `retained` vazio **e** resultados só de sucesso, então não há falso sucesso. A única imprecisão é n1;
- **nada mudou fora do ramo de contexto** além do Critical: o ramo por run passa incólume e o caminho de worker único não selecionado retorna antes de tocar a contagem;
- **não há chamador programático** do comando de limpeza no repositório; a CLI é dirigida por skill, e o protocolo manda ler saída 2 com payload como recusa. O dano do Critical é produzir 2 onde antes havia 0.

---

### Constitution References

Nenhum conflito constitucional descoberto. Os dois Critical são defeitos de disponibilidade e de cobertura; o fail-closed constitucional está preservado.

---

### Final Recommendation

**REQUEST CHANGES.**

Obrigatório antes do ship:

1. **R4-1** — escopar `retained` ao seletor, para o ramo por atividade parar de ser rebaixado por recurso alheio;
2. **R4-2** — cobrir o lado da recusa da guarda de identidade, que hoje não existe em teste algum;
3. **R4-3** — resolver a assimetria entre a tomada e os irmãos, para o bloqueio não ressurgir na primeira virada de etapa;
4. **R4-6** — cobrir o segundo emissor do estado projetado;
5. **R4-7** — mover o `checkout` para dentro do `try`, para o caso não vazar branch na fixture.

**Decisão do humano** recomendada para **R4-4** e **R4-5**: ambos são pré-existentes e de alcance maior que esta entrega — um pede âncora de árvore nova no predicado, o outro muda a derivação global de `project_id`, que re-deriva identidade de campanha já selada. Podem ser registrados como trabalho próprio em vez de entrarem aqui.

Registráveis como débito: n1 a n7, mais o já listado em R1, R2 e R3. **n2 merece atenção**: inventamos vocabulário de protocolo sem ensiná-lo a quem o consome.

Próximo passo: corrigir, rodar `/speckit.converge`, depois `verify` e `review` de novo.

---

## Review Report — R5

**Verdict: REQUEST CHANGES**

Source fingerprint: tree `b9e289cedc9b4eb86f51a62cd3fd43212922767dce409e595382de9939a23a30` / work `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` / plan `55cd6e61bbe2d7fe692ce9daf62df87d17a115a4263bcd992f6a321ddbb0e468`

Casa com `converge.md` (rodada 10) e `verify.md` (R5). Converge `CONVERGED`, Verify `PASS`.

**Primeira rodada sem Critical.** Três Important e quatro Minor, todos de arrumação ou de buraco lateral — nenhum reabre o defeito que a entrega existe para corrigir.

### A pergunta que decidia a rodada, respondida

As quatro rodadas anteriores acharam a **mesma forma de defeito** porque a regra de comparação de identidade vivia em três cópias. A Phase 10 extraiu para um ponto único. A pergunta era: a extração está completa, ou produziu a quinta instância?

**Está completa.** Os três comparadores de identidade contra a árvore viva passam todos pelo helper, e a varredura por `worktree_identity`, `real_path`, `git_common_dir`, `project_identity` e `worktree_key` não achou nenhum outro ponto comparando campo a campo — nem por igualdade de dicionário, nem por `in`, nem por subconjunto, nem dentro de validação de schema.

E apareceu uma distinção que vale mais que a confirmação: existe uma **quarta** comparação de identidade, em `validate_transition`, que compara o dicionário inteiro — e ela está **correta fora do helper**, porque responde outra pergunta. O helper responde "o carimbo bate com a árvore viva"; `validate_transition` responde "ninguém reescreveu o carimbo". São coisas diferentes, e só a primeira pode relaxar.

É justamente ela que fecha o argumento de T035 por via mecânica: carimbo imutável mais ausência de verbo de re-selagem implica que campo que se move na vida normal do contexto **tem** de ficar fora do predicado, ou a recusa é permanente. O raciocínio do worker estava certo por necessidade estrutural, não por preferência.

---

### Important Issues

#### R5-1 — Tirar `branch` do predicado abriu um buraco novo no carimbo de branch de execução

`grill_workspace.py:3301` (tupla), `:3564` (retomada), `:5889-5899` (preenchimento retroativo)

Existe controle compensatório real: `development["execution_branch"]` e a recusa por branch divergente impedem confirmar etapa na branch errada. **Mas esse controle só existe depois que alguém o carimbou**, e o código trata o campo ausente como preenchimento retroativo a partir da branch viva.

Cenário, verificado no código:

1. work item novo, nenhuma etapa confirmada, então a preparação de troca sintetiza o checkpoint inicial — e `execution_branch` ainda não existe;
2. o humano troca de branch na árvore, que é exatamente o que T035 declara rotineiro;
3. a retomada, que antes recusava por `branch`, agora passa — `real_path` e o diretório git comum são os mesmos;
4. a primeira confirmação de etapa preenche o campo e **liga o work item permanentemente à branch errada**.

Não é o defeito original voltando — ninguém lê sucesso sobre recurso aberto. É buraco novo aberto pela relaxação.

**Correção**: não recolocar `branch` na tupla, porque isso reabre a recusa permanente. Comparar contra o SSOT que já existe: na retomada, quando `execution_branch` for string não vazia, exigir que a branch viva coincida. E recusar o preenchimento retroativo quando o contexto corrente tem predecessor — carimbo de branch não deve nascer de uma sessão retomada.

#### R5-2 — Restauração de branch falha em silêncio, com casos depois dela

`tests/validate_agent_orchestration_contract.py:1587` e `:1268`

A troca de `check=True` por `check=False` na restauração está certa quanto ao mascaramento, mas **os dois métodos continuam executando casos depois do bloco**. Se a restauração falhar, ela agora falha em silêncio e os casos seguintes derivam identidade da branch de teste — exatamente a cascata que o comentário da correção diz estar fechando. O problema saiu do meio do bloco e foi para depois dele.

**Correção**: registrar a restauração como limpeza de teardown logo depois de capturar a branch original, e remover o `try`/`finally`. Restaura sempre, sem mascarar e sem deixar janela descoberta.

#### R5-3 — Asserção fora do `subTest` anula metade do caso de recusa

`tests/validate_agent_orchestration_contract.py:1624-1628`

O `assertEqual` está desindentado, fora do `with self.subTest(...)`. Confirmado por inspeção. Falhar a primeira iteração aborta o laço, e o caso com aplicação **nunca roda**. O arquivo usa o padrão correto noutro ponto, então é inconsistência interna.

Consequência: uma regressão que quebre só o caminho de aplicação fica invisível enquanto a prévia também estiver quebrada, e um relatório de falha mostra um subcaso em vez de dois.

**Correção**: indentar a asserção para dentro do bloco.

---

### Minor Issues

| # | Local | Achado |
|---|---|---|
| o1 | `grill_workspace.py:3946` e `tests/...:909-915` | A disjunção do escopo é **inalcançável**: o core fixa a origem do recurso como o contexto da atividade, e o seletor por atividade já exige que a atividade pertença ao contexto — então recurso de outro contexto nunca tem a atividade pedida. E o caso que a cobre monta um documento que **nenhum produtor gera** e que a validação não proíbe. É "fixture mais limpa que a realidade" invertido: dá confiança numa ramificação morta. Escolher entre afirmar o invariante na validação, tornando o caso defesa em profundidade honesta, ou reduzir a condição e apagar o caso |
| o2 | `tests/...:312` | A única cobertura dos dois emissores de estado projetado mora num teste cujo nome não a anuncia. Quem enxugar esse teste derruba a guarda sem perceber |
| o3 | `tests/...:1626` | Substituição de leitura por valor fixo em vez de função: inofensivo hoje, mas uma leitura futura com parâmetro diferente seria atendida por um objeto que o ignora |
| o4 | `grill_workspace.py:3714` vs `:3454` | O bridge da campanha leva o carimbo selado na tomada e a identidade viva na preparação de troca. Ninguém compara esse campo; é desigualdade de auditoria herdada, sem efeito de runtime |

---

### Test Quality

**Esta é a parte que mudou de patamar**, e merece registro depois de três rodadas apontando o contrário.

A prova decisiva veio de execução, não de leitura: **antes dos casos novos, três das quatro reversões fechavam verdes** nos três validadores que tocam tomada e continuidade. Agora reprovam. Em particular, o código de recusa da guarda de identidade tinha **zero** ocorrências nos testes e passou a ter duas, ambas no caso novo.

E houve rigor acima do pedido: **mutação diferencial** nos cinco campos projetados do segundo emissor, um a um — todos passavam com os testes antigos, todos reprovam com os novos. Isso não prova só que a cobertura existe; prova que ela discrimina campo a campo.

Sobre a solidez dos casos:

- o caso da recusa substitui a leitura de snapshot em vez de mover a árvore, porque o campo é imutável no store. **É sólido**: quem julga é o produto, a derivação de identidade roda de verdade sobre a árvore real, e a comparação é igualdade simétrica — mover o selado ou mover o vivo produz a mesma desigualdade. A prova é que apagar a guarda faz o caso reprovar; um teste da substituição passaria;
- os casos dos dois irmãos **provam o que prometem**: o teste move exatamente os campos que a derivação lê, e alargar a tupla de volta reprova os dois — uma fixture sem divergência real deixaria o mutante passar;
- **nenhum caso foi afrouxado**. Das nove remoções, oito são deslocamento sem mudança de conteúdo e acréscimo de parâmetro; a nona é a troca para restauração tolerante, que é o R5-2.

### Runtime Correctness

Verificado e limpo fora do R5-1:

- **o escopo da coleta está correto nos quatro caminhos**: por contexto o relato é idêntico ao de antes; por atividade passa a se comportar como o ramo de recurso próprio já se comportava; por run e no caminho de worker único o laço nunca é alcançado, por guarda pré-existente;
- **a mudança não reabriu o defeito original**: nenhuma combinação de seletor relê sucesso sobre recurso aberto. O único silêncio novo é sobre recurso de outra atividade, que a seleção não pede nem pode fechar;
- **fail-closed íntegro**: dicionário vazio e campo ausente bloqueiam nos dois lados, e o caminho de sucesso alargou apenas em `phase`, que é correto, e em `branch`, que é o R5-1;
- **nenhum irmão precisava ser mais estrito em `phase`**, e há prova mecânica: o checkpoint é carimbado com a identidade de nascimento do contexto, então a primeira virada de etapa travava os dois irmãos para sempre.

---

### Constitution References

Nenhum conflito constitucional descoberto.

---

### Final Recommendation

**REQUEST CHANGES**, com escopo pequeno e bem delimitado — os três Important somam poucas linhas.

Obrigatório antes do ship:

1. **R5-1** — fechar o buraco do carimbo de branch de execução comparando contra o SSOT existente, sem recolocar `branch` no predicado;
2. **R5-2** — restauração por limpeza de teardown, que não mascara e não deixa janela;
3. **R5-3** — indentar a asserção para dentro do bloco, para o segundo subcaso rodar.

Recomendado junto, por ser da mesma família e custar pouco: **o1**, escolhendo entre afirmar o invariante ou remover a ramificação morta com o caso que a cobre.

Registráveis como débito: o2, o3, o4, mais o já listado em R1 a R4.

Próximo passo: corrigir, rodar `/speckit.converge`, depois `verify` e `review` de novo.

---

## Review Report — R6

**Verdict: REQUEST CHANGES**

Source fingerprint: tree `1391107f8d541fd5cd34bf4ba2fcb0d2e1275288579330e5c4308cefb997279e` / work `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` / plan `7c34aec1d07bb1754c7cd033d53b3a9d21b5871ada727b220680295df46173db`

Casa com `converge.md` (rodada 12) e `verify.md` (R6). Converge `CONVERGED`, Verify `PASS`.

**Um Critical, dois Important, cinco Minor.** O Critical foi encontrado **independentemente pelos dois revisores**, por caminhos diferentes — um pela análise do critério, outro reproduzindo a sequência completa em cópia de scratchpad. E foi reverificado pelo coordenador.

### O defeito, e de quem é a culpa

**O critério errado foi instrução minha.** A tarefa T040 dizia, com essas palavras: *"recusar o preenchimento retroativo quando o contexto corrente tiver predecessor"*. O worker implementou exatamente isso. É a segunda vez nesta entrega que uma instrução imprecisa do coordenador produz o defeito — a primeira foi *"contar candidatos antes dos filtros"*, no T031, que gerou o bloqueio permanente do R4-3.

O padrão comum às duas não é técnico, é de método: **critério baseado em estado que só cresce**, aplicado a uma decisão que precisa ser reavaliável. "Tem predecessor" nunca deixa de ser verdade; "antes dos filtros" inclui o filtro que deveria discriminar.

---

### Critical Issues

#### R6-1 — A recusa do preenchimento retroativo é permanente, e o `phase-turn` a transforma em beco sem saída

`grill_workspace.py:5917` (guarda), `:3311` (predicado), `:6088` (`phase-turn`)

Três fatos, todos verificados no código:

1. **`predecessor_context_id` nunca é limpo.** Toda sucessão o grava no contexto novo, e `validate_transition:1513` **exige** que ele aponte para o contexto anterior. Logo `_continuity_resumed_context` é monotônico: uma vez verdadeiro, verdadeiro para sempre;
2. **`phase-turn` zera `development["execution_branch"]` de propósito**, com comentário explicando que é para a fase seguinte vincular a própria branch;
3. **só dois pontos escrevem o campo**: o preenchimento retroativo (`:5992`) e o `phase-turn` que o anula. Não existe verbo de re-vínculo.

Sequência, reproduzida por execução:

```
init 0
cp1 0 master
cp-again (contexto retomado, branch já vinculada) 0
cp-after-phase-turn (contexto retomado) 2 EXECUTION-BRANCH-UNSET
```

Depois de **qualquer** tomada ou retomada, o primeiro `phase-turn` bloqueia o work item permanentemente. E há um segundo caminho para o mesmo fim: tomada antes do primeiro passo confirmado — cenário que o próprio código declara suportado — deixa o campo sem existir nunca, e o primeiro checkpoint já nasce bloqueado.

**Assimetria agravante**: `phase_turn_command` tem o ramo de preenchimento **idêntico e sem a guarda**, então ele mesmo pode cunhar a vinculação a partir de um contexto retomado — e em seguida a zera.

**Correção**: trocar "tem predecessor" por **evidência**. Recusar somente quando houver carimbo contraditório:

```
carimbo = identidade de worktree do contexto corrente → branch
se carimbo existe e difere da branch viva → recusar
```

A tomada e a retomada derivam esse carimbo ao vivo e validam a identidade estrutural no ato, então ele é prova de qual branch a árvore tinha na sucessão. Carimbo ausente significa nenhuma reivindicação anterior a contradizer, e portanto carimbar pela primeira vez é correto. É a mesma doutrina que T023 e T035 já adotaram duas vezes neste arquivo, e que eu não apliquei ao redigir T040.

---

### Important Issues

#### R6-2 — A guarda só existe na retomada; a preparação de troca solta o líder antes de qualquer checagem de branch

`grill_workspace.py:3585`, contra `:3669` e `:3767`

A tomada está coberta a jusante: com carimbo selado e branch viva divergente, ela passa — a tupla estrutural ignora `branch` de propósito — mas o checkpoint seguinte recusa por divergência. Nenhuma escrita de fluxo escapa.

A **preparação de troca**, não: ela passa, cria a operação e o ponto de retomada, e **libera o líder**. A divergência só aparece na retomada, com o contexto já solto. É recuperável, mas o operador descobre tarde e no comando errado.

**Correção**: extrair a comparação para um helper e chamá-lo também na preparação de troca e na tomada, logo depois de derivar a identidade. Duas linhas em cada, e a falha passa a ser nomeada antes de mutar.

#### R6-3 — A metade que recusa não demonstra o defeito que a própria docstring afirma

`tests/validate_agent_orchestration_contract.py:1370` e `:1424-1429`

A docstring afirma que remover a comparação faz a metade divergente retornar prévia com saída zero. **Falso, medido**: removendo a guarda, o resultado é `GAUNTLET-NOT-ACTIVATED` com saída 2, porque o subcaso segue adiante **antes** de instalar os mocks de fronteira que só a outra metade instala.

Ou seja: o caso discrimina apenas pela **string do código**. A asserção de saída e a barreira de escrita passam idênticas com e sem a guarda. Ele nunca prova que, sem ela, uma retomada divergente **prossegue**.

Não é teste falso — reprova de verdade na reversão. É mais fraco do que anuncia.

**Correção, provada pelo revisor**: instalar os mesmos mocks de fronteira nas duas metades. Com eles, a reversão degrada para prévia com saída zero, que é literalmente o que a docstring promete. A guarda passa a separar "recusa" de "retoma numa branch alheia", em vez de decidir qual nome de código aparece primeiro.

---

### Minor Issues

| # | Local | Achado |
|---|---|---|
| p1 | `grill_workspace.py:3581` | `(state.get("development") or {})` só cobre valor falsy; a leitura de estado valida o topo, não o campo. Um `development` não-dicionário e não vazio produz traceback em vez de código nomeado. O comando de checkpoint protege isso; a retomada não |
| p2 | `grill_workspace.py:3311` | O predicado novo lê o store; store presente e **inválido** levanta erro de store, não recusa nomeada, e não é capturado ali. Envolver e tratar como indeterminado |
| p3 | `tests/...:1254-1259` e `:1712-1717` | A rede de limpeza de encerramento é decorativa: os blocos não estão em subcaso, então qualquer falha aborta o método e o diretório temporário é descartado. Inofensivo, mas o comentário promete proteção que quem entrega é a restauração explícita |
| p4 | mesmos blocos | A restauração duplicada caberia num gerenciador de contexto único, com restauração tolerante no caminho de exceção e estrita no de sucesso. Forma, não defeito |
| p5 | `tests/...` | O predicado de contexto retomado não tem caso para store **ausente**; o teste cobre item ausente. Uma linha, risco baixo |

---

### Test Quality

**Sólida no essencial**, e verificada por execução, não por leitura:

- as **quatro reversões foram reproduzidas uma a uma** em cópia de scratchpad, cada uma reprovando o caso correspondente;
- a reversão da indentação é a mais valiosa: indentada produz **dois** fracassos, desindentada produz **um** e o subcaso de aplicação não roda. Prova direta de que a correção mudou o alcance do teste;
- a guarda de branch está coberta **nos quatro cantos**, incluindo um lado que ninguém pediu — carimbo ausente continuar permissivo —, coberto por testes **já existentes**. Provado por mutação: apertar a guarda para tratar ausência como divergência reprova três casos existentes. A guarda não pode ser apertada demais sem que a suíte reclame;
- o invariante novo tem os dois lados, e o lado limpo é **real, não vazio**: a fixture exercita de fato o caminho "mesmo contexto", sem escapar pelo atalho de atividade nula;
- **nada foi afrouxado**. As 54 remoções são reindentação; as únicas linhas genuinamente removidas são o andaime do bloco protegido e as duas restaurações tolerantes que migraram para a rede.

### Sobre o desvio do worker, que eu pedi para ser avaliado

**A solução dele está correta, e a minha instrução estava errada.** Verificado nos dois sentidos:

- aplicando a instrução ao pé da letra — só limpeza de encerramento —, **dois casos reprovam**, porque os casos seguintes de cada método precisam da branch de volta na hora, não no teardown. O relato dele confere exatamente;
- a verificação estrita **não** reintroduz o mascaramento que o R5 apontou. Mascaramento exige restauração rodando com exceção em voo, que é o caminho do bloco protegido. Aqui a linha fica **depois de todas as asserções**: se alguma falha, ela nunca é alcançada. O caminho de exceção segue atendido pela rede, essa sim tolerante.

E há ganho, não neutralidade: o bloco original restaurava de forma tolerante, então um checkout que falhasse falhava **em silêncio** — exatamente o defeito do R5-2. A verificação estrita no caminho feliz é o que fecha isso.

### Runtime Correctness

Fora dos achados, duas frentes **explicitamente limpas**, com fundamentação que vai além de "não encontrei":

- **o invariante novo não pode recusar documento histórico**, porque a forma proibida era **inconstruível**: o único produtor que grava atividade em recurso fixa a origem na mesma expressão, nada reescreve esses campos depois, e a sucessão copia os recursos verbatim. Migração desnecessária porque nunca houve o que migrar;
- **o invariante já incide na escrita também** — o `transact` chama a validação sobre o candidato, então leitura e escrita compartilham a fronteira. Nada a acrescentar.

Fail-closed íntegro: as guardas recusam apenas divergência positiva, e ausência não autoriza nada, com a ressalva de p1. O caminho de sucesso estreitou demais em exatamente um ponto, que é o R6-1.

---

### Constitution References

Nenhum conflito constitucional descoberto. O R6-1 é defeito de disponibilidade: o caminho falho **recusa**, nunca autoriza indevidamente.

---

### Final Recommendation

**REQUEST CHANGES.**

Obrigatório antes do ship:

1. **R6-1** — trocar o critério de "tem predecessor" por evidência de carimbo contraditório, e alinhar o ramo de preenchimento do `phase-turn`, que hoje não tem guarda alguma;
2. **R6-2** — chamar a comparação de branch também na preparação de troca e na tomada, para a falha ser nomeada antes de o líder ser solto;
3. **R6-3** — instalar os mocks de fronteira nas duas metades, para o caso provar o que a docstring afirma.

Recomendado junto, por custarem uma linha cada: **p1** e **p2**.

Registráveis como débito: p3, p4, p5, mais o já listado em R1 a R5.

Próximo passo: corrigir, rodar `/speckit.converge`, depois `verify` e `review` de novo.

---

# R7 — 2026-09-20, após a Phase 12

## Review Report

**Verdict: REQUEST CHANGES** — 1 Critical, 2 Important, 9 Minor

Source fingerprint: tree `831d81aea348dfa6de4f72508d51448e3199e7bb8ef3f24391a3818a61811e32` / work `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` / plan `fb2993563b5e77a0737d9b3bb8885b5f9c560c78d15022191df10b2de626207f` — casa com o converge rodada 14 e o verify rodada 7.

Quatro revisores read-only: correção em runtime, qualidade de teste, arquitetura/legibilidade, segurança e regressão.

## O que esta rodada achou, em uma frase

A Phase 12 trocou o Critical do R6 por uma **regressão do J1**, um Critical que esta mesma entrega fechou na rodada 5 — e o comentário que registra o fechamento do J1 está três linhas acima do helper novo.

## Critical

### R7-1 — O carimbo congela no contexto, e a virada de fase legítima volta a bloquear permanentemente

`plugin/skills/grill-with-docs/scripts/grill_workspace.py:5961-5965` e `:6118-6122`

O R6 recusou o critério monotônico "o contexto corrente tem predecessor" porque ele bloqueava permanentemente todo work item já sucedido. A Phase 12 trocou por "o carimbo de branch existe e difere da branch viva". O critério novo é melhor, mas **continua irreavaliável**, por três propriedades que se combinam:

1. **Ninguém limpa o carimbo.** `worktree_identity` não está no conjunto mutável de `agent_orchestration.py:1488` — `{state, activation, campaign, scheduler_runs, leader, presentation}` — então `transact` recusa qualquer reescrita com `context immutable field changed`. Só a criação de contexto novo escreve o carimbo: `:3905` (takeover), `:3693` (resume), `:3540` (`setdefault` do prepare-switch).
2. **A virada de fase zera o vínculo de propósito**, e o comentário em `:6135-6137` diz por quê: *"so the first `specify` of the next phase can bind its own branch"*. Ou seja, o design **prevê** que a fase seguinte rode noutra branch.
3. **O preenchimento retroativo compara com o carimbo velho.** Sucessão em `A` → carimbo `A` → virada de fase → fase nova vincula `B` → `EXECUTION-BRANCH-MISMATCH`, para sempre.

A saída é só uma sucessão nova, e `takeover` exige sessão predecessora morta enquanto `resume` exige prepare-switch ou troca de runtime. **Um líder vivo não se sucede**: o work item fica parado até a sessão morrer.

**Isto é regressão de um Critical que esta mesma entrega já fechou.** Não é classe parecida — é o mesmo defeito, pelo mesmo mecanismo:

- **J1** (converge rodada 5, CRITICAL, FR-001): *"compara a identidade inteira; `phase` avança a cada etapa do ciclo… a tomada recusa `TAKEOVER-IDENTITY-DIVERGENT` para sempre"*. Fechado no T030 **removendo `phase` e `branch` do conjunto comparado**, deixando `("project_id", "work_id", "du", "git_common_dir", "real_path")`.
- **H1** (CRITICAL, FR-001 e FR-005): *"trocar de branch depois da morte da sessão faz o sucessor herdar identidade falsa, e toda retomada posterior falha **sem verbo de re-carimbo**"*. O registro de fechamento do H1 diz, com todas as letras, que o caso sem carimbo prévio não recusa *"porque recusar tornaria a tomada impossível para sempre, já que não existe verbo de re-carimbo"*.

A Phase 12 **reintroduziu a comparação de `branch`** — no caminho de cunhagem do vínculo, não no de identidade, mas com a mesma consequência que o J1 tinha e pelo mesmo motivo de fundo: a branch se move na vida normal e nada a re-carimba.

**O comentário do T035 é a justificativa de fechamento do J1**, ainda no arquivo em `:3294-3299`:

> `phase` and `branch` are stamped for the record but never compared: both move in normal life — a step turn advances the phase, a branch is switched — and no verb ever re-stamps, so comparing them means "nothing moved since the stamp was first written", which is not what quiescence proves.

A Phase 12 passou a comparar `branch` exatamente contra esse aviso. Não é um comentário que ficou velho: é o registro de por que o J1 foi fechado daquele jeito, e o defeito que ele descreve, em português claro, é este achado.

É o terceiro caso nesta entrega de **regra certa registrada e depois contrariada**, e o mais caro, porque desta vez o registro estava no próprio arquivo, três linhas acima do helper novo.

**Cobertura:** nenhum caso exercita carimbo `A` → virada → branch `B`. Os dois casos novos só cobrem carimbo igual à branch viva, ou branch fictícia sem virada (`tests/validate_agent_orchestration_contract.py:1521-1568`, `:1569-1605`).

### Duas saídas, e por que recomendo a mais curta

**Opção A — remover a comparação de branch do caminho de cunhagem** (recomendada).

O J1 foi fechado com a doutrina de que `branch` não se compara, porque se move e nada a re-carimba. A sucessão **é** o re-carimbo: `takeover` e `resume` derivam a identidade ao vivo e validam a identidade estrutural no ato, e o `r7-sec` confirmou no código que não existe caminho de carimbo forjado. Logo, depois de uma sucessão, a branch viva **é** a árvore daquele contexto, e vincular a ela é correto por construção.

O que a guarda supostamente protege — "o vínculo não deve nascer de sessão retomada" — já está protegido a montante, pela validação de identidade da própria sucessão. A guarda não acrescenta prova; acrescenta uma condição que envelhece.

**Opção B — considerar o carimbo superado pela virada** (conservadora).

Sem campo novo e sem tocar a imutabilidade do store, usando o audit append-only que a virada já grava: tratar o carimbo como **superado** quando a última entrada `phase-turn` de `development["audit"]` tiver `previous_execution_branch == stamped_branch`. O carimbo descreve então uma fase encerrada, logo não contradiz nada. A recusa sobra só para carimbo não superado por virada.

Recomendo **A**. B mantém viva uma comparação que o J1 já julgou insustentável e paga isso com uma consulta ao audit em dois sítios; A devolve o código ao estado que o J1 estabeleceu e deixa a prova onde ela é produzida. Se a implementação escolher B, o comentário do T035 precisa deixar de dizer que `branch` nunca é comparado.

Contra FR-001 e FR-005.

### Procedência deste achado

O critério que produziu o R7-1 foi **recomendado pelo próprio R6** e repassado por mim ao brief da Phase 12 sem confronto com o J1 — que está no mesmo `converge.md` que eu estava escrevendo. O worker executou o brief corretamente; a falha é da instrução.

É a terceira vez nesta entrega, e o padrão agora está completo:

| # | Tarefa | Critério que instruí | Por que quebrou |
|---|---|---|---|
| 1 | T031 | "contar candidatos antes dos filtros" | "antes dos filtros" incluía o filtro que discriminava |
| 2 | T040 | "recusar quando o contexto tiver predecessor" | predecessor só cresce; decisão precisa ser reavaliável |
| 3 | T044 | "recusar quando o carimbo existir e diferir" | carimbo só é escrito na sucessão; a branch se move sem ele |

Os três são **critérios ancorados em estado que não é reavaliável no momento da decisão**. Nos dois primeiros o estado só crescia; neste ele congela. A lição operacional é a mesma: antes de aceitar um critério de recusa, perguntar *quem escreve esse estado, quem o limpa, e o que acontece quando o mundo muda legitimamente e ele não muda junto*.

## Important

### R7-2 — O subcaso "carimbo coincidente" é cobertura falsa, provado por mutação

`tests/validate_agent_orchestration_contract.py:1534-1535`

O revisor trocou `if stamp is not None:` por `if stamp is not None and stamp != "live":` — ou seja, fez o subcaso `"stamp agrees"` não carimbar nada — e **o teste passou**. Esse subcaso é observacionalmente idêntico ao `"no stamp"`: ambos só assertam que o vínculo foi cunhado.

O terceiro lado que a docstring promete, "carimbo coincidente vinculando", **não é provado**. Se `_graft_succession` regredisse em silêncio — contexto errado, chave errada — só o lado divergente acusaria.

Conserto, uma linha depois do graft:

```python
self.assertEqual(grill_workspace._continuity_stamped_branch(root, "work-x"),
                 live_branch if stamp == "live" else stamp)
```

Agrava que `:1536` faz `self.assertNotEqual(stamp, live_branch)`, comparando o **literal** `"live"` com a branch viva em vez do valor carimbado — no subcaso agrees isso afirma apenas que a branch não se chama `"live"`.

Contra FR-011.

### R7-3 — O comentário do ponto único afirma que `branch` nunca é comparado

`plugin/skills/grill-with-docs/scripts/grill_workspace.py:3292-3299`, e o bloco irmão em `:3790-3796`

Falso desde `0eddb29`. É o mesmo material do R7-1, mas registrado à parte porque é uma **afirmação falsa deixada no código**, que é o gênero de defeito que esta entrega já viu em quase toda rodada. Um leitor que confie no comentário conclui que a comparação de branch não existe.

O bloco de `takeover` em `:3790-3796` tem o irmão do problema: diz que a árvore de uma sessão morta é *"free to change"*, sem ressalvar que o carimbo velho agora bloqueia a cunhagem até um takeover ou resume re-carimbar.

Conserto: reescrever para "fora do conjunto **estrutural** — nenhuma recusa de continuidade olha `branch`; a cunhagem do vínculo olha, como evidência, via `_continuity_stamped_branch`", com ponteiro ao helper. Se o R7-1 for consertado como proposto, o comentário precisa dizer também que o carimbo superado por virada não contradiz.

## Minor

| # | Local | Achado |
|---|---|---|
| m1 | `grill_workspace.py:3341` | `_continuity_require_bound_branch` **não exige vínculo**: carimbo ausente ou vazio passa em silêncio. O nome promete requisito, o comportamento é "recusa contradição". Renomear para `_continuity_refuse_diverged_branch` |
| m2 | `grill_workspace.py:3345-3348` | A docstring diz "the single point is called by all three verbs" — verdade só para os verbos de continuidade. A mesma regra vive em quarta cópia em `grill_core/gauntlet_runs.py:2470-2475`, e a mesma condição sai como `CONTINUITY-STATE-DIVERGENCE` nos verbos de continuidade e `EXECUTION-BRANCH-MISMATCH` nos de ciclo, sem nada explicando a diferença |
| m3 | `grill_workspace.py:5963` vs `:6134` | `EXECUTION-BRANCH-MISMATCH` carrega dois detalhes de causas distintas: `context identity is stamped on X` e `work item is bound to X` |
| m4 | `grill_workspace.py:3310`, `:3341` | Os nomes não marcam a fonte: um lê o Store (carimbo do contexto), o outro lê `state.json` (vínculo do work item). **Não** devem ser fundidos — fontes e donos diferentes |
| m5 | `grill_workspace.py:3320-3322` | A docstring cita dois verbos que derivam a identidade ao vivo; `prepare-switch` também deriva e sustenta a mesma prova. São três |
| m6 | `references/session-protocol.md:104` | `EXECUTION-BRANCH-MISMATCH` e `DEVELOPMENT-SCHEMA` não constam da família `Checkpoint`. **Lacuna, não quebra de contrato**: a coluna é rotulada "Recusas **principais** e ação" e nenhum validador amarra o conjunto de códigos ao documento. Um operador que encontra `context identity is stamped on X` não acha ação nenhuma no protocolo aprovado |
| m7 | `grill_workspace.py:6106-6107` | `phase_turn_command` zera `steps`/`current_step` em memória antes da guarda de `:6118`. Não há persistência entre os dois pontos, então não é observável; é frágil a edição futura |
| m8 | `grill_workspace.py:3327` | `_continuity_stamped_branch` lê o snapshot **fora** do `orchestrator_lock`, enquanto `:3181-3187` documenta que a autoridade é lida sob lock. Sob commit concorrente: recusa espúria ou carimbo obsoleto. Há precedente sem lock, então é consistência, não regressão |
| m9 | `grill_workspace.py:3359` e `:3331-3333` | Dois ramos sem teste algum: o `DEVELOPMENT-SCHEMA` do helper e a tradução de `StoreError`. Trocar qualquer um por `pass` deixa a suíte verde |

## Test Quality

Quatro reversões executadas de verdade, em cópia do repo fora da árvore, com o original intocado. **Três passaram**:

- reverter a guarda do checkpoint faz o caso falhar com o defeito real no payload — `verdict: UPDATED`, `execution_branch` cunhado, exit 0 — não por troca de string de código;
- reverter **só** a guarda da virada de fase produz falha isolada naquela asserção: os dois sítios de cunhagem são independentemente cobertos, que era o buraco do R6;
- reverter o helper faz a metade `bound-elsewhere` degradar para `PREVIEW`/exit 0, como a docstring afirma. R6-3 está fechado: as duas metades instalam os mesmos substitutos de fronteira, num único `run_cli`.

A quarta é o R7-2 acima.

Duas docstrings (`:1517-1518`, `:1577-1578`) prometem uma reversão em termos do critério **removido** — irreproduzível hoje. É o gênero do R7-3, na camada de teste.

## Runtime Correctness

Fora do R7-1: `_continuity_require_bound_branch` tem os três call sites declarados e **todos falham antes de mutar** — `:3476` antes de montar operação e checkpoint, `:3627` antes do preview, `:3817` antes do `transact`. Erros não capturados foram fechados pelo T047: `development` não-dicionário vira `DEVELOPMENT-SCHEMA`, store inválido vira recusa nomeada, store ausente devolve `None` sem reivindicação.

## Security

**Nenhum achado Critical ou Important.** A afrouxada da Phase 12 — carimbo ausente passou de "recusa" para "vincula" — está corretamente ancorada, e isso foi confirmado no código, não só na prosa do converge:

- `branch` é campo **required** do `worktree_identity` em `agent_orchestration.py:632` quando a chave existe, e vazio é recusado, então "carimbo presente sem branch" é inalcançável por documento válido;
- retomada e tomada derivam a identidade **ao vivo** e exigem coincidência estrutural contra o checkpoint e contra o contexto de origem antes de qualquer mutação; o sucessor é carimbado com a identidade derivada, nunca com cópia do predecessor;
- o contexto não pode ser reescrito no lugar, e nenhum verbo apaga `worktree_identity`.

Não há caminho em que o carimbo seja apagado ou omitido e o vínculo seja cunhado a partir de contexto não verificado.

**Fronteira**: a branch vem de `git branch --show-current`, nome curto, nunca prefixado de `refs/heads/`. Vazio recusa nomeado nos três pontos. Os dois sítios de cunhagem rodam `git check-ref-format --branch`. Toda comparação é igualdade de string crua, e `branch` não entra em `Path`, `join` nem nome de arquivo em lugar nenhum — o padrão do achado antigo, segmento com drive reancorando caminho, não se aplica aqui.

## Regressão R1–R6

**Nenhuma regressão.** Verificado no código integrado: o ponto único da Phase 10 está intacto e `_CONTINUITY_STRUCTURAL` é a única tupla, consumida pelos três verbos; o filtro de `origin_context_id` do R4-3 continua antes da contagem de candidatos; os quatro achados laterais do R5 seguem fechados; o R6-2 e o R6-3 estão fechados. `_continuity_resumed_context` e o `EXECUTION-BRANCH-UNSET` do caminho antigo não deixaram chamador órfão — o `EXECUTION-BRANCH-UNSET` remanescente é de `gauntlet_runs.py:2470`, outro contrato.

## Observação de qualidade que não é achado

`_graft_succession` (`tests/…:1449`) escreve o carimbo direto no store — fixture derivada do código, não da saída dos verbos reais. É o padrão que já mordeu este projeto. Aqui está mitigado porque `tests/…:1845-1848` prova, com tomada real, que o sucessor carrega a branch viva; o elo entre os dois existe, só não está no mesmo caso.

## Constitution References

Nenhum conflito descoberto. 6.0.3 sem publicar, `main` em 6.0.2, sem novo bump exigido.

## Final Recommendation

**REQUEST CHANGES**: consertar o R7-1 e os dois Important, rodar `/speckit.converge`, depois verify e review de novo.

Recomendo tratar junto os Minor m1, m3 e m5, de uma linha cada, e m9, que é a cobertura dos dois ramos que hoje podem virar `pass` sem reprovar nada. Os demais ficam como débito registrado.

---

# R8 — 2026-09-20, após a Phase 13

## Review Report

**Verdict: REQUEST CHANGES** — 0 Critical, 3 Important, 5 Minor

Source fingerprint: tree `c7d9d101b55e62fb6f35a53a044fffb338bd1e393ddd19a3e504a21e583f7f4c` / work `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` / plan `17a6be04aea20edbe11af3113a6a63cde11ba657097052bdbec020a762d50e6e` — casa com o converge rodada 16 e o verify rodada 8.

Três revisores read-only: correção em runtime, qualidade de teste por mutação, varredura de afirmação e regressão.

## Primeira rodada sem Critical desde o R5

O Critical do R7 está fechado e **verificado independentemente pelos três revisores**: a tupla estrutural tem uma definição e um consumidor, nada mais compara carimbo para recusar, e os dois sítios de cunhagem seguem vivos e cobertos. A regressão do J1 foi desfeita.

Os três Important que restam **não são defeito de comportamento**. Todos são da mesma família: **o código faz uma coisa e alguma afirmação diz outra**. É a família que mais apareceu nesta entrega, e desta vez duas das afirmações falsas são minhas.

## Important

### R8-1 — O comentário do T035 continua falso, e eu registrei que ele tinha voltado a ser verdadeiro

`plugin/skills/grill-with-docs/scripts/grill_workspace.py:3295-3301`

O bloco afirma que `phase` e `branch` são carimbados *"but never compared"*. Para `phase` é verdade. Para `branch` **não é**: `_continuity_refuse_branch_contradiction`, seis linhas abaixo em `:3318`, compara `identity["branch"]` — a mesma chave do mesmo dicionário produzido por `_continuity_identity` logo acima — contra `development["execution_branch"]`, e recusa com `CONTINUITY-STATE-DIVERGENCE`. Os três verbos chamam esse helper imediatamente depois de comparar a tupla estrutural.

O T048 tornou verdadeira a parte sobre o **carimbo**. Não tornou verdadeira a frase como escrita.

**E eu escrevi, no converge rodada 16, que o bloco "voltou a ser verdadeiro sozinho, sem edição".** Era eu confiando na negativa absoluta em vez de verificá-la — precisamente o erro que produziu o R7-1, quando um leitor confiou neste mesmo comentário.

**Conserto** (o revisor propôs, e concordo com o raciocínio): não acrescentar parágrafo nem mover explicação, porque a explicação correta já existe em dois lugares — `:3604-3608` e a docstring do helper — e um terceiro exemplar seria o R3/R4 de novo. **Estreitar a afirmação no lugar** e apontar:

```
# ... `phase` and `branch` are stamped for the record but stay OUT of it ...
# comparing the *stamped* value means "nothing moved since it was first written" ...
# The live branch IS compared, against a different source and by a different
# function: see `_continuity_refuse_branch_contradiction` below.
```

A última linha é a que fecha o R7-1: é o que faltou ao leitor da Phase 12.

Contra FR-010.

### R8-2 — O conserto do R7-2 não fechou o buraco no subcaso para o qual foi escrito

`tests/validate_agent_orchestration_contract.py:1614-1623`

Provado por mutação: removendo a escrita do carimbo de branca em `_graft_succession`, **só o subcaso de carimbo contraditório falha**. O subcaso `stamp agrees` fica verde, porque a identidade derivada já devolve `branch == live_branch` e o valor de fallback é idêntico ao valor asserido.

O comentário em `:1616-1618` diz que o readback pega *"a regression that stops the graft from writing the stamp"*. É falso exatamente para o subcaso que ele anota.

O readback ganhou alguma coisa — pega enxerto ausente por completo — mas continua sem distinguir "enxerto selou carimbo coincidente" de "enxerto selou carimbo sem branca".

**Conserto**: remover o subcaso `stamp agrees`. Depois do T048 ele é comportamentalmente idêntico a `no stamp`, e todo o poder de detecção está no subcaso contraditório — confirmado por mutação independente nos dois sítios. Menos código, zero perda de cobertura.

É o **quinto** defeito desta família nesta entrega: R6-3, o caso da Phase 12 que codificava o próprio defeito, o R7-2, e agora o conserto do R7-2. Vale registrar o padrão: **toda vez que a correção de uma cobertura falsa foi escrita sem rodar a mutação que a motivou, ela não fechou o buraco.**

Contra FR-011.

### R8-3 — A recusa por esquema é inalcançável justamente quando `active_phase` é nulo, e o teste planta o valor que a torna alcançável

`plugin/skills/grill-with-docs/scripts/grill_workspace.py:3289` e `tests/validate_agent_orchestration_contract.py:1494-1501`

`_continuity_identity` faz:

```python
phase = state.get("active_phase") or state.get("development", {}).get("current_step") or "unassigned"
```

Com `development` presente e não-mapping, `.get` levanta `AttributeError` — e `_continuity_identity` roda em `:3451`, `:3600` e `:3803`, **antes** da guarda `DEVELOPMENT-SCHEMA` que vive em `:3340`. Só o curto-circuito do `or` salva: se `active_phase` for verdadeiro, o segundo operando nem é avaliado.

O caso do T053 planta `active_phase = "specify"` e **documenta honestamente** que sem isso a derivação quebra antes da guarda sob teste.

O revisor graduou como Minor por ser pré-existente. **Subo para Important**, com evidência que ele não tinha:

- `active_phase` é **nulo em 4 dos 8** work items reais deste repositório;
- `audit_decisions.py:780` **exige** `active_phase` nulo em milestone terminal.

O nulo não é caso exótico: é estado obrigatório em parte do ciclo. Então a recusa nomeada que o projeto exige não acontece justamente nos work items em milestone terminal, e no lugar dela sai falha genérica. A guarda existe, o teste passa, e nenhum dos dois vale no caminho que mais importa.

**Conserto**: validar o tipo de `development` dentro de `_continuity_identity`, ou resolver `phase` sem assumir mapping. Aí a recusa vale incondicionalmente e o teste dispensa a muleta.

O crash em si é pré-existente. O que é desta entrega é a guarda que afirma tratá-lo e o teste que afirma prová-lo.

Contra FR-010.

## Minor

| # | Local | Achado |
|---|---|---|
| n1 | `grill_workspace.py:5952-5956` | O comentário diz que "a branca viva já é a árvore em que aquele contexto rodou". Verdadeiro para a **árvore**, e só quando algum verbo de continuidade rodou — a validação é de projeto, caminho real e `git_common_dir`, e `branch` está fora da tupla de propósito. Duas branches na mesma worktree passam idênticas |
| n2 | `tests/…:1395` | `assertNotEqual(bound, live_branch)` roda também no subcaso em que `bound is None`, onde é trivialmente verdadeira. Mover para dentro da condição |
| n3 | `grill_workspace.py:5961`, `:6123` | Dentro de uma mesma fase, renomear ou apagar a branca vinculada trava os dois pontos, e nenhum verbo limpa o vínculo. Recuperável recriando o nome. Pré-existente, escopo estreito |
| n4 | `grill_workspace.py:3441`, `:3585`, `:3770` | Os três verbos chamam a leitura de snapshot fora de tratamento próprio, então store inválido sai como falha genérica em vez de recusa nomeada. Pré-existente ao T048 — a tradução vivia no helper que a Phase 12 criou e o T048 removeu |
| n5 | `grill_workspace.py:5942-5958` | O primeiro ramo da cadeia ficou com corpo `pass` precedido de 14 linhas de comentário. Não é inalcançável nem incorreto; a cadeia precisa dele. Preferência |

## Test Quality

Seis mutações executadas em cópia fora da árvore, com a worktree intacta. **Cinco confirmaram o que deviam**:

- restaurar a guarda **só** na confirmação de etapa, e **só** na virada de fase, faz falhar a asserção daquele sítio e só dela — os dois continuam independentemente cobertos;
- restaurar o critério monotônico derruba três casos, incluindo o que cobre a sequência sucessão → virada → confirmação;
- neutralizar o `raise` do T053 faz o caso novo falhar pela asserção certa;
- remover o enxerto por completo é pego pelo readback.

A sexta virou o R8-2.

O elo entre a fixture que enxerta e os verbos reais **existe e é forte**: o caso de tomada exercita `prepare-switch` e `takeover --apply` de verdade e afirma que o sucessor carrega a branca derivada ao vivo mais os cinco campos estruturais. A forma que o enxerto fabrica é a forma que o verbo real emite.

## Runtime Correctness

**Sem achado Critical ou Important.** A remoção não deixou buraco:

- `development.execution_branch` tem exatamente **um escritor e um limpador** em toda a árvore do plugin, e os demais pontos só leem. As duas recusas remanescentes comparam contra estado que o próprio ciclo derruba a cada virada — não sofrem do defeito monotônico do carimbo, que é campo imutável escrito só na criação de contexto. A diferença é real, não cosmética;
- os três usos do helper renomeado falham **antes de mutar**, cada um antes do respectivo `transact`;
- nenhum chamador órfão, import morto ou ramo inalcançável ficou para trás.

## Regressão R1–R7

**Nenhuma regressão.** Varredura independente por dois revisores: a tupla estrutural tem definição e consumidor únicos aplicados nos três verbos; o filtro de contexto continua antes da contagem de candidatos; os achados do R4 e do R5 seguem fechados com seus casos; o R6-2 e o R6-3 seguem fechados.

A segunda metade do L1 — recusar o preenchimento retroativo quando o contexto tem predecessor — foi removida **de propósito**, pelo caminho R6-1 → R7-1 opção A, com o motivo escrito no código. É supersessão registrada, não regressão.

R4-4 e R4-5 continuam **não verificáveis**, porque nunca foram declarados fechados: o R4 os remeteu a decisão humana e eles seguem pendentes.

## Constitution References

Nenhum conflito descoberto. 6.0.3 sem publicar, `main` em 6.0.2, sem novo bump exigido.

## Final Recommendation

**REQUEST CHANGES**: consertar os três Important, rodar `/speckit.converge`, depois verify e review de novo.

Os três são pequenos — uma edição de comentário, uma remoção de subcaso e uma validação de tipo — e nenhum muda comportamento observável salvo o R8-3, que troca falha genérica por recusa nomeada. Recomendo tratar junto os Minor n1 e n2, de uma linha cada. n3, n4 e n5 ficam como débito registrado.

---

# R9 — 2026-09-21, após a Phase 14

## Review Report

**Verdict: REQUEST CHANGES** — 0 Critical, 3 Important, 4 Minor

Source fingerprint: tree `558640a87ac05d5e827ab2d0c3ff4ebc348729a12bc59dadad3ed78951958a18` / work `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` / plan `e80b7eb29b7dfcc0cca450d8f46674bf9a2cdfca7b83f4e4a71dc3c0931db301` — casa com o converge rodada 18 e o verify rodada 9.

Dois revisores read-only. O coordenador reproduziu independentemente as duas mutações centrais.

## O que esta rodada diz, e não é sobre a entrega

A Phase 14 existiu **principalmente para consertar afirmações falsas**. O R9 achou que ela consertou **uma de três cópias** da principal, e que o conserto de uma guarda deixou outra guarda morta com um recibo de reversão falsificado no teste.

Nenhum achado é defeito de comportamento. Todos são o mesmo padrão, e ele agora tem oito rodadas de evidência: **esta entrega não erra escrevendo código, erra escrevendo o que o código faz.**

## Important

### R9-1 — A afirmação que causou o Critical do R7 sobrevive em duas outras cópias

`plugin/skills/grill-with-docs/scripts/grill_workspace.py:6128-6133` e `tests/validate_agent_orchestration_contract.py:1574-1578`

O T054 corrigiu o comentário do sítio de confirmação de etapa, que passou a dizer, corretamente:

> There is no upstream proof that the live branch is the one the context ran on: `branch` was pulled out of the structural tuple in T035, and two branches inside the same worktree look identical on project/path/git_common_dir alone.

Seis linhas adiante, o gêmeo do `phase-turn` **continua** dizendo o oposto:

> takeover and continuity-resume already refuse structural divergence before mutating -- so the live branch is trustworthy on its own.

E a docstring do caso de cunhagem repete a mesma alegação quase palavra por palavra. Uma varredura confirma que são as duas únicas cópias restantes.

É falso pelo motivo já estabelecido: `branch` saiu da tupla estrutural, então os guardas estruturais não provam nada sobre branca — e nenhum deles roda no caminho da virada de fase.

**Este é o texto que produziu o Critical do R7.** A instrução do T054 dizia "o comentário do sítio de cunhagem", no singular, e não mandou varrer por cópias. É **a sexta instrução minha** desta família, e a segunda em que a regra certa já estava escrita e não foi aplicada onde importava.

**Conserto**: replicar o texto corrigido nas duas cópias.

Contra FR-010.

### R9-2 — O T055 matou a guarda que o T047 criou, e o teste carrega um recibo de reversão falsificado

`plugin/skills/grill-with-docs/scripts/grill_workspace.py:3352-3354` e `tests/validate_agent_orchestration_contract.py:1450-1462`

Com a validação de tipo subindo para `_continuity_identity`, e como os três chamadores passam **o mesmo** `state` e chamam a derivação antes, a guarda `DEVELOPMENT-SCHEMA` dentro de `_continuity_refuse_branch_contradiction` tornou-se **inalcançável por qualquer caminho de CLI**.

Confirmado por mutação, reproduzida pelo coordenador de forma independente: trocando o `raise` por atribuição silenciosa, **os 44 testes passam**.

Pior é o que a docstring do caso afirma:

> Verified by reversion: replacing the `raise` with `development = {}` makes this case return PREVIEW/exit 0 instead of refusing.

Isso **não acontece mais**: o caso continua recusando, porque a recusa vem de outro ponto. É um recibo de reversão que já não descreve o sistema — a forma mais perigosa de afirmação falsa, porque parece prova.

E há ironia registrável: o caso do T053 foi escrito precisamente porque aquela guarda *"had no case proving it there"*. O T057, que eu pedi para tornar a guarda alcançável, devolveu-a a esse estado e ainda a tornou inalcançável.

**Conserto — recomendo manter a guarda, não apagá-la.** As duas opções são legítimas, e a escolha é doutrinária:

- apagar é o menor diff e elimina código morto;
- **manter** é o que a doutrina deste projeto exige: a função declara `state: Any`, o projeto é fail-closed, e apagar cria armadilha para um quarto chamador futuro que não passe pela derivação.

Validação em fronteira de confiança é justamente a categoria que não se simplifica por economia. Então: manter, **dizer na docstring que hoje ela é defesa em profundidade inalcançável pelos três verbos**, e dar-lhe cobertura própria com um caso que a chame diretamente. E repontar a docstring do T053 para nomear a guarda que ela de fato exercita, com um recibo de reversão verdadeiro — que o revisor já mediu: `(2, 'UNEXPECTED-FAILURE')`, `AttributeError`.

Contra FR-010 e FR-011.

### R9-3 — A cláusula que preserva "ausência é estado legítimo" não tem teste nenhum

`plugin/skills/grill-with-docs/scripts/grill_workspace.py:3298`

```python
if development is not None and not isinstance(development, dict):
```

Trocando por `if not isinstance(development, dict):` — isto é, transformando **ausência** em recusa — a suíte inteira fica verde.

O runtime está **correto**: bloco ausente ou nulo segue para `"unassigned"`, idêntico ao comportamento anterior. O defeito é de cobertura: a única linha que separa "ausência legítima" de "ausência recusada" não é protegida por nada, e a fase que introduziu a guarda não a cobriu.

Isso importa porque ausência de bloco de desenvolvimento é estado real — não hipótese. Uma regressão aqui recusaria work items legítimos, e nada avisaria.

**Conserto**: um subcaso com o bloco removido e fase ativa nula, afirmando que o verbo segue, com o digest do armazenamento inalterado como já se faz ali.

Contra FR-011.

## Minor

| # | Local | Achado |
|---|---|---|
| p1 | `tests/…:1443-1444` e `:1613` | As duas asserções de desigualdade são **tautológicas**: comparam um literal fixo com a branca da fixture. Neutralizar ambas para `pass` deixa os 44 testes verdes. Não são nocivas — são sanidade de fixture, e a asserção com valor real é o readback ao lado. O defeito é a **afirmação**: o commit e o sidecar do nó dizem que a mudança as tornou não-triviais, e não tornou |
| p2 | `tests/…:1603` | Ternário morto: nenhum subcaso carrega o rótulo que o seleciona desde a remoção do T056. Colapsar |
| p3 | `tests/…:1575-1577` | A docstring ainda anuncia três casos de carimbo — "absent, agreeing, or contradicting" — quando o do meio foi removido de propósito |
| p4 | `grill_workspace.py:3286-3299` | A recusa de HEAD solto precede a guarda de esquema, então HEAD solto com bloco malformado sai com o código de divergência, não o de esquema. Não é incorreto; é arbitrário e não testado. Registro, sem ação |

## Runtime Correctness

**Sem achado Critical ou Important.** As verificações voltaram limpas:

- a guarda nova está antes de todo acesso que assume mapping, e o único acesso vem depois dela;
- bloco **ausente** segue funcionando de forma idêntica ao anterior;
- nenhum outro caminho do CLI passou a receber recusa que antes não recebia. O único delta observável é fase ativa falsy com bloco não-mapping: antes falha genérica, agora recusa nomeada — que é exatamente o conserto pedido;
- os irmãos que leem o bloco sem passar pela derivação já têm proteção própria, por recusa nomeada ou `isinstance` explícito;
- **ganho não declarado**: a guarda nova também blindou um segundo sítio que tinha a mesma forma de falha, no emissor do checkpoint inicial. O nó não reportou isso.

## Test Quality

O T055 é **genuinamente exercitado**: revertendo a guarda, o caso falha com `(2, 'UNEXPECTED-FAILURE') != (2, 'DEVELOPMENT-SCHEMA')`.

Os dois sítios de cunhagem **seguem cobertos** com o subcaso removido — cada subcaso restante roda confirmação de etapa **e** virada de fase, com as asserções intactas. A simplificação não deixou asserção vazia; deixou tautológica, que é diferente e está no p1.

Nada sobrou testando comportamento que não existe mais.

## Regressão R1–R8

**Nenhuma regressão.** Verificado por dois revisores: a tupla estrutural segue com definição e consumidor únicos aplicados nos três verbos; a comparação de branca congelada do R7-1 segue removida; os achados de R3 a R6 e os do R8 seguem fechados.

## Constitution References

Nenhum conflito descoberto. 6.0.3 sem publicar, `main` em 6.0.2, sem novo bump exigido.

## Final Recommendation

**REQUEST CHANGES**: consertar os três Important, rodar `/speckit.converge`, depois verify e review de novo.

Recomendo tratar junto os Minor p1, p2 e p3, que são uma linha cada e todos da mesma família de afirmação desatualizada. p4 fica como registro.

**Observação de método, que vale mais que os achados**: o R9 não achou nenhum defeito de comportamento, pela segunda rodada seguida. O que ele achou foi que a fase dedicada a consertar afirmações falsas corrigiu uma de três cópias, e que o conserto de uma guarda produziu um recibo falsificado. Antes da próxima fase, a instrução precisa parar de nomear **o** ponto e passar a exigir a varredura — porque em todas as vezes em que isso falhou, a cópia esquecida estava a menos de dez linhas da corrigida.

---

# R10 — 2026-09-21, sobre a base integrada com a `main`

## Review Report

**Verdict: REQUEST CHANGES** — 0 Critical, 5 Important, 4 Minor

Source fingerprint: tree `872f172172b94aea0409562a9e05f601f552865b907283cc780b188b4580af85` / work `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` / plan `c93b998468329cb61546c4dd452596a539be41cebb562413508487f1e30c82c7` — casa com o converge rodada 21 e o verify rodada 10.

Dois auditores read-only. Esta rodada não revisa implementação nova: revisa uma **integração**. A `main` avançou sete commits durante a entrega, de 6.0.2 a 6.0.12, na mesma área da feature.

## O que a integração preservou

**Zero regressões de merge**, e a prova é por medição, não por leitura. O auditor de regressão rodou dez mutações sobre a árvore integrada e, para cada sobrevivente, **repetiu a mutação na árvore pré-integração** para demonstrar que já sobrevivia antes. Nenhum achado fechado entre R1 e R9 reabriu.

Sete mutações morreram como deviam, incluindo a que reintroduz o J1/H1: acrescentar `phase` e `branch` à tupla estrutural derruba cinco testes. **O conserto crítico desta entrega está protegido por prova, não por comentário** — o que importa porque o lado entrante do `prepare-switch` oferecia exatamente essa reintrodução.

Nada se perdeu do lado entrante: `gauntlet.py` e `gauntlet_runs.py` têm diff **zero** contra a `main`, os verbos novos estão presentes e alcançáveis, e o arquivo de teste recebeu 285 inserções com **zero deleções** — nenhum caso da 032 foi removido, renomeado ou teve asserção alterada.

## Important

### R10-1 — O atalho `REUSED` perdeu a checagem de origem na junção

`plugin/skills/grill-with-docs/scripts/grill_workspace.py:1799-1803`

Defeito de junção, do mesmo tipo do que a suíte pegou, mas este **nenhum teste pega**:

- o T006 removeu `origin`, `policy_sha256` e a checagem de líder do gate `REUSED`, porque `_adoption_conflict` passou a cobri-los. Na época, `_adoption_conflict` recusava **toda** origem alterada, então a igualdade de origem ficava implícita;
- o merge afrouxou `_adoption_conflict` para aceitar origem alterada quando há contexto corrente e escopo igual. **A implicação evaporou.**

Com origem alterada, escopo igual, apresentação igual e mesmo líder, o HEAD devolve `REUSED` sem entrar na mutação; a `main` devolveria `ORCHESTRATION-ADOPTED`. O estado em disco é idêntico nos dois — por isso nenhum teste reprova. O que diverge é o **veredito**: `REUSED` significa "repetição idêntica já aplicada", e a origem não é idêntica.

**Ressalva que reduz o alcance, e o auditor a verificou**: isto **não** quebra a paridade prévia/apply. O gate roda depois de `_adoption_conflict` nos dois caminhos, então não produz prévia que o apply recusaria. É infidelidade à semântica de `REUSED`, não inversão do invariante do T006.

**Conserto**: repor a igualdade de origem no gate, alinhando à precedência do apply.

Contra FR-010.

### R10-2 — A seção 6.0.12 do CHANGELOG desapareceu, e ela já shipou

`CHANGELOG.md:3`

Minha resolução do segundo merge **renomeou** `## 6.0.12` para `## 6.0.13` em vez de abrir seção nova. A `main` tem a seção, a tag `v6.0.12` existe e tem Release — a cláusula constitucional `Release obrigatória por versão` garante isso.

Consequência: quando esta branch voltar para a `main`, o CHANGELOG não terá entrada alguma para a 6.0.12, e o item `ownership-transfer`, **que shipou naquela versão**, passa a aparecer como novidade da 6.0.13.

É erro meu de resolução, não da `main`, e é de governança: o CHANGELOG é o registro público do que cada versão entregou.

**Conserto**: restaurar `## 6.0.12` com o bullet original e abrir `## 6.0.13` acima, só com os itens desta entrega. Há também uma linha em branco solta no meio da lista.

Contra a cláusula `Release obrigatória por versão`.

### R10-3 — O invariante do T006 não tem teste no caminho que o merge mexeu

`tests/validate_agent_orchestration_contract.py:2419` e `plugin/…/grill_workspace.py:1762-1770`

O T006 estabeleceu que a prévia de `orchestration-adopt` levanta a mesma recusa que o apply. O único teste de paridade cobre **apenas** `CONTEXT-FENCED`. Nenhum teste exercita origem alterada nesse comando, e `ORCHESTRATION-POLICY-STALE` aparece uma única vez em `tests/`, em outro verbo.

Ou seja: o invariante que esta entrega criou está sustentado por **alinhamento manual** entre duas funções, não por prova. Foi essa ausência que permitiu ao merge invertê-lo sem aviso — e a suíte só reprovou porque um teste **da `main`** exercitava o caminho.

Agrava que o comentário que deixei em `_adoption_conflict` é **verdadeiro por acidente**: ele descreve o ramo do apply que atualiza a apresentação, e esse ramo é inalcançável quando a apresentação já é igual, porque o `REUSED` retorna antes. Escrevi olhando para a mutação sem olhar as quatro linhas acima dela.

**Conserto**: um caso de paridade para o caminho de origem, exercitando prévia e apply na mesma entrada e exigindo o mesmo veredito.

Contra FR-011.

### R10-4 e R10-5 — As duas metades que o R6-2 mandou acrescentar não têm prova

`plugin/skills/grill-with-docs/scripts/grill_workspace.py:3776` (prepare-switch) e `:4162` (takeover)

Provado por mutação: trocar a chamada do ponto único por `pass` em **qualquer** dos dois deixa os 51 testes verdes.

Estas são exatamente as metades que o R6-2 mandou acrescentar, com o argumento de que a preparação de troca *"cria a operação, grava o ponto de retomada e libera o líder antes de qualquer checagem"*. O conserto entrou; a prova, não.

Cenário de falha, no verbo de preparação: work item vinculado a `A`, árvore em `B` — a troca cria a operação, grava o ponto de retomada e **libera o líder** sem recusar. A divergência só aparece na retomada, com o contexto já solto. É literalmente o defeito que o R6-2 descreveu.

**São pré-existentes, não da integração**, e o auditor provou isso rodando a mesma mutação na árvore pré-merge: também sobrevivia.

**Conserto**: um subcaso irmão em cada um dos dois métodos, semeando o vínculo numa branca diferente da viva e exigindo a recusa com digest do armazenamento inalterado.

Contra FR-011.

## Minor

| # | Local | Achado |
|---|---|---|
| q1 | `grill_workspace.py:3536-3537` | O fail-closed de carimbo malformado não tem prova: trocar `return False` por `return True` no ramo de não-mapping deixa os 51 verdes, e um `worktree_identity` presente porém não-mapping passa a ser **aceito** nos três comparadores. Estreito, porque o esquema do store normalmente impede, mas é guarda de fronteira sem teste. Uma linha no caso direto que o T061 já criou resolve |
| q2 | `converge.md` rodada 21 | A tabela de invariantes diz "uma definição, **dois usos**". A tupla tem **um** uso; o comparador tem **quatro** call sites em três verbos. Afirmação minha, mais forte que o fato — a mesma família que esta entrega passou dez rodadas combatendo |
| q3 | `grill_core/agent_runtime.py:1178` | O predicado da 032 classifica como terminal **qualquer** estado fora de `dispatched`/`running` — inclusive um hipotético `queued`, que seria líder que nem começou, e a tomada seria autorizada. Pré-existente da R1, não do merge; os quatro estados que a `main` conhece não o exercitam. Nada o guarda, nem teste nem comentário |
| q4 | `CHANGELOG.md:9` | Linha em branco solta no meio da lista, resíduo da resolução |

## Fragilidade de processo, que não é achado de código

**O conserto do J1/H1 não está na `main`.** Toda integração futura vai reoferecer a linha do lado entrante, e o comentário que explica por que recusá-la existe **só nesta branch** — quem resolver o conflito a partir da `main` não o vê.

A proteção real não é o comentário: são os dois testes que derrubam a reintrodução. Eles também só existem aqui. **A blindagem só nasce quando esta entrega chegar à `main`**, e até lá cada integração depende de alguém lembrar.

## Nota metodológica do auditor, que vale preservar

Rodar dez mutações reusando o mesmo diretório de cópia fez um teste falhar em **todas** as rodadas, inclusive nas que não o tocavam. Em cópia limpa por mutação o efeito some: era poluição entre execuções, não defeito do teste.

Registro porque quase produziu um falso positivo, e porque a instrução de "provar por mutação" que esta entrega adotou precisa dizer **uma cópia nova por mutação**.

## Constitution References

`Release obrigatória por versão` — citada pelo R10-2: a 6.0.12 tem tag e Release, e o CHANGELOG mesclado precisa preservar a seção dela.

## Final Recommendation

**REQUEST CHANGES**: consertar os cinco Important, rodar `/speckit.converge`, depois verify e review de novo.

Três observações sobre a natureza desta rodada:

1. **Nenhum achado é regressão da integração.** R10-1 e R10-2 são defeitos que **eu** introduzi ao resolver os merges; R10-3, R10-4 e R10-5 são lacunas de cobertura pré-existentes que a integração apenas tornou visíveis ao trazer testes que exercitam caminhos vizinhos.
2. **O merge produziu dois defeitos de junção, não um.** O primeiro a suíte pegou; o segundo nenhum teste pega, porque o estado em disco não muda. É o argumento mais forte desta entrega a favor de auditar merge com o rigor de código novo.
3. **Os três achados de cobertura têm a mesma forma**: um conserto entrou e a prova não. R10-4 e R10-5 são literalmente as metades do R6-2. Vale tratar como classe, não como três itens.

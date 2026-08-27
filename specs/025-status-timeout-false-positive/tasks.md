---

description: "Tasks: correção do falso positivo de STATUS-TIMEOUT em workspace acumulado (feature 025)"
---

# Tasks: Falso positivo de timeout no status do workspace

**Input**: Design documents from `/specs/025-status-timeout-false-positive/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/grill-status-v1.md, quickstart.md

**Tests**: TDD explicitamente pedido. A correção de código (`grill_status.py`, `grill_workspace.py`,
`validate_status_contract.py`) está **commitada** no baseline `7b3c3fe` como **implementação
candidata** (ADR-0001) — nenhuma tarefa abaixo assume que ela está correta; cada tarefa que a toca
precisa ler/rodar e confirmar sobre o blob commitado, não presumir. Nenhuma tarefa depende de
mudança solta em working tree.

**Baseline de produto**: a implementação candidata acima está materializada no commit `7b3c3fe`
(`fix(status): prevent false timeout on accumulated workspaces`), que detém os três caminhos
`plugin/skills/grill-with-docs/scripts/grill_status.py`,
`plugin/skills/grill-with-docs/scripts/grill_workspace.py` e `tests/validate_status_contract.py`
**antes** da partition em subfases desta feature. Todo worker desta execução parte desse HEAD;
T002–T009 auditam exatamente esse baseline, não um estado hipotético pós-partition. Materializar
essa candidata em commit **não** a valida nem autoriza publicação: o veredito depende de T002–T009
fecharem sem achado e do bump ainda pendente (ver ADR-0001, "Consequências").

**Organization**: Tarefas agrupadas por user story (spec.md). Tarefas são file-disjuntas sempre que
a dependência permite — marcadas `[P]`. Nenhuma tarefa edita `.grill/` nem `.specify/reports/`
(escrita de atestação é do leader/gauntlet, fora de escopo de worker aqui). Hooks opcionais de
commit (`before_tasks`, `after_tasks`) foram detectados e **não** executados nesta geração.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependência). A ausência de `[P]`
  é declaração de serialidade obrigatória, não omissão.
- **[Story]**: `US1`, `US2` ou `US3` — mapeamento em spec.md. Tarefas **cross-cutting** (que
  não pertencem a uma única user story) usam a etiqueta **`[X]`** no lugar de `[Story]`, e a
  descrição nomeia os FR/SC que a tarefa fecha. São cross-cutting: T001 (baseline), T002–T004
  (auditoria do baseline pré-partition) e T010–T022 (bump, distribuição, CHANGELOG, gates).
- Caminhos de arquivo exatos em cada descrição.

### Regra fail-closed de achados (C2)

Qualquer **achado** registrado por T002, T003, T004 ou T008 — valor divergente, forma de
código diferente da descrita, teste reprovando, asserção mais fraca do que o exigido —
**bloqueia todas as fases seguintes**. Não há waiver, não há "seguir e anotar depois": a
execução para no checkpoint da fase, o achado é remediado e a tarefa que o produziu é
**reexecutada até passar limpa** antes de qualquer tarefa a jusante começar. Em particular,
nenhuma tarefa de bump (T010–T018) pode iniciar com achado aberto: bumpar a versão de uma
correção não validada publica uma afirmação sem evidência.

### Onde as tarefas de gate rodam (N1)

**T019–T022 executam exclusivamente no worktree coordenador da run**, e só **depois de todos os
waves da etapa `implement-parallel` convergirem** e de `tasks.md` ser **reconciliado**. Regras,
sem exceção:

1. Esse worktree contém **somente paths commitados da branch** `025-status-timeout-false-positive`
   e, no momento da execução dessas quatro tarefas, seu `git status --porcelain` **sai vazio**.
   Árvore limpa aqui é propriedade estrutural do worktree, não um passo de limpeza manual.
2. **Nenhum worker** roda T019–T022 dentro do próprio worktree de nó, e **nenhuma** dessas tarefas
   roda a partir do workspace principal.
3. **Sujeira do workspace principal e de work items irmãos não participa**: `.specify/feature.json`
   modificado, bundles não versionados (por exemplo `fix-attestation-registry-anchor-…`), atestações
   e evidências ainda não commitadas não existem no worktree coordenador, não sujam o
   `git status --porcelain` avaliado e não entram no SHA avaliado. Observá-las no workspace
   principal **não** é achado destas tarefas e **não** autoriza waiver da pré-condição de árvore
   limpa — se os gates foram rodados de lá, a execução é inválida e se repete no worktree
   coordenador.
4. **Obrigação do leader, antes de despachar**: (a) commitar os artefatos relacionados desta
   feature — `specs/025-status-timeout-false-positive/`, o bundle do work item
   `fix-status-timeout-false-positive-79cd99681a234f65a93a092b678e39b3` e as atestações das etapas
   já fechadas — **antes da partition**; (b) commitar o **Execution DAG e o relatório de partition
   antes do primeiro worker** ser despachado. Sem isso, workers partem de bases divergentes e a
   igualdade de SHA exigida por T022 deixa de significar igualdade de árvore avaliada.

---

## Phase 1: Setup

**Purpose**: Confirmar o ponto de partida real antes de qualquer mudança de versão/distribuição.

- [ ] T001 [X] Rodar `python3 tests/run_validators.py` a partir da raiz do repo e registrar o resultado
      literal (exit code, contagem de testes, quaisquer falhas). Não assumir "vai passar" — este é
      o baseline real do commit `7b3c3fe`, que já detém a correção de
      `grill_status.py`/`grill_workspace.py` e ainda **não** tem bump de versão. Esperado: exit 0, baseline ≥1303 testes em 27
      validadores (ver `CLAUDE.md`), mas o resultado real é o que conta, não a expectativa.
      **Composição da contagem**: `run_validators.py` soma as saídas de 26 módulos `unittest`
      (`validate_*.py` descobertos por glob) mais a execução à parte de `validate_distribution.py`,
      que é um script de asserções simples (não `unittest`) e **não contribui** para a contagem de
      testes reportada — ele só soma ao veredito exit 0/1 da suíte.

**Checkpoint**: baseline real capturado — segue para Foundational apenas se T001 não travar em erro
de ambiente (rede, `specify`/`node`/`backlogctl` reais são proibidos pela matriz e não devem
aparecer nas falhas).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Auditar a implementação preexistente linha a linha antes de confiar nela em qualquer
user story. Nenhuma user story pode iniciar antes de T002–T004 confirmarem, por leitura e execução
real, que o código **commitado em `7b3c3fe`** faz o que o ADR-0001/data-model.md descrevem.

**⚠️ CRITICAL**: Não pular para as user stories sem esta auditoria — o pedido do usuário é validar
o código preexistente como candidato, não aceitar de cabeça. O fato de ele já estar commitado em
`7b3c3fe` é conveniência de distribuição para os workers, **não** um atestado de correção.

- [ ] T002 [P] [X] Ler `plugin/skills/grill-with-docs/scripts/grill_workspace.py` e confirmar, por
      inspeção direta (não grep solto), que existe uma constante de módulo
      `STATUS_TIMEOUT_SECONDS = 30` e que **ambos** `status_command` e `status_markdown_command` a
      usam como `timeout=` na chamada que invoca `grill_status.py` (linhas atuais ~3760, ~3777,
      ~3804). Se o valor não for exatamente `30` ou se algum dos dois comandos não a referenciar,
      registrar como achado — não corrigir silenciosamente nesta tarefa.
- [ ] T003 [P] [X] Ler `plugin/skills/grill-with-docs/scripts/grill_status.py` e confirmar, por
      inspeção direta:
      (a) `local_branches` é resolvido **uma vez** em `build_status()` via
      `git for-each-ref --format=%(refname:short) refs/heads`, antes do laço de worktrees;
      (b) `live_state = live(worktree)` é calculado **uma vez por worktree**, antes do laço de
      work items daquele worktree;
      (c) `item_payload()` recebe `live_state` e `local_branches` por parâmetro e **não** chama
      `live()` nem resolve branches locais internamente;
      (d) `branch_alive` testa pertencimento em `local_branches` (operação em memória), sem
      spawnar `git rev-parse --verify` por item.
      Documentar qualquer desvio encontrado em vez de assumir que o data-model.md já está refletido
      corretamente no código.
- [ ] T004 [X] Rodar `python3 -m unittest tests.validate_status_contract -v` isolado (sem o
      restante da suíte) e confirmar que **todos** os casos passam, incluindo
      `test_live_git_state_is_resolved_once_per_worktree_not_per_item`. Depende de T002 e T003
      confirmarem a forma do código antes de rodar o teste sobre ele.
      **Fecha FR-005 (contrato `grill-status/v1` inalterado)**: a preservação não é inferida da
      ausência de diff — esta execução verifica os casos que cobrem o schema `grill-status/v1` e
      os códigos enumerados em `contracts/grill-status-v1.md` (`STATUS-TIMEOUT`,
      `STATUS-INVALID-OUTPUT`, `STATUS-SCHEMA`, `WORK-ITEM-MISSING`). Registrar nominalmente
      quais casos cobrem esses códigos/schema; se algum não existir ou não passar, é achado que
      dispara a regra fail-closed acima (FR-005 fica não comprovado).

**Checkpoint (fail-closed)**: código preexistente auditado (leitura) e testado (execução).
As user stories abaixo só prosseguem se T002, T003 e T004 fecharem **sem nenhum achado
aberto**. Um único achado registrado por qualquer uma das três — `STATUS_TIMEOUT_SECONDS`
diferente de `30`, um dos dois comandos sem referenciar a constante, `live()`/`local_branches`
resolvidos fora do escopo descrito, `item_payload()` chamando `live()` internamente, ou
qualquer caso reprovando — **para a execução aqui**. Remediar e reexecutar a tarefa até ela
passar limpa; só então avançar. Nada de "seguir e anotar depois". O baseline estar commitado não
reduz o rigor: reverter/corrigir um blob commitado é o remédio esperado se houver achado.

---

## Phase 3: User Story 1 - Diagnóstico completo em workspace real acumulado (Priority: P1) 🎯 MVP

**Goal**: `status` (JSON e Markdown) completa sem `STATUS-TIMEOUT` num workspace real de pior caso.

**Independent Test** (spec.md): rodar o status em JSON e em Markdown contra um workspace real com
múltiplos work items em múltiplos worktrees e confirmar retorno sem `STATUS-TIMEOUT`, dentro do
timeout público de 30s.

> **Serialidade obrigatória (P1)**: T005 e T006 medem **tempo de parede**. Rodá-las em
> paralelo faria as duas disputarem CPU, I/O de disco e processos `git`, inflando a própria
> grandeza medida e invalidando a comparação com os 10,56s de referência. Elas **não** levam
> `[P]`: T006 só começa depois de T005 terminar.
>
> **Argumento posicional obrigatório (U1)**: o subcomando é
> `grill_workspace.py status ROOT [--format ...]` — `root` é posicional e obrigatório
> (`status_parser.add_argument("root")`). Omiti-lo faz o `argparse` sair com código 2 antes de
> medir coisa alguma. Rodar da raiz do repositório, passando `.`.

- [ ] T005 [US1] Medir o tempo de parede real do formato JSON contra a árvore real do
      repositório (não fixture sintética), **da raiz do repo**:
      `time python3 plugin/skills/grill-with-docs/scripts/grill_workspace.py status .`
      Confirmar: exit code 0 (não 2 — 2 seria erro de uso, não medição); nenhuma ocorrência de
      `STATUS-TIMEOUT` no payload; tempo de parede registrado e comparado com margem confortável
      sob 30s (referência: 10,56s medidos em
      `.grill/evidence/grill-status-timeout-debug-report.md`). Se o tempo se aproximar de 30s,
      registrar como achado a revalidar antes do ship (research.md, "Verificação — timing real").
- [ ] T006 [US1] **Depois de T005 terminar** (nunca concorrente), medir o tempo de parede real do
      formato Markdown contra a mesma árvore real:
      `time python3 plugin/skills/grill-with-docs/scripts/grill_workspace.py status . --format markdown`
      Confirmar: exit code 0; nenhuma linha de fallback
      `| workspace | blocked | STATUS-TIMEOUT: ... |`; tempo de parede registrado com a mesma
      margem de T005. Registrar os dois tempos lado a lado, anotando que foram medidos em
      série.

**Checkpoint**: SC-001 verificado com timing real, não apenas com fixture — US1 entregável como MVP.

---

## Phase 4: User Story 2 - Custo não cresce com número de work items no mesmo worktree (Priority: P2)

**Goal**: custo de execução por worktree/repositório, não por work item.

**Independent Test** (spec.md): rodar o status num worktree único com múltiplos work items e
confirmar que o custo não cresce proporcionalmente à quantidade de itens.

- [ ] T007 [US2] Rodar isoladamente:
      `python3 -m unittest tests.validate_status_contract.StatusPublicContract.test_live_git_state_is_resolved_once_per_worktree_not_per_item -v`
      Confirmar PASS e que a asserção `observed.assert_called_once_with(self.r.resolve())` se
      sustenta com **dois** work items no mesmo worktree (`work-a`, `work-b`) — ou seja, `live()` é
      chamado exatamente uma vez por worktree, independente do número de itens (SC-002). Depende de
      T004 (ambiente já confirmado capaz de rodar o módulo).

**Checkpoint**: SC-002 verificado por prova estrutural (contagem de chamadas), não apenas por
tempo — imune a variância de máquina.

---

## Phase 5: User Story 3 - Regressão de custo por item fica travada por teste dedicado (Priority: P3)

**Goal**: uma futura reintrodução de custo O(items) é pega automaticamente pela suíte, antes de
voltar a bloquear workspaces reais.

**Independent Test** (spec.md): confirmar que existe um teste dedicado que reprova a regressão de
custo por item, e que ele roda como parte da suíte padrão (não é um teste órfão manual).

- [ ] T008 [US3] Ler `tests/validate_status_contract.py:100-109`
      (`test_live_git_state_is_resolved_once_per_worktree_not_per_item`) e confirmar que a asserção
      trava **contagem de chamadas** ao probe (`mock.patch.object(module, "live", wraps=module.live)`
      + `assert_called_once_with`), não tempo decorrido. Documentar explicitamente essa
      característica — é o que torna o teste determinístico e imune a CI lento/rápido
      (research.md, Decisão 3). Se o teste medisse apenas `elapsed < N`, registrar como achado
      grave (o teste não cumpriria FR-004).
- [ ] T009 [US3] Confirmar que `tests/run_validators.py` descobre `tests/validate_status_contract.py`
      automaticamente pelo glob `validate_*.py` (ler o padrão de descoberta em
      `tests/run_validators.py`) — ou seja, o teste de regressão roda em toda execução da suíte
      completa (`python3 tests/run_validators.py`) sem registro manual adicional, fechando FR-004
      em nível de suíte, não só de arquivo isolado.

**Checkpoint (fail-closed)**: FR-004/SC-003 verificados — regressão travada e descoberta
automaticamente pela suíte. Se T008 constatar que a asserção mede tempo decorrido em vez de
contagem de chamadas, ou que a asserção é mais fraca que `assert_called_once_with`, isso é
achado **grave** (FR-004 não cumprido): a Phase 6 não inicia até o teste ser corrigido e T008
reexecutada limpa. Idem para T009, se o teste não for descoberto pelo glob da suíte.

---

## Phase 6: Polish & Cross-Cutting Concerns — Bump, Distribuição, CHANGELOG, Gates

**Purpose**: sincronizar os 8 locais de distribuição, o CHANGELOG, e confirmar os gates
fail-closed. Todas as tarefas desta fase são cross-cutting (`[X]`) e fecham FR-006/FR-007/FR-008
e SC-004/SC-005/SC-006. Cada bump de arquivo é file-disjunto dos demais — T010–T018 são `[P]`.
Depende das Phases 1–5 **sem achado aberto** (código validado antes de bumpar a versão que o
descreve).

> **Pré-condição de commit, convergência e local de execução (D1/D2/N1)**: T019–T022 leem estado
> **commitado** e rodam **exclusivamente no worktree coordenador da run**, depois de **todos os
> waves convergirem** e de `tasks.md` ser **reconciliado** (regras completas em "Onde as tarefas de
> gate rodam"). `check_version_bump.py` decide sobre blobs
> (`git diff --no-renames --name-only main...HEAD` + `git show <rev>:plugin/.claude-plugin/plugin.json`).
> **Estado pré-bump desta branch**: como `7b3c3fe` alterou `plugin/**` sem bump, o veredito atual do
> gate é literalmente `MISSING-BUMP` / `verdict: FAIL`, com `base_version` e `head_version` ambos
> `5.2.0` — o gate já reprova, e T010–T018 existem para virá-lo. `NO-PLUGIN-CHANGE` sobrou como
> **código residual rejeitado**: descreve a árvore em que `plugin/**` não mudou no SHA avaliado,
> impossível a partir de `7b3c3fe`; se aparecer, é `--base-ref`/HEAD errados e é falha. Na trilha do
> gauntlet, os workers de `implement-parallel` **commitam** seus nós nos respectivos worktrees e
> `converge` integra tudo **antes** de T020 rodar. Portanto, ao entrar em T019, no worktree
> coordenador: `git status --porcelain` sai **vazio** e o bump de T010–T018 está no HEAD.

- [ ] T010 [P] [X] Atualizar `"version": "5.2.0"` → `"version": "5.2.1"` em
      `plugin/.claude-plugin/plugin.json`
- [ ] T011 [P] [X] Atualizar `"version": "5.2.0"` → `"version": "5.2.1"` em
      `plugin/.codex-plugin/plugin.json`
- [ ] T012 [P] [X] Atualizar `plugins[0].version` de `"5.2.0"` → `"5.2.1"` em
      `.claude-plugin/marketplace.json`
- [ ] T013 [P] [X] Atualizar `plugins[0].version` de `"5.2.0"` → `"5.2.1"` em
      `.agents/plugins/marketplace.json`
- [ ] T014 [P] [X] Em `tests/validate_distribution.py`, duas mudanças no mesmo arquivo
      (portanto uma única tarefa, sem conflito com as demais `[P]`):
      (a) atualizar a constante `VERSION = "5.2.0"` → `VERSION = "5.2.1"`;
      (b) **estender o validador para travar o CHANGELOG** (fecha C1 do `analysis.md`): antes do
      `print("distribution: OK")`, ler `CHANGELOG.md` da raiz e afirmar que existe **exatamente
      uma** linha igual a `## {VERSION}` (formato já usado pelas entradas anteriores: `## 5.2.0`),
      com mensagem de assert nomeando o arquivo e a versão esperada. Sem isso, FR-007/SC-005
      dependeriam de conferência humana e nenhum gate reprovaria um ship sem entrada de CHANGELOG.
      A asserção casa a própria constante `VERSION`, então o próximo bump reprova sozinho se o
      CHANGELOG não acompanhar.
- [ ] T015 [P] [X] Atualizar o heading `# Grill with Docs v5.2.0` → `# Grill with Docs v5.2.1` em
      `plugin/skills/grill-with-docs/SKILL.md`
- [ ] T016 [P] [X] Atualizar o heading `# Protocolo de sessão v5.2.0` → `# Protocolo de sessão v5.2.1`
      em `plugin/skills/grill-with-docs/references/session-protocol.md`
- [ ] T017 [P] [X] Atualizar o heading `**v5.2.0 · MIT**` → `**v5.2.1 · MIT**` (ou equivalente exato já
      presente) em `README.md`
- [ ] T018 [P] [X] Adicionar entrada `## 5.2.1` no topo de `CHANGELOG.md` (acima de `## 5.2.0`),
      descrevendo em prosa, no mesmo estilo das entradas anteriores: o falso positivo de
      `STATUS-TIMEOUT` corrigido, o escopo dos probes Git movido de por-work-item para
      por-worktree/repositório, e o timeout público subindo de 5s para 30s (FR-007/SC-005).
- [ ] T019 [X] **No worktree coordenador da run** (waves convergidos, `tasks.md` reconciliado),
      rodar `python3 tests/validate_distribution.py` e confirmar `distribution: OK`
      com os 8 locais coerentes em `5.2.1` **e** a nova asserção de T014 encontrando exatamente
      uma linha `## 5.2.1` em `CHANGELOG.md` (fecha FR-006/SC-004 e FR-007/SC-005). Depende de
      T010–T018 completas.
- [ ] T020 [X] **No worktree coordenador da run**, com o bump já **commitado e convergido** (ver
      pré-condição acima), rodar
      `python3 tests/check_version_bump.py --base-ref main --json` e exigir que o campo `code`
      seja **literalmente `BUMPED`**, com `verdict: PASS`, `base_version: "5.2.0"` e
      `head_version: "5.2.1"`.
      **Ponto de partida**: antes de T010–T018, este mesmo comando devolve `MISSING-BUMP` /
      `verdict: FAIL` (`5.2.0` → `5.2.0`), porque `7b3c3fe` já alterou `plugin/**` sem bump. Ver
      `MISSING-BUMP` **depois** do bump significa que o bump não entrou no SHA avaliado — falha.
      **`NO-PLUGIN-CHANGE` é código residual rejeitado**: descreve a árvore em que `plugin/**` não
      mudou no SHA avaliado, impossível a partir de `7b3c3fe`; se aparecer (apesar do exit 0), é
      `--base-ref`/HEAD errados e é **falha**, nunca aprovação. Não basta conferir o exit code; a
      verificação é sobre o campo `code`. `VERSION-REGRESSION` e `VERSION-UNREADABLE` também são
      falha. Qualquer código diferente de `BUMPED` bloqueia T021/T022 e o ship (FR-008/SC-006).
      Sequencial em relação a T019 — T019 e T020 **não** rodam em paralelo (T020 exige a árvore
      commitada que T019 acabou de validar; ver F2 do `analysis.md`).
- [ ] T021 [X] **No worktree coordenador da run**, rodar a suíte completa novamente:
      `python3 tests/run_validators.py`. Confirmar exit 0 e
      comparar a contagem de testes/validadores contra o baseline capturado em T001 — nenhuma
      tarefa desta fase deveria alterar a contagem de testes (só valores de versão e prosa).
      Qualquer divergência, sem exceção, é achado a investigar antes do ship — inclusive a
      asserção nova de CHANGELOG introduzida por T014 (depende de T019–T020).
- [ ] T022 [X] Verificação fail-closed dos dois gates de distribuição — **fecha FR-008/SC-006**
      (plan.md, seção "Fail-Closed: `bump-gate.yml` × `ci.yml`").
      **Pré-condições explícitas, verificadas nesta ordem e registradas literalmente**, todas
      **dentro do worktree coordenador da run** (waves convergidos, `tasks.md` reconciliado):
      (a) `git status --porcelain` sai **vazio** — o worktree coordenador contém só paths
      commitados da branch, então todo o bump está commitado e convergido; com árvore suja a
      igualdade de SHA entre as rodadas não significa igualdade de árvore avaliada, e a verificação
      não prova o que FR-008 pede. Sujeira do workspace principal e de work items irmãos
      (`.specify/feature.json`, bundles não versionados, atestações não commitadas) **não
      participa** desta checagem e não é achado desta tarefa;
      (b) `git rev-parse HEAD` registrado **antes** das duas execuções;
      (c) `check_version_bump.py --base-ref main --json` reportando `code == "BUMPED"` (T020) e
      `run_validators.py` com exit 0 (T021), ambos sobre esse mesmo HEAD;
      (d) `git rev-parse HEAD` registrado **depois**, e **idêntico** ao de (b), com
      `git status --porcelain` ainda vazio.
      Qualquer divergência entre (b) e (d), qualquer sujeira em (a)/(d), ou qualquer código
      diferente de `BUMPED` invalida as duas execuções: as duas são refeitas juntas sobre o novo
      SHA, sem waiver — e rodar esta tarefa fora do worktree coordenador invalida a execução em vez
      de justificar exceção. Isso não substitui a checagem em CI na PR real — `bump-gate.yml` e
      `ci.yml` ainda precisam passar verdes na mesma revisão de topo antes do ship; uma
      re-execução verde de um gate após nova alteração invalida a aprovação anterior do outro
      para aquele SHA. Nenhuma escrita em `.grill/` ou `.specify/reports/` nesta tarefa — isso é
      atestação, fora de escopo de worker.

**Checkpoint (fail-closed)**: FR-006/FR-007/FR-008 e SC-004/SC-005/SC-006 verificados; ambos
os gates confirmados localmente sobre o **mesmo SHA** e a **mesma árvore limpa**, com o gate de
bump reportando literalmente `BUMPED`.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências — roda primeiro.
- **Foundational (Phase 2)**: depende de Setup (T001) só para ter o baseline registrado; T002/T003
  são leitura pura e podem começar em paralelo com T001 terminando; T004 depende de T002+T003.
  **BLOQUEIA** todas as user stories — e bloqueia fail-closed: qualquer achado em T002/T003/T004
  para a execução até a remediação e a reexecução limpa da tarefa (ver "Regra fail-closed de
  achados").
- **User Stories (Phase 3–5)**: todas dependem de Foundational (T002–T004) completo **e sem
  achado aberto**.
  - US1 (T005, T006): sem dependência de US2/US3, mas **T006 depende de T005** — as duas medem
    tempo de parede e são serializadas de propósito.
  - US2 (T007): depende de T004 (ambiente do módulo já confirmado); sem dependência de US1/US3.
  - US3 (T008, T009): leitura pura, sem dependência de execução de US1/US2, mas conceitualmente
    segue Foundational.
  - US3 (T008): achado grave aqui (asserção por tempo em vez de contagem de chamadas) bloqueia
    a Phase 6 inteira.
- **Polish (Phase 6)**: T010–T018 só começam com Phases 2–5 fechadas **sem achado aberto** (não
  faz sentido bumpar a versão de uma correção ainda não validada). T019 depende de T010–T018.
  T020 depende de T019 **e** do commit/convergência do bump (blobs commitados, não working tree).
  T021 depende de T019–T020. T022 depende de T020 e T021 e exige árvore limpa e o mesmo HEAD nas
  duas rodadas. **T019–T022 dependem, além disso, do local de execução**: só rodam no worktree
  coordenador da run, com todos os waves convergidos e `tasks.md` reconciliado.

### Parallel Opportunities

- T002 e T003 em paralelo (arquivos diferentes: `grill_workspace.py` vs `grill_status.py`).
- **T005 e T006 NÃO rodam em paralelo.** Ambas medem tempo de parede; concorrência entre elas
  disputa CPU, disco e processos `git` e contamina a própria grandeza medida. São serializadas
  (T005 → T006) e por isso não levam `[P]`.
- T010–T018 em paralelo entre si — 9 arquivos disjuntos, nenhuma dependência cruzada.
- **T019 → T020 → T021 → T022 são estritamente sequenciais.** T020 exige o bump commitado e
  convergido que T019 validou, T021 compara contra o baseline pós-bump, e T022 exige que T020 e
  T021 tenham rodado sobre o mesmo HEAD com árvore limpa. Nenhuma delas leva `[P]`.

---

## Parallel Example: Foundational

```bash
# T002 e T003 em paralelo — leitura de arquivos diferentes
Task: "Auditar STATUS_TIMEOUT_SECONDS=30 em plugin/skills/grill-with-docs/scripts/grill_workspace.py"
Task: "Auditar escopo por worktree/repositório em plugin/skills/grill-with-docs/scripts/grill_status.py"
```

## Parallel Example: Bump de distribuição (Phase 6)

```bash
# T010-T018 — 9 arquivos file-disjuntos, todos [P]
Task: "Bump plugin/.claude-plugin/plugin.json → 5.2.1"
Task: "Bump plugin/.codex-plugin/plugin.json → 5.2.1"
Task: "Bump .claude-plugin/marketplace.json → 5.2.1"
Task: "Bump .agents/plugins/marketplace.json → 5.2.1"
Task: "Bump VERSION → 5.2.1 e adicionar asserção de heading '## 5.2.1' no CHANGELOG em tests/validate_distribution.py"
Task: "Bump heading em plugin/skills/grill-with-docs/SKILL.md → v5.2.1"
Task: "Bump heading em plugin/skills/grill-with-docs/references/session-protocol.md → v5.2.1"
Task: "Bump heading em README.md → v5.2.1"
Task: "Adicionar entrada ## 5.2.1 em CHANGELOG.md"
```

---

## Implementation Strategy

### MVP First (User Story 1 apenas)

1. Phase 1: Setup (T001)
2. Phase 2: Foundational (T002–T004) — CRÍTICO, valida o código preexistente antes de confiar nele
3. Phase 3: User Story 1 (T005 e depois T006, em série) — timing real sem `STATUS-TIMEOUT`
4. **PARE e VALIDE**: SC-001 confirmado com timing real, não fixture
5. Só então considerar bump/release (Phase 6) — bumpar antes de validar US1 seria versionar uma
   correção ainda não comprovada em timing real.

### Incremental Delivery

1. Setup + Foundational → base validada
2. US1 → SC-001 confirmado (MVP: falso positivo eliminado no caso real)
3. US2 → SC-002 confirmado (custo não escala por item, prova estrutural)
4. US3 → FR-004/SC-003 confirmado (regressão travada e descoberta pela suíte)
5. Polish → bump 5.2.1, CHANGELOG (com gate no validador), distribuição, gates fail-closed sobre
   o mesmo SHA — só depois de 1–4 fechados sem achado aberto

---

## Notes

- Nenhuma tarefa assume que `grill_status.py`/`grill_workspace.py` já estão corretos: T002–T004,
  T008–T009 exigem leitura e execução real antes de qualquer tarefa de bump confiar no código.
- Nenhuma tarefa escreve em `.grill/` ou `.specify/reports/` — atestação/receipt é responsabilidade
  do leader/gauntlet, não deste tasks.md.
- Hooks opcionais de commit (`before_tasks`, `after_tasks` → `speckit.git.commit`,
  `speckit.agent-assign.assign`) foram detectados em `.specify/extensions.yml` e **não** executados
  por instrução explícita do usuário.
- [P] = arquivos diferentes, sem dependência. A ausência de [P] é serialidade obrigatória.
- [Story] mapeia a tarefa à user story correspondente em spec.md; [X] marca tarefa cross-cutting,
  cuja descrição nomeia os FR/SC que ela fecha.
- `.specify/feature.json` aparece modificado no working tree, mas é **artefato gerado** pelos
  scripts do Spec Kit (seleção da feature ativa), não superfície de produto nem de distribuição:
  nenhuma tarefa deste arquivo o edita (ver `plan.md §Project Structure`).
- Achado em T002/T003/T004/T008 é parada, não anotação: bloqueia todas as fases seguintes até a
  remediação e a reexecução limpa da tarefa.
- T019–T022 rodam só no worktree coordenador da run, após convergência de todos os waves e
  reconciliação de `tasks.md`; sujeira do workspace principal e de work items irmãos não participa
  (ver "Onde as tarefas de gate rodam").
- Pare em qualquer checkpoint para validar a story isoladamente antes de avançar.

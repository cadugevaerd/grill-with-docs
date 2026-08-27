# Release Checklist: Falso positivo de timeout no status do workspace

**Purpose**: Unit tests for requirements — valida qualidade dos requisitos antes do release (audiência: reviewer; profundidade: rigorosa)
**Created**: 2026-08-26
**Feature**: [spec.md](../spec.md) · [plan.md](../plan.md)
**Foco**: requisitos de performance, falso timeout, contrato `grill-status/v1`, regressão por escopo de probes Git, bump SemVer nos 8 locais, CHANGELOG, gates de distribuição, timing real

## Requisitos de Performance (Clareza/Mensurabilidade)

- [x] CHK001 O pior caso medido está quantificado com número absoluto (não termo vago tipo "lento")? [Clarity, Spec §FR-003] — 10,56s citado explicitamente.
- [x] CHK002 A restrição de margem do timeout é testável objetivamente (não cair abaixo de um valor medido)? [Measurability, Spec §FR-003]
- [x] CHK003 O requisito de custo distingue explicitamente o caso trivial (single-item) do pior caso (multi-item/multi-worktree)? [Coverage, Spec §Edge Cases]
- [x] CHK004 O requisito de escalabilidade (custo por worktree, não por item) é formulado como propriedade mensurável/testável, não como "eficiente" vago? [Measurability, Spec §FR-002]
- [x] CHK005 O valor concreto do timeout público (30s) está fixado em algum artefato rastreável a partir do spec? [Traceability, Spec §FR-003] — corrigido: FR-003 agora pina `STATUS_TIMEOUT_SECONDS = 30` explicitamente, com referência cruzada a `research.md`, Decisão 2 (as decisões numeradas vivem em `research.md`; a referência anterior a `plan.md` Decisão 2 apontava para uma seção inexistente — finding X1).

## Falso Positivo de Timeout (STATUS-TIMEOUT)

- [x] CHK006 O código de falha `STATUS-TIMEOUT` está amarrado a uma condição mensurável (estouro do timeout) e não a uma noção subjetiva de "lentidão"? [Clarity, Spec §FR-001]
- [x] CHK007 Existe requisito impedindo que o timeout seja reduzido abaixo do pior caso medido em mudança futura? [Spec §FR-003, Edge Cases]
- [x] CHK008 A rationale para não elevar o timeout muito acima de 30s (evitar mascarar travamento real) está referenciada a partir do spec? [Traceability, Spec §Edge Cases, §FR-003] — corrigido: novo bullet em Edge Cases e cláusula em FR-003 declaram 30s como teto deliberado, com link a `research.md` Decisão 2.
- [x] CHK009 O cenário edge "workspace com único work item" está definido com expectativa mensurável (permanece rápido, sem timeout)? [Coverage, Spec §Edge Cases]

## Contrato `grill-status/v1`

- [x] CHK010 O spec declara explicitamente que schema e formato de saída do contrato público permanecem inalterados? [Spec §FR-005]
- [x] CHK011 O escopo de "inalterado" está desambiguado entre contrato público (schema/códigos/Markdown) e comportamento interno (custo/timeout), evitando confundir os dois? [Clarity] — `contracts/grill-status-v1.md` seção "O que esta correção altera (não-contratual, interno)" resolve a ambiguidade.
- [x] CHK012 Os códigos de contrato preservados (`STATUS-TIMEOUT`, `STATUS-INVALID-OUTPUT`, `STATUS-SCHEMA`, `WORK-ITEM-MISSING`) estão enumerados em artefato rastreável a partir do FR-005? [Traceability, Spec §FR-005 → contracts/grill-status-v1.md]
- [x] CHK013 A suposição "esta correção não altera o contrato" é consistente entre `spec.md §Assumptions` e `contracts/grill-status-v1.md`? [Consistency]

## Regressão por Escopo de Probes Git

- [x] CHK014 O requisito de teste de regressão é específico o bastante para ser verificado objetivamente (não apenas "adicionar testes")? [Measurability, Spec §FR-004]
- [x] CHK015 O critério de aceite distingue custo-por-worktree de custo-por-item de forma mensurável? [Spec §SC-002]
- [x] CHK016 O cenário de regressão (User Story 3) é testável de forma independente, sem depender do fixture real de pior caso? [Coverage, Spec §User Story 3]
- [x] CHK017 O requisito de regressão trava a propriedade estrutural (contagem de chamadas ao probe) e não só um limite de tempo frágil? [Measurability, Gap-check] — confirmado: `research.md` Decisão 3 rejeita assert só-de-tempo por ser flaky.

## Bump SemVer / 8 Locais de Distribuição

- [x] CHK018 O requisito fixa o número exato de locais de distribuição a manter coerentes ("oito"), sem ambiguidade de contagem? [Clarity, Spec §FR-006]
- [x] CHK019 O tipo de bump (patch/minor/major) é resolvido por regra documentada e amarrada a FR-005, em vez de deixado a critério do implementador? [Traceability, research.md §Decisão 4]
- [x] CHK020 O critério de aceite de coerência de versão é mensurável via gate automatizado existente? [Measurability, Spec §SC-004 → tests/validate_distribution.py]
- [x] CHK021 O estado atual dos 8 locais (todos em 5.2.0, sem entrada 5.2.1 no CHANGELOG) é consistente com "bump ainda pendente de implementação", sem drift entre plan.md e o repositório? [Consistency] — reafirmado na 5ª revisão: com a correção já commitada em `7b3c3fe` sem bump, o gate reprova a branch com `MISSING-BUMP`, que é exatamente "bump pendente" expresso como veredito.

## CHANGELOG

- [x] CHK022 Existe requisito explícito exigindo entrada de CHANGELOG para a versão bumpada? [Spec §FR-007] — lacuna fechada nesta revisão: CHANGELOG só existia como artefato em `plan.md §Project Structure`, sem FR/SC correspondente; adicionado FR-007 e SC-005.
- [x] CHK023 O critério de aceite do CHANGELOG define o momento em que deve existir (antes do ship)? [Measurability, Spec §SC-005]

## Gates de Distribuição (validate_distribution.py, bump-gate.yml)

- [x] CHK024 O mecanismo de enforcement do FR-006 (bump-gate.yml + check_version_bump.py) está referenciado no plano em vez de ficar implícito? [Traceability, Plan §Technical Context]
- [x] CHK025 O plano define o comportamento esperado caso o gate de bump (`bump-gate.yml`) e a matriz de CI (`ci.yml`) reportem vereditos divergentes para a mesma PR? [Spec/Plan, Fail-Closed] — corrigido: nova seção `plan.md §Fail-Closed: bump-gate.yml × ci.yml` define que falha ou divergência em qualquer um bloqueia o ship até ambos passarem verde na mesma revisão (mesmo SHA), sem waiver.

## Timing Real (Revalidação Antes do Ship)

- [x] CHK026 O critério de aceite (SC-001) cobre qualquer execução testada em workspace real, sem depender apenas do timestamp do laudo de evidência já medido? [Measurability, Spec §SC-001]
- [x] CHK027 A necessidade de revalidar o timing real contra a árvore atual (não um número histórico) antes do ship está registrada com rationale rastreável? [Traceability, research.md §Verificação — timing real do pior caso]

## Gates Fail-Closed no Mesmo SHA (FR-008 / SC-006)

- [x] CHK030 A regra fail-closed dos dois gates existe como **requisito do spec** (FR-008), e não
      apenas como prosa de plano sem FR/SC correspondente? [Traceability, Spec §FR-008] — fechado
      nesta revisão: a regra vivia só em `plan.md §Fail-Closed`, sem requisito rastreável
      (finding T1).
- [x] CHK031 O critério de aceite dos gates é mensurável por veredito literal, e não por
      "passou/exit 0"? [Measurability, Spec §SC-006] — SC-006 exige o código `BUMPED` e enumera os
      quatro códigos rejeitados (`NO-PLUGIN-CHANGE`, `MISSING-BUMP`, `VERSION-REGRESSION`,
      `VERSION-UNREADABLE`).
- [x] CHK032 O tratamento dos vereditos do gate está desambiguado — estado pré-bump real e código
      residual? [Clarity, Spec §FR-008 ↔ tasks.md T020] — atualizado na 5ª revisão: com `7b3c3fe`
      commitado alterando `plugin/**` sem bump, o veredito **atual** da branch é `MISSING-BUMP` /
      `verdict: FAIL` (`5.2.0` → `5.2.0`), e é esse o ponto de partida declarado em plan.md,
      quickstart.md §4 e tasks.md Phase 6. `NO-PLUGIN-CHANGE` permanece enumerado apenas como
      **código residual rejeitado** (árvore impossível a partir de `7b3c3fe`; se aparecer é
      `--base-ref`/HEAD errados, e é falha apesar do exit 0) — preservando o fechamento do finding
      D1 sem descrever o estado atual de forma errada.
- [x] CHK033 A pré-condição de estado commitado (workers commitam, `converge` integra) antes do
      gate de bump está declarada, em vez de assumida? [Coverage, plan.md §Fail-Closed ↔ tasks.md
      Phase 6/Phase 7 ↔ quickstart.md §4] — reescrito na 6ª revisão para a topologia real do
      gauntlet: **Phase 6** contém T010–T016 em até três nós worker e T017–T018 devolvidas ao leader
      pelo Evidence Boundary; o commit leader ocorre após a convergência desses nós e antes da
      Phase 7. A **Phase 7** contém T019–T022; a fronteira entre as duas **é** a barreira. Os
      gates rodam num **nó único**, worktree isolado criado do HEAD coordenador após a convergência
      integral da Phase 6, sem commit nem merge entre T019 e T022. `gauntlet-tasks-reconcile` é
      **posterior** à convergência desse nó — removida a obrigação de commitar `state.json`/`tasks.md`
      antes dos gates. Preservada a obrigação do leader de commitar os artefatos relacionados antes
      da partition e o Execution DAG/relatório antes do primeiro worker.
- [x] CHK034 A exigência de árvore limpa **e** mesmo HEAD antes/depois das duas execuções está
      escrita como pré-condição verificável, e não como expectativa? [Measurability, tasks.md T022]
      — fechado: T022 lista (a) limpeza, (b)/(d) `git rev-parse HEAD` idêntico (finding D2).
      Precisado na 6ª revisão: a limpeza exigida é **somente tracked**
      (`git status --porcelain --untracked-files=no` vazio), porque é isso que os gates avaliam —
      `check_version_bump.py` decide sobre blobs commitados e
      `validate_distribution.py`/`run_validators.py` leem paths versionados. **Untracked sidecar e
      scratch de controle do próprio nó não participam, não são achado e não são waiver.** A
      igualdade de HEAD entre (b) e (d) passou a ser **invariante por construção**: não há commit nem
      merge entre T019 e T022 dentro do nó de gate.
- [x] CHK035 O requisito de CHANGELOG (FR-007) passou a ter gate automatizado, em vez de depender
      de conferência humana? [Measurability, Spec §FR-007/SC-005 ↔ tasks.md T014] — requisito e
      tarefa declarados: `validate_distribution.py` deve exigir exatamente uma linha `## {VERSION}`
      (finding C1). **A extensão do validador ainda não está aplicada** — é T014, da fase de
      implementação.
- [x] CHK036 FR-008/SC-006 especificam, como requisito, que os dois gates (`bump-gate.yml` e
      `ci.yml`) devem reportar verde sobre o **mesmo SHA**, com veredito literal `BUMPED`? [Clarity,
      Spec §FR-008/SC-006] — confirmado: SC-006 exige o código `BUMPED` e enumera os quatro
      vereditos de rejeição; FR-008 amarra a regra fail-closed ao mesmo SHA. Execução real (PR,
      T020/T022) permanece pendente nas tarefas, não nesta checklist.
- [x] CHK037 FR-007/SC-005 e as tasks T014/T018 exigem, como requisito, entrada de CHANGELOG e gate
      automatizado que reprova sua ausência? [Traceability, Spec §FR-007/SC-005 ↔ tasks.md
      T014/T018] — confirmado: SC-005 exige a entrada antes do ship, T014 estende
      `validate_distribution.py` com a asserção de CHANGELOG, T018 aplica o bump real. Execução real
      (CHANGELOG.md com `## 5.2.1`) permanece pendente nas tarefas, não nesta checklist.

## Dependências e Assunções

- [x] CHK028 A suposição de que o workspace real medido representa o pior caso está declarada explicitamente, junto do plano de revalidação que mitiga o risco de ficar desatualizada? [Assumption, Spec §Assumptions ↔ research.md]
- [x] CHK029 A suposição de exclusão de otimizações além do necessário para eliminar o falso positivo é consistente com o escopo cirúrgico declarado em `plan.md §Scale/Scope`? [Consistency]

## Notes

- Correção aplicada na 1ª revisão: `spec.md` ganhou FR-007 e SC-005 para fechar a lacuna do requisito de CHANGELOG, que antes só existia como artefato de implementação em `plan.md` sem requisito correspondente.
- Correções aplicadas na 2ª revisão (CHK005, CHK008, CHK025):
  - `spec.md` FR-003 agora pina `STATUS_TIMEOUT_SECONDS = 30` como valor obrigatório, com referência cruzada a `plan.md`/`research.md` (fecha CHK005).
  - `spec.md §Edge Cases` ganhou bullet declarando 30s como teto deliberado contra mascarar travamento real (fecha CHK008).
  - `plan.md` ganhou a seção `## Fail-Closed: bump-gate.yml × ci.yml`, definindo que falha ou divergência de veredito entre os dois gates bloqueia o ship até ambos passarem verde na mesma revisão, sem waiver; a linha "Fail-closed sem waiver" da Constitution Check foi atualizada para referenciar a regra (fecha CHK025).
- Correções aplicadas na 3ª revisão (remediação dos findings do `analysis.md`):
  - `spec.md` ganhou **FR-008** e **SC-006** (regra fail-closed dos dois gates sobre o mesmo SHA,
    com veredito literal `BUMPED`) — fecha T1; FR-005 passou a mapear explicitamente contrato e
    teste — fecha G1; FR-007/SC-005 passaram a exigir gate automatizado — fecha C1; a referência
    cruzada `plan.md` Decisão 2 virou `research.md`, Decisão 2 — fecha X1; a concordância de US1
    ("Diagnóstico completo") foi uniformizada — fecha W1.
  - `plan.md` amarrou a seção fail-closed a FR-008/SC-006, declarou a pré-condição de commit e a
    exigência de mesmo HEAD/árvore limpa, e declarou `.specify/feature.json` como artefato gerado
    fora do produto — fecha S1.
  - `tasks.md`: T005/T006 recebem o `root` posicional obrigatório (`.`) e passam a rodar em série
    (fecha U1 e P1); T020 exige literalmente `BUMPED` com `NO-PLUGIN-CHANGE` como falha, sobre
    árvore commitada e convergida (fecha D1); T022 exige árvore limpa e mesmo HEAD antes/depois
    (fecha D2); T014 estende `validate_distribution.py` com a asserção de CHANGELOG (fecha C1);
    regra fail-closed explícita para achados em T002/T003/T004/T008 (fecha C2); convenção `[X]`
    para tarefas cross-cutting (fecha F1); T019–T022 declaradas estritamente sequenciais, sem
    afirmação de paralelismo sem marcador (fecha F2).
  - `quickstart.md` passou a usar `status .`, medir em série, exigir commit antes do gate de bump
    e listar SC-005 e SC-006 na tabela de aceite (fecha Q1).
- Correções aplicadas na 4ª revisão (CHK036, CHK037): reformulados de verificação de execução
  (evidência de PR real / CHANGELOG já commitado) para unit test de requisito — perguntam se
  FR-008/SC-006 e FR-007/SC-005+tasks T014/T018 **especificam** a exigência, não se ela já foi
  executada. Marcados [x] porque a especificação está documentada nos artefatos.
- Correções aplicadas na 5ª revisão (remediação N1–N6 da análise final; nenhum item novo, apenas
  CHK021/CHK032/CHK033/CHK034 reescritos para casar o estado real):
  - **N1** — `plan.md`, `quickstart.md` (§4/§6) e `tasks.md` (nova seção "Onde as tarefas de gate
    rodam" + T019–T022) fixam que os gates rodam exclusivamente no **worktree coordenador da run**,
    após convergência de todos os waves e reconciliação de `tasks.md`; sujeira do workspace principal
    e de work items irmãos não participa; leader commita artefatos relacionados antes da partition e
    o DAG/relatório antes do primeiro worker.
  - **N2** — toda prosa "fix só no working tree" foi substituída pelo **baseline commitado
    `7b3c3fe`** em `plan.md`, `quickstart.md`, `tasks.md` e `ADR-0001`.
  - **N3** — estado pré-bump declarado como **`MISSING-BUMP`** (`verdict: FAIL`, `5.2.0` → `5.2.0`);
    `NO-PLUGIN-CHANGE` mantido como código residual rejeitado.
  - **N4** — `analysis.md` marcado **SUPERSEDED** com o conteúdo preservado na íntegra; relatório
    vigente passa a ser `analysis-final.md`.
  - **N5** — `ADR-0001` registra que `7b3c3fe` materializou a candidata preexistente antes da
    partition, que ela será auditada por T002–T009 e que isso **não** autoriza publicação.
  - **N6** — a árvore de `plan.md §Project Structure` passou a incluir `checklists/` e
    `analysis*.md`.
- Correções aplicadas na 6ª revisão (remediações R1/R2 e N1-A/N1-B; nenhum item novo, apenas
  CHK033/CHK034 reescritos para casar a topologia real do gauntlet):
  - **N1-A — nó único de gate, atrás de barreira de convergência.** A Phase 6 passou a conter
    **somente** os bumps T010–T018 e uma **Phase 7** nova passou a conter T019–T022; a fronteira
    entre as duas é a barreira. As quatro tarefas de gate executam **todas no mesmo nó** — um
    worktree **isolado de gate** criado a partir do HEAD do coordenador **depois** do merge e da
    convergência de todos os workers da Phase 6. Substitui a formulação anterior ("worktree
    coordenador da run"), que não descrevia um nó do DAG. Aplicado em `plan.md §Fail-Closed`,
    `tasks.md` (seção "Onde as tarefas de gate rodam", Phase 6, Phase 7, Dependencies, Parallel
    Opportunities, Implementation Strategy, Notes) e `quickstart.md` (pré-requisitos, §4, §6).
  - **N1-B — limpeza tracked-only.** A pré-condição virou
    `git status --porcelain --untracked-files=no` **vazio**. Untracked sidecar e scratch de controle
    do próprio nó **não** entram no gate, **não** são achado e **não** funcionam como waiver — os
    gates avaliam blobs commitados e paths versionados. Aplicado em `plan.md`, `tasks.md` T022 e
    `quickstart.md` §4/§6.
  - **R1 — mesmo conflict component forçado por inputs declarados (A3).** Cada uma de T019–T022
    declara os três inputs comuns `tests/validate_distribution.py`, `tests/check_version_bump.py` e
    `tests/run_validators.py`, garantindo que o particionador não as espalhe entre nós; **nenhuma
    leva `[P]`**, e a serialidade T019 → T020 → T021 → T022 é obrigatória. Como não há commit nem
    merge entre elas dentro do nó, `git rev-parse HEAD` é **idêntico por construção** — a igualdade
    exigida por T022 deixou de ser expectativa e virou invariante verificável.
  - **R2 — ordem da reconciliação e obrigações do leader (A2).** `gauntlet-tasks-reconcile` ocorre
    **somente depois** da convergência do nó de gate, nunca antes de T019; foi **removida** a
    obrigação de commitar `state.json`/`tasks.md` antes dos gates, que moveria o HEAD dentro da
    janela avaliada. Preservadas, sem mudança, as duas obrigações do leader: commitar os artefatos
    relacionados **antes da partition** e o Execution DAG/relatório de partition **antes do primeiro
    worker**.
  - Escopo desta revisão: `plan.md`, `quickstart.md`, `tasks.md`, `spec.md` (Status Draft → **Ready
    for Implementation**) e esta checklist. Os IDs T001–T022 foram preservados; nenhum código de
    produto, `analysis.md`, `.grill/` ou work item irmão foi tocado; nenhum commit executado.
- Correções aplicadas na 7ª revisão após executar o particionador real:
  - todos os paths relevantes passaram para a primeira linha de T001–T022, eliminando tarefas
    unmapped e scopes espúrios;
  - T010–T016 formam três nós worker com grants exatos; T017–T018 são `deferred_to_leader`
    exclusivamente por declararem `.specify/reports/status-timeout-bump-leader.md` — os nomes raiz
    não são extraídos porque o parser exige `/`; o leader executa e commita esses bumps antes de
    despachar a Phase 7;
  - T019–T022 declaram os três inputs comuns na primeira linha e o preview determinístico produz um
    único nó `p07-a`, na ordem correta, dependente dos três nós da Phase 6;
  - baseline documental corrigido para 1237 testes em 26 módulos `unittest`, mais o validador
    standalone de distribuição, com 1 skip.
- **Estado de marcação**: 37 de 37 itens marcados [x] com evidência real nos artefatos.
  Isso valida a qualidade dos **requisitos**, não a execução: `BUMPED` sobre o mesmo SHA
  (T020/T022) e a entrada `## 5.2.1` no `CHANGELOG.md` (T014/T018) seguem pendentes de execução
  real — o repositório está em `5.2.0` e o gate de bump reprova a branch com `MISSING-BUMP`. A checklist 100% não é um veredito de "feature pronta para
  ship"; é um veredito de "spec/plan/tasks especificam corretamente o que falta executar".
- Hooks opcionais de commit (`before_checklist`/`after_checklist`) não foram executados, por instrução explícita do usuário. Nenhum commit, hook ou tarefa de implementação foi executado nesta revisão — apenas edição de artefatos de especificação.

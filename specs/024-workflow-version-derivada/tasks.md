# Tasks: Versão de workflow derivada do documento

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Branch**: `fix/audit`

**Input**: plan.md, spec.md, research.md, data-model.md, contracts/cli.md, quickstart.md

**Tests**: gerados. FR-008 exige cobertura de matriz explícita, `quickstart.md` define os cenários executáveis e o projeto exige suíte verde a cada entrega.

**Reescopo**: esta lista substitui a anterior, de 32 tarefas. A 5.0.0 encerrou por redefinição o caso irmão deste defeito e corrigiu o gate da camada executável, então as tarefas do reader e a inversão reader-antes-de-writer saíram (ADR-0003). O que restou é menor e mais focado.

## Path Conventions

Repositório é o próprio plugin e o consome. Produção em `plugin/skills/grill-with-docs/{scripts,assets}/`; testes em `tests/`, com `tests/run_validators.py` fazendo glob de `validate_*.py`. Não há `src/`. Caminhos relativos à raiz do repositório.

---

## Phase 1: Setup (Shared Infrastructure)

- [ ] T001 Capturar a linha de base da suíte rodando `tests/run_validators.py` sob python3 e registrar contagem de testes, de validadores e o exit code em `specs/024-workflow-version-derivada/baseline.md`
- [ ] T002 Capturar a classificação e o veredito de cada work item existente, iterando `.grill/work-items/` e gravando `work_id`, sequência declarada e `verdict` em `specs/024-workflow-version-derivada/baseline-fleet.txt` — precisa rodar antes de qualquer alteração, senão a comparação de US3 não tem contra o que comparar

**Checkpoint**: linha de base capturada. Nenhum arquivo de produção tocado.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: detector estrito, com paridade provada. Pré-requisito de todas as histórias.

- [ ] T003 [P] Criar as sete fixtures da matriz de `research.md` §R5, materializando cada documento pelo próprio `ensure_workflow` e nunca escrevendo o texto à mão — os malformados por edição mecânica do documento real, nunca por texto inventado (FR-008). Os caminhos são `tests/fixtures/workflow-marker-matrix/none/WORKFLOW.md` (sem marcador), `tests/fixtures/workflow-marker-matrix/v2/WORKFLOW.md`, `tests/fixtures/workflow-marker-matrix/v3/WORKFLOW.md`, `tests/fixtures/workflow-marker-matrix/v4/WORKFLOW.md`, `tests/fixtures/workflow-marker-matrix/duplicate-same/WORKFLOW.md` (dois marcadores iguais), `tests/fixtures/workflow-marker-matrix/duplicate-distinct/WORKFLOW.md` (dois distintos) e `tests/fixtures/workflow-marker-matrix/unknown-v9/WORKFLOW.md` (marcador único não reconhecido). Nomear cada arquivo é obrigatório: um grant que nomeia diretório não cobre arquivo algum, e o `converge` o recusa com `GRANT-SCOPE-VIOLATION`.
- [ ] T004 Implementar `sole_managed_version(text)` em `plugin/skills/grill-with-docs/scripts/ensure_workflow.py`, usando `re.findall` e devolvendo o marcador apenas quando houver exatamente uma ocorrência — sem tocar `managed_version`
- [ ] T005 [P] Adicionar em `tests/validate_workflow_v3_contract.py` o teste de matriz de `sole_managed_version` sobre as sete fixtures de T003
- [ ] T006 [P] Adicionar em `tests/validate_workflow_v3_contract.py` o teste que fixa a semântica first-match de `managed_version`, cobrindo dois marcadores e o retorno `None` sem marcador, para que uma mudança futura nela reprove em vez de quebrar a materialização
- [ ] T007 Adicionar em `tests/validate_workflow_v3_contract.py` o teste de paridade que compara, para cada fixture de T003, o que `sole_managed_version` resolve com a decisão de aceitar ou recusar da verificação de marcador que `plugin/skills/grill-with-docs/scripts/audit_decisions.py` já faz — este teste é o SSOT da regra, no lugar do módulo compartilhado recusado em ADR-0002 (FR-005, V-3, SC-005)

**Checkpoint**: detector estrito existe, é testado e concorda com o auditor. Nenhum writer mudou.

---

## Phase 3: User Story 1 — Repositório que preserva uma declaração anterior (Priority: P1) 🎯 MVP

**Goal**: o campo que declara a sequência passa a vir do documento, e a criação recusa antes de gravar quando a declaração não resolve.

**Independent test**: criar work item em repositório temporário com documento v3, ler o campo, conferir a sequência que a projeção aplica.

**Nota de ordem**: a recusa (T008) precede a derivação (T009) dentro desta fase. Separá-las abriria janela em que `state_template` grava sem saber o que fazer com declaração não resolvível — fail-open que a Constituição não admite.

- [ ] T008 [US1] Implementar em `plugin/skills/grill-with-docs/scripts/grill_workspace.py` (`state_template`), no ponto imediatamente anterior a qualquer escrita, a recusa `WORKFLOW-MARKER-UNRESOLVED` com `markers_found` e `accepted`, cunhada em `SCREAMING_SNAKE` e traduzida para KEBAB na fronteira, saindo com exit code 2 (FR-003, FR-004, V-1, `specs/024-workflow-version-derivada/contracts/cli.md`)
- [ ] T009 [US1] Implementar em `plugin/skills/grill-with-docs/scripts/grill_workspace.py` (`state_template`) a resolução do marcador via `sole_managed_version` e a gravação de `development.workflow_version` a partir dela. A resolução só é alcançada quando T008 já garantiu declaração única e reconhecida, então `None` é inalcançável aqui por construção. Não tocar `value["workflow"]`, `workflow_info()` nem `immutable_metadata()` (FR-001, FR-002, R2, ADR-0003)
- [ ] T010 [US1] Implementar em `plugin/skills/grill-with-docs/scripts/grill_workspace.py` (`state_template`) a equivalência declarada de FR-002 para o caso `v2`, com comentário citando a identidade das sequências em `WORKFLOW_SEQUENCE_BY_MARKER` como justificativa, **e derivar `development.sequence` da mesma resolução**, de `SEQUENCE_BY_VERSION`. Os dois campos descrevem o mesmo fato: derivar `workflow_version` deixando `sequence` vir do asset produz bundle que declara uma versão e lista a sequência de outra, reprovado como `DEVELOPMENT-SCHEMA` por `tests/validate_checkpoint_contract.py` (FR-002, R3, SC-007, V-5)
- [ ] T011 [US1] Manter a chave `development.workflow_version` em `plugin/skills/grill-with-docs/assets/state.template.json` com o valor atual como semente inerte, acrescentando comentário de schema que declare o valor sempre sobrescrito na criação. **Não remover a chave**: a ausência muda a forma do documento e `development_workflow_version()` trata declaração ausente como schema não reconhecido
- [ ] T012 [P] [US1] Adicionar em `tests/validate_workspace_contract.py` o teste do cenário de documento v3: o campo grava `v3` (FR-001, FR-002, SC-001)
- [ ] T013 [P] [US1] Adicionar em `tests/validate_workspace_contract.py` o teste do caso v2: grava `v3` pela equivalência, e `development_workflow_version()` não devolve `None` (R3, V-2)
- [ ] T014 [P] [US1] Adicionar em `tests/validate_workspace_contract.py` o teste do caso v4: o campo grava `v4`, agora por derivação e não por coincidência com o literal
- [ ] T015 [US1] Adicionar em `tests/validate_status_contract.py` o teste que exige a projeção de status classificar um bundle criado sobre documento v3 pela sequência v3, com as etapas agent-assign e agent-execute no lugar de partition e implement-parallel (FR-007, SC-002)
- [ ] T016 [US1] Adicionar em `tests/validate_workspace_contract.py` o teste que prova a justificativa de SC-007: toda equivalência aplicada corresponde a sequências comprovadamente idênticas, comparando as tuplas em vez de confiar no mapa
- [ ] T017 [US1] Adicionar em `tests/validate_workspace_contract.py` o teste que cobre o segundo writer, `migrate`, provando que ele passa pelo mesmo `state_template` e grava o mesmo valor (R1)

- [ ] T030 [US1] Dessalgar a sequência de etapas fixada em `tests/validate_checkpoint_contract.py` e nos testes de `phase-turn` de `tests/validate_workspace_contract.py`: hoje ambos declaram a tupla v4 como literal e criam o item a partir do template, que é v2 por padrão. Os dois só passavam porque o defeito forçava todo bundle a declarar v4 — dois erros que se cancelavam. Derivar a sequência esperada da versão que o item efetivamente declara, ou materializar explicitamente o documento da versão que o teste quer exercitar. **Não** alterar o padrão v2 do template, que é deliberado (LD-004). São 10 testes: 2 em `validate_checkpoint_contract.py` e 8 nos de `phase-turn` (FR-002, V-5, cláusula constitucional `Versão resolvida, nunca embutida`)

- [ ] T031 [US1] Dessalgar a sequência fixada em `tests/validate_gauntlet_converge_contract.py` (linha 60) e `tests/validate_gauntlet_scheduler_contract.py` (linha 68): ambas declaram a tupla v4 como literal e criam o item a partir do template, que é v2 por padrão. Mesma correção de T030 — derivar de `development.sequence` do item que o teste criou. Levantamento completo já feito: **são só esses dois**; os hardcodes v3 em `validate_status_contract.py` e `validate_v3_wiring_contract.py` são deliberados, testam bundles v3 explicitamente, e **não** devem ser tocados
- [ ] T032 [US1] Tratar em `plugin/skills/grill-with-docs/scripts/grill_workspace.py` a etapa que existe globalmente mas não pertence à sequência do item: hoje `checkpoint --step partition` sobre item que declara v3 estoura `ValueError` não capturado e o CLI devolve `UNEXPECTED-FAILURE`, que é o código de "erro não previsto". Deve devolver código de contrato nomeando a condição — etapa válida, ausente nesta sequência —, e a mensagem deve dizer qual sequência o item declara. Reproduzir antes: criar repo, `ensure_workflow --ensure` (materializa v2), `init`, `checkpoint --step partition`
- [ ] T033 [US1] Dessalgar em `tests/validate_status_contract.py` os oito testes de contrato geral que assumem a sequência v4 ao criar o item (`test_one_item_top_level_and_item_schema`, `test_markdown_*`, `test_drift_*`, `test_both_heads_*`, `test_specify_checkpoint_binds_*`), derivando de `development.sequence`. E corrigir em `plugin/skills/grill-with-docs/scripts/grill_status.py:160` o fallback `sequence = SEQUENCE if sequence is None else sequence`, que cai silenciosamente na tupla v4 fixada em `:24` quando o item não declara sequência — é exatamente o default silencioso que a cláusula constitucional `Versão resolvida, nunca embutida` proíbe. Sequência ausente deve ser tratada como o que é, não suprida pela versão ativa

**Checkpoint**: US1 entregue. Repositórios com declaração anterior deixam de ser julgados pela sequência errada.

---

## Phase 4: User Story 2 — Declaração ausente ou ambígua recusada na origem (Priority: P2)

**Goal**: provar que a recusa implementada em T008 cobre toda a matriz e não deixa artefato.

**Nota**: a implementação vive em T008, na Phase 3, por exigência de ordem. Esta fase é a prova.

- [ ] T018 [P] [US2] Adicionar em `tests/validate_workspace_contract.py` o teste de recusa para `tests/fixtures/workflow-marker-matrix/duplicate-same/WORKFLOW.md`, que é o caso que alcança o gate desta feature: exigir `WORKFLOW-MARKER-UNRESOLVED` com `markers_found: 2` e `accepted` listando as versões aceitas (FR-004)
- [ ] T019 [P] [US2] Adicionar em `tests/validate_workspace_contract.py` os testes dos casos barrados pelo gate de compatibilidade preexistente — `none`, `duplicate-distinct` e `unknown-v9` — exigindo o código que cada um efetivamente devolve hoje, e **não** `WORKFLOW-MARKER-UNRESOLVED`. Documentar no teste que são dois caminhos de recusa distintos, conforme FR-004, para que ninguém "conserte" o teste alinhando-o ao código errado
- [ ] T020 [P] [US2] Adicionar em `tests/validate_workspace_contract.py` o teste que exercita o gate desta feature por `migrate`, que não passa pelo gate de compatibilidade: `unknown-v9` deve devolver `WORKFLOW-MARKER-UNRESOLVED` com `markers_found: 1`, provando que o campo `accepted` é o que explica a recusa de marcador único não aceito
- [ ] T021 [US2] Adicionar em `tests/validate_workspace_contract.py` o teste que prova a garantia fail-closed nos **quatro** casos, por ambos os caminhos: depois de cada recusa, `.grill/work-items/` não contém diretório algum, nem staging, nem lock remanescente (FR-003, SC-004)

**Checkpoint**: US2 entregue.

---

## Phase 5: User Story 3 — Work items já publicados não mudam de veredito (Priority: P1)

**Goal**: provar que a mudança não altera o veredito nem a classificação de nenhum bundle existente.

**Independent test**: reexecutar auditoria e projeção sobre os work items existentes e comparar com `baseline-fleet.txt`.

- [ ] T022 [US3] Reexecutar a auditoria e a projeção de status de cada work item existente e comparar com `specs/024-workflow-version-derivada/baseline-fleet.txt`, exigindo igualdade linha a linha (FR-006, SC-003)
- [ ] T023 [US3] Adicionar em `tests/validate_status_contract.py` o teste de invariância: um bundle materializado antes desta mudança continua sendo classificado pelo que ele próprio declara, e o teste declara no docstring que existe para impedir a reintrodução do cross-check contra o disco recusado em ADR-0001 (FR-006)
- [ ] T024 [US3] Confirmar que nenhum arquivo sob `.grill/work-items/` foi reescrito, migrado ou renumerado, comparando os hashes dos bundles antes e depois (FR-006)

**Checkpoint**: US3 entregue. Todas as histórias completas.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T025 Incrementar a versão SemVer nos pontos travados: `plugin/.claude-plugin/plugin.json`, `plugin/.codex-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.agents/plugins/marketplace.json`, a constante `VERSION` em `tests/validate_distribution.py`, o heading de `plugin/skills/grill-with-docs/SKILL.md`, o de `plugin/skills/grill-with-docs/references/session-protocol.md` e o de `README.md` (FR-009)
- [ ] T026 [P] Acrescentar em `CHANGELOG.md` a entrada descrevendo a mudança de contrato: o campo de sequência passa a ser derivado do documento e a criação recusa declaração não-única
- [ ] T027 [P] Registrar no `CLAUDE.md` a nova baseline de testes, substituindo a contagem de T001 pela contagem final
- [ ] T028 Rodar `tests/run_validators.py` sob python3 e exigir exit 0, com a contagem acima da linha de base de T001 (SC-006)
- [ ] T029 Rodar `tests/validate_distribution.py` isoladamente sob python3 e exigir exit 0

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)** — sem dependência. **Precisa rodar antes de qualquer alteração**, senão T022 e T028 perdem a referência.
- **Phase 2 (Foundational)** — depende de Phase 1. Bloqueia todas as histórias.
- **Phase 3 (US1)** — depende de Phase 2. T008 é o primeiro toque no writer, e é a recusa: nada é gravado antes de a declaração resolver.
- **Phase 4 (US2)** — depende de T008. Só testes.
- **Phase 5 (US3)** — depende da Phase 3 inteira: a invariância só é medível depois de o writer mudar.
- **Phase 6 (Polish)** — depende de todas as anteriores.

### User Story Dependencies

- **US1** carrega toda a implementação. **US2** e **US3** são provas sobre ela e independentes entre si.

### Within Each User Story

Fixtures → implementação → testes. Os testes podem ser escritos antes, mas só passam depois da implementação.

### Parallel Opportunities

- T005 e T006 tocam arquivo de teste distinto de T004 e podem correr em paralelo depois dele.
- T012, T013 e T014 são paralelos entre si; T018, T019 e T020 idem.
- T026 e T027 são documentação e não colidem com nada.
- **Não paralelizar** T008, T009 e T010, nessa ordem: os três editam `state_template` na mesma função, e T008 precisa preceder T009.

---

## Implementation Strategy

### MVP First (US1)

US1 é o MVP e é a correção inteira: recusa, derivação e equivalência. Publicável sozinha.

### Incremental Delivery

1. Phase 1 + Phase 2 → detector estrito, com paridade provada.
2. Phase 3 → o campo passa a vir do documento; declaração não resolvível recusa antes de gravar.
3. Phase 4 → prova de que a recusa cobre a matriz inteira sem deixar artefato.
4. Phase 5 → prova de que a frota não mudou.
5. Phase 6 → bump e publicação.

### Parallel Team Strategy

Um executor em `ensure_workflow.py` e seus testes (T004–T007). Do T008 em diante o trabalho serializa numa função só.

---

## Notes

- 33 tarefas: 2 de setup, 5 fundacionais, 10 em US1, 4 em US2, 3 em US3, 5 de polish.
- T026 e T027 tocam arquivos na raiz do repositório. O particionador não trata nome sem diretório como caminho — é recusa deliberada de inferir diretório — então as duas ficam sem grant de arquivo e são devolvidas ao leader no nó serial. Correto, não defeito.
- `R8` (tabela de sequências duplicada) foi resolvido fora deste trabalho: a 5.0.0 passou a derivá-la do SSOT `grill_core.workflow_versions`.

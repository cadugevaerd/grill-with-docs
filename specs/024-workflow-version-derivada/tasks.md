# Tasks: Versão de workflow derivada do documento

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Branch**: `fix/audit`

**Input**: plan.md, spec.md, research.md, data-model.md, contracts/cli.md, quickstart.md

**Tests**: gerados. FR-009 exige cobertura de matriz explícita, `quickstart.md` define os cenários executáveis e o projeto exige suíte verde a cada entrega — testes não são opcionais aqui.

## Path Conventions

Repositório é o próprio plugin e o consome. Produção em `plugin/skills/grill-with-docs/{scripts,assets}/`; testes em `tests/`, com `tests/run_validators.py` fazendo glob de `validate_*.py`. Não há `src/`. Todos os caminhos abaixo são relativos à raiz do repositório.

**Restrição de ordem herdada do plano**: o reader (`audit_decisions.py`) muda **antes** do writer (`grill_workspace.py`). Invertido, todo work item criado entre as duas mudanças reprovaria. Isso põe a US4 antes das demais histórias, apesar de ela aparecer por último na spec — a prioridade P1 dela é a mesma.

---

## Phase 1: Setup (Shared Infrastructure)

- [ ] T001 Capturar a linha de base da suíte rodando `tests/run_validators.py` sob python3 e registrar contagem de testes, de validadores e o exit code em `specs/024-workflow-version-derivada/baseline.md`
- [ ] T002 Capturar o veredito de auditoria de cada work item existente, iterando `.grill/work-items/*/` e gravando `work_id` e `verdict` em `specs/024-workflow-version-derivada/baseline-fleet.txt` — precisa rodar antes de qualquer alteração, senão a comparação de US4 não tem contra o que comparar

**Checkpoint**: linha de base capturada. Nenhum arquivo de produção tocado.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: detector estrito e reader tolerante. Ambos são pré-requisito de todas as histórias, e é aqui que a ordem reader-antes-de-writer é cumprida.

- [ ] T003 [P] Criar as fixtures da matriz de `research.md` §R5 em `tests/fixtures/`, materializando cada `WORKFLOW.md` pelo próprio `ensure_workflow` e nunca escrevendo o texto à mão: sem marcador, um `v2`, um `v3`, um `v4`, dois marcadores iguais, dois distintos, um `v9` desconhecido (FR-009)
- [ ] T004 Implementar `sole_managed_version(text)` em `plugin/skills/grill-with-docs/scripts/ensure_workflow.py`, usando `re.findall` e devolvendo o marcador apenas quando houver exatamente uma ocorrência — sem tocar `managed_version`
- [ ] T005 [P] Adicionar em `tests/validate_workflow_v3_contract.py` o teste de matriz de `sole_managed_version` sobre as sete fixtures de T003
- [ ] T006 [P] Adicionar em `tests/validate_workflow_v3_contract.py` o teste que fixa a semântica first-match de `managed_version`, cobrindo o caso de dois marcadores e o retorno `None` sem marcador, para que uma mudança futura nela reprove em vez de quebrar a materialização
- [ ] T007 Adicionar em `tests/validate_workflow_v3_contract.py` o teste de paridade que compara, para cada fixture de T003, o que `sole_managed_version` resolve com a decisão de aceitar ou recusar de `audit_decisions.py` — este teste é o SSOT da regra, no lugar do módulo compartilhado recusado em ADR-0002 (FR-006, V-4, SC-005)
- [ ] T008 Trocar em `plugin/skills/grill-with-docs/scripts/audit_decisions.py:801` a comparação com o literal `"v2"` por pertencimento a `ACCEPTED_WORKFLOW_MARKERS`, mantendo a string do finding inalterada (FR-003, V-2)
- [ ] T009 [P] Adicionar em `tests/validate_contract.py` os testes da asserção de estado: `v2`, `v3` e `v4` aprovam; `null`, valor fora do conjunto, campo ausente e `workflow` não-objeto reprovam com a string de finding atual

**Checkpoint**: detector estrito existe e é testado; auditoria aceita qualquer versão gerenciada. Nenhum writer mudou ainda, então nada que hoje aprova passou a reprovar.

---

## Phase 3: User Story 4 — Work items já publicados não mudam de veredito (Priority: P1) 🎯 MVP

**Goal**: provar que a troca do reader não altera o veredito de nenhum bundle existente.

**Independent test**: rodar a auditoria sobre os work items existentes e comparar com `baseline-fleet.txt` de T002; as duas saídas devem ser idênticas linha a linha.

- [ ] T010 [US4] Reexecutar a auditoria de cada work item existente e comparar com `specs/024-workflow-version-derivada/baseline-fleet.txt`, exigindo igualdade linha a linha (SC-003)
- [ ] T011 [US4] Adicionar em `tests/validate_contract.py` o teste de invariância de frota: um bundle carimbado `"v2"` sobre documento v4 mantém o veredito, e o teste declara no docstring que ele existe para impedir a reintrodução do cross-check contra o disco recusado em ADR-0001 (FR-007, R7)
- [ ] T012 [US4] Confirmar que nenhum arquivo sob `.grill/work-items/` foi reescrito, migrado ou renumerado, comparando os hashes dos bundles antes e depois (FR-007)

**Checkpoint**: US4 entregue e verificável sozinha. Este é o MVP — a partir daqui, a mudança do reader pode ser publicada sem o writer e nada regride.

---

## Phase 4: User Story 1 — Registro verdadeiro sobre a declaração corrente (Priority: P1)

**Goal**: um work item criado sobre documento v4 registra v4 nos dois campos e audita sem intervenção manual.

**Independent test**: criar work item em repositório temporário com documento v4, ler os dois campos, auditar.

**Nota de ordem**: a recusa fail-closed entra **antes** da primeira escrita derivada. O plano trata writer e
recusa como uma fase só (plan.md §Fases 3), e separá-los abriria janela em que `state_template` grava sem
saber o que fazer com declaração não resolvível — fail-open que a Constituição não admite.

- [ ] T013 [US1] Implementar em `plugin/skills/grill-with-docs/scripts/grill_workspace.py` (`state_template`), no ponto imediatamente anterior a qualquer escrita, a recusa `WORKFLOW-MARKER-UNRESOLVED` com `markers_found` e `accepted`, cunhada em `SCREAMING_SNAKE` e traduzida para KEBAB na fronteira, saindo com exit code 2 (FR-004, FR-005, V-1, `specs/024-workflow-version-derivada/contracts/cli.md`)
- [ ] T014 [US1] Implementar em `plugin/skills/grill-with-docs/scripts/grill_workspace.py:687` (`state_template`) a resolução do marcador via `sole_managed_version` e a aplicação do mapa de derivação de `data-model.md` aos dois campos. A resolução só é alcançada quando T013 já garantiu declaração única e reconhecida, então `None` é inalcançável aqui por construção. Não tocar `workflow_info()` nem `immutable_metadata()` (FR-001, FR-002, R2)
- [ ] T015 [US1] Manter a chave `development.workflow_version` em `plugin/skills/grill-with-docs/assets/state.template.json` com o valor atual como semente inerte, acrescentando comentário de schema que declare o valor sempre sobrescrito na criação. **Não remover a chave**: a ausência muda a forma do documento e `development_workflow_version()` trata declaração ausente como schema não reconhecido
- [ ] T016 [P] [US1] Adicionar em `tests/validate_workspace_contract.py` o teste ponta a ponta do cenário 1 de `quickstart.md`: criação sobre documento v4 grava `v4` nos dois campos (FR-001, FR-002, SC-001)
- [ ] T017 [P] [US1] Adicionar em `tests/validate_workspace_contract.py` o teste que audita esse work item recém-criado e exige ausência de qualquer finding de divergência de versão (SC-002)
- [ ] T018 [US1] Adicionar em `tests/validate_workspace_contract.py` o teste que cobre o segundo writer, `migrate`, provando que ele passa pelo mesmo `state_template` e grava os mesmos valores (R1, CHK002)

**Checkpoint**: US1 entregue. Criação sobre documento corrente deixa de exigir edição manual.

---

## Phase 5: User Story 2 — Repositório que preserva uma declaração anterior (Priority: P1)

**Goal**: documento v3 produz registro v3, e a equivalência declarada cobre o caso v2.

**Independent test**: criar work item sobre documento v3 e sobre documento v2; conferir os dois campos e a sequência que a projeção de status aplica.

- [ ] T019 [US2] Implementar em `plugin/skills/grill-with-docs/scripts/grill_workspace.py` (`state_template`) a equivalência declarada de FR-002 para o caso `v2`: `workflow.version` recebe `v2` e `development.workflow_version` recebe `v3`, com comentário citando a identidade das sequências em `WORKFLOW_SEQUENCE_BY_MARKER` como justificativa (FR-002, R3, SC-007)
- [ ] T020 [P] [US2] Adicionar em `tests/validate_workspace_contract.py` o teste do cenário 2 de `quickstart.md`: documento v3 grava `v3` nos dois campos
- [ ] T021 [P] [US2] Adicionar em `tests/validate_workspace_contract.py` o teste do caso v2: grava `v2` e `v3` respectivamente, e o bundle resultante tem sequência reconhecível — `development_workflow_version()` não devolve `None` (R3, V-3)
- [ ] T022 [US2] Adicionar em `tests/validate_status_contract.py` o teste que exige a projeção de status classificar um bundle v3 pela sequência v3, com as etapas agent-assign e agent-execute no lugar de partition e implement-parallel (FR-008)
- [ ] T023 [US2] Adicionar em `tests/validate_workspace_contract.py` o teste que prova a justificativa de SC-007: toda equivalência aplicada corresponde a sequências comprovadamente idênticas, comparando as tuplas em vez de confiar no mapa

**Checkpoint**: US2 entregue. Repositórios com declaração anterior deixam de ser julgados pela sequência errada.

---

## Phase 6: User Story 3 — Declaração ausente ou ambígua recusada na origem (Priority: P2)

**Goal**: provar que a recusa implementada em T013 cobre toda a matriz e não deixa artefato.

**Nota**: a implementação vive em T013, na Phase 4, por exigência de ordem. Esta fase é a prova.

**Independent test**: para cada caso de recusa da matriz, tentar criar e conferir código, mensagem e ausência total de artefato.

- [ ] T024 [P] [US3] Adicionar em `tests/validate_workspace_contract.py` o teste de recusa para documento sem marcador, exigindo `markers_found: 0`
- [ ] T025 [P] [US3] Adicionar em `tests/validate_workspace_contract.py` o teste de recusa para dois marcadores iguais e para dois distintos, exigindo `markers_found: 2` em ambos — a regra é unicidade da declaração, não distinção de valores (R5)
- [ ] T026 [P] [US3] Adicionar o teste de recusa para marcador único não reconhecido (`v9`), exigindo `markers_found: 1` e o campo `accepted` explicando a recusa (`specs/024-workflow-version-derivada/contracts/cli.md`)
- [ ] T027 [US3] Adicionar o teste que prova a garantia fail-closed: depois de cada recusa acima, `.grill/work-items/` não contém diretório algum, nem staging, nem lock remanescente (FR-004, SC-004, CHK001)

**Checkpoint**: US3 entregue. Todas as histórias completas.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [ ] T028 Incrementar a versão SemVer nos oito pontos travados: `plugin/.claude-plugin/plugin.json`, `plugin/.codex-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.agents/plugins/marketplace.json`, a constante `VERSION` em `tests/validate_distribution.py`, o heading de `plugin/skills/grill-with-docs/SKILL.md`, o de `plugin/skills/grill-with-docs/references/session-protocol.md` e o de `README.md` (FR-010)
- [ ] T029 [P] Acrescentar em `CHANGELOG.md` a entrada descrevendo a mudança de contrato: os dois campos passam a ser derivados, a auditoria valida por pertencimento e a criação recusa declaração não-única
- [ ] T030 [P] Registrar no `CLAUDE.md` a nova baseline de testes, substituindo a contagem de T001 pela contagem final
- [ ] T031 Rodar `tests/run_validators.py` sob python3 e exigir exit 0, com a contagem acima da linha de base de T001 (SC-006)
- [ ] T032 Rodar `tests/validate_distribution.py` isoladamente sob python3 e exigir exit 0 (cenário 6 de `quickstart.md`)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)** — sem dependência. **Precisa rodar antes de qualquer alteração**, senão T010 e T031 perdem a referência.
- **Phase 2 (Foundational)** — depende de Phase 1. Bloqueia todas as histórias.
- **Phase 3 (US4)** — depende de Phase 2. Verificável assim que o reader muda, e **antes** de o writer existir.
- **Phase 4 (US1)** — depende de Phase 2. T013 é o primeiro toque no writer, e é a recusa: nada é gravado antes de a declaração resolver.
- **Phase 5 (US2)** — depende de T014 (mesma função).
- **Phase 6 (US3)** — depende de T013. Só testes; a implementação da recusa vive na Phase 4.
- **Phase 7 (Polish)** — depende de todas as anteriores.

### User Story Dependencies

- **US4** é independente das demais e vem primeiro por causa da ordem reader-antes-de-writer.
- **US1**, **US2** e **US3** compartilham `state_template` e por isso são sequenciais entre si, não paralelas. US1 estabelece a recusa e a derivação, nessa ordem; US2 acrescenta a equivalência; US3 apenas prova a recusa que US1 já implementou.

### Within Each User Story

Fixtures → implementação → testes. Os testes de uma história só passam depois da implementação dela, mas podem ser escritos antes.

### Parallel Opportunities

- T005, T006 e T009 tocam arquivos de teste distintos de T004 e T008 e podem correr em paralelo depois deles.
- T016 e T017 são paralelos entre si; T020 e T021 idem; T024, T025 e T026 idem.
- T029 e T030 são documentação e não colidem com nada.
- **Não paralelizar** T013, T014 e T019, nessa ordem: os três editam `state_template` na mesma função, e T013 precisa preceder T014.

---

## Implementation Strategy

### MVP First (US4)

O MVP aqui não é a primeira história da spec — é a US4. A troca do reader (Phase 2) mais a prova de invariância (Phase 3) já entregam valor sozinhas: a auditoria deixa de exigir um valor específico, sem que nenhum bundle existente mude de veredito. Publicável nesse ponto.

### Incremental Delivery

1. Phase 1 + Phase 2 + Phase 3 → reader tolerante, frota provada intacta.
2. Phase 4 → declaração não resolvível passa a ser recusada, e a criação registra a verdade no caso corrente.
3. Phase 5 → repositórios com declaração anterior deixam de ser mal classificados.
4. Phase 6 → prova de que a recusa cobre a matriz inteira sem deixar artefato.
5. Phase 7 → bump e publicação.

Cada corte acima deixa a suíte verde e nenhum estado intermediário reprova o que hoje aprova.

### Parallel Team Strategy

Dois executores: um em `ensure_workflow.py` + testes de detector (T004–T007), outro em `audit_decisions.py` + testes de auditoria (T008, T009). Convergem no checkpoint da Phase 2. Do T013 em diante o trabalho serializa numa função só.

---

## Notes

- 32 tarefas: 2 de setup, 7 fundacionais, 3 em US4, 6 em US1, 5 em US2, 4 em US3, 5 de polish.
- T029 e T030 tocam arquivos na raiz do repositório (`CHANGELOG.md`, `CLAUDE.md`). O particionador não trata nome sem diretório como caminho — é recusa deliberada de inferir diretório — então as duas ficam sem grant de arquivo e são devolvidas ao leader no nó serial. Correto, não defeito.
- A ordem das histórias **não** segue a numeração da spec, e isso é deliberado: a restrição reader-antes-de-writer do plano é mais forte que a ordem de apresentação.
- Os quatro itens abertos de `checklists/contract.md` foram decididos no `analyze` de 2026-08-22 e **excluídos de escopo**: CHK003 (rebind posterior) e CHK004 (rollback pós-publicação) com justificativa registrada em `docs/adr/ADR-0001.md` do work item; CHK005 (concorrência) e CHK031 (recuperação após recusa) por mecanismo preexistente e por FR-005, respectivamente. Nenhum deles gera tarefa.

---

description: "Task list for 025-goal-materialization"
---

# Tasks: Materialização e validação do goal.md

**Input**: Design documents from `/specs/025-goal-materialization/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Tarefas de teste são **obrigatórias** nesta feature. FR-012 e FR-013
exigem que a suíte reprove documento não conforme, nomeando a parte ausente, sem
rede e sem ferramenta externa. US3 é inteiramente sobre isso.

**Organization**: Agrupadas por user story, para permitir implementação e teste
independentes de cada uma.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo — arquivo disjunto, sem dependência pendente
- **[Story]**: a user story a que a tarefa pertence (US1, US2, US3)
- Caminhos de arquivo exatos em cada descrição

## Path Conventions

O repositório não tem `src/`. O código do plugin vive em
`plugin/skills/grill-with-docs/scripts/`, com lógica pura em `grill_core/` e
fronteiras de I/O nos scripts irmãos. A suíte canônica vive em `tests/`.

Os **treze** caminhos abaixo são o escopo fechado declarado em
`WORK-ITEM.json`. Nenhum outro caminho de produto é tocado — em especial,
`ensure_workflow.py` permanece byte-intacto (ADR-0101).

```text
plugin/skills/grill-with-docs/scripts/grill_core/goal_document.py   # A — novo
plugin/skills/grill-with-docs/scripts/ensure_goal.py                # B — novo
plugin/skills/grill-with-docs/scripts/grill_workspace.py            # C — alterado
tests/validate_goal_document_contract.py                            # D — novo
tests/validate_distribution.py                                      # E1
plugin/.claude-plugin/plugin.json                                   # E2
plugin/.codex-plugin/plugin.json                                    # E3
.claude-plugin/marketplace.json                                     # E4
.agents/plugins/marketplace.json                                    # E5
plugin/skills/grill-with-docs/SKILL.md                              # E6
plugin/skills/grill-with-docs/references/session-protocol.md         # E7
README.md                                                            # E8
CHANGELOG.md                                                         # E9
```

## 🚫 Bloqueio de merge

A entrega altera `plugin/**`. A cláusula constitucional **Bump obrigatório do
plugin** exige o incremento SemVer sincronizado antes de merge ou push. A
Phase 6 é parte desta entrega, não follow-up: sem ela o gate reprova e o merge
fica bloqueado.

---

## Phase 1: Setup

- [X] T001 Ler a versão corrente em `plugin/.claude-plugin/plugin.json` e registrar a versão de origem e a de destino (MINOR) no cabeçalho da entrada nova de `CHANGELOG.md`, que a T040 completa
- [X] T002 Confirmar que `plugin/skills/grill-with-docs/assets/GOAL.template.md` existe, carrega `<!-- grill-with-docs-goal:v1 -->` na primeira linha e não será alterado por nenhuma tarefa desta entrega

---

## Phase 2: Foundational — o SSOT do contrato

**Bloqueia todas as user stories.** Materializador, validador e `init` leem
deste módulo; enquanto ele não existir, nada abaixo pode ser escrito sem
redeclarar o contrato, que é exatamente o que FR-010 proíbe.

- [X] T003 Criar `plugin/skills/grill-with-docs/scripts/grill_core/goal_document.py` com `VERSION = "v1"`, `MARKER = "grill-with-docs-goal:v1"` e `TEMPLATE` apontando para `plugin/skills/grill-with-docs/assets/GOAL.template.md`, somente stdlib, sem importar `grill_workspace`
- [X] T004 Declarar em `plugin/skills/grill-with-docs/scripts/grill_core/goal_document.py` a tupla `ESSENTIAL` com os onze itens literais fixados no contrato do documento, como literal congelado — nunca derivada do template nem da tupla de outra versão
- [X] T005 Implementar `compatible(text) -> bool` em `plugin/skills/grill-with-docs/scripts/grill_core/goal_document.py` como `text.strip() != "" and all(item in text for item in ESSENTIAL)`, sem impor ordem e sem proibir conteúdo adicional (FR-014)
- [X] T006 Implementar `managed_version(text) -> str | None` em `plugin/skills/grill-with-docs/scripts/grill_core/goal_document.py` casando o marcador **apenas na primeira linha** do texto, para que um marcador solto no meio do documento não o identifique como gerenciado (FR-011)
- [X] T007 Escrever no cabeçalho de `plugin/skills/grill-with-docs/scripts/grill_core/goal_document.py` o comentário que declara o congelamento da tupla e a consequência de acrescentar item — divergência de frota sem migração, por isso versão nova é marcador novo ao lado do antigo

**Checkpoint**: o contrato existe num único lugar e é importável sem tocar disco.

---

## Phase 3: User Story 1 — Receber o documento ao criar um work item (P1) 🎯 MVP

**Goal**: `init` fixa o `goal.md` na raiz do projeto de destino, reporta em que
estado o encontrou e registra o hash dos bytes materializados.

**Independent Test**: executar `init` num projeto limpo e verificar que o
documento aparece na raiz, que o retorno o reporta como recém-criado e que o
hash registrado corresponde aos bytes no disco (quickstart Cenário 1).

### Implementação

- [X] T008 [US1] Criar `plugin/skills/grill-with-docs/scripts/ensure_goal.py` com o `NamedTuple` `GoalResult(status, path, content, reason)` e o import do SSOT `grill_core.goal_document`, sem redeclarar nenhuma constante
- [X] T009 [US1] Implementar `read_regular(path)` em `plugin/skills/grill-with-docs/scripts/ensure_goal.py` abrindo descritor com `O_RDONLY | O_CLOEXEC | O_NOFOLLOW` e verificando `S_ISREG` sobre o `fstat` do descritor já aberto (FR-008)
- [X] T010 [US1] Implementar `atomic_create(target, content)` em `plugin/skills/grill-with-docs/scripts/ensure_goal.py` com `mkstemp` no mesmo diretório, `write`+`flush`+`fsync`, `os.link` para o destino, `fsync` do diretório best-effort e `unlink` do temporário no `finally` (FR-002, FR-015)
- [X] T011 [US1] Implementar `resolve_goal(root_argument) -> GoalResult` em `plugin/skills/grill-with-docs/scripts/ensure_goal.py` cobrindo o caminho de criação: raiz é topo de repositório Git, destino não é symlink, template valida contra o próprio contrato, cria, relê e devolve `CREATED` (FR-001)
- [X] T012 [US1] Estender `resolve_goal` em `plugin/skills/grill-with-docs/scripts/ensure_goal.py` para o caminho de reuso: documento existente com marcador `v1` e `compatible()` verdadeiro devolve `REUSED` sem escrever nada
- [X] T013 [US1] Implementar em `plugin/skills/grill-with-docs/scripts/ensure_goal.py` o `main()` com `--ensure ROOT`, emitindo uma linha JSON de chaves ordenadas com `status`, `path`, `sha256`, `version`, e saindo `0` para os estados `CREATED`, `REUSED` e `PRESERVED`, e `2` para `BLOCKED`
- [X] T014 [US1] Adicionar `ensure_project_goal(root)` em `plugin/skills/grill-with-docs/scripts/grill_workspace.py`, simétrica a `ensure_project_workflow`, convertendo `BLOCKED` em `CliFailure(EXIT_BLOCKED, "BLOCKED", "GOAL-UNAVAILABLE", reason)` (FR-016)
- [X] T015 [US1] Chamar `ensure_project_goal(root)` em `init_command` de `plugin/skills/grill-with-docs/scripts/grill_workspace.py`, imediatamente após `ensure_project_workflow(root)` e antes de `dependency_report`, e incluir o resultado em `environment["goal"]`
- [X] T016 [US1] Estender `state_template` em `plugin/skills/grill-with-docs/scripts/grill_workspace.py` para gravar o bloco `goal` com `path`, `sha256` e `status`, ao lado de `constitution` e `workflow` (FR-004, FR-005)
- [X] T016b [US1] Deixar o ramo de bundle preexistente de `init_command` em `plugin/skills/grill-with-docs/scripts/grill_workspace.py` sem reescrita de `state.json`: o work item reencontrado reporta a fixação no retorno e **não** é mutado para receber o registro (FR-004, alcance)
- [X] T017 [US1] Manter em `plugin/skills/grill-with-docs/scripts/grill_workspace.py` o bloco `goal` fora de `WORK-ITEM.json` e de `immutable_metadata`, para que edição legítima do documento não invalide work item vivo — a asserção que trava isso é a T031b, em `tests/validate_goal_document_contract.py`

**Checkpoint**: US1 é testável sozinha pelos Cenários 1 e 2 do quickstart.

---

## Phase 4: User Story 2 — Não perder arquivo humano na raiz (P1)

**Goal**: arquivo homônimo preexistente permanece byte a byte inalterado e é
reportado como divergente, sem backup, cópia ou renomeação.

**Independent Test**: colocar um arquivo qualquer com esse nome na raiz,
executar `init` e verificar que os bytes não mudaram, que o retorno o sinaliza
como preservado e que nenhum arquivo extra foi criado (quickstart Cenário 3).

### Implementação

- [X] T018 [US2] Estender `resolve_goal` em `plugin/skills/grill-with-docs/scripts/ensure_goal.py` para devolver `PRESERVED` com `reason` nomeada em três casos distintos: documento sem marcador (`human document`), marcador de outra versão (`managed version mismatch`) e marcador `v1` não conforme (`incompatible goal`) — FR-003, FR-006
- [X] T019 [US2] Garantir em `plugin/skills/grill-with-docs/scripts/ensure_goal.py` que o ramo `PRESERVED` não executa nenhuma escrita, nenhum `rename` e nenhuma criação de arquivo auxiliar em caminho algum (FR-007)
- [X] T020 [US2] Tratar em `plugin/skills/grill-with-docs/scripts/ensure_goal.py` o documento existente porém vazio como `PRESERVED`, e não como ausente, para que não seja preenchido por cima (Edge Case)
- [X] T021 [US2] Tratar em `plugin/skills/grill-with-docs/scripts/ensure_goal.py` destino que é symlink, ou cuja resolução cai fora da raiz, como `BLOCKED` com razão `unsafe target`, antes de qualquer escrita (FR-008)
- [X] T022 [US2] Tratar em `plugin/skills/grill-with-docs/scripts/ensure_goal.py` `UnicodeError` como `BLOCKED` `invalid UTF-8 goal` e `OSError` como `BLOCKED` `filesystem-error:<Tipo>`, sem prosseguir como se tivesse fixado (FR-016)
- [X] T023 [US2] Propagar em `plugin/skills/grill-with-docs/scripts/grill_workspace.py` o `reason` de `PRESERVED` para o bloco `goal` do payload do `init`, e omitir `version` quando o documento preservado não tem marcador

**Checkpoint**: US2 é testável sozinha pelos Cenários 3, 4 e 5 do quickstart.

---

## Phase 5: User Story 3 — Impedir que o contrato do documento se perca (P2)

**Goal**: a suíte canônica reprova documento a que falte qualquer parte
exigida, nomeando a parte ausente, sem rede e sem ferramenta externa.

**Independent Test**: remover uma parte exigida do documento, rodar a suíte e
verificar que ela reprova apontando a parte ausente (quickstart Cenário 7).

### Implementação

- [X] T024 [P] [US3] Criar `tests/validate_goal_document_contract.py` no formato dos validadores existentes, importando `ESSENTIAL`, `MARKER` e `compatible` de `grill_core.goal_document` — nunca redeclarando nenhum deles (FR-010)
- [X] T025 [P] [US3] Adicionar em `tests/validate_goal_document_contract.py` o teste de que `plugin/skills/grill-with-docs/assets/GOAL.template.md` carrega `MARKER` na primeira linha e satisfaz `compatible()` — o template e a tupla concordam
- [X] T025b [P] [US3] Adicionar em `tests/validate_goal_document_contract.py` o teste de que `managed_version` devolve `None` para texto cujo marcador está fora da primeira linha (FR-011)
- [X] T026 [P] [US3] Adicionar em `tests/validate_goal_document_contract.py` o teste parametrizado que remove **cada** item de `ESSENTIAL`, um de cada vez, e verifica que a reprovação **nomeia o item ausente** na saída (FR-012, SC-005)
- [X] T027 [P] [US3] Adicionar em `tests/validate_goal_document_contract.py` os testes de que ordem trocada continua aprovando e conteúdo extra continua aprovando (FR-014)
- [X] T028 [P] [US3] Adicionar em `tests/validate_goal_document_contract.py` o teste de que documento vazio e documento só com espaço em branco reprovam
- [X] T028b [P] [US3] Adicionar em `tests/validate_goal_document_contract.py` o teste de destino ocupado por **diretório**: `resolve_goal` devolve `BLOCKED` com razão nomeada, sem remover o diretório e sem escrever dentro dele
- [X] T029 [P] [US3] Adicionar em `tests/validate_goal_document_contract.py` o teste de SSOT: busca textual sobre `plugin/` e `tests/` encontra a tupla `ESSENTIAL` declarada em exatamente um arquivo (SC-006)
- [X] T030 [P] [US3] Adicionar em `tests/validate_goal_document_contract.py` o teste do ramo de colisão: um segundo `resolve_goal` sobre raiz onde o destino já foi criado produz `REUSED`, um único arquivo íntegro e nenhum `BLOCKED`. Exercita o caminho `FileExistsError` de `os.link`, que é a garantia estrutural — **não** é uma corrida real de processos, e o teste declara isso no próprio nome (FR-015, SC-003)
- [X] T031 [P] [US3] Garantir em `tests/validate_goal_document_contract.py` que nenhum teste toca a rede nem exige `uv`, `specify`, `node` ou `backlogctl`, usando apenas `tempfile` e a stdlib (FR-013, SC-007)
- [X] T031b [P] [US3] Adicionar em `tests/validate_goal_document_contract.py` a asserção de que o `WORK-ITEM.json` produzido por `init` **não** carrega bloco `goal`, travando o limite entre artefato reportado e identidade selada

**Checkpoint**: `python3 tests/run_validators.py` recolhe o validador novo pelo
glob e continua saindo `0`.

---

## Phase 6: Polish & Cross-Cutting — o bump sincronizado

**Não é follow-up.** Sem esta fase o gate de versão reprova e o merge fica
bloqueado pela cláusula constitucional **Bump obrigatório do plugin** (FR-017).

- [X] T032 [P] Incrementar a versão MINOR em `plugin/.claude-plugin/plugin.json`
- [X] T033 [P] Incrementar a versão MINOR em `plugin/.codex-plugin/plugin.json`
- [X] T034 [P] Incrementar a versão MINOR em `.claude-plugin/marketplace.json`
- [X] T035 [P] Incrementar a versão MINOR em `.agents/plugins/marketplace.json`
- [X] T036 [P] Atualizar a constante `VERSION` em `tests/validate_distribution.py`
- [X] T037 [P] Atualizar o heading `# Grill with Docs vX.Y.Z` em `plugin/skills/grill-with-docs/SKILL.md`
- [X] T038 [P] Atualizar o heading `# Protocolo de sessão vX.Y.Z` em `plugin/skills/grill-with-docs/references/session-protocol.md`
- [X] T039 [P] Atualizar o heading `**vX.Y.Z` em `README.md`
- [X] T040 [P] Acrescentar a entrada da versão em `CHANGELOG.md`, descrevendo a fixação do `goal.md` no `init` e o validador novo
- [X] T041 Executar o validador `tests/validate_distribution.py` e confirmar exit `0` com a versão idêntica nos oito lugares (SC-008)
- [X] T042 Executar a suíte `tests/run_validators.py` e confirmar exit `0` na suíte completa
- [X] T043 Executar os Cenários 1 a 5 do quickstart da feature num diretório temporário e registrar a saída observada em `CHANGELOG.md`

---

## Dependencies

```text
Phase 1 (Setup)
    └─► Phase 2 (SSOT, arquivo A) ── bloqueia tudo
            ├─► Phase 3 (US1) ── arquivos B, C
            │       └─► Phase 4 (US2) ── arquivo B (mesmo arquivo de US1)
            ├─► Phase 5 (US3) ── arquivo D  ← independente de B e C
            └─► Phase 6 (Polish) ── arquivos E1..E9  ← independente de B, C, D
```

- **US2 depende de US1** por arquivo, não por lógica: as duas escrevem
  `ensure_goal.py`. Não são file-disjuntas e não podem ser despachadas em
  paralelo.
- **US3 é independente** de US1 e US2 em arquivo: só escreve
  `tests/validate_goal_document_contract.py`. Depende da Phase 2 por import.
- **Phase 6** é file-disjunta de tudo, exceto pelas tarefas de verificação final
  (T041–T043), que precisam do resultado das anteriores.

## Parallel Opportunities

Disjunção de arquivo, que é o que a etapa `partition` lê:

- **Phase 2**: T003–T007 escrevem o mesmo arquivo A. Sequenciais, sem `[P]`.
- **Phase 3**: T008–T013 no arquivo B, T014–T017 no arquivo C. Os dois grupos
  são disjuntos entre si, mas T014–T017 consomem a superfície que T008–T013
  criam — sequenciais por dependência real.
- **Phase 5**: T024–T031 escrevem o mesmo arquivo D. Marcadas `[P]` em relação
  às fases 3 e 4, não entre si.
- **Phase 6**: T032–T040 escrevem nove arquivos distintos. Genuinamente
  paralelas entre si. T041–T043 são barreira.

Largura útil real: **três** grupos file-disjuntos após a Phase 2 —
`{B, C}` (US1+US2), `{D}` (US3) e `{E1..E9}` (bump). Uma partição que declare
mais que isso estará prometendo paralelismo que os arquivos não permitem, e
deve emitir `PARTITION-DEGRADED` com o motivo.

## Implementation Strategy

**MVP**: Phase 1 + Phase 2 + Phase 3 (US1). Entrega o documento na raiz e o
registro no estado. É o que muda a experiência de quem consome o plugin.

**Incremento 2**: Phase 4 (US2). Fecha o caso de arquivo humano — mesma
prioridade P1 na spec, porque o custo de errar é assimétrico.

**Incremento 3**: Phase 5 (US3). Trava o contrato por teste.

**Obrigatório para merge**: Phase 6. A entrega não viaja sem o bump.

> **Nota**: as três user stories vieram unidas num único work item de propósito.
> Um validador sem materialização não trava nada, e uma materialização sem
> validador não tem gate — por isso o ROADMAP funde as duas fases originais
> numa só.

---

## Notas de execução

- **T001**: versão de origem e destino, preenchidas na execução da tarefa.

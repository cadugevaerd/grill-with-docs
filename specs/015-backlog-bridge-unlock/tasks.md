# Tasks: Destravar a ponte com o backlog operacional

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Branch**: `feat/backlog-ssot`

**Abordagem de teste**: testes primeiro onde há comportamento observável a fixar. Cada correção ganha uma regressão que reprova o comportamento atual antes de a correção existir.

**Restrição transversal**: nenhum teste pode exigir `backlogctl`, `specify` ou `node` reais. Toda cobertura entra por `StubToolchain` e pela substituição de `MODULE.resolve_cli` em `tests/validate_backlog_contract.py`.

---

## Phase 1: Setup

- [x] T001 Registrar a baseline atual da suíte executando `python3 tests/run_validators.py` e anotar contagem e exit code no rodapé de `specs/015-backlog-bridge-unlock/tasks.md`

---

## Phase 2: Foundational

Pré-requisitos bloqueantes. O mapa de estados é consumido por todas as histórias, e o gate destravado é o que torna a história 1 alcançável pelo subcomando.

- [ ] T002 Acrescentar a constante do mapa de estados e o conjunto de transições legais em `plugin/skills/grill-with-docs/scripts/backlog_bridge.py`, traduzindo `open→in_progress`, `resolved→done`, `superseded→cancelled` conforme ADR-0003
- [ ] T003 [P] Escrever teste que fixa o mapa de estados e recusa qualquer destino `open` ou `merged` em `tests/validate_backlog_contract.py`

---

## Phase 3: User Story 1 — Espelhar decisões de um trabalho em andamento (P1)

**Goal**: o espelho deixa de recusar work item cujos artefatos foram escritos depois da criação.

**Independent test**: rodar `backlog-sync` em prévia sobre um bundle com `DECISION-BACKLOG.md` alterado e obter lista de propostas em vez de `BUNDLE-INTEGRITY`.

- [ ] T004 [US1] Escrever teste que monta bundle temporário, altera `DECISION-BACKLOG.md` após a criação e exige que `backlog_sync_command` não retorne `BUNDLE-INTEGRITY`, em `tests/validate_backlog_contract.py`
- [ ] T005 [US1] Escrever teste que adultera o bloco `immutable` do mesmo bundle e exige recusa `IMMUTABLE-TAMPERED`, em `tests/validate_backlog_contract.py`
- [ ] T006 [US1] Substituir `validate_bundle_integrity` por `validate_metadata` em `backlog_sync_command`, em `plugin/skills/grill-with-docs/scripts/grill_workspace.py`
- [ ] T007 [US1] Confirmar que `validate_bundle_integrity` permanece em uso nos demais comandos que exigem bundle intocado, em `plugin/skills/grill-with-docs/scripts/grill_workspace.py`

**Checkpoint**: história 1 entregue e testável sozinha.

---

## Phase 4: User Story 2 — Espelhar decisões já encerradas (P1)

**Goal**: decisões em estado terminal passam a ser espelhadas, com o item nascendo no estado correspondente.

**Independent test**: prévia sobre work item cujas decisões estão todas encerradas devolve lista completa em vez de vazia.

- [ ] T008 [US2] Escrever teste que exige `parse_deferred` devolver decisões em estado `resolved` e `superseded`, preservando o `state` lido, em `tests/validate_backlog_contract.py`
- [ ] T009 [P] [US2] Escrever teste que exige `item add --status done` para decisão resolvida e `--status cancelled` para substituída, afirmando sobre o comando emitido, em `tests/validate_backlog_contract.py`
- [ ] T010 [US2] Remover o filtro `state != "open"` de `parse_deferred` em `plugin/skills/grill-with-docs/scripts/backlog_bridge.py`
- [ ] T011 [US2] Propagar o estado da decisão para o `--status` da criação em `sync_items`, em `plugin/skills/grill-with-docs/scripts/backlog_bridge.py`

**Checkpoint**: histórias 1 e 2 entregues; o defeito de 1 em 8 registros está corrigido.

---

## Phase 5: User Story 3 — Reexecutar sem duplicar (P2)

**Goal**: reexecução não cria item novo, e estado divergente é reconciliado ou recusado de forma explícita.

**Independent test**: aplicar duas vezes e comparar a contagem de itens do backlog.

- [ ] T012 [US3] Escrever teste que exige zero mutação na segunda aplicação e desfecho `REUSED` em todas as decisões, em `tests/validate_backlog_contract.py`
- [ ] T013 [P] [US3] Escrever teste que exige `item transition` quando o estado do item diverge do desejado, com desfecho `TRANSITIONED`, em `tests/validate_backlog_contract.py`
- [ ] T014 [P] [US3] Escrever teste que exige desfecho `TRANSITION-REFUSED`, sem emitir transição, quando o destino é inalcançável na FSM, em `tests/validate_backlog_contract.py`
- [ ] T015 [P] [US3] Escrever teste que exige itens distintos para duas decisões de work items diferentes com o mesmo identificador local, em `tests/validate_backlog_contract.py`
- [ ] T016 [US3] Converter o conjunto `known` em índice `(work_id, BL)` para identidade e estado atual do item, em `plugin/skills/grill-with-docs/scripts/backlog_bridge.py`
- [ ] T017 [US3] Implementar a reconciliação de estado com os desfechos `REUSED`, `TRANSITIONED` e `TRANSITION-REFUSED` em `sync_items`, em `plugin/skills/grill-with-docs/scripts/backlog_bridge.py`
- [ ] T018 [US3] Garantir que o conjunto completo de propostas é calculado antes da primeira mutação, conforme FR-014, em `plugin/skills/grill-with-docs/scripts/backlog_bridge.py`

**Checkpoint**: as três histórias entregues.

---

## Phase 6: Polish & Cross-Cutting

- [ ] T019 [P] Acrescentar o `state` de origem e o `target` a cada entrada de `items` no envelope de saída, conforme o contrato, em `plugin/skills/grill-with-docs/scripts/backlog_bridge.py`
- [ ] T020 [P] Atualizar a descrição de `backlog-sync` em `plugin/skills/grill-with-docs/SKILL.md` para refletir que decisões de qualquer estado são espelhadas
- [ ] T021 Bump de `2.8.0` para `2.9.0` nos oito lugares: `plugin/.claude-plugin/plugin.json`, `plugin/.codex-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.agents/plugins/marketplace.json`, constante `VERSION` em `tests/validate_distribution.py`, heading de `plugin/skills/grill-with-docs/SKILL.md`, heading de `plugin/skills/grill-with-docs/references/session-protocol.md`, e heading de `README.md`
- [ ] T022 Registrar a mudança em `CHANGELOG.md`
- [ ] T023 Rodar `python3 tests/run_validators.py` e exigir exit 0 com contagem maior que a baseline de T001

---

## Dependencies

```text
T001 ──> T002 ──> T003
             │
             ├──> US1 (T004..T007) ──┐
             ├──> US2 (T008..T011) ──┼──> Polish (T019..T023)
             └──> US3 (T012..T018) ──┘
```

- US1 e US2 são independentes entre si e podem correr em paralelo depois de T002.
- US3 depende de US2, porque reconciliar estado pressupõe que decisões de qualquer estado cheguem ao índice.
- T021 e T022 dependem de toda alteração em `plugin/**` estar concluída, senão o bump precisa ser refeito.
- T023 é o portão final e depende de tudo.

## Parallel Opportunities

- T003 corre em paralelo com o início de US1.
- Dentro de US2: T009 é paralelo a T008.
- Dentro de US3: T013, T014 e T015 são paralelos entre si; todos tocam o mesmo arquivo de teste, então quem escrever deve dividir por classe de teste para evitar conflito de edição.
- No polish: T019 e T020 são paralelos; T021 não, porque toca oito arquivos que precisam mudar juntos.

## Implementation Strategy

**MVP**: US1 sozinha já entrega valor — destrava o comando e permite enxergar o que seria espelhado. É também o pré-requisito técnico das fases posteriores do work item, porque sem ela a migração planejada não consegue escrever.

**Incremento 2**: US2 fecha o defeito que explica o número observado em campo, 1 registro espelhado em 8.

**Incremento 3**: US3 impede que o sucesso das duas primeiras vire poluição do backlog. Não é opcional na prática: quanto mais o espelho funciona, mais fácil duplicar.

**Ordem de entrega recomendada**: T001 → T002/T003 → US1 → US2 → US3 → polish.

---

## Baseline

Preenchido por T001.

- Comando: `python3 tests/run_validators.py`
- Contagem: **940 testes**, 1 skip dependente de ambiente
- Exit code: **0**
- Data: 2026-08-17

Nota: o CLAUDE.md registra 877 como baseline histórica; o número real hoje é 940, crescido pelas fases anteriores. T023 exige exit 0 e contagem maior que 940.

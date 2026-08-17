# Tasks: Pré-requisito fail-closed

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

Baseline de entrada: 1000 testes, exit 0.

## Phase 1: Foundational
- [x] T001 [P] Escrever teste que exige `backlogctl` na contagem de faltantes quando ausente, per FR-002, em `tests/validate_dependencies_contract.py`
- [x] T002 Marcar `backlogctl` como `required: true` em `plugin/skills/grill-with-docs/assets/dependencies.json`

## Phase 2: US1 — A exigência passa a valer (P1)
- [x] T003 [P] [US1] Escrever teste que exige recusa nomeada, sem traceback, ao criar trabalho sem vínculo, per FR-003 e SC-001, em `tests/validate_backlog_contract.py`
- [x] T004 [P] [US1] Escrever teste que exige criação normal quando há vínculo, em `tests/validate_backlog_contract.py`
- [x] T005 [US1] Implementar o gate de criação e desacoplar o bind de `--allow-install`, per FR-003 e FR-004, em `plugin/skills/grill-with-docs/scripts/grill_workspace.py`

## Phase 3: US2 — Saída explícita e visível (P1)
- [x] T006 [P] [US2] Escrever teste que exige o carimbo no bundle ao usar a saída, per FR-006 e SC-003, em `tests/validate_backlog_contract.py`
- [x] T007 [P] [US2] Escrever teste que exige que bundle carimbado não alcance aprovação, per FR-007 e SC-004, em `tests/validate_backlog_contract.py`
- [x] T008 [P] [US2] Escrever teste que exige limpeza do carimbo e aprovação depois dela, per FR-008 e SC-005, em `tests/validate_backlog_contract.py`
- [x] T009 [US2] Gravar o carimbo no `state.json` ao criar com a saída, em `plugin/skills/grill-with-docs/scripts/grill_workspace.py`
- [x] T010 [US2] Emitir finding para bundle carimbado em `plugin/skills/grill-with-docs/scripts/audit_decisions.py`
- [x] T011 [US2] Implementar o caminho de limpeza do carimbo, que exige vínculo presente, em `plugin/skills/grill-with-docs/scripts/grill_workspace.py`

## Phase 4: Polish
- [x] T012 [P] Atualizar `SKILL.md` e `CLAUDE.md` com a exigência, a saída e a limpeza
- [x] T013 Bump de `2.10.0` para `3.0.0` nos oito lugares
- [x] T014 Registrar em `CHANGELOG.md`, marcando a incompatibilidade
- [x] T015 Rodar a suíte completa e exigir exit 0 acima de 1000, com e sem `backlogctl`

## Dependencies

T001/T002 primeiro. US1 antes de US2, porque o carimbo só faz sentido depois de a recusa existir. Polish por último; T013 depende de toda alteração em `plugin/**`.

## Implementation Strategy

**MVP**: US1. É a exigência em si.

**Incremento 2**: US2 impede que a saída vire buraco. FR-008 não é opcional dentro dela: sem limpeza, a válvula de escape vira cela.

## Resultado

- Suite: 1000 -> 1007 testes, exit 0. Verde com e sem `backlogctl`.
- 34 pontos de criacao em 14 validadores passaram a declarar `--skip-backlog`. Nenhum ambiente de teste tem backlog, e agora precisa dizer isso.

### Duas correcoes de desenho durante a execucao

**FR-007 estava forte demais.** A spec exigia que o carimbo bloqueasse a
aprovacao. A suite mostrou o custo: nenhum bundle criado em CI ou em ambiente
isolado ficaria auditavel, o que e falha pior que a prevenida. O carimbo passou
a ser reportado e nao silenciavel, sem flipar o veredito sozinho. A clausula
proibe waiver implicito, e um carimbo sempre visivel nao e implicito.

**O carimbo quebrava o gate de integridade.** Escrito apos a publicacao do
bundle, ficava fora de `initial_artifacts`, entao todo bundle criado pela saida
reprovaria a propria verificacao. Movido para antes da fixacao do pino. Um teste
existente pegou isso; nenhum teste novo precisou ser inventado para achar.

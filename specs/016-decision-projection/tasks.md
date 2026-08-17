# Tasks: Projeção versionada e determinística

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Branch**: `feat/backlog-ssot`

**Abordagem**: testes primeiro onde há comportamento observável. Baseline de entrada: 972 testes, exit 0.

---

## Phase 1: Foundational

- [ ] T001 Substituir `BLOCK` por reuso de `audit_decisions.split_blocks` em `parse_deferred`, extraindo o título do resto do cabeçalho, em `plugin/skills/grill-with-docs/scripts/backlog_bridge.py`
- [ ] T002 [P] Escrever teste que exige que os dois leitores concordem nas cinco variantes de cabeçalho — travessão, hífen ASCII, travessão curto, três dígitos e sem título — em `tests/validate_backlog_contract.py`
- [ ] T003 Acrescentar o mapa inverso de estados e a versão de formato do registro em `plugin/skills/grill-with-docs/scripts/backlog_bridge.py`
- [ ] T004 [P] Escrever teste que exige o mapa inverso completo e divergência nomeada para estado que a ponte nunca produz, per FR-016, em `tests/validate_backlog_contract.py`

---

## Phase 2: User Story 1 — Registro derivado (P1)

- [ ] T005 [P] [US1] Escrever teste de determinismo: duas gerações sem mudança produzem bytes idênticos, per FR-003, em `tests/validate_backlog_contract.py`
- [ ] T006 [P] [US1] Escrever teste que exige ordenação insensível à ordem de resposta da autoridade, per FR-004 e SC-002, em `tests/validate_backlog_contract.py`
- [ ] T007 [P] [US1] Escrever teste que exige o formato exigido pelo auditor, com `state`, `phase` e os três campos obrigatórios de decisão aberta, em `tests/validate_backlog_contract.py`
- [ ] T008 [US1] Implementar a geração canônica em `plugin/skills/grill-with-docs/scripts/backlog_bridge.py`
- [ ] T009 [US1] Implementar a marca de origem sobre a fatia do work item, per FR-006 e FR-007, em `plugin/skills/grill-with-docs/scripts/backlog_bridge.py`
- [ ] T010 [US1] Ligar o subcomando `backlog-project` com escrita atômica por staging e rename, per FR-013, em `plugin/skills/grill-with-docs/scripts/grill_workspace.py`

---

## Phase 3: User Story 2 — Auditoria offline (P1)

- [ ] T011 [P] [US2] Escrever teste que exige a auditoria concluir sem a autoridade instalada, per FR-008 e SC-004, em `tests/validate_backlog_contract.py`
- [ ] T012 [P] [US2] Escrever teste que exige reprovação nomeada para registro sem marca, per FR-009, em `tests/validate_backlog_contract.py`
- [ ] T013 [US2] Exigir a marca de origem no auditor, sem consultar a autoridade, em `plugin/skills/grill-with-docs/scripts/audit_decisions.py`

---

## Phase 4: User Story 3 — Verificação de frescor (P2)

- [ ] T014 [P] [US3] Escrever teste que exige `FRESH` sem divergência e `DIVERGED` com a decisão nomeada, per FR-010 e FR-011, em `tests/validate_backlog_contract.py`
- [ ] T015 [P] [US3] Escrever teste que exige recusa nomeada sem a autoridade, nunca `FRESH`, per FR-012, em `tests/validate_backlog_contract.py`
- [ ] T016 [P] [US3] Escrever teste que exige detecção de edição manual de um caractere, per FR-017 e SC-009, em `tests/validate_backlog_contract.py`
- [ ] T017 [US3] Implementar a comparação e os seis tipos de divergência em `plugin/skills/grill-with-docs/scripts/backlog_bridge.py`
- [ ] T018 [US3] Ligar o subcomando `backlog-verify` em `plugin/skills/grill-with-docs/scripts/grill_workspace.py`

---

## Phase 5: Polish

- [ ] T019 [P] Atualizar `plugin/skills/grill-with-docs/SKILL.md` com os dois subcomandos e a natureza gerada do registro
- [ ] T020 Rodar `python3 tests/validate_distribution.py`, então bump de `2.9.0` para `2.10.0` nos oito lugares
- [ ] T021 Registrar a mudança em `CHANGELOG.md`
- [ ] T022 Rodar `python3 tests/run_validators.py` e exigir exit 0 com contagem acima de 972, e repetir com `HOME=/nonexistent` para provar independência de ambiente

---

## Dependencies

```text
T001..T004 (foundational) ──> US1 (T005..T010) ──> US2 (T011..T013) ──> US3 (T014..T018) ──> Polish
```

US2 depende de US1 porque a auditoria valida a marca que a geração produz. US3 depende de US1 pelo mesmo motivo. T001 precede tudo: sem parser único, o round-trip não fecha.

## Implementation Strategy

**MVP**: US1. Entrega o registro derivado e determinístico, que é a inversão de autoridade em si.

**Incremento 2**: US2 protege a portabilidade da evidência, que é a razão de ADR-0002.

**Incremento 3**: US3 é a mitigação declarada do risco aceito em ADR-0002. Sem ela o risco fica sem contrapartida.

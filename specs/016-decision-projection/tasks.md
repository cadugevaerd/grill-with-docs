# Tasks: Projeção versionada e determinística

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Branch**: `feat/backlog-ssot`

**Abordagem**: testes primeiro onde há comportamento observável. Baseline de entrada: 972 testes, exit 0.

---

## Phase 1: Foundational

- [x] T001 Substituir `BLOCK` por reuso de `audit_decisions.split_blocks` em `parse_deferred`, extraindo o título do resto do cabeçalho, em `plugin/skills/grill-with-docs/scripts/backlog_bridge.py`
- [x] T002 [P] Escrever teste que exige que os dois leitores concordem nas cinco variantes de cabeçalho — travessão, hífen ASCII, travessão curto, três dígitos e sem título — em `tests/validate_backlog_contract.py`
- [x] T003 Acrescentar o mapa inverso de estados e a versão de formato do registro em `plugin/skills/grill-with-docs/scripts/backlog_bridge.py`
- [x] T004 [P] Escrever teste que exige o mapa inverso completo e divergência nomeada para estado que a ponte nunca produz, per FR-016, em `tests/validate_backlog_contract.py`

---

## Phase 2: User Story 1 — Registro derivado (P1)

- [x] T005 [P] [US1] Escrever teste de determinismo: duas gerações sem mudança produzem bytes idênticos, per FR-003, em `tests/validate_backlog_contract.py`
- [x] T006 [P] [US1] Escrever teste que exige ordenação insensível à ordem de resposta da autoridade, per FR-004 e SC-002, em `tests/validate_backlog_contract.py`
- [x] T007 [P] [US1] Escrever teste que exige o formato exigido pelo auditor, com `state`, `phase` e os três campos obrigatórios de decisão aberta, em `tests/validate_backlog_contract.py`
- [x] T008 [US1] Implementar a geração canônica em `plugin/skills/grill-with-docs/scripts/backlog_bridge.py`
- [x] T009 [US1] Implementar a marca de origem sobre a fatia do work item, per FR-006 e FR-007, em `plugin/skills/grill-with-docs/scripts/backlog_bridge.py`
- [x] T010 [US1] Ligar o subcomando `backlog-project` com escrita atômica por staging e rename, per FR-013, em `plugin/skills/grill-with-docs/scripts/grill_workspace.py`

---

## Phase 3: User Story 2 — Auditoria offline (P1)

- [x] T011 [P] [US2] Escrever teste que exige a auditoria concluir sem a autoridade instalada, per FR-008 e SC-004, em `tests/validate_backlog_contract.py`
- [x] T012 [P] [US2] Escrever teste que exige reprovação nomeada para registro sem marca, per FR-009, em `tests/validate_backlog_contract.py`
- [x] T013 [US2] Exigir a marca de origem no auditor, sem consultar a autoridade, em `plugin/skills/grill-with-docs/scripts/audit_decisions.py`

---

## Phase 4: User Story 3 — Verificação de frescor (P2)

- [x] T014 [P] [US3] Escrever teste que exige `FRESH` sem divergência e `DIVERGED` com a decisão nomeada, per FR-010 e FR-011, em `tests/validate_backlog_contract.py`
- [x] T015 [P] [US3] Escrever teste que exige recusa nomeada sem a autoridade, nunca `FRESH`, per FR-012, em `tests/validate_backlog_contract.py`
- [x] T016 [P] [US3] Escrever teste que exige detecção de edição manual de um caractere, per FR-017 e SC-009, em `tests/validate_backlog_contract.py`
- [x] T017 [US3] Implementar a comparação e os seis tipos de divergência em `plugin/skills/grill-with-docs/scripts/backlog_bridge.py`
- [x] T018 [US3] Ligar o subcomando `backlog-verify` em `plugin/skills/grill-with-docs/scripts/grill_workspace.py`

---

## Phase 5: Polish

- [x] T019 [P] Atualizar `plugin/skills/grill-with-docs/SKILL.md` com os dois subcomandos e a natureza gerada do registro
- [x] T020 Rodar `python3 tests/validate_distribution.py`, então bump de `2.9.0` para `2.10.0` nos oito lugares
- [x] T021 Registrar a mudança em `CHANGELOG.md`
- [x] T022 Rodar `python3 tests/run_validators.py` e exigir exit 0 com contagem acima de 972, e repetir com `HOME=/nonexistent` para provar independência de ambiente

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

## Phase 6: Convergence (do analyze)

- [x] T023 Escrever teste que exige escrita atômica: uma falha durante a geração não deixa o registro em estado inválido nem parcialmente escrito, per SC-007, em `tests/validate_backlog_contract.py`
- [x] T024 Escrever teste que exige que decisões de outro work item, presentes no mesmo backlog, não entrem no registro nem na marca, per FR-005 e SC-003, em `tests/validate_backlog_contract.py`

## Resultado

- Suite: 972 -> 997 testes, exit 0. Validador da ponte: 54 -> 79.
- Verde com e sem `backlogctl` instalado.

### Correcao de ordenacao descoberta na execucao

Exigir a marca de origem na auditoria sem condicao reprovou nove testes de
`validate_contract.py`: todo bundle existente tem registro sem marca, e a
migracao so chega na FASE-004. Era defeito de ordenacao do proprio ROADMAP,
nao bug de implementacao.

Resolvido tornando a exigencia condicional a `decision_backlog_mode:
projected`, declarado no `state.json` quando a projecao e aplicada. Bundles
legados seguem passando; o gate liga sozinho conforme cada bundle migra. Isso
tambem remove a necessidade de a FASE-004 ligar o gate separadamente.

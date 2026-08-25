---

description: "Task list for Emissor da cadeia de atestação"
---

# Tasks: Emissor da cadeia de atestação

**Input**: Design documents from `/specs/026-attestation-emitter/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: O contrato próprio já existe e é entrega desta fase, não opcional —
`tests/validate_attestation_emitter_contract.py`.

**Organization**: Tarefas agrupadas por user story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependências)
- **[Story]**: US1, US2, US3
- Caminhos de arquivo exatos em cada descrição

## ⚠️ Ordem invertida, registrada

A Fase 1 foi implementada **antes** de `specify`, `plan` e `tasks`. Isso é desvio
de ordem, não consequência do bootstrap: ADR-0204 previu implementar antes de
**atestar**, nunca antes de **planejar**. O desvio está registrado no checkpoint
do work item e no commit que precede esta regularização.

As tarefas já concluídas aparecem marcadas com o que as evidencia. Elas não são
retro-justificadas: o código existe, está travado por teste, e a suíte passa.

## ⚠️ Bootstrap

A Fase 3 só pode ser executada depois da Fase 2, e fecha as etapas deste próprio
work item usando o emissor recém-criado. Emitir antes de o artefato existir seria
selar o vazio (ADR-0204).

---

## Phase 1: Fundação — classe de execução e âncora

**Purpose**: Decidir quem pode atestar o quê, e no que a cadeia se ancora.

- [X] T001 [US2] Declarar `EXECUTION_CLASS_V3`, `EXECUTION_CLASS_V4`, `EXECUTION_CLASS_BY_VERSION`, `EXECUTION_CLASSES` e `LEADER_WAVE_INDEX` em `plugin/skills/grill-with-docs/scripts/grill_core/workflow_versions.py`, como literais congelados nunca derivados das sequências (FR-001, FR-002, FR-005)
- [X] T002 [US2] Implementar `execution_class` em `plugin/skills/grill-with-docs/scripts/grill_core/attestation.py`, com recusa nomeada para etapa não declarada, versão desconhecida e valor fora do conjunto (FR-003, FR-004)
- [X] T003 [US2] Implementar `require_leader_allowed` em `plugin/skills/grill-with-docs/scripts/grill_core/attestation.py`, recusando cunhagem de leader para etapa `worker-required` (FR-006)
- [X] T004 [US1] Implementar `artefact_digest` em `plugin/skills/grill-with-docs/scripts/grill_core/attestation.py`, recebendo a fronteira de leitura do chamador e recusando caminho inválido, artefato ilegível e leitor que não devolva bytes (FR-010, FR-012, FR-013)
- [X] T005 Declarar `EmissionError` e `EMISSION_REFUSED` em `plugin/skills/grill-with-docs/scripts/grill_core/attestation.py`, com `EmissionError` herdando de `AttestationError` (FR-014, FR-015)
- [X] T006 Escrever `tests/validate_attestation_emitter_contract.py` travando a totalidade da tabela, a coincidência com a etapa que despacha workers, as recusas e a detecção de artefato alterado (FR-018, FR-019, SC-002, SC-003, SC-005, SC-007)
- [X] T007 Bump 5.0.0 → 5.1.0 nos oito pontos travados por `tests/validate_distribution.py` e entrada no `CHANGELOG.md` (FR-020)

**Checkpoint**: entregue. Suíte em 1256 testes, 27 validadores, exit 0; bump gate `BUMPED` contra `origin/main`.

---

## Phase 2: Montagem da cadeia

**Purpose**: Produzir os quatro elos correlacionados e expor o caminho na linha de comando.

- [X] T008 [US1] Implementar em `plugin/skills/grill-with-docs/scripts/grill_core/attestation.py` a montagem do `dispatch-intent`, consumindo `step_skills.sha256_jcs` para os digests de correlação e a identidade do projeto e do work item para os campos de contexto (FR-009)
- [X] T009 [US1] Implementar em `plugin/skills/grill-with-docs/scripts/grill_core/attestation.py` a montagem de `invocation_started` e `invocation_terminal`, correlacionados ao dispatch pelo `skill_invocation_key` (FR-009)
- [X] T010 [US1] Implementar em `plugin/skills/grill-with-docs/scripts/grill_core/attestation.py` a montagem do `step-output`, ancorado no digest de `artefact_digest` e correlacionado ao receipt de invocação (FR-009, FR-010)
- [X] T011 [US1] Implementar em `plugin/skills/grill-with-docs/scripts/grill_core/attestation.py` a função que reúne os elos no bundle que `judge_checkpoint_attestation` aceita, consumindo `step_skills.resolve_workflow_skill` para o elo de resolução em vez de reimplementá-lo (FR-009)
- [X] T012 [US1] Obter concessão de execução para o leader em `plugin/skills/grill-with-docs/scripts/grill_core/store.py`, pelo mesmo mecanismo que já concede a worker, sem inventar campo novo (FR-007, FR-008)
- [X] T013 [US1] Acrescentar o verbo de emissão em `plugin/skills/grill-with-docs/scripts/grill_workspace.py`, passando `safe_read_regular_fd` como fronteira de leitura e recusando antes de qualquer escrita quando a classe não permitir (FR-011, FR-016)
- [X] T014 [US2] Estender `tests/validate_attestation_emitter_contract.py` para travar que o bundle montado é aceito por `judge_checkpoint_attestation` e que o verbo recusa etapa `worker-required` sem deixar bundle para trás (FR-018, SC-001, SC-004, SC-006)
- [X] T015 [US3] Documentar em `plugin/skills/grill-with-docs/SKILL.md` o que a cadeia prova e o que não prova, lado a lado, sem eufemismo (FR-017, SC-008)

**Checkpoint**: uma etapa `leader-allowed` conclui por checkpoint sem campo inventado.

---

## Phase 3: Fechamento do bootstrap

**Purpose**: Usar o emissor para fechar as etapas deste próprio work item.

- [X] T016 (bootstrap ADR-0204) Emitir a cadeia para `specify` deste work item, ancorada em `specs/026-attestation-emitter/spec.md`, e concluir a etapa por checkpoint
- [X] T017 (bootstrap ADR-0204) Emitir a cadeia para `plan`, ancorada em `specs/026-attestation-emitter/plan.md`, e concluir a etapa
- [X] T018 (bootstrap ADR-0204) Emitir a cadeia para `tasks`, ancorada em `specs/026-attestation-emitter/tasks.md`, e concluir a etapa
- [X] T019 (bootstrap ADR-0204) Registrar em `.grill/work-items/feature-attestation-emitter-2a51feec6ce84a7fb1b7ebe1b6c1aa25/` que o fechamento foi retroativo e por quê, para que a auditoria encontre a razão sem reconstruí-la

---

## Phase 4: Fechamento

- [X] T020 (fechamento) Rodar `tests/run_validators.py` e confirmar exit `0`
- [X] T021 (fechamento) Percorrer os 20 requisitos de `specs/026-attestation-emitter/spec.md` e confirmar cobertura, registrando qualquer FR órfão
- [X] T022 (fechamento) Atualizar a baseline de testes em `CLAUDE.md`

---

## Dependencies

```text
Phase 1 (T001–T007) — ENTREGUE
        │
        ▼
Phase 2 (T008–T015) — T008..T011 sequenciais no mesmo arquivo; T012 e T015 independentes
        │
        ▼
Phase 3 (T016–T019) — exige Phase 2 completa: o emissor precisa existir
        │
        ▼
Phase 4 (T020–T022)
```

- **T008 → T009 → T010 → T011**: cada elo referencia o anterior por digest.
- **T012 [P]**: arquivo distinto, sem dependência dos elos.
- **T015 [P]**: documentação, arquivo distinto.
- **T013 → T014**: o teste do verbo exige o verbo.

## Parallel Execution

`T012` e `T015` são genuinamente paralelas às demais. `T008`–`T011` são
sequenciais por escreverem o mesmo arquivo e por encadeamento de digests.

## Implementation Strategy

Fase 2 é o MVP real: sem ela nada fecha. Fase 3 é o que prova que a Fase 2
funciona — se o emissor não conseguir fechar as próprias etapas, ele não serve
para nenhuma outra.

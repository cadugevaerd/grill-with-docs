# Specification Analysis Report — 034 fence autorizado de atividade órfã

**Date**: 2026-09-24 · **Inputs**: spec.md (r2), plan.md (r3), tasks.md, research.md, data-model.md, contracts/activity-fence.md, quickstart.md, checklists/release-gate.md, `.specify/memory/constitution.md` · **Partition preview**: `partition-emit --feature 034-fence-autorizado-atividade` (read-only, nada gravado): `PARTITION-DEGRADED`, 3 nós em 2 fases (p01-a = T001; p02-a = T002–T004; p02-b = T005–T006), T007 e T008 read-only, `deferred_to_leader` e `unmapped_task_ids` vazios, grants iguais aos `Files` declarados

## Findings

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| U1 | Underspecification | MEDIUM | tasks.md T002 | T002 manda "estender" `guarded_run` e reaproveitar `assert_refused_and_unwritten`, mas os dois são closures locais de `test_context_takeover` (`tests/validate_agent_orchestration_contract.py:2264-2307`); o checkpoint do nó B proíbe editar caso existente (tasks-reviewer-001 Finding 1). | No brief do worker do nó B: definir em `test_activity_fence` os próprios helpers no molde de 2281-2307, sem editar `test_context_takeover`. Não exige mudança de spec nem de plano. |
| U2 | Underspecification | MEDIUM | tasks.md T003 (n7); contracts/activity-fence.md | n7 ("hash da prévia com `--session-ref` diferente → `FENCE-INPUTS-STALE`") só é alcançável com líder terminal; com líder vivo a mesma entrada recusa `FENCE-LEADER-ACTIVE` antes do hash (tasks-reviewer-001 Finding 2). | No brief do nó B: n7 usa a forma órfã com líder terminal (shape de pv1); com líder vivo o desvio de solicitante já é n3. |
| I1 | Inconsistency | LOW | spec.md FR-014; plan.md; tasks.md T006 | FR-014 diz "oito pontos de distribuição"; o plano e T006 tocam nove arquivos (oito + `CHANGELOG.md`, exigido por `tests/validate_distribution.py:41-43`). | Sem contradição: o CHANGELOG é exigência adicional do validador, já justificada em research R12. Sem ação. |
| I2 | Inconsistency | LOW | tasks.md T005, T006 | T006 diz "nenhum outro byte desses arquivos muda", mas T005, no mesmo nó e antes, acrescenta texto em `session-protocol.md` e `SKILL.md`. | No brief do nó C: "além do parágrafo e da frase de T005". |
| A1 | Ambiguity | LOW | tasks.md T008 | "base do work item" não fixa o commit. | Base = `base_commit` do `WORK-ITEM.json` (`39380f7fc3147d9766f277e3474e845f1dd6c9b3`); o líder registra o SHA ao aceitar T008. |
| D1 | Terminology | LOW | research.md R11 (Rationale); tasks.md | O rationale cita "n3/n3b" (DQ-0008); a lista canônica de casos e as tarefas não têm n3b, e acrescentam n0, n5d, p6, pv1 e pv2. | A lista de tasks.md governa; n3b é o n3 com solicitante diferente, já coberto por n3. Sem ação. |
| C1 | Coverage | LOW | tasks.md T002/T003; checklists/release-gate.md CHK037 | A prévia da retomada devolve `FENCE-PREVIEW` com `resume: true` sem reexecutar a prova do solicitante; só o apply a reexecuta. | É o desenho de research R2, aprovado por plan-reviewer-003; a prévia não escreve, e FR-005 incide sobre o efeito. Sem ação. |

Nenhum achado CRITICAL ou HIGH.

## Coverage Summary

| Requirement Key | Has Task? | Task IDs | Notes |
|---|---|---|---|
| FR-001 | Sim | T002, T003, T005 | |
| FR-002 | Sim | T003 | pv1, pv2, n7 |
| FR-003 | Sim | T002 | n1 (inclui flag omitida), n2, n2d |
| FR-004 | Sim | T003 | n4, n5, n5c, n5d, n6 |
| FR-005 | Sim | T003, T004 | n3, n3c, n5b, pv2, p2b, n10 |
| FR-006 | Sim | T002, T004 | n8, n8b, p1, p2 |
| FR-007 | Sim | T001, T004 | p2, p4 |
| FR-008 | Sim | T004 | p1, p2, p5 |
| FR-009 | Sim | T004 | p1, p6 |
| FR-010 | Sim | T004 | p1 |
| FR-011 | Sim | T004, T005 | |
| FR-012 | Sim | T003, T004 | n7, p3, p3b, p5, n9 |
| FR-013 | Sim | T002, T003, T004 | todo negativo em prévia e apply |
| FR-014 | Sim | T006, T008 | nove arquivos |
| FR-015 | Sim | T008 | grant do DAG e diff |
| SC-001..SC-004 | Sim | T004 | |
| SC-005 | Sim | T007 | matriz de 3 SOs conferida no PR |

**Constitution Alignment Issues:** nenhum. Constituição com sha256 `54d5522b…7569` igual ao selado; o plano não a toca, e as cláusulas "Bump obrigatório" e "Release obrigatória por versão" estão cobertas por T006 e pelo `publish.yml`.

**Unmapped Tasks:** nenhuma. T007 e T008 são verificação read-only aceita pelo líder na Phase 3.

## Metrics

- Total Requirements: 15 FR + 5 SC
- Total Tasks: 8 (6 despacháveis em 3 nós, 2 read-only)
- Coverage: 100% (20/20 com ao menos uma tarefa)
- Ambiguity Count: 1
- Duplication Count: 0
- Critical Issues Count: 0

## Next Actions

- Sem CRITICAL nem HIGH: seguir para `partition`.
- U1, U2 e I2 entram como esclarecimento no brief dos workers dos nós B e C; o `tasks.md` atestado não é reescrito.
- A1 é registrado pelo líder ao aceitar T008.

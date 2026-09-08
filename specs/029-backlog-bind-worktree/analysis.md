# Specification Analysis Report — 029 backlog vinculado de qualquer worktree

**Date**: 2026-09-08 · **Inputs**: spec.md, plan.md, tasks.md, contracts/, data-model.md, research.md, `.specify/memory/constitution.md` · **Partition preview**: `partition-emit --groups 3` (read-only)

## Findings

| ID | Category | Severity | Location(s) | Summary | Resolution |
|----|----------|----------|-------------|---------|------------|
| P1 | Inconsistency (partition) | MEDIUM | tasks.md T002, T005, T007 | Tokens com `/` fora de caminho real (`NEEDS-BIND`/`NEEDS-CREATE`, `name`/`code`, `<tmp>/linked`, `<tmp>/repo`) vazavam para os grants de p01-a e p02-a | **Remediado** nesta rodada: três linhas reescritas sem barra fora de caminho; preview reemitido mostra grants só com caminhos reais (p01-a: `backlog_bridge.py`; p02-a: `validate_backlog_contract.py`; p02-b: `SKILL.md` + `validate_distribution.py`; p02-c: 4 manifests + `session-protocol.md`). Atestação de `tasks` sucedida (`029-tasks-r2.json`, ADR-0205), não reescrita |
| I1 | Partition | LOW | tasks.md Phase 1 | `PARTITION-DEGRADED` / `CONFLICT_GROUPS_BELOW_LIMIT` (1 grupo de 3): T001→T002→T003 escrevem o mesmo arquivo | Esperado por design; veredito aceito — nenhuma ação |
| A1 | Terminology | LOW | spec.md vs plan/tasks | "checkout principal"/"verificação prévia"/"ferramenta de versionamento" vs "worktree de controle"/"preflight"/"git" | Deliberado (spec para não-técnicos); data-model e glossário do work item ligam os pares — nenhuma ação |
| C1 | Coverage | LOW | spec.md FR-008 | "mesma resolução em todos os verbos" não tem tarefa própria | Estrutural: os seis callers já passam por `resolve_backlog` (plan §Summary); T002 é a única superfície; T010 documenta — nenhuma ação |

## Coverage

| Requirement | Tasks |
|---|---|
| FR-001 | T001, T002, T004 |
| FR-002 | T001, T004, T006 |
| FR-003 | T002, T005 |
| FR-004 | T003, T005 |
| FR-005 | T002, T004 |
| FR-006 | T002, T006 |
| FR-007 | T001, T006 |
| FR-008 | T002 (estrutural), T010 |
| FR-009 | T002 |
| FR-010 | T001 |
| FR-011 | T004, T005, T006, T007 |
| FR-012 | T008, T009, T010, T011, T012 (leader) |
| SC-001 | T004, T007 |
| SC-002 | T005 (+ quickstart §4 pós-ship) |
| SC-003 | T012 (quickstart §3) |
| SC-004 | T007 (`skipTest` sem git), suíte inteira |
| SC-005 | T002, T008 |

## Constitution alignment

Nenhum conflito. *Bump obrigatório do plugin*: T008–T012 cobrem os oito pontos. *Fail-closed sem waiver*: ambiguidade recusa sem mutar (T002, T006); nenhum re-bind (T002, T004). *Sequência obrigatória* e *Rastreabilidade*: cada tarefa cita FR/SC/contrato. T012 é a única tarefa de evidência de coordenador e o partition a devolve ao leader (`deferred_to_leader: [T012]`).

## Unmapped tasks

Nenhuma (11 despacháveis + 1 leader). Divergência branch `cadugevaerd/chore-fix-backlog` vs diretório `029-backlog-bind-worktree` está declarada no cabeçalho da spec e do plan e não é conflito.

## Metrics

- Requisitos: 12 FR + 5 SC · Tarefas: 12 · Cobertura: 100%
- Ambiguidades: 0 · Duplicações: 0 · Críticos: 0

## Next actions

Sem CRITICAL. Seguir para `partition` com `--groups 3`; esperado `PARTITION-DEGRADED` por I1, aceito.

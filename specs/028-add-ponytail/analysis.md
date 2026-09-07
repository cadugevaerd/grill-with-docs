# Specification Analysis Report — 028 ponytail na stack oficial

**Date**: 2026-09-07 · **Inputs**: spec.md, plan.md, tasks.md, contracts/, data-model.md, research.md, `.specify/memory/constitution.md` · **Partition preview**: `partition-emit --groups 3` (read-only)

## Findings

| ID | Category | Severity | Location(s) | Summary | Resolution |
|----|----------|----------|-------------|---------|------------|
| P1 | Inconsistency (partition) | MEDIUM | tasks.md T004, T006, T008 | Tokens com `/` fora de caminho real (`CLAUDE_CONFIG_DIR`/`CODEX_HOME`, `HOME/.claude`, `present`/`outdated`, `ausente/chave`, `antes/depois`, fixtures relativas) vazavam para o grant dos nós p01-a e p02-a | **Remediado** nesta rodada: quatro linhas reescritas sem barra fora de caminho; preview reemitido mostra grants só com caminhos reais do repositório (p01-a: `ensure_dependencies.py`; p01-b: `dependencies.json` + contrato; p02-a: `validate_dependencies_contract.py`; p02-b: `settings.json`, `SKILL.md`, `validate_distribution.py`; p02-c: 4 manifests + `session-protocol.md`). Atestação de `tasks` sucedida (ADR-0205), não reescrita |
| I1 | Partition | LOW | tasks.md Phase 1 | `PARTITION-DEGRADED` / `CONFLICT_GROUPS_BELOW_LIMIT` (2 grupos de 3): T002→T003→T004 escrevem o mesmo arquivo | Esperado por design; veredito aceito — nenhuma ação |
| A1 | Terminology | LOW | spec.md vs plan/tasks | "verificação prévia" vs "preflight" | Deliberado (spec para não-técnicos); glossário do work item liga os dois — nenhuma ação |

## Coverage

| Requirement | Tasks |
|---|---|
| FR-001 | T001 |
| FR-002, FR-003 | T004, T005, T006 |
| FR-004 | T001, T003, T005 |
| FR-005, FR-006 | T003, T007 |
| FR-007, FR-008, FR-009, FR-010 | T008 |
| FR-011, FR-012 | T014 (leader) |
| FR-013 | T013 |
| FR-014 | T011, T012, T014 |
| FR-015 | T009, T010, T011, T012, T014 |
| SC-001 | T005, T006 |
| SC-002 | T007 |
| SC-003 | T009 (+ suíte inteira) |
| SC-004 | T008 |
| SC-005 | T014 |

## Constitution alignment

Nenhum conflito. *Bump obrigatório do plugin*: T009–T014 cobrem os oito pontos. *Fail-closed sem waiver*: `undetermined` nunca vira `missing` nem instala (T004, T008); `--require-dependencies` recusa (T008). *Sequência obrigatória* e *Rastreabilidade*: cada tarefa cita FR/SC/contrato. T014 é a única tarefa de evidência de coordenador e o partition a devolve ao leader (`deferred_to_leader: [T014]`).

## Unmapped tasks

Nenhuma (13 despacháveis + 1 leader). Divergência branch `cadugevaerd/chore-add-ponytail` vs diretório `028-add-ponytail` está declarada no cabeçalho da spec e do plan (CHK033) e não é conflito.

## Metrics

- Requisitos: 15 FR + 5 SC · Tarefas: 14 · Cobertura: 100%
- Ambiguidades: 0 · Duplicações: 0 · Críticos: 0

## Next actions

Sem CRITICAL. Seguir para `partition` com `--groups 3`; esperado `PARTITION-DEGRADED` por I1, aceito.

# ROADMAP

- execution-order: FASE-001

## FASE-001 — Atestação ancorada na versão declarada
- state: blocked
- objetivo: checkpoints de work items v3 e v4 são julgados contra o registry da versão que o próprio item declara; condição prevista de skill não resolvida retorna código de contrato e diagnóstico íntegro, nunca `UNEXPECTED-FAILURE`.
- scope-in: threading obrigatório e keyword-only de `workflow_version` pelas três entradas públicas da cadeia de atestação; carregamento do registry por versão quando não há bytes injetados; propagação de `development.workflow_version` pela fronteira do CLI; tradução de `SkillResolutionError`; testes v3/v4, ausência do argumento, regressão do checkpoint e bump patch 5.0.1 nos pontos de distribuição.
- scope-out: derivação inicial de `development.workflow_version`, pertencente ao work item `fix-audit-workflow-version-2a9e7a7ba01f42dcb24b3bb83d801b03`; alteração dos registries, sequências ou catálogos versionados; migração de bundles; correção do reconciliador para reutilização de escopo histórico, acompanhada em BL-0001/SGD-24.
- context-refs: versão declarada, versão ativa, registry ancorado, resolução de skill, código de contrato, escopo declarado, reivindicação histórica, conflito de escopo
- ADRs: ADR-0001, ADR-0002
- BLs: BL-0001
- depends-on: none
- specify-handoff: handoffs/FASE-001-SPECIFY-HANDOFF.md
- delivery-units: DU-001

> Estados: `planned | ready-for-specify | blocked | complete | superseded`. `complete` e `superseded` são terminais. `execution-order` é explícita, topológica e independente dos números de fase. Cada fase tem um handoff exclusivo; somente a primeira incompleta pode ficar `ready-for-specify`. Se todas forem terminais e não houver BL/DQ material aberto, grave `milestone_status=completed`, `state.status=complete`, `active_phase=null` e `audit_verdict=GO`; a auditoria retorna `MILESTONE-COMPLETE`.

## Delivery First
Feature/fix phases are plan-only. Hotfix-fast incidents are tracked in the work-item HOTFIX.md and reconciled after ship.

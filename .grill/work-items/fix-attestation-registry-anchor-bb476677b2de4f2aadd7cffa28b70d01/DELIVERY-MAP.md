# DELIVERY-MAP

decomposition-schema: v1

## MOD-001 — Cadeia de atestação versionada
- module-kind: platform
- responsibility: Julgar cada cadeia de atestação contra a versão declarada pelo work item e preservar códigos de contrato na fronteira do CLI
- boundary: Validação pura de resolução e invocação, composição da atestação e adaptação do checkpoint no CLI
- depends-on: none

### DU-001 — Registry ancorado e diagnóstico nomeado
- development-type: platform-devops
- phase: FASE-001
- scope-in: Parâmetro `workflow_version` obrigatório e keyword-only nas três entradas públicas; propagação até `load_registry(workflow_version=...)`; uso de `development.workflow_version` pelo checkpoint; tradução de `SkillResolutionError`; regressões v3/v4; bump patch 5.0.1 e paridade da distribuição
- scope-out: Writer do campo `development.workflow_version`; conteúdo dos registries e catálogos; sequência por versão; política de conflito de escopo do reconciliador
- depends-on: none
- acceptance: Um checkpoint v3 com `agent-assign` ou `agent-execute` usa o registry v3 e pode atestar; v4 continua usando v4; omitir a versão falha por assinatura; skill não resolvida produz `UNATTESTED-STEP-OUTPUT` com razão preservada; validadores relevantes e distribuição fecham em exit 0

> IDs are stable within this work item. `module-kind` is one of `domain|platform|cross-cutting`; each DU has exactly one closed development type.

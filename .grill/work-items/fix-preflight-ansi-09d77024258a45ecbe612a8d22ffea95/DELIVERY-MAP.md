# DELIVERY-MAP

decomposition-schema: v1

## MOD-001 — Preflight de dependências
- module-kind: platform
- responsibility: Responder, com evidência observada, se cada dependência declarada está utilizável — e, quando não está, nomear a causa e a ação que a resolve
- boundary: `plugin/skills/grill-with-docs/scripts/ensure_dependencies.py` e `plugin/skills/grill-with-docs/assets/dependencies.json`
- depends-on: none

### DU-001 — Detecção de extensão pelo registro
- development-type: platform-devops
- phase: FASE-001
- scope-in: Fonte de detecção de extensão, tratamento de registro não legível, avaliação de `enabled`, remediação condicional ao motivo observado, status de dependência nos validadores, contrato de distribuição e changelog
- scope-out: Parser da saída de `specify extension list`, dependências de tipo `runtime` e `binary`, catálogo de confiança, hooks, instalação delegada
- depends-on: none
- acceptance: Em ambiente com as quatro extensões registradas e habilitadas, `preflight` reporta `OK` e nenhuma extensão aparece em `missing_required`; com o registro não legível, a causa aparece uma vez como dependência de caminho faltante e nenhuma extensão é reportada como ausente; com extensão registrada e `enabled: false`, o item bloqueia com remediação `enable` e não `add`

> IDs are stable within this work item. `module-kind` is one of `domain|platform|cross-cutting`; each DU has exactly one closed development type.

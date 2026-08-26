# DELIVERY-MAP

decomposition-schema: v1

## MOD-001 — Fixação project-wide do documento
- module-kind: platform
- responsibility: Declarar a identidade do documento gerenciado e materializá-lo no consumidor
- boundary: SSOT do documento e script de materialização
- depends-on: none

### DU-001 — Materialização e contrato travado
- development-type: platform-devops
- phase: FASE-001
- scope-in: SSOT em `grill_core`, script fino, fixação pelo `init` com reporte, preservação de documento humano, validador na suíte, bump sincronizado
- scope-out: O texto normativo do documento
- depends-on: none
- acceptance: `init` fixa o documento sem clobber e reporta estado e hash; documento humano incompatível permanece byte-intacto; a suíte reprova qualquer quebra do contrato; a versão fica idêntica em todos os pontos travados

> IDs are stable within this work item. `module-kind` is one of `domain|platform|cross-cutting`; each DU has exactly one closed development type.

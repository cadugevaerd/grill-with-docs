# DELIVERY-MAP

decomposition-schema: v1

## MOD-001 — Política de reconciliação de escopo
- module-kind: platform
- responsibility: Distinguir sucessão direta autorizada de sobreposição concorrente nos reconciliadores completo e targeted
- boundary: Metadata `depends-on-work`, scopes normalizados, receipts históricos e emissão de conflitos de reconciliação
- depends-on: none

### DU-001 — Dependência direta autoriza sucessão
- development-type: platform-devops
- phase: FASE-001
- scope-in: Regra direcional compartilhada; integração full/targeted; testes positivos e negativos; bump patch 5.0.1 e distribuição
- scope-out: Fechamento transitivo, waiver por conclusão, schema novo de receipt e alteração de conflitos ADR
- depends-on: none
- acceptance: Dependência direta elimina somente o SCOPE-OVERLAP do par declarado nos dois caminhos; ausência, terceiro e transitividade continuam recusados; demais conflitos não mudam; validadores e distribuição fecham em exit 0

> IDs are stable within this work item. `module-kind` is one of `domain|platform|cross-cutting`; each DU has exactly one closed development type.

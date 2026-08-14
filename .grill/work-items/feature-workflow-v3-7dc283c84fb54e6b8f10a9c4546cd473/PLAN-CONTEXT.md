# PLAN-CONTEXT

## FASE-001 — Catálogo de skills canônicas
- phase: FASE-001
- ADRs: ADR-0001, ADR-0002
- BLs: none
- delivery-units: DU-001
- development-type: platform-devops

### HOW
O registro fixa a mesma sequência de onze etapas que o Workflow V2 já declara. Cada etapa é obrigatória e tem uma identidade lógica única; somente `ship` requer autorização humana adicional. A resolução somente aceita um catálogo cujo conteúdo e identidade correspondem ao pin versionado. O runtime Claude é o único com todos os entrypoints comprovados; runtimes sem entrada comprovada devem bloquear de forma explícita, sem descoberta ou substituição.

## FASE-002 — Migração explícita para Workflow V3
- phase: FASE-002
- ADRs: ADR-0001
- BLs: none
- delivery-units: DU-002
- development-type: platform-devops

### HOW
O documento V2 e seu bootstrap permanecem intocados. A adoção de V3 é preview-first, depende do hash da origem inspecionada, é atômica e idempotente. O documento V3 fixa a identidade do registro; pin ausente, placeholder ou divergente bloqueia leitura, bootstrap e hook. O hook continua somente leitura e comunica o pin antes de qualquer resumo sujeito a truncamento.

## FASE-003 — Work Item V3 e Project Store
- phase: FASE-003
- ADRs: ADR-0003
- BLs: none
- delivery-units: DU-003
- development-type: platform-devops

### HOW
Work Item V3 preserva todos os campos V2 e acrescenta somente identidade lógica, linhagem e estado de orquestração verificáveis. A migração é preview-first, atômica e rejeita paths absolutos, traversal, tamper e escrita stale. O Project Store fica no diretório comum do Git para que worktrees vinculadas compartilhem um único snapshot, journal encadeado, revisão CAS e locks cooperativos.

## FASE-004 — Atestação cooperativa e wiring V3
- phase: FASE-004
- ADRs: ADR-0002, ADR-0003, ADR-0004
- BLs: BL-0001, BL-0002
- delivery-units: DU-004
- development-type: platform-devops

### HOW
Um output aceito precisa correlacionar resolução, intenção de dispatch, recibo iniciado, recibo terminal e output da etapa à mesma identidade de projeto, work item, run, geração e plano. O coordenador pode delegar a composição e revisão do receipt a um subagente cooperativo. Resultado direto, replay, identidade divergente, terminal não concluído ou cadeia inválida bloqueia. O receipt é evidência estrutural auditável, não proveniência criptográfica nem defesa contra executor malicioso.

> Mantenha um bloco por fase e referências ADR/BL exatamente equivalentes ao ROADMAP e ao handoff. Nunca registre `selected-handoff` aqui.

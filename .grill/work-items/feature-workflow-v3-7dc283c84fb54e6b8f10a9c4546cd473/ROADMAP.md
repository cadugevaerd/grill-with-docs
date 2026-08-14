# ROADMAP

- execution-order: FASE-001, FASE-002, FASE-003, FASE-004

## FASE-001 — Catálogo de skills canônicas
- state: complete
- objetivo: cada uma das onze etapas obrigatórias resolve para uma única capacidade canônica, verificável e fail-closed no runtime suportado
- scope-in: registro ordenado das etapas; pin do catálogo confiável; resolução por versão e conteúdo; recusa de fallback ou runtime não comprovado
- scope-out: migração do documento de workflow; migração de work item; aceitação de output de etapa
- context-refs: Managed Workflow, Canonical Skill, Skill Resolution
- ADRs: ADR-0001, ADR-0002
- BLs: none
- depends-on: none
- specify-handoff: handoffs/FASE-001-SPECIFY-HANDOFF.md
- delivery-units: DU-001

## FASE-002 — Migração explícita para Workflow V3
- state: complete
- objetivo: um operador pode pré-visualizar e aprovar a adoção de Workflow V3 sem alterar nem degradar Workflow V2
- scope-in: documento V3; preview; aprovação pela identidade inspecionada; coexistência V2/V3; comportamento read-only do hook
- scope-out: descoberta de novas capacidades; migração de work item; execução de etapas
- context-refs: Managed Workflow, Workflow V2, Workflow V3, Skill Resolution
- ADRs: ADR-0001
- BLs: none
- depends-on: FASE-001
- specify-handoff: handoffs/FASE-002-SPECIFY-HANDOFF.md
- delivery-units: DU-002

## FASE-003 — Work Item V3 e Project Store
- state: complete
- objetivo: work items podem evoluir explicitamente para V3 e manter identidade e histórico íntegros entre worktrees vinculadas
- scope-in: leitura dupla V2/V3; migração atômica; identidade lógica segura; store compartilhado; CAS, locks e journal verificável
- scope-out: autorização de skills; aceitação de output de etapa; reconciliação global
- context-refs: Work Item V3, Project Store
- ADRs: ADR-0003
- BLs: none
- depends-on: none
- specify-handoff: handoffs/FASE-003-SPECIFY-HANDOFF.md
- delivery-units: DU-003

## FASE-004 — Atestação cooperativa e wiring V3
- state: blocked
- objetivo: somente outputs com cadeia estrutural completa da skill canônica, no contexto correto, podem avançar uma etapa V3 cooperativa
- scope-in: cadeia de atestação; detecção de replay e divergência; terminais imutáveis; tradução estável de diagnósticos; compatibilidade nas interfaces públicas
- scope-out: execução direta de verify, review ou ship; defesa contra executor malicioso e proveniência criptográfica
- context-refs: Execution Attestation, Canonical Skill, Skill Resolution, Work Item V3
- ADRs: ADR-0002, ADR-0003, ADR-0004
- BLs: BL-0001, BL-0002
- depends-on: FASE-001, FASE-002, FASE-003
- specify-handoff: handoffs/FASE-004-SPECIFY-HANDOFF.md
- delivery-units: DU-004

> Estados: `planned | ready-for-specify | blocked | complete | superseded`. `complete` e `superseded` são terminais. `execution-order` é explícita, topológica e independente dos números de fase. Cada fase tem um handoff exclusivo; somente a primeira incompleta pode ficar `ready-for-specify`. Se todas forem terminais e não houver BL/DQ material aberto, grave `milestone_status=completed`, `state.status=complete`, `active_phase=null` e `audit_verdict=GO`; a auditoria retorna `MILESTONE-COMPLETE`.

## Delivery First
Feature/fix phases are plan-only. Hotfix-fast incidents are tracked in the work-item HOTFIX.md and reconciled after ship.

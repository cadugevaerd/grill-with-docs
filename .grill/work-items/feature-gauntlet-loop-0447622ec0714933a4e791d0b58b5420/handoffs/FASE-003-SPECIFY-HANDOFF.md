# FASE-003 — Scheduler Claude e waves do DAG

- phase: FASE-003
- state: blocked
- roadmap: ROADMAP.md#FASE-003
- context-refs: Execution DAG, Model Tier, Capability Grant, Autonomous Run, Stall Recovery, Execution Wave
- ADRs: ADR-0001, ADR-0004, ADR-0005, ADR-0007, ADR-0012, ADR-0013, ADR-0014
- BLs: BL-0001

## WHAT
- delivery-units: DU-003
- development-type: platform-devops
- Cada macroetapa usa um subagente Claude, e nós independentes podem executar em waves de até cinco workers.
- O scheduler acompanha progresso, recupera um stall de forma limitada e bloqueia resultados que não cumpram dependências ou gates.

## WHY
O ganho do Gauntlet Loop depende de paralelizar apenas trabalho declarado independente, mantendo o workflow V3 e as evidências verificáveis. O monitoramento evita que uma execução aparentemente autônoma fique silenciosamente abandonada.

> Não inclua headings/campos de stack, banco, framework, classes, componentes, implementação ou API interna. Este handoff cobre somente uma fase.

> Feature/fix handoffs remain plan-only. Incident hotfixes use HOTFIX.md and do not bypass constitutional safety.

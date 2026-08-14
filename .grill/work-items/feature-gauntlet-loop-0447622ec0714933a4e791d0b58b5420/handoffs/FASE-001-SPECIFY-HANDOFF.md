# FASE-001 — Ativação explícita e contrato de configuração

- phase: FASE-001
- state: ready-for-specify
- roadmap: ROADMAP.md#FASE-001
- context-refs: Gauntlet Loop, Gauntlet Configuration, Gauntlet-Enabled Work Item, Model Tier, Canonical Skill
- ADRs: ADR-0001, ADR-0004, ADR-0007
- BLs: none

## WHAT
- delivery-units: DU-001
- development-type: platform-devops
- Um operador consegue preparar explicitamente um work item V3 para o Gauntlet Loop e iniciar uma run somente no Claude Code verificado.
- A configuração torna visíveis o limite de cinco workers, o limite de stall e a política de Model Tiers sem alterar o comportamento de work items V2.

## WHY
O Loop deve ser previsível e opt-in: ativação ou fallback implícitos permitiriam executar um workflow sem capacidade canônica comprovada. A primeira fase cria o contrato que as fases seguintes usam para persistir e despachar trabalho com a mesma linguagem e os mesmos gates.

> Não inclua headings/campos de stack, banco, framework, classes, componentes, implementação ou API interna. Este handoff cobre somente uma fase.

> Feature/fix handoffs remain plan-only. Incident hotfixes use HOTFIX.md and do not bypass constitutional safety.

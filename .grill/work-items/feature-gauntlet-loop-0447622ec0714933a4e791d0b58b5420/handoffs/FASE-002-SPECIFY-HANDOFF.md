# FASE-002 — Estado durável, evidência e isolamento

- phase: FASE-002
- state: ready-for-specify
- roadmap: ROADMAP.md#FASE-002
- context-refs: Resumable Run, Evidence Boundary, Worker Worktree, Capability Grant, Stall Recovery
- ADRs: ADR-0003, ADR-0005, ADR-0006, ADR-0010
- BLs: none

## WHAT
- delivery-units: DU-002
- development-type: platform-devops
- Cada Gauntlet Run mantém estado recuperável, evidência correlacionada e workers isolados por worktree.
- O coordenador registra a evidência e conserva artefatos necessários para diagnóstico sem conceder essa autoridade aos workers.

## WHY
Autonomia sem estado durável perde a capacidade de provar o que foi feito depois de interrupções. Isolamento e Capability Grants permitem paralelismo sem permitir que um worker altere a coordenação ou se autoaprove.

> Não inclua headings/campos de stack, banco, framework, classes, componentes, implementação ou API interna. Este handoff cobre somente uma fase.

> Feature/fix handoffs remain plan-only. Incident hotfixes use HOTFIX.md and do not bypass constitutional safety.

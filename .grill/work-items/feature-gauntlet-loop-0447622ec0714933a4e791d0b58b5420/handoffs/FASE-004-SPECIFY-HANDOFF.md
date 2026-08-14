# FASE-004 — Convergência, revisão e entrega verificável

- phase: FASE-004
- state: planned
- roadmap: ROADMAP.md#FASE-004
- context-refs: Integration Conflict, Independent Review, Review Block, Autonomous Run, Canonical Skill
- ADRs: ADR-0002, ADR-0008, ADR-0009, ADR-0011
- BLs: none

## WHAT
- delivery-units: DU-004
- development-type: platform-devops
- Mudanças aceitas convergem em série, passam por verify e Independent Review, e só então aguardam a autorização humana de ship.
- Conflitos e revisão reprovada são bloqueios nomeados; a distribuição torna disponível a nova extensão opt-in.

## WHY
Paralelismo só é seguro quando sua integração preserva a ordem e a revisão é independente de quem produziu a mudança. O gate humano final mantém o controle sobre ações externas mesmo após uma execução autônoma bem-sucedida.

> Não inclua headings/campos de stack, banco, framework, classes, componentes, implementação ou API interna. Este handoff cobre somente uma fase.

> Feature/fix handoffs remain plan-only. Incident hotfixes use HOTFIX.md and do not bypass constitutional safety.

# ROADMAP

- execution-order: FASE-001, FASE-002, FASE-003, FASE-004

## FASE-001 — Ativação explícita e contrato de configuração
- state: complete
- objetivo: um work item V3 apto pode ativar explicitamente o Gauntlet Loop no Claude Code, sem mudar os fluxos V2
- scope-in: comandos de inicialização, execução, status, retomada e limpeza; configuração versionada; guardas de workflow V3, adapter Claude e sequência canônica; política de tiers e limite de cinco workers
- scope-out: criação de workers, persistência de runs, integração de mudanças e revisão
- context-refs: Gauntlet Loop, Gauntlet Configuration, Gauntlet-Enabled Work Item, Model Tier, Canonical Skill
- ADRs: ADR-0001, ADR-0004, ADR-0007
- BLs: none
- depends-on: none
- specify-handoff: handoffs/FASE-001-SPECIFY-HANDOFF.md
- delivery-units: DU-001

## FASE-002 — Estado durável, evidência e isolamento
- state: complete
- objetivo: cada run e worker mantém estado, evidências e worktrees isolados que podem ser recuperados sem autoridade externa
- scope-in: extensão validada do Project Store e journal existente; leases e recuperação; Evidence Boundary do coordenador; Worker Worktrees e limpeza segura
- scope-out: scheduler do Claude Code, paralelismo e lógica de converge/review
- context-refs: Resumable Run, Evidence Boundary, Worker Worktree, Capability Grant, Stall Recovery
- ADRs: ADR-0003, ADR-0005, ADR-0006, ADR-0010
- BLs: none
- depends-on: FASE-001
- specify-handoff: handoffs/FASE-002-SPECIFY-HANDOFF.md
- delivery-units: DU-002

## FASE-003 — Scheduler Claude e waves do DAG
- state: blocked
- objetivo: o Loop despacha cada macroetapa a subagentes Claude e executa em paralelo somente os nós independentes do Execution DAG
- scope-in: adapter nativo Claude Code; mapeamento de tiers; criação e observação de workers; DAG versionado; waves de até cinco workers; retry transitório e Stall Recovery automática
- scope-out: runtimes Codex/Hermes, resolução automática de conflitos e reparo automático pós-review
- context-refs: Execution DAG, Model Tier, Capability Grant, Autonomous Run, Stall Recovery, Execution Wave
- ADRs: ADR-0001, ADR-0004, ADR-0005, ADR-0007, ADR-0012, ADR-0013, ADR-0014, ADR-0015, ADR-0016, ADR-0017, ADR-0018, ADR-0019
- BLs: BL-0001, BL-0002, BL-0003
- depends-on: FASE-001, FASE-002
- specify-handoff: handoffs/FASE-003-SPECIFY-HANDOFF.md
- delivery-units: DU-003
- nota: deliverable substantivo (spec, plan, tasks, implementação, testes, 3 rounds de review independente) já commitado, mergeado e publicado em `origin/main` (`4ac6746`), por confirmação explícita do operador. `state: blocked` reflete só o ledger formal V3 — `phase-turn` recusa `PHASE-INCOMPLETE: specify` até existir checkpoint genuíno (BL-0003). BL-0001 resolvido.

## FASE-004 — Convergência, revisão e entrega verificável
- state: blocked
- objetivo: resultados paralelos convergem de modo fail-closed e chegam ao gate humano de ship somente após revisão independente
- scope-in: converge serial; bloqueio de conflito; verify e review independentes; Run Status Events; testes de contrato e atualização de distribuição com bump SemVer próprio (2.8.0 — 2.6.0 já consumido pela FASE-002, 2.7.0 já consumido pela FASE-003)
- scope-out: resolução automática de conflito, ciclo automático de reparo após review reprovado e push/release direto
- context-refs: Integration Conflict, Independent Review, Review Block, Autonomous Run, Canonical Skill
- ADRs: ADR-0002, ADR-0008, ADR-0009, ADR-0011, ADR-0020, ADR-0021, ADR-0022, ADR-0023
- BLs: BL-0004
- depends-on: FASE-003
- specify-handoff: handoffs/FASE-004-SPECIFY-HANDOFF.md
- delivery-units: DU-004
- nota: deliverable substantivo (spec, plan, tasks, implementação — T001-T032 —, testes, 1 round de review independente com verdito APPROVE) já commitado e publicado em `origin/main` (`37fd179`), por confirmação explícita do operador. `state: blocked` reflete só o ledger formal V3, mesma lacuna de BL-0003 na FASE-003: `phase-turn` confirmado bloqueado (`PHASE-INCOMPLETE: specify`, verificado read-only, sem mutação de estado) até existir checkpoint genuíno (BL-0004).

> Estados: `planned | ready-for-specify | blocked | complete | superseded`. `complete` e `superseded` são terminais. `execution-order` é explícita, topológica e independente dos números de fase. Cada fase tem um handoff exclusivo; somente a primeira incompleta pode ficar `ready-for-specify`. Se todas forem terminais e não houver BL/DQ material aberto, grave `milestone_status=completed`, `state.status=complete`, `active_phase=null` e `audit_verdict=GO`; a auditoria retorna `MILESTONE-COMPLETE`.

## Delivery First
Feature/fix phases are plan-only. Hotfix-fast incidents are tracked in the work-item HOTFIX.md and reconciled after ship.

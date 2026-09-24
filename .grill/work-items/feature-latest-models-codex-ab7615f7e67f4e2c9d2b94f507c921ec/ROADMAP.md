# ROADMAP

- execution-order: FASE-001

## FASE-001 — Modelo mais recente: Codex por família e especialista Claude em Opus
- state: ready-for-specify
- objetivo: workers e especialistas Codex despachados pelo GWD usam automaticamente o slug listado de menor `priority` da família do seu tier/papel, sem edição manual a cada geração, e recusam fail-closed quando o catálogo não resolve; o par autor/revisor Claude passa a ser o alias `opus` (xhigh/high) no lugar de `fable`
- scope-in: binding tier→modelo Codex; papéis autor/revisor Codex da policy de orquestração; par autor/revisor Claude `fable`→`opus` na policy, no core e nos documentos; registro durável do slug resolvido; validadores offline
- scope-out: tiers Claude e seus aliases (`haiku/sonnet/opus`); slug fixo de modelo Claude; recomendação textual do líder; configuração global do Codex do usuário; alias de API `gpt-6`; rede
- context-refs: família de modelo, catálogo local do Codex, slug resolvido, tier, papel de especialista, alias de modelo Claude
- ADRs: ADR-0001, ADR-0002
- BLs: none
- depends-on: none
- specify-handoff: handoffs/FASE-001-SPECIFY-HANDOFF.md
- delivery-units: DU-001

> Estados: `planned | ready-for-specify | blocked | complete | superseded`. `complete` e `superseded` são terminais. `execution-order` é explícita, topológica e independente dos números de fase. Cada fase tem um handoff exclusivo; somente a primeira incompleta pode ficar `ready-for-specify`. Se todas forem terminais e não houver BL/DQ material aberto, grave `milestone_status=completed`, `state.status=complete`, `active_phase=null` e `audit_verdict=GO`; a auditoria retorna `MILESTONE-COMPLETE`.

## Delivery First
Feature/fix phases are plan-only. Hotfix-fast incidents are tracked in the work-item HOTFIX.md and reconciled after ship.

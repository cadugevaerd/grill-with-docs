# ROADMAP

- execution-order: FASE-001

## FASE-001 — Emissor da cadeia de atestação
- state: ready-for-specify
- objetivo: Concluir uma etapa do ciclo passa a ser possível sem fabricar evidência: quem conduz a etapa obtém a cadeia emitida a partir do que o núcleo já sabe, ancorada no artefato produzido.
- scope-in: Classe de execução por etapa como tabela congelada; concessão de lease ao leader pelo mecanismo já existente; emissor que monta os quatro elos e sela o digest do artefato; recusa nomeada para artefato ausente, ilegível ou fora do projeto; validador do contrato do emissor.
- scope-out: Proveniência criptográfica, defesa contra executor malicioso e acoplamento ao formato de rastro de qualquer runtime de agente — todos declarados fora de escopo pelo desenho original da atestação.
- context-refs: cadeia de atestação, emissor, leader, executor da etapa, evidência estrutural, artefato da etapa, lease
- ADRs: ADR-0201, ADR-0202, ADR-0203, ADR-0204
- BLs: BL-0201
- depends-on: none
- specify-handoff: handoffs/FASE-001-SPECIFY-HANDOFF.md
- delivery-units: DU-001, DU-002

> Estados: `planned | ready-for-specify | blocked | complete | superseded`. `complete` e `superseded` são terminais. `execution-order` é explícita, topológica e independente dos números de fase. Cada fase tem um handoff exclusivo; somente a primeira incompleta pode ficar `ready-for-specify`. Se todas forem terminais e não houver BL/DQ material aberto, grave `milestone_status=completed`, `state.status=complete`, `active_phase=null` e `audit_verdict=GO`; a auditoria retorna `MILESTONE-COMPLETE`.

## Origem

Este work item existe por causa de BL-0101, aberto em
`feature-goal-materialization`: sob a frontier ativa o núcleo passou a exigir a
cadeia de atestação em toda conclusão de etapa, valida essa cadeia, e não a
emite. O ciclo de onze etapas ficou inalcançável por checkpoint em qualquer
projeto na frontier ativa.

Não é regressão: o gate estava silenciosamente desligado para documentos da
frontier ativa e foi corrigido. A correção revelou que a outra ponta nunca
existiu.

## Delivery First
Feature/fix phases are plan-only. Hotfix-fast incidents are tracked in the work-item HOTFIX.md and reconciled after ship.

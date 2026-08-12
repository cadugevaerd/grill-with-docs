# Converge — FASE-001

## O que entrou

| Task | Resultado |
|---|---|
| T-001 | `resolve_development_item`, `global_snapshotter`, `read_development_state` extraídos de `checkpoint_command` |
| T-002 | `phase_turn_command`, com os cinco resultados do contrato |
| T-003 | `PHASE-TURN-REQUIRED` quando todos os passos estão `complete` |
| T-004 | subparser `phase-turn` e entrada no mapa de handlers |
| T-005 | 10 testes novos em `validate_workspace_contract.py` |
| T-006 | 2.5.1 → 2.5.2 nos oito pontos |

## Prova de que a extração não mudou comportamento

`validate_workspace_contract.py` passou de 53 para 63 testes; os 53 originais continuam verdes sem alteração. Eles cobrem o caminho extraído em profundidade: concorrência (`test_reconcile_concurrent_apply_is_serialized`), lock órfão (`test_reconcile_concurrent_waiters_recover_one_orphan_lock`), identidade de processo indisponível, e recibo inválido liberando lock.

## Comportamento observado

```
phase-turn com fase incompleta  → PHASE-INCOMPLETE, lista os 6 passos que faltam
phase-turn sem razão            → REASON-REQUIRED
phase-turn com fase completa    → TURNED, matriz volta a pending, current_step = specify
phase-turn repetido             → REUSED, arquivo byte-idêntico
checkpoint in-progress após ciclo → PHASE-TURN-REQUIRED (era INVALID-TRANSITION)
checkpoint pulando passos       → INVALID-TRANSITION (inalterado)
```

## Dogfooding

Esta própria fase foi conduzida com o `checkpoint`, passo a passo. A trilha do work item registra as 11 etapas com evidência por passo — o que a milestone anterior não conseguiu fazer em duas de três fases, e que é exatamente o defeito corrigido aqui.

## Suíte

301 testes, exit 0. `validate_workspace_contract` 53 → 63; `validate_status_contract` 27 → 28 (o teste de guarda do snapshot, entregue antes nesta sessão).

## O que não foi feito

A virada não é automática, e continua sendo um passo manual do ciclo. É a decisão de ADR-0001, e o risco residual está registrado: quem esquecer reencontra a recusa — agora com o código que nomeia a saída.

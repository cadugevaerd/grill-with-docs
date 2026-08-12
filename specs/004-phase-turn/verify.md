# Verify — FASE-001

**Veredito: PASS.**

## Suíte canônica

`python3 tests/run_validators.py`, exit 0. Total **301**, contra baseline de 291.

| Validador | Testes |
|---|---|
| validate_backlog_contract | 22 |
| validate_bump_gate_contract | 35 |
| validate_checkpoint_contract | 36 |
| validate_contract | 30 |
| validate_dependencies_contract | 21 |
| validate_publish_contract | 52 |
| validate_status_contract | 28 |
| validate_workflow_contract | 14 |
| validate_workspace_contract | **63** (era 53), 1 skip de ambiente |
| validate_distribution | `distribution: OK` |

## Checklist

| Item | Estado | Evidência |
|---|---|---|
| CHK-001 matriz reiniciada | ✅ | `test_phase_turn_reopens_the_matrix_and_records_the_reason` |
| CHK-002 `current_step` volta ao primeiro | ✅ | idem |
| CHK-003 razão na trilha | ✅ | idem |
| CHK-004 razão vazia recusada | ✅ | `test_phase_turn_requires_a_reason` |
| CHK-005 fase incompleta recusada sem mutação | ✅ | `test_phase_turn_refuses_an_unfinished_phase_without_touching_state` |
| CHK-006 idempotência sem escrita | ✅ | `test_phase_turn_is_idempotent_and_writes_nothing_on_reuse`, compara bytes |
| CHK-007 legado recusado | ✅ | `test_phase_turn_refuses_an_untracked_work_item` |
| CHK-008 forma do estado inalterada | ✅ | `set(before) == set(after)` sobre as chaves de `development` |
| CHK-009 `PHASE-TURN-REQUIRED` | ✅ | `test_a_finished_phase_names_the_turn_instead_of_invalid_transition` |
| CHK-010 `INVALID-TRANSITION` preservado | ✅ | `test_a_genuinely_invalid_transition_still_says_so` |
| CHK-011 dois ciclos completos | ✅ | `test_three_phases_leave_three_trails_in_one_work_item` cobre três |
| CHK-012 trilha distingue as fases | ✅ | 68 entradas = 3×11×2 + 2 viradas, com as razões das duas viradas conferidas |
| CHK-013 work item anterior legível | ✅ | `audit` do antigo devolve `MILESTONE-COMPLETE` |
| CHK-014 projeção global válida | ✅ | `reconcile` preview `OK`, 26 IDs, zero conflitos; recibo e ROADMAP global byte-idênticos |
| CHK-015 guarda global ativa | ✅ | `test_phase_turn_refuses_to_disturb_the_global_projection` |
| CHK-016 lock serializando | ✅ | os 53 testes originais de concorrência e lock órfão seguem verdes sobre o caminho extraído |
| CHK-017 suíte verde | ✅ | 301, exit 0 |
| CHK-018 bump aprovado | ✅ | `PASS BUMPED: plugin/ mudou e a versão aumentou de 2.5.1 para 2.5.2` |

## Não-regressão do que já estava pronto

O work item `feature-release-repo-sync` continua terminal e projetado: `audit` devolve `MILESTONE-COMPLETE`, `reconcile` em preview devolve `OK` com os mesmos 26 IDs, e os arquivos da projeção global continuam com os hashes de antes desta fase — `d9edb785…` no recibo e `3be206f4…` no ROADMAP global. Nenhuma migração foi necessária, que era a restrição dura de FR-006.

Nota de leitura: `reconcile --apply` devolveu `DIRTY-WORKTREE` durante a verificação. Não é regressão — é a guarda funcionando, porque o próprio `checkpoint` desta etapa alterou `state.json` depois do commit.

## Dogfooding

A fase foi conduzida com o `checkpoint` do início ao fim. A trilha registra as 11 etapas com evidência por passo, que é precisamente o que a milestone anterior não conseguiu produzir em duas de três fases.

# Verify — FASE-003

**Veredito: PASS. A execução real aconteceu e está verificada nos dois destinos.**

## Suíte canônica

`python3 tests/run_validators.py`, exit 0.

| Validador | Testes |
|---|---|
| validate_backlog_contract | 22 |
| validate_bump_gate_contract | 35 |
| validate_checkpoint_contract | 36 |
| validate_contract | 30 |
| validate_dependencies_contract | 21 |
| validate_publish_contract | **52** (era 33) |
| validate_status_contract | 27 |
| validate_workflow_contract | 14 |
| validate_workspace_contract | 52, 1 skip dependente de ambiente |
| validate_distribution | `distribution: OK` |

Total 289, contra o baseline de 270. As 19 novas são as classes `VerifyRelease` e `VerifyCommandLine`, os dois testes do defeito encontrado na revisão e o da lacuna de cobertura que a revisão independente apontou.

## Checklist de aceite

| Item | Estado | Evidência |
|---|---|---|
| CHK-001 aprova índice correto | ✅ | `test_a_published_index_verifies` |
| CHK-002 reprova versão | ✅ | `test_a_stale_version_is_reported` |
| CHK-003 reprova cada campo do pin | ✅ | `test_every_pinned_field_is_compared`, cinco subtestes |
| CHK-004 reprova entrada ausente | ✅ | `test_an_absent_entry_is_reported` |
| CHK-005 reprova entrada duplicada | ✅ | `test_duplicate_entries_are_reported_instead_of_picked` |
| CHK-006 acumula divergências | ✅ | `test_every_divergence_is_reported_together` |
| CHK-007 curadoria não reprova | ✅ | `test_curated_fields_never_fail_the_verification` |
| CHK-003b reprova referência extra no `source` | ✅ | achado da revisão; `test_a_second_reference_inside_source_is_reported`, `test_the_publisher_refuses_what_the_verification_would_reject` |
| CHK-008 saídas 0 e 3 | ✅ | `test_verify_approves_what_apply_published`, `test_verify_exits_three_on_divergence` |
| CHK-009 `--verify` com `--apply` recusado | ✅ | `test_verify_refuses_to_run_together_with_apply` |
| CHK-010 aplicar depois verificar | ✅ | `test_verify_approves_what_apply_published` |
| CHK-011 releitura de clone novo | ✅ | `publish.yml`, clone em `marketplace-verify` |
| CHK-012 tag precisa resolver | ✅ | provado contra `v2.4.1` real, peela para o commit; `v9.9.9` entrega vazio |
| CHK-013 releitura depois do push | ✅ | ordem dos passos conferida no YAML parseado |
| CHK-014 nenhum segredo novo | ✅ | reusa `AUTH_HEADER` já mascarado; nenhuma URL carrega token |
| CHK-015 gatilho manual segue declarado | ✅ | `on: [push, workflow_dispatch]` |
| CHK-016 suíte verde | ✅ | 288, exit 0 |
| CHK-017 nada em `plugin/` mudou | ✅ | diff toca `tests/`, `.github/`, `specs/`, `.grill/` |
| CHK-018 publicador fora do glob | ✅ | `test_the_publisher_is_not_collected_as_a_validator` |
| CHK-019 segredo instalado | ✅ | autorizado pelo usuário; gravado por stdin (`gh auth token \| gh secret set`), valor nunca em linha de comando |
| CHK-020 disparo executado | ✅ | run 31603973983, três jobs verdes |
| CHK-021 destinos em dia | ✅ | ver "Publicação real" abaixo |
| CHK-022 segundo disparo sem commit | ✅ | run 31604076395: tag "nada a criar", ambos `UNCHANGED`, ambos "nada a empurrar", ambos `VERIFIED` |

## Prova de ponta a ponta, sem push

Contra clones reais dos dois destinos, com `sha` do `HEAD` atual: claude `UPDATED` em 3+3 linhas, codex `CREATED` em 17 linhas, `--verify` aprovando os dois depois, segunda aplicação `UNCHANGED` nos dois. Detalhe em `converge.md`.

## Publicação real

Primeira execução em condições reais do pipeline inteiro, run 31603973983, disparada por `workflow_dispatch` sobre `main` em `c2a0c02`.

Estado final, lido de fora, direto da API dos repositórios publicados:

```
tag no canônico   v2.5.0 -> objeto 31991b52…, commit c2a0c024a7f3fb9628383c9b552e6ce950e84a50
claude-skills     version 2.5.0, ref v2.5.0, sha c2a0c024…, source git-subdir
codex-skills      version 2.5.0, ref v2.5.0, sha c2a0c024…, source git-subdir
```

Commits gerados: `9714537b` em `claude-skills` e `979c2368` em `codex-skills`, ambos `chore(grill-with-docs): aponta para v2.5.0`. O codex passou de nenhuma entrada para entrada válida; o claude saiu de 2.4.1.

A releitura foi o que autorizou o verde, não o código de saída do push — o passo de verificação reportou `VERIFIED` com `problems: []` nos dois destinos, a partir de clone novo, e confirmou que `v2.5.0` resolve para `c2a0c02` na consulta anônima ao canônico.

Segunda execução imediata, run 31604076395: `v2.5.0 já aponta para c2a0c02; nada a criar`, `UNCHANGED` nos dois publicadores, `nada a empurrar` nos dois, e `VERIFIED` nos dois. Nenhum commit novo em nenhum destino. SC-002, SC-003 e SC-005 provados em produção, não por simulação.

## O que continua não verificado

O caminho de falha por destino indisponível (FR-006 de FASE-002, edge case desta spec) nunca foi exercitado de verdade: os dois destinos estavam disponíveis nas duas execuções. A independência dos jobs está garantida por `fail-fast: false`, mas isso é uma propriedade declarada, não observada.

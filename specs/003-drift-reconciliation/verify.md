# Verify — FASE-003

**Veredito: PASS para tudo que não depende da credencial. A execução real permanece bloqueada por ato humano.**

## Suíte canônica

`python3 tests/run_validators.py`, exit 0.

| Validador | Testes |
|---|---|
| validate_backlog_contract | 22 |
| validate_bump_gate_contract | 35 |
| validate_checkpoint_contract | 36 |
| validate_contract | 30 |
| validate_dependencies_contract | 21 |
| validate_publish_contract | **49** (era 33) |
| validate_status_contract | 27 |
| validate_workflow_contract | 14 |
| validate_workspace_contract | 52, 1 skip dependente de ambiente |
| validate_distribution | `distribution: OK` |

Total 286, contra o baseline de 270. As 16 novas são as classes `VerifyRelease` e `VerifyCommandLine`.

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
| CHK-008 saídas 0 e 3 | ✅ | `test_verify_approves_what_apply_published`, `test_verify_exits_three_on_divergence` |
| CHK-009 `--verify` com `--apply` recusado | ✅ | `test_verify_refuses_to_run_together_with_apply` |
| CHK-010 aplicar depois verificar | ✅ | `test_verify_approves_what_apply_published` |
| CHK-011 releitura de clone novo | ✅ | `publish.yml`, clone em `marketplace-verify` |
| CHK-012 tag precisa resolver | ✅ | provado contra `v2.4.1` real, peela para o commit; `v9.9.9` entrega vazio |
| CHK-013 releitura depois do push | ✅ | ordem dos passos conferida no YAML parseado |
| CHK-014 nenhum segredo novo | ✅ | reusa `AUTH_HEADER` já mascarado; nenhuma URL carrega token |
| CHK-015 gatilho manual segue declarado | ✅ | `on: [push, workflow_dispatch]` |
| CHK-016 suíte verde | ✅ | 286, exit 0 |
| CHK-017 nada em `plugin/` mudou | ✅ | diff toca `tests/`, `.github/`, `specs/`, `.grill/` |
| CHK-018 publicador fora do glob | ✅ | `test_the_publisher_is_not_collected_as_a_validator` |
| CHK-019 segredo instalado | ⛔ | **ato humano, não realizado** |
| CHK-020 disparo executado | ⛔ | bloqueado por CHK-019 |
| CHK-021 destinos em dia | ⛔ | bloqueado por CHK-019 |
| CHK-022 segundo disparo sem commit | ⛔ | bloqueado por CHK-019 |

## Prova de ponta a ponta, sem push

Contra clones reais dos dois destinos, com `sha` do `HEAD` atual: claude `UPDATED` em 3+3 linhas, codex `CREATED` em 17 linhas, `--verify` aprovando os dois depois, segunda aplicação `UNCHANGED` nos dois. Detalhe em `converge.md`.

## O que não foi verificado

Nada exercitou o workflow dentro do GitHub Actions. A prova acima roda o mesmo publicador com os mesmos argumentos que o YAML passa, mas o clone autenticado, o push e a interação com `GITHUB_ENV` só existem lá. Isso é irredutível sem a credencial instalada — e é exatamente o risco que motivou a fase.

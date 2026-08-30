# Rollback e monitoração — 5.3.1 status timeout

Evidência exigida por `ship.require_rollback_plan` e
`ship.require_monitoring_notes` para a correção do falso `STATUS-TIMEOUT`.

## Superfície de risco

- `grill_status.py`: resolve branch uma vez por repositório e estado Git live
  uma vez por worktree, em vez de repetir por work item.
- `grill_workspace.py`: o timeout público de `status` passa a 30 segundos nos
  formatos JSON e Markdown.
- Não há migração, alteração de schema ou escrita nova: `status` continua
  read-only e o comportamento funcional da projeção permanece igual.

O risco principal é mascarar uma lentidão real ou reutilizar estado Git entre
worktrees diferentes. O teste
`test_live_git_state_is_resolved_once_per_worktree_not_per_item` trava a
granularidade correta.

## Plano de rollback

1. Reverter o merge em `main` preservando o primeiro pai:
   `git revert -m 1 <sha-do-merge>`.
2. Fazer bump para `5.3.2` nos oito pontos validados por
   `tests/validate_distribution.py` e registrar a reversão no `CHANGELOG.md`.
3. Deixar `.github/workflows/publish.yml` criar a nova tag e release. Nunca
   apagar ou reutilizar a tag imutável `v5.3.1`.

Não há rollback de dados. A reversão restaura apenas a estratégia anterior de
resolução Git e o timeout anterior.

## Monitoração

- Confirmar `ci.yml`, `bump-gate.yml` e `publish.yml` após o push.
- Rodar `status --format json` e `status --format markdown` em workspace com
  muitos work items; ambos devem terminar sem `STATUS-TIMEOUT`.
- Observar recorrência de `STATUS-TIMEOUT`, chamadas live por item em vez de
  por worktree, divergência de versão ou ausência da release `v5.3.1`.
- Manter o teste de regressão acima e a validação de distribuição no gate.

Não existe telemetria: a monitoração é manual/offline. Na reprodução validada,
o status acumulado concluiu em aproximadamente 2,4 segundos, abaixo do limite
público de 30 segundos.

# Evidência de entrega — rollback e monitoração da 5.3.1

## Rollback

Se a otimização de `status` causar regressão após o merge, executar
`git revert -m 1 <sha-do-merge>`, aplicar bump para `5.3.2` nos oito pontos de
distribuição e publicar pela workflow normal. A tag `v5.3.1` não pode ser
apagada nem reutilizada. Não há migração ou dado persistido a desfazer.

## Monitoração

- Gates: `.github/workflows/ci.yml`, `bump-gate.yml` e `publish.yml`.
- Sinal funcional: JSON e Markdown concluem sem `STATUS-TIMEOUT` em workspace
  acumulado; referência observada de aproximadamente 2,4 segundos sob timeout
  público de 30 segundos.
- Sinal estrutural: estado Git live é resolvido uma vez por worktree, coberto
  por `test_live_git_state_is_resolved_once_per_worktree_not_per_item`.
- Sinal de distribuição: oito pontos em `5.3.1`, tag e release no mesmo commit.

A monitoração é manual/offline porque o plugin não possui telemetria.

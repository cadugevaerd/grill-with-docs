# Rollback e monitoração — ship bloqueado

Nenhum merge, push, tag, release ou alteração de marketplace ocorreu. Não há estado remoto novo para reverter.

Quando os gates forem aprovados, usar integração isolada a partir do `origin/main`, merge `--no-ff`, verificar igualdade exata do ref remoto e manter tag imutável. Se uma publicação futura precisar ser desfeita, usar `git revert -m 1 <merge-sha>` e novo bump SemVer; nunca apagar/reutilizar tag.

Monitoração pós-publicação futura: `ci.yml`, `bump-gate.yml`, `publish.yml`, existência da release/tag ancorada no merge e preflight em Codex/Claude. A matriz live de ambos os runtimes continua requisito antes de ativar esse plano.

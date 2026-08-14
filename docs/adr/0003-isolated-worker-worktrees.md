# Isolated worker worktrees

Os workers paralelos executarão cada nó independente em um Worker Worktree e branch filho, ambos fixados no commit-base da tarefa; nenhum worker escreve no worktree do coordenador. `converge` integra resultados aceitos em série, e só worktrees limpos, convergidos e comprovadamente pertencentes à run podem ser removidos automaticamente; artefatos de bloqueio ou falha são preservados para diagnóstico.

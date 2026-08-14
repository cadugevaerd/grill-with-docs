# Worker least privilege

Cada worker recebe apenas seu Worker Worktree, comandos aprovados pelo nó e Git local. Workers não alteram Project Store, leases, dispatch, worktree do coordenador, `ship`, push ou release; rede e capacidades externas são negadas por padrão e só são concedidas quando declaradas no Execution DAG. O coordenador mantém autoridade exclusiva sobre orquestração e integração.

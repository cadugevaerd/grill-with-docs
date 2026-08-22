# Worker Model Floor

Nenhum worker despachado sob `implement-parallel` MUST receber modelo de fronteira. O binding tier→modelo é um asset versionado (`assets/workflow-tier-models.json`), declara `frontier` por modelo e cobre os runtimes `claude` e `codex`.

A garantia é derivação, não escolha: `declare_worker` resolve o modelo a partir do tier do nó e da classe do ator, e o chamador não passa `--model`. Um modelo marcado `frontier` para classe `worker` MUST bloquear com `FRONTIER-MODEL-FORBIDDEN` antes de qualquer worktree existir, e o modelo resolvido MUST ser gravado no worker record — que modelo rodou qual nó é fato durável, não memória de sessão.

Consequência deliberada sobre o ADR-0001: promoção de tier continua acontecendo só antes do dispatch, mas em `implement-parallel` uma promoção para `large` bloqueia em vez de promover. O leader orquestra e pode ser frontier; o worker implementa escopo fechado e não pode.

`partition` cai de `large` para `medium` no v4. O `agent-assign` do v3 casava tarefa e agente por nome e julgamento; `partition` é parsing determinístico mais bin-packing, com a heurística fixada em código. Rebaixar o piso é possível porque a etapa é nova: o ADR-0007 proíbe reduzir o mínimo de uma etapa existente, não impede declarar o mínimo honesto de uma etapa que nasce agora.

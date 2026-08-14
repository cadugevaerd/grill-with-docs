# CONTEXT

## Glossário

| Termo canônico | Definição | Termos a evitar | Evidência |
|---|---|---|---|
| Gauntlet Loop | Ciclo que orquestra etapas prontas do workflow por agentes cooperativos. | gauntled, executor externo | ADR-0004 |
| Gauntlet Configuration | Configuração versionada que governa a execução de um work item apto. | configuração global oculta, ativação implícita | ADR-0007 |
| Gauntlet-Enabled Work Item | Work item V3 configurado e autorizado a iniciar uma run. | work item V2 ativado, adapter não verificado | ADR-0007 |
| Canonical Skill | Skill registrada e autorizada para uma etapa específica. | substituto direto, emulação semântica | `workflow-step-skills.json`; ADR-0004 |
| Model Tier | Classe de capacidade atribuída a uma execução de skill. | nome comercial implícito, downgrade silencioso | ADR-0001 |
| Autonomous Run | Run que avança pelas etapas permitidas sem confirmação humana intermediária. | ship autônomo, aprovação implícita | ADR-0002 |
| Execution DAG | Grafo versionado que declara nós de trabalho e suas dependências. | paralelismo implícito, dependência inferida | ADR-0004 |
| Resumable Run | Run cujo progresso e evidências persistem para recuperação validada. | retomada cega, estado apenas em memória | ADR-0005 |
| Worker Worktree | Worktree Git isolado atribuído a um worker para um nó independente. | worktree compartilhado, branch compartilhada | ADR-0003 |
| Evidence Boundary | Fronteira local em que o coordenador valida resultado e registra evidência. | receipt autoafirmado, autoridade externa | ADR-0010 |
| Capability Grant | Permissão mínima declarada concedida a um worker pelo nó. | capacidade implícita, rede liberada por padrão | ADR-0006 |
| Stall Recovery | Recuperação limitada de uma run sem progresso observável. | timeout silencioso, retry ilimitado | ADR-0005 |
| Independent Review | Revisão somente leitura por subagente que não planejou nem executou a mudança. | autoaprovação, review pelo executor | ADR-0008 |
| Integration Conflict | Bloqueio quando mudanças de workers não convergem limpas. | auto-merge, conflito silencioso | ADR-0009 |
| Review Block | Bloqueio emitido quando a revisão independente reprova a mudança. | reparo automático fora do workflow, ship sem aprovação | ADR-0011 |

> Somente linguagem ubíqua; decisões e tarefas vivem em ADR/BL/ROADMAP.

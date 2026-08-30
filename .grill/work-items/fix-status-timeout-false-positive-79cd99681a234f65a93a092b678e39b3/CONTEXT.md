# CONTEXT

## Glossário

| Termo canônico | Definição | Termos a evitar | Evidência |
|---|---|---|---|
| STATUS-TIMEOUT | Código emitido pelo wrapper público de `status` quando a subprocess que calcula a projeção excede o timeout configurado | timeout genérico, travamento | `.grill/evidence/grill-status-timeout-debug-report.md` §Causa raiz |
| probe Git por worktree | Consulta ao estado Git (branch/head/dirty) resolvida uma única vez por worktree e uma única vez por repositório, nunca uma vez por work item enumerado | probe por item | `grill_status.py` função `build_status`, comentário sobre custo O(items) |
| timeout público suficiente | Limite do wrapper público (`grill_workspace.py status`) dimensionado com margem sobre o pior caso real medido, em vez de um valor arbitrário menor que ele | timeout fixo arbitrário | `.grill/evidence/grill-status-timeout-debug-report.md` tabela de evidências (10,56s real vs. 5s/30s testados) |

> Somente linguagem ubíqua; decisões e tarefas vivem em ADR/BL/ROADMAP.

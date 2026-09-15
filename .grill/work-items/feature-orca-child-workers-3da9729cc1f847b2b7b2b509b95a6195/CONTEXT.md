# CONTEXT

## Glossário

| Termo canônico | Definição | Termos a evitar | Evidência |
|---|---|---|---|
| sessão líder | Sessão do humano que conduz o GWD, invoca skills canônicas e é a única Evidence Boundary | leader agent, orquestrador genérico | SKILL.md 6.0.0 §Orquestração |
| coordenador | Papel Orca de quem cria a Run, inicia children e consome `check --wait` | supervisor, manager | `orca skills get orchestration` §Classify the role |
| child | Agente iniciado por `orchestration worker-start`, com preâmbulo de Task/Dispatch e fim por `worker_done` | subagente, subagent nativo, teammate | guia orchestration Orca 1.4.200 |
| Run | Namespace durável e inbox do coordenador; não agenda nem posiciona workers | sessão Orca | guia orchestration §Authority |
| Dispatch | Tentativa autoritativa de uma Task; fonte da autoridade de ciclo de vida do child | terminal, pane | guia orchestration §Authority |
| especialista | Child de autoria (xhigh) ou revisão (high) em etapa de julgamento | revisor líder | agent-orchestration.v1.json roles |
| worker | Child não-frontier que implementa um nó do Execution DAG | especialista | workflow-tier-models.json actor_classes |
| candidata 6.0.0 | Estado de `cadugevaerd/feat-new-subagents` ainda não publicado | 6.0.0 lançada | plugin.json f7aa733 |
| caminho degradado | Execução sem Orca pronto, pelo mecanismo nativo do runtime | fallback silencioso | GOAL.template.md §Delegação |

> Somente linguagem ubíqua; decisões e tarefas vivem em ADR/BL/ROADMAP.

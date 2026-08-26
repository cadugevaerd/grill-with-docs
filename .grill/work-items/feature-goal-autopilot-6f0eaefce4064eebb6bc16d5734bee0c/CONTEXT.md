# CONTEXT

## Glossário

| Termo canônico | Definição | Termos a evitar | Evidência |
|---|---|---|---|
| goal loop | Laço autônomo de um CLI agente que reinjeta um prompt de continuação após cada turno até o objetivo ser julgado satisfeito, o orçamento acabar ou o humano intervir. | "modo auto", "agente automático" | `~/.codex/goals_1.sqlite` (tabela `thread_goals`); `~/.hermes/hermes-agent/hermes_cli/goals.py` |
| goal.md | Documento de instruções, alvo desta feature, consumido como objetivo/contexto de um goal loop para conduzir um ciclo grill-with-docs sem supervisão contínua. | "prompt", "runbook" | Pedido de origem desta feature |
| runtime de goal | Implementação concreta do goal loop. Dois conhecidos nesta máquina: Codex CLI e Hermes. | "goal" sozinho | `codex --help`; `hermes_cli/goals.py` |
| ponto de interação | Momento do ciclo em que o goal loop deve parar e devolver o controle ao humano em vez de continuar sozinho. | "erro", "pausa" | ADR-0001 |
| GWD | Este plugin, `grill-with-docs`: protocolo plan-only de entrevista decisória por work item. | "grill" sozinho | `CLAUDE.md` da raiz |
| ciclo v4 | Sequência canônica do `WORKFLOW.md` deste repositório: specify, plan, checklist, tasks, analyze, partition, implement-parallel, converge, verify, review, ship. | "pipeline", "fases" | `grill_core/workflow_versions.py`; `state.json.development.sequence` |

> Somente linguagem ubíqua; decisões e tarefas vivem em ADR/BL/ROADMAP.

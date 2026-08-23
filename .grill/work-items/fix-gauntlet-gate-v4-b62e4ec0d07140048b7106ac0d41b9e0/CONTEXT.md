# CONTEXT

## Glossário

| Termo canônico | Definição | Termos a evitar | Evidência |
|---|---|---|---|
| gate de execução | Função `execution_gate(text) -> Gate` de um módulo `workflow_vN`, que decide se um `WORKFLOW.md` é elegível para ativar o Gauntlet. Retorna `OK` ou `BLOCKED` com código. | "validador", "checker" | `grill_core/workflow_v3.py:433`, `grill_core/workflow_v4.py:246` |
| módulo de gate | O módulo `workflow_vN` inteiro, injetado por keyword na fronteira do Gauntlet. Só dois atributos dele são consumidos: `execution_gate` e `Failure`. | "gate" sozinho | `grill_core/gauntlet.py` (únicos usos: `workflow_v3.execution_gate`, `workflow_v3.Failure`) |
| ponto de injeção | Cada chamada em `grill_workspace.py` que passa `workflow_v3=<módulo>` para o core do Gauntlet. São quatro. | "import", "dependência" | `grill_workspace.py:2388,2458,2532,2542` |
| marcador de workflow | Comentário HTML `<!-- grill-with-docs-workflow:vN -->` na primeira linha do `WORKFLOW.md`, que declara a versão do documento. | "header", "versão do arquivo" | `grill_core/workflow_v3.py:355`, `grill_core/gauntlet.py:378-383` |
| frontier ativa | A versão de workflow que este build materializa e considera corrente: `workflow_versions.ACTIVE_VERSION`. Hoje `v4`. | "última versão", "versão nova" | `grill_core/workflow_versions.py:163` |
| tabela por versão | Literal congelado `*_BY_VERSION` no SSOT `workflow_versions.py`, nunca derivado de outra versão. | "mapa de migração" | `CLAUDE.md`, `grill_core/gauntlet.py:33-60` |

> Somente linguagem ubíqua; decisões e tarefas vivem em ADR/BL/ROADMAP.

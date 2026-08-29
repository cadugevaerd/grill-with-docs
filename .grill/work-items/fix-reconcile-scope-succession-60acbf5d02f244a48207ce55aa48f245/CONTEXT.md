# CONTEXT

## Glossário

| Termo canônico | Definição | Termos a evitar | Evidência |
|---|---|---|---|
| recibo histórico | Receipt imutável de um work item já concluído e reconciliado; preserva escopo e dependências para rastreabilidade. | ownership ativo, lock de arquivo | `grill_workspace.py:1829-1838`; tri-sgd24-scope-succession |
| sucessão explícita | Relação direta `depends-on-work` pela qual um trabalho posterior declara que se apoia num trabalho reconciliado anterior; transitividade não é inferida. | sobreposição liberada, waiver de escopo | ADR-0001 |
| sobreposição concorrente | Interseção de escopo sem uma relação de sucessão comprovada e válida. | qualquer sobreposição | `.grill/triage-evidence/SGD-24-debug.md` |
| ownership perpétuo | Comportamento defeituoso em que todo escopo de recibo bloqueia para sempre qualquer trabalho posterior. | segurança fail-closed | `.grill/triage-evidence/SGD-24-debug.md` |

> Somente linguagem ubíqua; decisões e tarefas vivem em ADR/BL/ROADMAP.

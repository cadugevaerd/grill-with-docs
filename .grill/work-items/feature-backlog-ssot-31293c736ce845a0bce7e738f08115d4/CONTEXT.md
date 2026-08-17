# CONTEXT

## Glossário

| Termo canônico | Definição | Termos a evitar | Evidência |
|---|---|---|---|
| Backlog de decisão | Conjunto de decisões adiadas de um work item, identificadas por `BL-NNNN` locais ao work item | backlog, BL genérico | `DECISION-BACKLOG.md`; SKILL.md "IDs são locais ao work item" |
| Backlog operacional | Registro de trabalho por repositório mantido pelo `backlogctl`, global à máquina e compartilhado entre repos | backlog, backlog global | `backlogctl backlog list`; 10 backlogs em `~/.backlog/backlog.db` |
| Item de backlog | Unidade do backlog operacional, identificada por `<CODE>-<n>` atribuído pelo `backlogctl` | BL, ticket, issue | `SGD-3`; `backlog_bridge.py` `item add` |
| Referência de decisão | Token `BL-NNNN` que nomeia uma decisão adiada dentro do work item e é citado em ROADMAP, PLAN-CONTEXT e handoff | ID do backlog | `audit_decisions.py:512` valida a coerência entre os três |
| Projeção | Artefato gerado a partir de uma autoridade externa, versionado e nunca escrito à mão | espelho, cópia, cache | `.grill/global/` é projeção de work items concluídos |
| Autoridade de estado | Componente que decide o ciclo de vida de um registro (transições, criticality) | dono, fonte da verdade | ADR-0001 |
| Evidência no commit | Artefato versionado que prova, no commit, o que foi decidido | histórico, log | Constituição, cláusula Rastreabilidade |

## Relações

- Um **Backlog de decisão** pertence a exatamente um work item.
- Uma **Referência de decisão** aponta para exatamente um **Item de backlog**.
- O **Backlog operacional** é a **Autoridade de estado** de um **Item de backlog**.
- `DECISION-BACKLOG.md` é uma **Projeção** do **Backlog operacional** e serve como **Evidência no commit**.

## Ambiguidades sinalizadas

- "backlog" era usado para três coisas distintas: o ledger local de decisões adiadas, o registro do `backlogctl` e a lista de trabalho do ROADMAP. Resolvido: **Backlog de decisão** e **Backlog operacional** são conceitos separados; o ROADMAP não é backlog.
- "fonte da verdade" juntava autoridade sobre ciclo de vida e prova no commit. Resolvido: são **Autoridade de estado** e **Evidência no commit**, e podem viver em lugares diferentes (ADR-0001).

> Somente linguagem ubíqua; decisões e tarefas vivem em ADR/BL/ROADMAP.

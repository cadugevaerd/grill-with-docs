# CONTEXT

## Glossário

| Termo canônico | Definição | Termos a evitar | Evidência |
|---|---|---|---|
| status bruto | Projeção JSON `grill-status/v1`, completa e destinada a automações | resposta humana, tabela | ADR-0001 |
| status humano | Projeção Markdown canônica consumida pela skill e reproduzida sem reformulação | resumo livre, interpretação do agente | ADR-0001 |
| work item coerentemente fechado | Item que satisfaz simultaneamente todos os invariantes de milestone, fases, auditoria e etapas GWD | concluído por aparência, `next_gate=complete` isolado | ADR-0002 |
| pendência operacional | Classificação aditiva de um item em `blocked`, `in-progress` ou `pending`, acompanhada de motivos determinísticos | resumo, próximo gate | ADR-0003 |
| etapa GWD | Um dos onze passos ordenados de `specify` a `ship` registrados em `development.steps` | fase, tarefa | WORKFLOW.md; ADR-0002 |
| all good | Resposta humana terminal exata quando não existe pendência operacional nem erro global | OK, tudo certo, vazio | ADR-0003 |
| inicialização pendente | Estado de workspace GWD sem nenhum work item, que exige `init` e não equivale a `all good` | workspace vazio saudável | ADR-0003 |
| bump obrigatório | Incremento SemVer exigido por alteração em `plugin/**`, replicado nas superfícies fixadas pelo contrato de distribuição | versionar depois, reutilizar tag | ADR-0004 |

> Somente linguagem ubíqua; decisões e tarefas vivem em ADR/BL/ROADMAP.

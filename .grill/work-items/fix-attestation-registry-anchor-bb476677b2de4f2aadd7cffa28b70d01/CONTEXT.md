# CONTEXT

## Glossário

| Termo canônico | Definição | Termos a evitar | Evidência |
|---|---|---|---|
| versão declarada | O valor de `development.workflow_version` no `state.json` do work item; a versão de workflow sob a qual aquele bundle foi escrito e é julgado. | "versão do projeto", "versão do plugin" | ADR-0001 |
| versão ativa | `WORKFLOW_VERSION` do build em execução; hoje v4. Não é autoridade sobre bundle algum. | "versão atual", "a versão" | step_skills.py:436 |
| registry ancorado | O asset de registry escolhido pela versão declarada, contra o qual a resolução de skill é recomputada e comparada. | "registry", sem qualificar | ADR-0001 |
| resolução de skill | Documento `skill-resolution/v1` que afirma qual skill, adapter e entrypoint atendem um `step_id` num runtime. Prova nada por si só: vale o que o registry ancorado confirmar. | "skill", "resolução" | step_skills.py:1011-1093 |
| código de contrato | Código de saída nomeado e previsto pelo contrato do CLI, oposto a `UNEXPECTED-FAILURE`, que é a máscara de um defeito. | "erro", "falha" | grill_workspace.py:3255-3272 |
| escopo declarado | Lista honesta em `WORK-ITEM.json scope.paths` dos arquivos que o trabalho pode alterar. | "escopo mínimo" quando omite arquivo tocado | DQ-0004 |
| reivindicação histórica | Escopo preservado em recibo de trabalho já concluído; é rastreabilidade, não ownership exclusivo perpétuo. | "conflito ativo" | BL-0001 |
| conflito de escopo | Sobreposição material entre trabalhos concorrentes ou sem relação de dependência; não inclui sucessão explícita após trabalho concluído. | "qualquer sobreposição" | BL-0001 |

> Somente linguagem ubíqua; decisões e tarefas vivem em ADR/BL/ROADMAP.

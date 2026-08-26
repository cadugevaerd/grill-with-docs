# CONTEXT

## Glossário

| Termo canônico | Definição | Termos a evitar | Evidência |
|---|---|---|---|
| goal.md | Documento de instruções que um goal loop segue para conduzir o protocolo, materializado na raiz do projeto consumidor. | "prompt", "runbook" | `plugin/skills/grill-with-docs/assets/GOAL.template.md` |
| materialização | Ato de fixar um asset gerenciado na raiz do projeto consumidor, no-clobber, com marcador versionado e hash registrado no estado do work item. | "instalação", "cópia" | `ensure_workflow.py`, que já faz isso para o contrato de workflow |
| marcador | Comentário HTML na primeira linha que declara a versão do contrato daquele documento, independente da versão SemVer do plugin. | "header", "versão" | `<!-- grill-with-docs-goal:v1 -->` |
| tupla ESSENTIAL | Literal congelado de substrings que precisam aparecer no documento materializado; nunca derivada da tupla de outro documento ou de outra versão. | "checklist", "schema" | `specs/024-goal-md-contract/contracts/essential-substrings.md` |
| SSOT de documento | Módulo que declara marcador, versão e tupla de um documento gerenciado, e do qual todo consumidor lê em vez de redeclarar. | "constante", "config" | ADR-0101 |
| no-clobber | Criação que nunca sobrescreve arquivo existente: preserva bytes e reporta o estado em vez de substituir. | "force", "overwrite" | `ensure_workflow.atomic_create` |

> Somente linguagem ubíqua; decisões e tarefas vivem em ADR/BL/ROADMAP.

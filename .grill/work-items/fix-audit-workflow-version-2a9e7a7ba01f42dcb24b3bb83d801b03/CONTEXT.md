# CONTEXT

## Glossário

| Termo canônico | Definição | Termos a evitar | Evidência |
|---|---|---|---|
| marcador de workflow | A string `grill-with-docs-workflow:vN` presente no corpo do `WORKFLOW.md` materializado. É a única declaração que o próprio documento faz sobre qual contrato ele cumpre. | "versão do workflow" (ambíguo: pode significar o marcador, o campo carimbado ou a versão que o plugin fala) | `ensure_workflow.py:111`; `audit_decisions.py:361` |
| campo derivado | Campo de `state.json` cujo valor é lido do artefato que ele descreve, no momento da escrita. `constitution.sha256` e `workflow.sha256` já são derivados. | "campo calculado", "campo dinâmico" | `grill_workspace.py:645` (`workflow_info`) |
| campo constante | Campo de `state.json` cujo valor é um literal do código ou do asset, independente do artefato descrito. `state.workflow.version` e `development.workflow_version` são constantes hoje. | "default", "valor padrão" — sugerem que algo pode sobrescrever, e nada sobrescreve | `grill_workspace.py:691`; `assets/state.template.json:5` |
| versão ativa do plugin | `workflow_versions.ACTIVE_VERSION` — a versão de workflow que esta build do plugin materializa. Não é, por si, a versão do documento que já existe no repositório. | "versão do workflow", "versão atual" | `grill_core/workflow_versions.py:163` |
| detector estrito | Resolução de marcador que exige **exatamente uma** ocorrência no documento; zero ou duas não resolvem. É a regra que `audit_decisions.py:366` já aplica. | "detector", sem qualificar — `managed_version` é first-match e tem regra diferente | `audit_decisions.py:361-369` |
| par writer/reader | O carimbo em `state.json` e a asserção correspondente na auditoria. Um par que compartilha o mesmo literal nunca diverge — e por isso não verifica nada. | "validação" | `grill_workspace.py:691` + `audit_decisions.py:801` |

> Somente linguagem ubíqua; decisões e tarefas vivem em ADR/BL/ROADMAP.

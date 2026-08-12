# CONTEXT

## Glossário

| Termo canônico | Definição | Termos a evitar | Evidência |
|---|---|---|---|
| Matriz de etapas | O mapa dos 11 passos do ciclo externo com o estado de cada um, guardado em `state.json` sob `development.steps`. Representa o **estado corrente**, não o histórico. | "checkpoint", "progresso", "steps" | `grill_workspace.py` subcomando `checkpoint`; `development.steps` do work item anterior |
| Trilha de checkpoint | A lista append-only de transições em `development.audit`, com passo, estado, razão e evidência. É onde o histórico sobrevive quando a matriz muda. | "log", "auditoria" (que é o veredito documental) | 22 entradas no work item `feature-release-repo-sync`, cobrindo os 11 passos de uma fase |
| Virada de fase | O momento em que uma fase do ROADMAP fica terminal e a seguinte começa. Exige que a matriz de etapas volte ao início. | "reset", "próxima fase" | ADR-0001 |
| Pino de identidade | Os campos `branch` e `head` gravados em `immutable` no `WORK-ITEM.json`, no instante do `init`. Protegidos por `immutable_sha256`. | "HEAD gravado", "recorded" | `WORK-ITEM.json`; `grill_status.py:87` |
| Deriva viva | A diferença entre o pino de identidade e o estado vivo do Git no momento da leitura. Nem toda deriva é defeito. | "LIVE-VS-RECORDED" usado como sinônimo de erro | ADR-0002 |
| Work item terminal | Work item com `state.status=complete` e `milestone_status=completed`. Depois disso, deriva contra o pino é esperada, porque o branch de trabalho já foi mergeado e apagado. | "concluído", "fechado" | `feature-release-repo-sync` em `main`, com `feat/release-repo-sync` inexistente |
| Gate de bump | O job que reprova PR que altera `plugin/` sem subir a versão. Hoje reporta, mas não bloqueia. | "CI", "check" | `.github/workflows/ci.yml`, job `bump-gate`; FR-007 da FASE-001 anterior |
| Required status check | Registro no branch protection que transforma a reprovação de um check em bloqueio de merge. É configuração de repositório, não código. | "gate obrigatório" | SGD-4 |
| Filtro de paths | O `paths:` de `on.pull_request`, que é **por workflow** e não por job. Um workflow pulado não reporta status nenhum. | "filtro do job" | `.github/workflows/ci.yml`; SGD-7 |

> Somente linguagem ubíqua; decisões e tarefas vivem em ADR/BL/ROADMAP.

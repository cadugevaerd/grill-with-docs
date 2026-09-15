# Revisão independente do plano — R1

- verdict: NO-GO
- task: task_5edfb77cd81f
- dispatch: ctx_bde909c3bbc3
- requested/effective: gpt-6-astra/high
- report-message: msg_193a7538791b
- completion-message: msg_d2a4bc65f2a2
- outcome: succeeded (revisão concluída, plano não aprovado)
- writes: none

## P1 — Preservar barreiras de tarefas fora do scheduler

Locais: contracts/task-files.md:27–29,54–56; data-model.md:134–136; contracts/integrations.md:11, todos em specs/030-agent-orchestration.

Files: [] e tarefas reservadas ao líder ficam somente em read_only_tasks/deferred_to_leader; nodes e dependências contêm somente workers. O plano promete fases-barreira sem definir aceite por task/fase dessas listas nem verificação antes de declarar a wave seguinte. No baseline, partition.py:249–270 elimina deferred antes de construir fases, e grill-implement-parallel/SKILL.md:74–85 executa deferred somente depois de todas as waves. O suplemento muda a receita de sidecar, mas não essa ordem.

Consequência: Phase 1 read-only de revisão/aprovação ou tarefa do líder que prepara arquivo consumido pela Phase 2 pode ser ultrapassada. Conjunto totalmente fora do scheduler é descrito como válido e retorna diagnóstico sem DAG, mas grill-partition/SKILL.md:64–77 exige DAG-VALID para checkpoint e gauntlet_runs.py:628–630 recusa nodes vazio.

Recomendação do revisor: aceite por task_id/fase usando activities/receipts já propostos; impedir waves posteriores enquanto houver pendência anterior e especificar conclusão canônica sem workers para conjunto vazio, sem scheduler ou workers fictícios, preservando pins. Checks propostos: fase só read-only/deferred antes de worker respeita aceite; conjunto totalmente read-only/deferred alcança conclusão canônica válida com zero worker.

Nota de coordenação para análise do autor: a recomendação de conclusão zero-worker precisa ser reconciliada com a classe worker-required imutável de implement-parallel. Não aceitar receipt fictício ou enfraquecer classe congelada. Definir a menor solução compatível com requisitos realmente aprovados; não tratar recomendação do revisor como autorização para violar governança.

## P2 — Suspensão do estilo não pode bloquear o trabalho

Locais: data-model.md:118–120; contracts/cli.md:13; plan.md:174.

use_ready exige application=active e loaded corrente, e todos os despachos/entradas exigem use_ready. Porém stop adhd mode produz suspended_by_user e compactação nesse estado proíbe recarga. A opção prometida como suspensão somente de apresentação bloqueia a próxima entrada/despacho, inclusive após compactação.

Correção recomendada: separar readiness do trabalho de aplicação visual ativa; suspensão humana explícita vinculada à mesma sessão satisfaz o gate de trabalho, mantendo presença/habilitação obrigatórias. Nova sessão volta ao default; suspensão não serve de aceite positivo de FR-024. Check: bootstrap → stop adhd mode → compactação → próxima atividade autorizada sem estilo, Ponytail e outputs intactos, nova sessão ativa.

## Demais conclusões

Sem outros findings materiais. Cleanup trata a causa compartilhada e preserva leitores de sucesso/convergência. Continuidade prevê seletor único, ponte de campanhas, CAS e recovery sem reetiquetar outputs. Papéis, preview e gates são verificáveis; Orca com bootstrap neutro fornece caminho positivo. Carga local distingue instalação efetiva/habilitação/leitura/comportamento; C1/C2/A1/A2, recarga e controle externo são roteiro suficiente para a prova futura. Pins v3/v4, sequência11, stdlib/offline, bump6.0.0 e bundle histórico estão coerentes; os dois módulos novos correspondem a fronteiras existentes, sem framework excessivo.

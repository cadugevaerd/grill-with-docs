# Suplemento de orquestração de agentes v1

Este suplemento integra `grill-agent-orchestration/v1` à entrada canônica já resolvida. Ele não é uma skill, alias, macroetapa ou substituto do registry: o líder recebe o contexto e invoca a skill canônica aplicável com estas instruções específicas.

## Contexto de invocação

O contexto devolve o entrypoint canônico, o registry hash, esta política e template com seus hashes, classificação, atividades exigidas e apresentação. Ler o contexto não é invocar a skill. O core verifica admissibilidade e os especialistas produzem artefatos; o líder mantém coordenação e evidência.

## Autoria, revisão e matriz

Use a matriz da política para as onze etapas: `specify`, `plan`, `checklist`, `tasks`, `analyze`, `partition`, `implement-parallel`, `converge`, `verify`, `review` e `ship`. Uma entrevista pré-ciclo usa `activity_scope=interview` e `step_id=null`; ela não cria uma macroetapa. Autorias novas requerem autor técnico xhigh e julgamentos requerem revisor high independente. O líder pode executar somente o trabalho mecânico listado; workers continuam não-frontier.

## Tasks, Files e Result

Para o contrato adotado da candidata, entregue ao autor o template `task-files/v1`. Cada tarefa declara `Files:` JSON; tarefa despachável com escrita declara um `Result:` explícito que também esteja em `Files:`. Tarefa com path de evidência reservado ao líder é inteira `deferred_to_leader`, inclusive seus paths de produto, e não exige `Result:`. Não infira paths, não acrescente sidecar de node e não use `FEATURE_WIDE`. Resultados por tarefa substituem a receita histórica de sidecar por node somente neste contrato adotado; tasks históricas e DAGs selados não são reinterpretados.

Agrupe conflitos somente dentro da fase. Em cada fase, converja workers e depois aceite atividades read-only/deferred na ordem das tasks antes de avançar. Fase sem worker é resolvida nessa posição. Activities vinculam task ID, fase, fingerprint e DAG; aceite positivo é necessário para ultrapassar a barreira. Se não houver tarefa despachável, `partition-emit` retorna `PARTITION-NO-WORKERS` antes de admissão, DAG-VALID, checkpoint ou worker fictício.

## Capabilities e classificação

Verifique capabilities observadas antes de enviar payload técnico: identidade, modelo/esforço efetivos, encerramento e transporte bootstrap/payload separado. Ausência, alias não comprovado ou observação incompleta bloqueiam; configuração solicitada não prova execução. Classifique frontend por handoff, DU e PLAN-CONTEXT coerentes. `platform-devops` sem superfície é `NOT_APPLICABLE`; classificação contraditória não pode contornar o gate visual. Frontend exige preview HTML, capturas PNG, manifest, autor/revisor independentes e aprovação humana do digest corrente antes de `tasks`.

## Apresentação local GWD

No fluxo GWD, o bootstrap obrigatório resolve a instalação efetiva e lê integralmente a referência aprovada `i-have-adhd@i-have-adhd` antes da primeira resposta de trabalho. A apresentação é local ao fluxo/projeto GWD, preserva instruções superiores, conteúdo solicitado e Ponytail; não invoca a skill upstream, não cria flag global e não edita cache/configuração global. `stop adhd mode` suspende somente a apresentação na sessão comprovada; nova sessão volta ao default ativo. Retomada, mudança de runtime/incarnation e compactação revalidam contexto; suspensão válida mantém `work_ready`, mas não `use_ready` nem `functional_verified`.

O evento de leitura precisa ser observado na mesma sessão, geração, hash e escopo. Enumeração, hash textual ou autorrelato não bastam. A referência carregada organiza apresentação; ela não substitui a skill canônica invocada, não altera JSON/código/evidência e não prova por si só comportamento do modelo.

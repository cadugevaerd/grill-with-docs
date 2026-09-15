# Data model: orquestração de agentes

Contrato novo: `grill-agent-orchestration/v1`; política suplementar e persistência são versionadas independentemente do workflow v4. Não alterar schemas/bytes de recibos antigos, admission do scheduler ou tabelas de workflow.

## Convenções e armazenamento

Novos objetos são JSON de chaves fechadas, sem duplicatas, NaN ou valores implícitos. IDs são tokens seguros; digests usam a convenção já existente: Store em hex puro, referências públicas de skills em `sha256:<hex>`. Não comparar formatos sem conversão explícita. Timestamps UTC RFC3339 servem para diagnóstico, não para decidir quem é o owner atual.

Store ganha campo top-level opcional `agent_orchestration = {schema, work_items}`. Dentro de `work_items[work_id]`: `policy_ref`, `policy_sha256`, `adopted_at`, `origin`, `current_context_id`, `contexts`, `activities`, `resources`, `operations`, `checkpoints`, `checkpoint_head`, `visual_decisions`, `scope_files`, `scope_revision`, `scope_history`, `last_transition`. Ausência significa legado; presença inválida bloqueia. Adoção escreve o bloco uma vez e impede removê-lo. Readers antigos recusam campo desconhecido; essa limitação é apresentada no preview da migração, nunca contornada apagando o bloco.

`origin` fixa hashes do snapshot legado, state, ativação e campanha de origem e a revisão Store observada na adoção; não os substitui. `scope_files` é a lista exata aprovada para a entrega; `scope_revision` é inteiro monotônico e `scope_history` preserva revisões e evidências de aprovação: grants são subconjuntos, mas Files continua a única autoridade de escrita de cada tarefa. Ampliar escopo exige revisão e adoção explícita do novo digest; não inferir do texto.

Receipts estruturados de observação/atividade/preview são gravados pelo líder sob `.grill/work-items/<work_id>/agent-orchestration/`, fora das worktrees de workers. O Store guarda refs+digests e o estado comprometido. Nem path sozinho nem conteúdo produzido pelo worker dá autoridade. Artefatos de produto/planejamento ficam em `specs/<feature>/`; snapshots de evidência de coordenação continuam reservados ao líder.

## Contexto de execução

Cada `contexts[context_id]` contém:

| Campo | Conteúdo/invariante |
|---|---|
| `context_id`, `epoch` | ID único, inteiro positivo monotônico por work item; nunca reutilizar epoch |
| `predecessor_context_id`, `continuity_ref` | Null apenas no primeiro contexto adotado; demais apontam para origem comprovada |
| `worktree_identity` | project_id, work_id, fase/DU, Git common-dir identity, caminho real e branch de execução; não migrar worktree |
| `runtime`, `adapter` | Codex/Claude da sessão corrente, explícitos e comprovados |
| `activation` | Snapshot integral do shape de ativação existente; hash, fontes e catálogo daquele runtime |
| `campaign` | Mesmo shape estrito de sete campos de attestation: project_id, run_id, runtime, adapter, registry_sha256, recovery_generation_id, plan_revision |
| `scheduler_runs` | Mapa run_id→admission_sha256/DAG pin/origin_context_id; campaign run_id não é confundido com scheduler run_id |
| `leader` | owner_id, session_ref, provider incarnation, fence/epoch, state, observation_ref e digest |
| `presentation` | Estado do estilo GWD para a sessão líder; fonte instalada, escopo e quatro eixos independentes definidos abaixo |
| `state` | PREPARED, ACTIVE, QUIESCING, RELEASED ou SUPERSEDED |
| `policy_sha256`, `inputs_sha256` | Contrato e entradas correntes; incompatibilidade não muda silenciosamente o contexto |

Transições: primeiro contexto comprovado PREPARED→ACTIVE; ACTIVE→QUIESCING por prepare-switch; QUIESCING→RELEASED somente após ausência comprovada de trabalho ativo e obrigação de cleanup avaliada; destino PREPARED→ACTIVE por CAS que move current_context_id e marca origem SUPERSEDED. Se preparação é interrompida, permanece QUIESCING e a próxima chamada retoma a mesma operação. Reativar a origem também exige novo contexto/epoch e prova; não desfazer fence antigo.

`leader.state` distingue ACTIVE, RELEASING e RELEASED. Lease expirada não cria RELEASED. Toda operação mutável correlaciona contexto, session_ref/incarnation, fence e identidade do work item. Um processo antigo pode continuar existindo, mas não pode escrever no GWD depois do fence; para trocar CLI também é necessária observação de que sua atividade GWD terminou/ficou estacionada, sem turno ou worker ativo. Incerteza bloqueia.

No bootstrap de um trabalho novo, ainda podem não existir ativação Gauntlet, campanha ou scheduler run. `activation` e `campaign` são null e `scheduler_runs` vazio até a primeira vinculação comprovada por gauntlet-init/atestação; essa ausência não é prova falsa nem inicialização de campanha fictícia. A primeira vinculação é write-once naquele contexto. Atividades da entrevista usam o mesmo fence e checkpoint, com `activity_scope=interview` e `step_id=null`; não criam uma décima segunda macroetapa. Entrada no ciclo canônico exige as provas de ativação que o workflow já requer. Troca antes da primeira campanha preserva explicitamente sua ausência e não inventa ponte entre recibos inexistentes.

## Participação especializada

`activities[activity_id]`:

- Identidade: `activity_id`, `context_id`, `step_id`, `activity_scope`, `activity_type`, `role`, `attempt`, `author_activity_ids`, `input_manifest`, `input_sha256`, `task_binding`.
- Política: `runtime`, `requested_model`, `requested_effort`, `policy_sha256`, `write_files`. Author xhigh; reviewer high; modelo obrigatório conforme runtime. Reviewer tem `write_files=[]`.
- Execução: `session_resource_id`, `launch_observation_ref`, `effective_model`, `effective_effort`, `resolved_model_id`, `payload_sha256`, `released_at`, `state`, `presentation_observation_ref`.
- Resultado: `result_ref`, `result_sha256`, `output_manifest`, `diagnostic_ref`, `accepted_by_context`, `acceptance_ref`, `review_verdict`.

Campos de observação/resultados inexistentes permanecem null até a transição que os comprova; não preencher com solicitado. `resolved_model_id` pode diferir do alias literal somente por mapeamento observado do runtime. Reviewer deve ter session identity diferente da identidade de todos os authors do input; `author_activity_ids` não pode omitir autores de um artefato composto.

Estados: DECLARED→BOOTSTRAPPING→VERIFIED→DISPATCHED→RESULT_RECORDED→ACCEPTED; qualquer etapa de admissão pode ir a BLOCKED com diagnóstico. DISPATCHED pode terminar FAILED, registrando diagnóstico antes de cleanup. RESULT_RECORDED não equivale a ACCEPTED. Payload técnico só sai em VERIFIED→DISPATCHED; bootstrap não recebe código/spec/desenho do trabalho. Fonte de modelo/esforço ausente impede VERIFIED. Modelo divergente no retorno impede ACCEPTED e exige nova tentativa, preservando a anterior.

Revisão aceita refere digest dos artefatos correntes e verdict APPROVED ou CHANGES_REQUIRED. Edição de inputs/outputs torna essa revisão STALE por comparação, sem reescrever o resultado histórico. Receipts determinísticos têm `activity_type=deterministic_check` e não satisfazem autor/revisor.

`task_binding` é null fora das tarefas de execução read-only/deferred; nessas tarefas contém `task_id`, `phase`, `tasks_semantic_sha256`, `dag_content_sha256`, conferidos contra tasks/DAG/report e copiados no receipt de aceite. O input_manifest fixa os inputs e atividades obrigatórias daquela tarefa; aprovação humana exigida referencia a interação observada, nunca flag do executor. A barreira é projeção dos aceites positivos dessas activities, das integrações de workers e das importações comprovadas, sem nova entidade de scheduler: ACCEPTED com CHANGES_REQUIRED ou falha diagnosticada não satisfaz tarefa. Escrita deferred exige output_manifest e efeito confirmado; tarefa read-only usa retorno persistido pelo líder, sem Result/commit fictício. Fence e inputs são revalidados no dispatch/aceite; checkpoint accepted_executions conserva os vínculos para retomada idempotente.

Especialistas escrevem somente outputs autorizados fora das reservas de evidência, ou retornam conteúdo ao líder. Nunca recebem grant de checkpoint, ativação, decisões humanas ou macroetapa. Separar o autor de tasks do worker de implementação: o autor pode produzir tasks.md como artefato; workers nunca o editam.

## Recurso de agente

`resources[resource_id]` tem `kind=session|worktree|branch`, `agent_id`, `activity_id` ou vínculo `scheduler_run_id/worker_id/wave_id`, `origin_context_id`, `identity`, `creation_observation`, `result_acceptance_ref`, `evidence_manifest`, `state`, `last_observation`, `preservation_reasons`, `operation_id`.

Identidades específicas:

| Tipo | Identidade obrigatória |
|---|---|
| session | provider/adapter, host identity, runtime instance, handle ou session ID emitido pelo runtime, incarnation, owner dispatch quando existir |
| worktree | Git common-dir, chave e caminho real de criação, branch ref, base_commit original; observed terminal_head/integrated_head são fatos separados |
| branch | ref local completa e repo identity; OID esperado no momento da remoção; criação vinculada ao worker, nunca somente prefixo |

Estado de recurso: REGISTERED→CLOSE_PENDING/REMOVE_PENDING→CLOSED/REMOVED. REGISTERED ou pending pode passar a PRESERVED ou UNKNOWN, com razão e observação; nova avaliação pode voltar a pending se os fatos mudarem. CLOSED/REMOVED é terminal para aquela identidade. Uma sessão/ref nova com o mesmo nome é recurso novo/divergente, não reabertura automática.

Sessão requer resultado/diagnóstico durável e término comprovado do agente antes de close. Worktree/branch requerem cumulativamente sessão encerrada, identidade exata, integração comprovada, árvore limpa e ausência de evidência exclusiva. Arquivos ignorados entram na inspeção de exclusividade. Falha de worker com trabalho pendente não pode receber REMOVED. Ref só é removida após worktree ausente e comparação OLD_OID.

Razões estáveis incluem `RESULT_NOT_DURABLE`, `SESSION_ACTIVE`, `SESSION_CLOSE_UNCONFIRMED`, `IDENTITY_UNPROVEN`, `IDENTITY_CHANGED`, `WORKTREE_DIRTY`, `IGNORED_CONTENT`, `WORK_NOT_INTEGRATED`, `EXCLUSIVE_EVIDENCE`, `BRANCH_IN_USE`, `REF_CHANGED`, `PROVIDER_UNAVAILABLE`. Várias podem coexistir; não substituir todas por PRESERVED genérico.

Ausência observada na primeira descoberta não prova cleanup. Só replay de uma intenção com identidade previamente verificada pode terminar em ALREADY_ABSENT confirmado. Estado worker TERMINAL/FAILED e flags de convergência são independentes da remoção de recursos. Leitura de CLEANED legado exige correlação com conclusão e convergência antigas para satisfazer dependências.

## Operação e checkpoint

`operations[operation_id]` guarda `kind`, `context_id`, `fence`, `subject_ids`, `input_sha256`, `expected_before`, `intended_after`, `idempotency_key`, `state`, `result_ref`, `result_sha256`, `observation_ref` e `error`.

Estados: INTENT→APPLIED→CONFIRMED; INTENT/APPLIED→UNKNOWN quando resultado não é observável; INTENT→REFUSED se pré-condição mudou sem efeito. APPLIED não basta para declarar cleanup completo. Repetição da mesma chave e inputs devolve a operação; mesma chave com inputs diferentes bloqueia. Chave inclui ação, identidade e digest, nunca apenas nome do worker. Não repetir UNKNOWN cegamente.

Checkpoint imutável `checkpoints[checkpoint_id]` contém:

- `schema=grill-continuity-checkpoint/v1`, `checkpoint_id`, `context_id`, `previous_checkpoint_id`, `worktree_identity`, `created_at`, `store_revision` e journal anchor.
- `state_sha256`, `inputs_manifest`, `workflow_sha256`, `constitution_sha256`, `policy_sha256`, ativação/campanha correntes e refs históricas.
- `development_sequence`, `current_step`, estados das etapas, `accepted_outputs`, `accepted_executions`, `pending_attempts`, `scheduler_runs` com admission/DAG/lineage heads.
- `operations`, `cleanup_obligations`, `preserved_resources`, `blocking_activity`, `visual_state`, `presentation` e `checkpoint_sha256`.

O head é atualizado apenas no commit validado. Outputs aceitos são copiados por referência/digest exatos; `provenance` antigo não é reetiquetado como execução do destino. A origem/contexto de cada receipt é guardada separadamente. Captura sem accepted receipt deixa a tentativa pendente, nunca promove artefato existente por suposição.

Recibo de continuidade liga `from_checkpoint`, `from_context`, `to_context`, hashes das duas campanhas/ativações, snapshot dos accepted outputs, motivo, observações de quiescência e cleanup, target session e operação CAS. Recusa alteração de projeto/work item/fase/worktree/branch, de sequência ou accepted output. Mudança de código/plano é outra revisão; não se disfarça de mudança de CLI.

O snapshot de apresentação da origem permanece histórico. Retomar em outra sessão/runtime exige presença/habilitação e carga novas no destino; não importar `LOADED` ou `CONFORMANT` da origem. Mesmo runtime com nova incarnation também exige carga própria. Isso não invalida resultados técnicos aceitos nem repete efeitos: só restabelece o contexto de apresentação antes do próximo trabalho.

## Estado do estilo GWD

`presentation` usa schema `grill-gwd-presentation/v1`, no contexto existente, sem novo banco ou arquivo global. Antes de existir work item, preflight pode retornar o mesmo shape em memória com work_id/context_id null; a primeira operação de init/adopt registra a observação no contexto. Leitura isolada de preflight não cria work item nem receipt no Store.

| Campo | Conteúdo/invariante |
|---|---|
| `component`, `minimum_version`, `loader` | `i-have-adhd@i-have-adhd`, `0.3.0`, `gwd-reference/v1` |
| `runtime`, `session_identity`, `config_fingerprint` | Runtime explícito, provider/session/incarnation e fingerprint da configuração efetiva pertinente, sem valores secretos |
| `scope` | `kind=gwd`, Git root real, project_id/work_id/context_id quando existentes, source invocation ref; nunca `global` |
| `policy_sha256`, `gwd_skill_sha256` | Policy suplementar e bytes do entrypoint GWD usado; separados do registry v3/v4 |
| `installation` | `status=present|outdated|missing|undetermined`, versão resolvida, marketplace, install root, manifest ref, SKILL ref/SHA-256 e body SHA-256 |
| `compatibility` | `approved|incompatible|undetermined`, comparação com versão/digest admitidos na policy; instalação acima do mínimo não implica approved |
| `enablement` | `enabled|disabled|undetermined`, observation ref/digest, origem/configuração/projeto usados no probe; cache ou registro de instalação não prova enabled |
| `trust` | `ready|pending|undetermined`, referência da observação de startup; aprovação de hook não significa loaded |
| `loading` | `required|loaded|stale|unconfirmed`, native event/tool-call ref, hash dos bytes realmente entregues, scope binding, session/context generation e timestamp |
| `behavior` | `not_tested|conformant|nonconformant|unconfirmed`, refs dos prompts/respostas completos, cases/turn IDs, conteúdo exigido e revisão correlacionada |
| `application` | `active|suspended_by_user|out_of_scope|blocked`; suspensão/saída exige source ref da instrução explícita, não flag silenciosa de bypass |
| `suspension` | Null ou source ref/digest da instrução humana, session_identity/incarnation e escopo GWD vinculados; validada novamente após compactação, não herdada por outra sessão |
| `use_ready`, `work_ready`, `functional_verified` | Projeções distintas de aplicação ativa, admissão de trabalho e prova funcional; não são flags fornecidas pelo caller |
| `diagnostics` | Lista de código/campo/motivo/recuperação; não apagar evidência parcial ao falhar outro eixo |

Loader remove apenas o frontmatter inicial; registra hash dos bytes originais e do corpo UTF-8 entregue. A policy admite inicialmente versão 0.3.0/SKILL SHA-256 `3170b16ace00aecb0dd7feb54c0b5aa642e7502acda06ecd24fd89a11c7127e9`; o hash do corpo é derivado desses bytes, não um segundo texto autoral. Corpo vazio, truncado, encoding inválido, symlink ou instalação divergente não geram load request utilizável. O caminho externo ao projeto é permitido **somente** para leitura da instalação identificada pelo runtime, ancorada no cache/registro do componente; nunca vira grant de escrita.

`loading=loaded` requer um evento observado de leitura/injeção completa pela GWD na mesma sessão e geração de contexto, ligado ao digest da referência e ao escopo. Saída que só enumera a skill ou imprime seu hash não basta; texto do modelo dizendo que a carregou também não. O líder referencia o evento nativo efetivamente visto, e o adapter valida correlação/formato conforme [integrations.md](contracts/integrations.md). Não fabricar tool-call IDs quando o provider só oferece transcript: guardar o trecho integral observado e seu tipo de evidência, com limites explícitos.

`use_ready` exige instalação presente, compatibilidade approved, habilitação enabled, startup pronto, escopo GWD corrente, loaded corrente e aplicação active. `work_ready` exige os mesmos pré-requisitos de instalação/compatibilidade/habilitação/startup/escopo e **ou** use_ready **ou** application=suspended_by_user com instrução humana comprovada para a mesma sessão/incarnation e escopo. Suspensão dispensa apenas aplicação/carga corrente do estilo; não dispensa dependência, confiança, modelo/esforço ou qualquer gate do trabalho. Entradas/despachos usam work_ready. Out_of_scope/blocked não liberam trabalho GWD.

Isso permite a primeira resposta ativa com `behavior=not_tested`, sem pré-condição circular. `functional_verified` só é true com use_ready e amostra conformant válida para essa sessão/configuração/versão; suspensão não é prova positiva de FR-024, e amostras anteriores continuam históricas. O aceite de release agrega início e retomada de Codex/Claude, mais controles externos, em evidência do líder e revisão high independente.

Mudança de runtime, incarnation, geração de contexto, bytes de GWD/upstream/policy ou configuração relevante torna loading stale até nova observação; preserve o registro anterior. Compactação da mesma sessão conserva `suspended_by_user`: revalidar a fonte humana e pré-requisitos mantém work_ready=true com loading=stale, use_ready=false e functional_verified=false, sem recarregar/aplicar o corpo. Fonte ausente/divergente não fabrica suspensão válida. Reativação explícita exige carga corrente antes da próxima resposta ativa. `out_of_scope` encerra a aplicação local sem mudar plugin/configuração/Ponytail; nova sessão/incarnation GWD, inclusive especialista ou destino de continuidade, não herda suspensão e inicia pelo default ativo com carga própria. Uma configuração global preexistente pode impedir provar isolamento; registrar `STYLE-SCOPE-CONFLICT`, preservá-la e pedir resolução específica ao operador, sem apagar seus bytes.

Evidência de comportamento é artefato de coordenação do líder sob a reserva já existente. Respostas completas e observações ficam duráveis antes de cleanup; versão sanitizada para revisão não descarta os originais protegidos. Revisor julga dez regras e exceções aplicáveis, preservação do conteúdo e controles externos. Assert/regex pode ajudar a detectar truncamento, mas não promove `behavior` a conformant por si só. Esses registros são evidência estrutural auditável, sem prova criptográfica de obediência.

## Prévia visual e decisão humana

Manifest `grill-design-preview/v1` fixa feature/fase/DU, classificação, input digest, invocation ref de Impeccable, author activity, lista fechada de arquivos `path/media_type/sha256/size`, entrypoint HTML e capturas `viewport/state/path`. HTML é autocontido; nenhuma dependência remota entra no conteúdo aprovado. Alterar ou adicionar asset exige outro manifest. Validar signatures básicas HTML/PNG, referências locais e existência; avaliação estética não é inferida de assinatura.

`visual_decisions` armazena revisão técnica e decisão humana separadas. Decisão humana: `decision_id`, `preview_sha256`, `review_ref`, `actor_ref`, `decision=approved|rejected`, `source_ref`, `recorded_at`, `context_id`. Source é a interação humana observada que o líder persiste; comando/flag não fabrica aprovação. Texto “OK” sem vínculo inequívoco à preview apresentada não produz decisão válida.

Estados projetados: NOT_APPLICABLE, REQUIRED, PREVIEW_READY, REVIEWED, PENDING_APPROVAL, APPROVED, REJECTED ou STALE. NOT_APPLICABLE precisa classificação coerente das fontes; não pode ser selecionado por flag para ignorar frontend. APPROVED exige review técnica aprovada e decisão humana no mesmo digest corrente. Se o conteúdo mudar, a projeção vira STALE; o registro antigo é preservado.

## Declaração de arquivos e DAG

Task inclui id/fase/descrição/markers e, no contrato novo, Files e Result. Paths são normalizados e validados antes do agrupamento. Result é membro de Files, nunca capacidade implícita. Files vazio encaminha tarefa sem escrita fora do scheduler de workers; task de evidência reservada vai inteira ao líder. Scope da feature é limite adicional, não outra fonte que conceda escrita.

DAG `grill-gauntlet-execution-dag/v2` tem campos v1 `schema,feature,max_workers,nodes` e novos `tasks_contract`, `tasks_semantic_sha256`, `accepted_tasks`. Nodes conservam `id,depends_on,tier,parallel,files` e incluem `task_ids,result_files`. `result_files` é mapa task_id→path declarado. Todos os ids/paths únicos e correspondentes ao tasks parseado; task não pode desaparecer ou entrar em dois nodes. Report v2 identifica deferred_to_leader e read_only_tasks por task_id/fase/razão e conserva todas as fases com `phases[].task_ids`, inclusive sem workers. O mapa é conferido contra tasks parseado e fingerprint antes de uso; não basta o report declarar uma fase. `accepted_tasks` é mapa imutável de importação task_id→receipt/digest/contexto e commit integrado quando houve escrita, vazio na primeira execução. Na migração, somente resultados aceitos verificáveis entram nesse mapa; checkbox marcado sozinho não prova conclusão. Nodes contêm somente tasks restantes, sem workers fictícios TERMINAL; importações preservam a proveniência e são verificadas contra receipts/commits antes de declarar waves. A união de task_ids dos nodes, read_only, deferred e accepted deve cobrir o tasks inteiro sem sobreposição; aceitar uma activity não reescreve o DAG/report selado.

Ordem do suplemento: workers de cada fase convergem, depois suas tarefas read-only/deferred recebem aceite por activities, na ordem declarada; fase só dessas tarefas também constitui barreira. Antes de qualquer wave/worker/prepare/remediation/payload ou activity de task, o guard comum exige aceites positivos de todas as fases anteriores, e activity fora do scheduler exige workers da própria fase convergidos. Revalidar no CAS impede ultrapassar pendência/receipt stale. Fechamento de implement-parallel exige também as atividades da última fase; scheduler COMPLETE sozinho não fecha a macroetapa nem impede aceitar essas atividades fora do scheduler. Sem nenhum worker restante, partition devolve PARTITION-NO-WORKERS antes de admissão, sem DAG/receipt completo; suporte a ciclo novo inteiramente read-only/deferred não faz parte deste contrato e a classe worker-required permanece intacta.

Hash semântico cobre o texto de tasks com somente as posições de checkbox das tarefas normalizadas para `[ ]`; outros bytes, incluindo descrição, Files, Result e fase, continuam cobertos. Não usar replace global em exemplos/código. Reconciliar checkboxes não muda o DAG; alterar a tarefa exige nova revisão. DAG pin continua sobre bytes exatos do DAG. V1 selado permanece legível sem ser regenerado.

## Transações, locks e compatibilidade

Novo evento de orquestração possui `schema=grill-orchestration-event/v1`, `event`, `work_id`, `context_id`, `operation_id`, `input_sha256`, `output_sha256`, `receipt_sha256`; receipt fixa os mesmos ids/hashes e categoria runtime. `_transition_fields`, `_candidate_transition`, validação e recovery selecionam a união pelo schema, nunca pela presença acidental de wave. Formato Gauntlet v1 existente permanece idêntico; não cunhar wave/lease fictícios para atividade anterior a partition.

Ordem de locks: lock do work item do CLI → lock do Store em transações curtas; se uma operação legada também exige config lock, obtê-lo antes do lock do item conforme a ordem existente e nunca tentar adquiri-lo dentro da transação Store. Não manter lock global durante chamada de provider, Git lento, geração de artefato ou decisão humana. Após I/O reler contexto/epoch/inputs em CAS; mudança invalida a tentativa.

Checkpoint coordenado: (1) validar e persistir intenção com bytes/digests before/after do state e próximo checkpoint; (2) escrever state por fronteira segura/rename atômico; (3) finalizar Store+receipt+journal e mover checkpoint_head. Nenhuma nova atividade enquanto a intenção estiver pendente. Recovery sob os mesmos locks aceita state igual a before ou after e executa somente o trecho faltante; terceiro estado é `CONTINUITY-STATE-DIVERGENCE`. Receipts/conteúdo são escritos em paths imutáveis antes de referenciados no commit; órfão não comprometido não vira resultado aceito.

Store v1 com novo bloco é leitura compatível no binário novo, sem migração silenciosa. Escrita por binário antigo após adoção falha em chaves desconhecidas. Não editar activation/config/schema legado para forçar essa compatibilidade. Restore de backup é recuperação humana fora do fluxo normal, nunca uma flag de downgrade que apaga as provas novas.

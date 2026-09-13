# Contrato CLI: agent-orchestration/v1

Superfície prevista para implementação; comandos novos abaixo ainda não existem no baseline 5.4.1. Executável continua `python3 plugin/skills/grill-with-docs/scripts/grill_workspace.py`. ROOT é o Git root real e ID é o work_id registrado; contratos usam metavariáveis de sintaxe, não valores a gravar em receipts.

Esse caminho source descreve o CLI **candidato**. O líder que constrói a própria 6.0.0 opera a campanha histórica pelo CLI absoluto do bundle 5.4.1 preservado e validado, conforme [quickstart](../quickstart.md); depois da primeira edição, não usar o source candidato sobre o estado histórico nem exigir adoção no meio do ciclo. Os verbos novos são validados em estado isolado até o rollout explícito.

## Fronteira comum

Todos os verbos do trabalho sob contrato novo exigem `--work-id ID` e contexto de sessão comprovado: `--context-id CTX --epoch N --session-ref REF`. REF aponta a uma observação segura emitida pelo adapter e relida/correlacionada; não é uma string livre que promove caller a líder. Campos podem vir de contexto nativo explicitamente vinculado pelo harness, mas não de default salvo em integration.json. Core verifica contexto/epoch/owner/identidade no início e na transação; parâmetros sozinhos não são prova.

`--runtime codex|claude` permanece explícito no início, adoção e retomada. Atividades e comandos subsequentes usam o contexto vigente; runtime informado diferente sem operação de continuidade é erro. Startup e resume retornam `coordinator_recommendation` Sol ou Opus e `active_model_changed=false`; nunca editam configuração do modelo.

O contexto inclui `presentation` para i-have-adhd local. Entrada de trabalho e despacho exigem `work_ready`, conforme [data-model.md](../data-model.md): pré-requisitos obrigatórios mais carga/aplicação ativa (`use_ready`) ou suspensão humana comprovada da mesma sessão. `use_ready` informa estilo ativo; `functional_verified` exige amostra live ativa e não é pré-condição circular da primeira resposta. Suspensão não dispensa instalação/habilitação nem outros gates. Read-only de diagnóstico, bootstrap/instalação autorizada e cleanup de trabalho já encerrado continuam disponíveis se a apresentação falhar; não reter recurso elegível nem repetir resultado aceito por ausência do estilo.

Preview é o default de migração/adoção/decisão com side effect administrativo. Apply usa `--apply --expected-sha256 HASH`; hash cobre inputs, target, contexto e revisão observados no preview. Uma mudança entre preview/apply exige novo preview. Fechamento automático já faz parte do contrato adotado: não pede aprovação de novo por recurso, mas sempre revalida elegibilidade.

Saída JSON com `verdict`, `code`, `work_id`, `context_id`, `epoch`, `operation_id`, `details` pertinentes. Erros não contêm segredo de provider/capability; path/handle só quando necessários para identificar o recurso. Exit 0 = operação/preview comprovados; EXIT_BLOCKED=2 exige payload BLOCKED/código nominal. Erro de parsing não é gate satisfeito só porque também retorna 2. Preservação/unknown de cleanup retornam estado detalhado, não CLEANED.

Não aceitar shell command livre, PID escolhido pelo usuário, path fora do projeto ou caminho de transcript inferido. Hook/status não invocam mutações nem consultam rede.

## Preflight e carga local da GWD

```text
preflight ROOT --runtime codex|claude [--session-ref REF]
    [--allow-install] [--skip-backlog]

init ROOT --runtime codex|claude --type feature|fix|hotfix --slug SLUG
    --session-ref REF [opções existentes]
```

Preflight é pré-ciclo: não exige work_id/context/epoch ainda inexistentes e não cria Store/receipt de apresentação. Mantém as verificações existentes de workflow/backlog; o novo diagnóstico de estilo não autoriza mutá-los. `session-ref` é o mesmo contrato de observação do adapter usado nos demais verbos, agora com os campos de apresentação. Fonte pode ser resultado nativo observado ou registro persistido pelo líder em path seguro; nunca aceitar uma string que declara enabled/loaded sem origem correlacionada.

Saída acrescenta `presentation` com schema de [data-model.md](../data-model.md) e `presentation.load_request` quando falta carregar para aplicação ativa: loader, componente, versão efetiva, skill_ref, skill_sha256, body_sha256, policy_sha256 e limite de escopo. O path de leitura é a instalação regular aprovada identificada pelo runtime; é exceção restrita de leitura fora do projeto, não autorização de escrita ou execução desse arquivo. Preflight não executa node/hook, não chama a skill upstream nem consulta marketplace para carregar suas regras.

Sem sessão/observação, reportar fatos em disco e eixos desconhecidos, com código nominal e payload BLOCKED; não devolver estilo functional. Quando instalação/habilitação estão confirmadas e só falta leitura para apresentação ativa, retornar `STYLE-LOAD-UNCONFIRMED`, exit 2, e load_request íntegro. A skill GWD trata esse caso como próximo passo de bootstrap: lê os bytes completos pela ferramenta da própria sessão, coleta nova observation vinculada ao pedido e repete a verificação com REF atualizado. Isso é recuperação explícita, não bypass da recusa nem invocação manual de i-have-adhd pelo usuário.

Depois da carga comprovada com aplicação ativa: `presentation.use_ready=true`, `work_ready=true`, `loading=loaded`, `behavior=not_tested` e `functional_verified=false`; o veredito agregado só fica OK se os outros pré-requisitos também passarem. `init`/adopt/resume/step-enter persistem a observação corrente sob o contexto existente. `gauntlet-step-enter` devolve `invocation_context.presentation` com fonte/hash/escopo para a skill canônica; o resultado não afirma invocação nem comportamento. Especialista recebe esse conteúdo apenas após modelo/esforço verificados; sua sessão nova inicia ativa com carga própria, e o aceite exige work_ready da própria sessão, sem herdar suspensão do líder nem conceder escrita de evidência.

`--allow-install` mantém instalação delegada: adicionar i-have-adhd ao manifesto não autoriza editar arquivos globais de instrução, criar flag always-on, alterar metadados upstream ou habilitar plugin deliberadamente desabilitado. Nesse caso, diagnóstico aponta controle nativo de habilitação e requer autorização específica ou já existente. O componente é obrigatório no fluxo novo independentemente de `--require-dependencies`; esta ampliação não torna silenciosamente bloqueantes as demais dependências antes apenas consultivas. `GRILL_SKIP_DEPENDENCIES=1` continua SKIPPED e não libera esse gate.

O detector de presença usa disco; habilitação vem de observation da configuração efetiva do runtime, como definido em [integrations.md](integrations.md). Não promover o maior cache a versão efetiva, nem inferir enabled da instalação. `status` só projeta observações existentes/frescor e não executa listagens ou reads de sessão para inventar evidência nova. Retomada ou compactação torna a carga anterior stale até recarga. Com suspensão explícita validada na mesma sessão, não emitir pedido de recarga nem recusar entrada/despacho por loading stale: reportar application=suspended_by_user, work_ready=true, use_ready=false e functional_verified=false, desde que os demais pré-requisitos permaneçam comprovados. Pedido humano de saída produz out_of_scope, sem liberar trabalho GWD; nova sessão/incarnation volta ao default ativo. A fonte humana é revalidada, não substituída por flag CLI permanente de opt-out.

## Adoção e contexto

```text
gauntlet-orchestration-adopt ROOT --work-id ID --runtime codex|claude
    --session-ref REF [--scope-file PATH ...]
    [--apply --expected-sha256 HASH]
```

Preview mostra contrato/policy hash, branch/worktree, versão mínima do novo binário, snapshot de origem, ativação/campanha, outputs aceitos, inventário de recursos, escopo e limitações de rollback. Apply valida fontes e adiciona o bloco/época inicial; não reescreve gauntlet.yaml, WORK-ITEM, workflow, Constituição, catálogo ou receipts. Resultado ORCHESTRATION-ADOPTED ou REUSED idempotente.

Novo `init` cria esse vínculo como parte de seu fluxo, após pré-condições atuais. Legacy reading/status/diagnosis não exigem adoção. Continuar execução no binário novo sem vínculo retorna ORCHESTRATION-MIGRATION-REQUIRED. Trabalho COMPLETE também pode ser adotado para inventário/limpeza e uso posterior, sem reabrir etapas. Adoção de trabalho pendente exige checkpoint coerente e prova de quiescência; não supre sessões antigas por suposição.

`--scope-file` repete uma vez por arquivo. Durante plan o escopo é o conjunto autorizado de outputs de planejamento; após tasks revisadas, uma nova revisão explícita da adoção de escopo inclui Files/Results do plano de execução. `--scope-file` não amplia grants existentes nem reescreve a origem: grava revisão de escopo com evidência da autorização/revisão. IDs/result paths ainda não conhecidos no init não são substituídos por globs.

## Gate de entrada e atividades

```text
gauntlet-step-enter ROOT --work-id ID --context-id CTX --epoch N
    --session-ref REF --step STEP
```

Operação idempotente de admissão: valida sequência, contexto, classificação, políticas, work_ready e pré-condições; persiste step intent e devolve `invocation_context` da skill canônica. Não executa semântica da skill nem a atesta. Em tasks verifica aprovação visual corrente antes de liberar contexto de invocação. `checkpoint --state in-progress` aplica o mesmo guard; `attest` e complete rechecando não aceitam um bypass. Recarga ou suspensão do estilo não reexecuta etapa aceita nem muda hash de campanha.

```text
gauntlet-activity ROOT --work-id ID --context-id CTX --epoch N --session-ref REF
    --activity-id A [--step STEP | --scope interview] --kind author|reviewer|deterministic_check
    --phase prepare|dispatch|accept
    --input-manifest PATH
    [--author-activity ID ...] [--files PATH ...]
    [--observation PATH] [--result PATH] [--diagnostic PATH]
```

- **prepare**: fixa inputs, papel e pares derivados da policy; verifica capabilities, reserva identidade/activity e produz solicitação de bootstrap neutro. Não libera payload técnico, grant de escrita ou atestação.
- **dispatch**: exige observation real da mesma sessão, modelo/esforço efetivos comprovados e inputs imutáveis; reviewer é distinto dos autores. Grava VERIFIED e intenção de envio, liberando somente o brief que corresponde ao digest/fence. Adapter/skill efetua envio pela superfície conhecida e registra observação correlacionada. Resposta perdida conserva intenção e exige read-back, nunca segundo envio cego.
- **accept**: líder fornece refs de output/diagnóstico, adapter confirma término e identidade/modelo/esforço; valida hashes/ownership. Persiste resultado aceito ou falha diagnosticada, registra obrigação de cleanup e tenta encerrar recursos elegíveis. Arquivo produzido sem observation/tentativa aceita não fecha macroetapa.

Atividade de entrevista usa --scope interview e step_id null; author/reviewer seguem a mesma política antes de PLAN_ONLY_STOP, sem invocar macroetapa extra. Atividade de ciclo usa --step e exige ativação válida.

Deterministic_check não cria sessão nem exige modelo; recebe command/check identity do teste permitido e resultado reproduzível, sem qualificar como revisão. `--files` é grant do autor para artefatos; reviewer exige lista vazia. Worker de implementação usa os verbos existentes do scheduler, não esse caminho para escapar do binding não-frontier.

Para task read-only/deferred, o input_manifest inclui `task_binding={task_id, phase, tasks_semantic_sha256, dag_content_sha256}`; phase é a fase de tasks, distinta de `--phase prepare|dispatch|accept`. Core confere esse vínculo no parse/DAG/report e o grava na atividade/receipt. Dispatch/accept exigem fases anteriores satisfeitas e workers da própria fase convergidos; resultado de julgamento exige o papel correto, e decisão humana exigida precisa de source observada. Aceitar diagnóstico ou review CHANGES_REQUIRED não conclui a task. O líder persiste retorno read-only/bookkeeping deferred pelos mesmos receipts, sem Result, worker ou novo comando de scheduler fictício.

## Cleanup

```text
gauntlet-cleanup ROOT --work-id ID --context-id CTX --epoch N --session-ref REF
    [--run-id RUN [--worker-id WORKER] | --activity-id ACTIVITY]
```

Sem selector, processa somente recursos registrados do work item e obrigações pendentes, inclusive especialistas. Selector inválido/misto bloqueia. Forma legada run+worker permanece reconhecida para diagnóstico e cleanup protegido de recursos antigos, mas não pode declarar sessão encerrada se ela nunca foi identificada. Cleanup pode ler run COMPLETE/BLOCKED sem autorizar preparação nela.

Resposta inclui `resources[]` com resource_id/kind/identity, elegibilidade, state, reason(s), intent/observation refs e resultado individual. Aggregate CLEANED somente se todos os recursos-alvo removíveis/encerráveis foram confirmados; PRESERVED se há retenção conhecida; UNKNOWN se há observação insuficiente. ALREADY_ABSENT só com intenção anterior e identidade correlacionada. Não ocultar branch preservada quando worktree saiu.

O mesmo serviço é chamado automaticamente por accept/worker terminal/wave terminal/converge/checkpoint/prepare-switch. O fechamento persiste sua obrigação antes da tentativa. `checkpoint` pode responder `step_state=complete, cleanup_state=UNKNOWN`, código STEP-ACCEPTED-CLEANUP-PENDING e exit 2: resultado já está aceito e não deve ser reexecutado. Retry drena cleanup, não repete a etapa. Retenção legítima por trabalho pendente é reportada e só bloqueia a ação seguinte quando viola sua pré-condição; sessão unknown sempre bloqueia troca e concorrência nova.

## Preparação e retomada entre CLIs

```text
gauntlet-prepare-switch ROOT --work-id ID --context-id CTX --epoch N
    --session-ref REF --to-runtime codex|claude

gauntlet-resume ROOT --work-id ID --runtime codex|claude
    --checkpoint CHECKPOINT_ID --session-ref TARGET_REF
    [--apply --expected-sha256 HASH]
```

Prepare-switch é idempotente para origem/destino/checkpoint; cerca novos despachos, fecha obrigações elegíveis e persiste checkpoint. Se workers/turnos continuam ativos, retorna CONTINUITY-ACTIVE-WORK e a operação permanece QUIESCING. Não cancela workers para atender à troca. Depois de encerrada/estacionada a atividade da origem, o destino confirma a identidade e inatividade dela; ausência de acesso produz CONTINUITY-QUIESCENCE-UNPROVEN.

Resume sem apply mostra checkpoint escolhido, accepted outputs, trecho interrompido, operações a reconciliar, recursos retidos, nova ativação/campanha, recomendação e estado de apresentação no destino. Apply relê tudo, prova mesma worktree, quiescência e carga do estilo na sessão destino e adquire época em CAS. Cria recibo de continuidade e campanha sucessora, mantendo histórico/admissions/DAGs. Não roda skill, worker ou efeito automaticamente; devolve next-step e tentativas autorizadas ainda não aceitas. Loaded/behavior do checkpoint de origem são históricos, nunca prova herdada do destino.

`gauntlet-resume` legado com --run-id continua legível como recovery de scheduler, mas não troca runtime nem bypassa migração. `recovery_count` do scheduler não é contador de epochs. Parametrização ambígua entre recovery e continuidade bloqueia com INVALID-ARGUMENTS.

## Preview e decisão humana

```text
gauntlet-preview ROOT --work-id ID --context-id CTX --epoch N --session-ref REF
    --manifest PATH --author-activity A --review-activity R

gauntlet-preview-decide ROOT --work-id ID --context-id CTX --epoch N --session-ref REF
    --manifest PATH --decision approved|rejected --human-evidence PATH
    [--apply --expected-sha256 HASH]
```

Preview valida manifestação/capturas/bytes/classificação e atividades, registra PREVIEW_READY/REVIEWED; não aprova. Decide lê interação humana previamente observada, vinculada à preview apresentada, valida digest corrente e registra decisão. Não cunha aprovação só porque --decision approved foi passado. Human-evidence é artefato de coordenação escrito pelo líder a partir da resposta humana, não pelo designer.

No-frontend não usa esses verbos para burlar o gate; status deriva NOT_APPLICABLE das fontes coerentes. Preview alterada/rejeitada/pendente bloqueia tasks. Aprovação velha nunca autoriza novo manifest, mesmo quando o filename é igual.

## Tasks, DAG e migração

```text
task-files-migrate ROOT --work-id ID --context-id CTX --epoch N --session-ref REF
    --feature FEATURE --proposal PATH --author-activity A --review-activity R
    [--apply --expected-sha256 HASH]

partition-emit ROOT --work-id ID --context-id CTX --epoch N --session-ref REF
    --feature FEATURE [--groups N] [--revision N]
    [--apply --expected-sha256 HASH]
```

Proposal é tasks completo com declarações revisadas; core não adivinha Files. Migração mantém identidade/checkboxes/resultados e mostra diff. Partition novo exige tasks contract, escopo aprovado, gate de tasks e fingerprint corrente. `--revision 2` seleciona explicitamente arquivos `.r2.json`; nunca escolhe um nome novo silenciosamente para contornar pin. Apply sobre path selado com bytes diferentes retorna DAG-SEALED, inclusive run COMPLETE. Mesmos bytes retornam REUSED sem reescrita.

Report v2 mantém todas as fases/tasks, inclusive read_only/deferred. Antes de admissão de run, conjunto sem tarefa despachável retorna BLOCKED/`PARTITION-NO-WORKERS`, exit 2, listas completas e nenhum DAG; não prosseguir a gauntlet-run, DAG-VALID ou checkpoint completo. Corrigir escopo real em tasks, sem worker fictício; se não há trabalho restante, conservar aceites históricos sem reabrir ciclo. O contrato não promete conclusão nova de implement-parallel com zero workers.

`gauntlet-dag-validate`, wave/worker-declare, prepare legado, partition-brief, tasks-reconcile e converge aceitam v2 por schema explícito. Worker-declare continua `--files` repetido por arquivo e deve coincidir com node.files; não aceitar vírgulas como lista. V1 selado mantém interpretação histórica somente na execução do bundle antigo; o novo binário não inicia nova atividade legada sem adoção/migração. Reconcile valida Results e não marca task de outra tentativa.

Wave/worker-declare, prepare legado/remediation e liberação do payload aplicam o mesmo guard de fases de [task-files.md](task-files.md), no início e no commit/fence: nenhuma task de fase anterior pode ficar pendente, inclusive read-only/deferred. Recusa `TASK-PHASE-PENDING` lista IDs/fases e não cria grant nem envia trabalho. Reconcile aceita também receipts positivos dessas atividades, por task/fase/revisão; retry/continuidade conserva os aceites sem reexecutar. Attest/checkpoint complete de implement-parallel exige todas as tasks fora do scheduler satisfeitas, inclusive a última fase, além da prova de workers reais cobrindo o DAG exigida pela classe worker-required congelada; run COMPLETE não substitui esse guard. O suplemento fornece à skill pinada a ordem por fase que substitui o deferred final legado.

## Recusas obrigatórias

| Família | Códigos principais |
|---|---|
| Contrato/autoridade | ORCHESTRATION-MIGRATION-REQUIRED, ORCHESTRATION-POLICY-STALE, LEADER-AUTHORITY-UNPROVEN, CONTEXT-FENCED |
| Modelo/papel | SPECIALIST-CAPABILITY-UNPROVEN, SPECIALIST-MODEL-DIVERGENT, SPECIALIST-EFFORT-DIVERGENT, REVIEWER-NOT-INDEPENDENT, ACTIVITY-REQUIRED |
| Sessão/cleanup | SESSION-CLOSE-UNPROVEN, RESOURCE-IDENTITY-DIVERGENT, WORKSPACE-PRESERVED, CLEANUP-UNKNOWN, STEP-ACCEPTED-CLEANUP-PENDING |
| Continuidade | CONTINUITY-CHECKPOINT-MISSING, CONTINUITY-STATE-DIVERGENCE, CONTINUITY-ACTIVE-WORK, CONTINUITY-QUIESCENCE-UNPROVEN, CONTINUITY-CAS-CONFLICT, EFFECT-OUTCOME-UNKNOWN |
| Visual | FRONTEND-CLASSIFICATION-DIVERGENT, IMPECCABLE-CAPABILITY-UNPROVEN, PREVIEW-MISSING, PREVIEW-NOT-VISUAL, PREVIEW-APPROVAL-REQUIRED, PREVIEW-STALE |
| Tasks | Códigos de [task-files.md](task-files.md), sem grant parcial |
| Apresentação | STYLE-DEPENDENCY-MISSING, STYLE-DEPENDENCY-OUTDATED, STYLE-DEPENDENCY-UNDETERMINED, STYLE-DISABLED, STYLE-ENABLEMENT-UNPROVEN, STYLE-CONTENT-INCOMPATIBLE, STYLE-TRUST-PENDING, STYLE-LOAD-UNCONFIRMED, STYLE-LOAD-STALE, STYLE-SCOPE-CONFLICT, STYLE-BEHAVIOR-UNPROVEN, STYLE-BEHAVIOR-NONCONFORMANT |

Código é acompanhado do dado que falta/diverge e ação de recuperação concreta. Nenhum gera receipt COMPLETED ou libera payload dependente. Verificação de integridade determinística pode continuar mesmo quando a capacidade de runtime está bloqueada. STYLE-BEHAVIOR-UNPROVEN/NONCONFORMANT bloqueiam aceite funcional de FR-024, sem impedir gerar/avaliar a amostra após carga válida. Recusar casos inválidos não substitui os casos positivos nos dois CLIs.

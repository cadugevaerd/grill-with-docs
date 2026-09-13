# Research: decisões técnicas da spec 030

Data: 2026-09-13. Escopo: FASE-001/DU-001 do work item `feature-new-subagents-unified-69f619a1a4774d598e4a46c77396f0fa`, oito requisitos FR-001..024/SC-001..008. As escolhas do usuário nos ADR-0001..0005 estão fechadas; esta pesquisa resolve mecanismos, sem reabrir modelos, independência, formato explícito, aprovação visual ou alcance local do estilo.

## Fontes locais lidas

Paths abaixo são relativos à raiz do repositório; símbolos permitem reencontrar a evidência quando linhas mudarem.

| Fonte | Fato relevante observado |
|---|---|
| [spec.md](spec.md), [CLAUDE.md](../../CLAUDE.md), [Constituição](../../.specify/memory/constitution.md), [WORKFLOW.md](../../WORKFLOW.md) | Requisitos, stdlib/offline, onze etapas, ownership, imutabilidade v3/v4, oito pontos de versão e release |
| [PLAN-CONTEXT](../../.grill/work-items/feature-new-subagents-unified-69f619a1a4774d598e4a46c77396f0fa/PLAN-CONTEXT.md) e [ADRs](../../.grill/work-items/feature-new-subagents-unified-69f619a1a4774d598e4a46c77396f0fa/docs/adr/ADR-0001.md) | Decisões aceitas e reprodução original; ADR-0001..0005 lidos integralmente |
| [STACK-I-HAVE-ADHD](../../.grill/work-items/feature-new-subagents-unified-69f619a1a4774d598e4a46c77396f0fa/STACK-I-HAVE-ADHD.md), cópias instaladas 0.3.0 de i-have-adhd nos dois caches | Instalação e hashes conferidos; hook condicionado a flag, regras completas e política de invocação explícita; nenhum deles prova default local |
| [ensure_dependencies.py](../../plugin/skills/grill-with-docs/scripts/ensure_dependencies.py), `plugin_registry_state`, `Toolchain`, `preflight`; `ensure_workflow.py`, `render_hook_output` | Detector harness-plugin já é genérico e lê disco sem subprocesso; hook tem orçamento limitado, logo não receberá o corpo inteiro do estilo |
| [gauntlet_runs.py](../../plugin/skills/grill-with-docs/scripts/grill_core/gauntlet_runs.py), `_run_for_worker`, `cleanup_worker`, `_workspace_git_state`, `_mint_worker_converged` | COMPLETE/BLOCKED recusados no guard compartilhado; elegibilidade nasce false e converge só marca converged; remove somente worktree; identidade compara HEAD ao base |
| Mesmo módulo, `_node_ready`, `_converged_lineage_head`, `_wave_would_complete`, `_close_convergence_chain` | Sucesso depende de TERMINAL; CLEANED pode deixar de satisfazer dependências; fechamento/convergência são transações separadas |
| Mesmo módulo, `declare_worker`, `prepare_worker`, `_strict_scopes`, `_dag_scope_violation` | Grants fechados, isolamento, anti-frontier e reservas de evidência já existem; caminho legado de prepare também exige proteção |
| [partition.py](../../plugin/skills/grill-with-docs/scripts/grill_core/partition.py), `extract_files`, `parse_tasks`, `_conflict_groups`, `partition` | Heurística exige barra, infere da prosa, cria sidecar implicitamente e dá escopo feature-wide a tarefa unmapped |
| [grill_workspace.py](../../plugin/skills/grill-with-docs/scripts/grill_workspace.py), `partition_emit_command`, `gauntlet_partition_brief_command`, `gauntlet_tasks_reconcile_command` | Apply sobrescreve arquivos; brief procura sidecar pelo sufixo do node; reconcile aceita completed dos sidecars sem vínculo completo de autoria/task |
| Mesmo CLI, `gauntlet_run_admission`, `gauntlet_resume_command`, `attest_command`, `verify_checkpoint_attestation`, `checkpoint_command`, `phase_turn_command` | Runtime vem da ativação; resume atual só registra recovery; campanha é herdada e checkpoint aceita cadeia estrita; state é escrito sob lock do item |
| [gauntlet.py](../../plugin/skills/grill-with-docs/scripts/grill_core/gauntlet.py), `current_activation`, `activate`, `_activation_is_stale`, `require_activation` | Ativação fecha runtime/catalog/inputs e é imutável; seleção é por workflow version; alterar runtime diretamente conflita |
| [attestation.py](../../plugin/skills/grill-with-docs/scripts/grill_core/attestation.py), `_checkpoint_campaign`, `judge_checkpoint_attestation`, `mint_chain` | Sete campos de campanha incluem runtime/adapter; predecessor é comparado exatamente; runtime_handle pode ser None; cadeia não prova modelo |
| [store.py](../../plugin/skills/grill-with-docs/scripts/grill_core/store.py), `transact_with_event`, `_candidate_transition`, `_validate_gauntlet_state_transitions` | WAL recuperável existente; evento atual exige run/wave; admission é imutável; esquemas têm chaves fechadas; generic CAS não altera Gauntlet |
| [tier_models.py](../../plugin/skills/grill-with-docs/scripts/grill_core/tier_models.py), [binding](../../plugin/skills/grill-with-docs/assets/workflow-tier-models.json) | Classes leader/worker, sem effort; large Sol/Opus e worker frontier recusado |
| [workflow_versions.py](../../plugin/skills/grill-with-docs/scripts/grill_core/workflow_versions.py), [step_skills.py](../../plugin/skills/grill-with-docs/scripts/grill_core/step_skills.py) | Tabelas literais congeladas; resolução fixa registry/catalog/trusted bytes; não admite trocar catálogo arbitrariamente |
| [manifest local](../../plugin/skills/grill-with-docs/assets/grill-local-skills.manifest.json), [validador](../../tests/validate_tier_model_binding_contract.py) | Hashes reais das duas skills canônicas e do agent são checados; editar skill e manter catálogo não é rollout fiel |
| [tasks template](../../.specify/templates/tasks-template.md), [speckit-tasks](../../.agents/skills/speckit-tasks/SKILL.md) | Template pede paths na descrição; skill aceita argumentos explícitos e lê contracts; não existe campo Files atual |
| [grill-partition](../../plugin/skills/grill-partition/SKILL.md), [grill-implement-parallel](../../plugin/skills/grill-implement-parallel/SKILL.md) | Líder invoca comandos, workers recebem brief; receita legada usa sidecar por node e fallback unmapped |
| [audit_decisions.py](../../plugin/skills/grill-with-docs/scripts/audit_decisions.py), `DEVELOPMENT_TYPES` e validação do handoff/PLAN-CONTEXT | frontend e platform-devops já são categorias; DU e fase precisam concordar |
| [validate_distribution.py](../../tests/validate_distribution.py), [run_validators.py](../../tests/run_validators.py) | Oito pontos fixados; glob integra novo validador sem editar runner |

## D1 — Cleanup é lifecycle de recurso, não de resultado

**Decisão**: separar estado do recurso do resultado do worker; usar elegibilidade derivada e transações de intenção/observação por recurso. Aproveitar helpers Git e cleanup existentes, corrigindo o guard compartilhado e a identidade.

**Razão**: corrigir somente a recusa de COMPLETE deixa `cleanup_eligible=false`; trocar somente a flag deixa HEAD-base divergente; levar worker a CLEANED cedo pode quebrar a prontidão da wave seguinte. O resultado aceito tem consumidores além do cleanup. Encerramento de sessão e exclusão de branch nem existem no caminho atual.

**Alternativas rejeitadas**: forçar flags; remover por prefixo; confiar no estado TERMINAL como prova de processo encerrado; usar branch -D; considerar árvore limpa sem arquivos ignorados. Todas ocultam pendência ou removem sem identidade suficiente.

**Mecanismo**: três recursos por identidade, com sessão opcionalmente única para read-only. Persistir resultado/diagnóstico fora do recurso; sessão terminada e encerrada por adapter; Git exige HEAD terminal integrado e estado limpo, incluindo conteúdo ignorado. Read-back confirma cada remoção. Recursos com falha ou unknown ficam no checkpoint. Worktree e branch têm resultados independentes; o commit-base permanece proveniência histórica.

## D2 — Continuidade por época e ponte de campanhas

**Decisão**: manter ativação/admission/campanha de origem imutáveis e registrar contexto sucessor no Store. Resolver ativação corrente por um helper comum; validar destino pelo mesmo `current_activation`. Uma ponte auditável transporta referências a outputs aceitos para a campanha sucessora, não seus autores ou runtime.

**Razão**: `gauntlet.activate` recusa runtime diferente; `attest` recusa ACTIVATION-RUNTIME-DIVERGENT; judge compara sete campos. Relaxar comparação de runtime ou apenas adicionar `--runtime` a resume aceita recibo no contexto errado. Também não é correto criar run nova e reexecutar os passos aceitos.

**Alternativas rejeitadas**: mutar gauntlet.yaml; apagar campanha; copiar memória privada; transferir workers ativos; resetar remediation; reatestar tudo; interpretar expiração como morte.

**Mecanismo**: checkpoint committed, suspensão do fence de origem, observações exatas de quiescência, cleanup, proposta de destino e CAS de época. O contexto successor guarda campaign antiga/nova e o checkpoint de origem; o primeiro novo resultado valida predecessor contra essa ponte; outputs antigos continuam referindo receipts antigos. Admission de scheduler e DAG não mudam. Criar `recovery_generation_id` distinto sem alterar plan_revision por mera troca de CLI.

## D3 — Persistência e efeitos interrompidos

**Decisão**: ampliar a união estrita de `transact_with_event` para eventos de orquestração sem wave, mantendo o formato Gauntlet antigo; usar seu WAL para o novo bloco. Coordenar a projeção state.json por intenção que fixa bytes before/after e uma operação idempotente.

**Razão**: especialistas de plan aparecem antes de existir uma wave e não devem receber wave fictícia. Um arquivo JSON paralelo sem lock e journal permite duas retomadas. Store e state não são um único rename; a janela precisa ser representada e testada.

**Alternativas rejeitadas**: adicionar chaves desconhecidas aos eventos antigos; daemon/DB novo; somente timeout; alegar exactly-once porque um comando retorna 0.

**Mecanismo**: guard de work item antes da operação, lock de Store só para transação curta, intenção durável antes de I/O e read-back depois. Recovery compara a projeção com before/after e só avança quando coincidir; terceiro estado bloqueia. Aceitação depende do commit final, nunca de artefato apenas produzido. Efeito externo sem prova da aplicação permanece UNKNOWN; não duplicar merge/push/release pela retomada.

## D4 — Especialistas com admissão anterior ao trabalho

**Decisão**: política independente do binding dos implementadores; autor xhigh e revisor high em identidades distintas, obrigatórios por atividade. Abrir bootstrap neutro, validar observação efetiva, depois liberar o payload técnico. O líder mantém invocação e evidência.

**Razão**: nome na configuração não prova aplicação. O runtime pode aplicar defaults, arquivo de agent ou fallback; um check depois de enviar todo o problema chega tarde. O mesmo agente em outra mensagem continua sendo o autor.

**Alternativas rejeitadas**: trocar o chat principal; usar o líder como fallback; tratar review final como única revisão; usar teste determinístico como aprovação; permitir frontier para classe worker inteira.

**Fontes oficiais atuais**: Codex documenta configuração de subagentes e precedência de model/effort, inclusive overrides de arquivos de agent; também diferencia concluir trabalho e fechar thread. Isso orienta validar a observação do runtime, não apenas o argumento solicitado. [OpenAI — Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents).

Claude documenta esforço por subagente, disponibilidade de níveis dependente do modelo e substituições de modelo; a tela de tarefas pode mostrar modelo e esforço. O alias `fable` é documentado e high/xhigh são níveis disponíveis para a família, mas alias/conta/provider e fallback exigem observação por tentativa. Não transformar essa documentação em prova local de lançamento. [Claude — Subagents](https://code.claude.com/docs/en/subagents), [Claude — Model configuration](https://code.claude.com/docs/en/model-config).

**Evidência local de Orca**: `orca skills get orchestration`, referências `coordinator-loop.md` e `recovery-and-cleanup.md`, `worker-start --help` e `worker-show --dispatch ctx_f11a3c3e87c7 --json` foram lidos. O último mostrou `worker.startOptions.launch.requested/effective` com Codex, `gpt-6-astra`, `xhigh`, e uma `processIncarnation` ligada ao terminal desta dispatch; a projeção também mostrou provider model. É evidência de lançamento e identidade dessa tentativa, não prova criptográfica de inferência.

**Prova adicional do líder nesta revisão**: [sondagem Claude high](../../.grill/work-items/feature-new-subagents-unified-69f619a1a4774d598e4a46c77396f0fa/claude-fable-high-probe.json) e [sondagem Claude xhigh](../../.grill/work-items/feature-new-subagents-unified-69f619a1a4774d598e4a46c77396f0fa/claude-fable-xhigh-probe.json), com observations correspondentes, registram `fable/high` e `fable/xhigh`, requested=effective e turnos reais. O contexto reportou Fable 5.1; effort não é observável pelo próprio worker. A sessão high foi **retida por user_takeover**, processAction none; a xhigh teve release/closed_agent_terminal confirmado. Não apresentar a primeira como limpa nem o autorrelato como prova independente de backend. Isso fornece caminho local positivo de lançamento nos dois esforços e fechamento de uma sessão Claude; não comprova apresentação i-have-adhd.

**Limite explícito**: a superfície nativa de colaboração disponível nesta sessão permite spawn/interrupt, mas não expõe um receipt portátil que comprove fechamento definitivo e esforço efetivo por filho; documentação geral não preenche esse campo. Adapters nativos só liberam trabalho quando a versão instalada fornece os fatos exigidos. Orca oferece o caminho observável já demonstrado, opcional e selecionado explicitamente; não é downgrade nem dependência nova do bundle. Os testes de entrega devem percorrer o caminho positivo dos dois runtimes e as recusas de superfícies incompletas, sem declarar a feature entregue apenas porque soube bloquear.

## D5 — Encerramento de sessão pertence ao seu proprietário

**Decisão**: adapter normaliza identidade e confirma fechamento, sem descobrir processos por nomes. Orca usa worker-release após settlement aceito, com read-back da mesma dispatch/incarnation. Native runtime usa apenas operação real descoberta e resposta observável que cumpra o contrato; capacidade ausente bloqueia admissão futura e preserva recurso legado.

**Razão**: o guia local Orca diz que release fecha apenas o terminal pertencente à dispatch aceita e pode preservar terminais reaproveitados/unknown. PTY vivo não prova agente vivo; silêncio/contact loss não prova saída. Interromper turno não é necessariamente encerrar sessão.

**Alternativas rejeitadas**: kill por PID sem token de início; terminal close como fallback de release; assumir que SubagentStop remove a sessão; usar estado do worker GWD como estado do provider.

**Consequência**: fechamento não confirmado aparece separado da elegibilidade Git e impede declarar quiescência. O core não promete limpeza universal de um recurso que o runtime não permite identificar.

## D6 — Design é resultado visual interno de plan

**Decisão**: classificar por DU/handoff, resolver Impeccable e produzir preview autocontido com capturas e manifest, revisado por high e aprovado pelo operador. Gate no core antes de tasks e na aceitação posterior. Esta feature é platform-devops sem superfície, portanto NOT_APPLICABLE.

**Fonte local de integração**: `/home/carlosaraujo/.agents/skills/impeccable/SKILL.md`, versão 4.3.1, e launcher `scripts/impeccable` foram lidos como dependência de desenho, sem executá-los. A skill define shape/critique, contexto e fallback quando launcher indisponível; o launcher pode baixar engine. GWD não deve chamar esse caminho para detectar capacidade nem introduzir download no core. Referência pessoal é evidência da pesquisa, não path hardcoded de distribuição.

**Alternativas rejeitadas**: nova macroetapa; brief como preview; aprovação sem digest; alterar PRODUCT.md/DESIGN.md project-wide incidentalmente; construir frontend próprio só para demonstrar suporte; depender de node/renderizador nos validadores.

**Mecanismo**: ferramentas visuais do harness já instalado geram/capturam o artefato da feature. Core verifica arquivos seguros, manifest/digests e decisões correlacionadas; revisor e operador avaliam o visual. Tests usam imagens mínimas locais e adapters falsos; não alegam que esses testes avaliaram qualidade estética.

## D7 — Tasks com Files e Result explícitos

**Decisão**: bloco imediato `Files:` JSON em cada tarefa, com `Result:` explícito nas despacháveis e incluído no array. DAG v2 transporta task_ids, result_files e fingerprint; a prosa nunca gera grant. Files vazio é declaração de não escrita, não autorização feature-wide.

**Razão**: melhorar regex não distingue ACTIVE/FREE de path legítimo. O sidecar que partition hoje acrescenta automaticamente também viola “todos e somente os declarados”; ele precisa fazer parte da declaração. Resultado por tarefa tem path conhecido antes de agrupar nodes e evita circularidade de escolher node_id no gerador de tasks.

**Alternativas rejeitadas**: heurística mais ampla; globs de diretório; placeholder de node no path; sidecar reservado adicionado ao grant; parser externo de Markdown/YAML; manter tarefa unmapped com escopo amplo.

**Mecanismo**: stdlib json estrito e máquina de estados curta, reuso dos checks de paths/grants reforçados na fronteira. Conflicts permanecem; o report preserva todas as fases/tasks antes de filtrar workers. Activities/receipts existentes vinculam task_id/fase/fingerprint/DAG e aceite positivo das tarefas read-only/deferred. Um guard comum exige fases anteriores satisfeitas antes de wave/worker-declare, prepare legado/remediation, payload e atividade de task; nesta, exige também workers da própria fase convergidos. Reconcile, checkpoint e retomada usam esses aceites sem duplicação, e a última fase fora do scheduler continua obrigatória no fechamento. Migração usa proposta completa revisada e expected hash; não inventa Files a partir do extrator legado. Ler DAG v1 selado não o reescreve; novas execuções adotadas exigem v2/adaptação explícita.

**Correção delimitada R1/P1**: conferência do baseline confirma que `partition.partition` calcula fases após remover deferred, e `grill-implement-parallel/SKILL.md` executa deferred só no final. O suplemento substitui explicitamente essa ordem: workers/convergência da fase, depois atividades read-only/deferred na ordem declarada, antes da fase seguinte; fases só dessas atividades não somem. Dependência anterior a worker exige fase anterior explícita em tasks, sem interpretar prosa ou criar scheduler. `gauntlet_runs._validate_dag_structure` recusa nodes vazio, `grill-partition` exige DAG-VALID antes do checkpoint e `attestation.require_emission_allowed` exige execução real de workers para worker-required. Logo, conjunto sem tarefa despachável retorna PARTITION-NO-WORKERS antes da admissão, listas completas e nenhum receipt terminal; não se promete conclusão zero-worker. Esse caso geral foi acrescido pelo desenho, não exigido pela spec, e permanece limite explícito sem enfraquecer a cobertura dos planos mistos, os pins ou as classes v3/v4.

## D8 — Rollout obrigatório sem mudar snapshots congelados

**Decisão**: publicar 6.0.0 com suplemento de invocação, sem alterar as onze skills canônicas e arquivos que seus catálogos pinam. A skill de entrada GWD e seu protocolo serão atualizados, inclusive o bootstrap do estilo; não são as entradas canônicas protegidas. Novos trabalhos entram no novo contrato; legado deve adotar antes de continuar no binário novo. O bundle anterior segue disponível para concluir o ciclo que constrói esta release, sem dizer que esse ciclo já cumpriu requisitos ainda não implementados.

**Razão**: editar `grill-partition/SKILL.md` exige atualizar seu manifest real e catálogo de confiança; a ativação atual fixa esses bytes. Trocar in-place catálogos ou registry invalida a frota e o próprio ciclo. Criar workflow v5 seria uma evolução de governança maior que a decisão de manter onze etapas e documentos intactos.

**Alternativas rejeitadas**: sobrescrever catálogos; desabilitar stale checks; opts permanentes que dispensem a política; mudar Constitução/WORKFLOW; atualizar integrações globais do usuário automaticamente.

**Mecanismo**: suplemento versionado/hashado é fornecido como argumento específico à mesma skill canônica, com instruções de autoria, gate, formato e ordem por fase das tarefas fora do scheduler. Substitui expressamente a receita final de deferred; em partition manda parar antes de admissão se não houver workers. Core valida resultado/barreiras e recusa o formato antigo sob o contrato novo, sem mudar a classe worker-required. O ciclo atual pode adotar depois do ship inclusive em estado COMPLETE, importando apenas referências verificadas e inventário; nenhum recibo é reemitido. Legacy read/diagnosis/cleanup continuam possíveis, mas novo trabalho no binário novo exige migração. Divergência entre suplemento e instrução operacional efetivamente entregue é falha de integração, coberta por teste, não exceção documental.

**Âncora operacional conferida**: cache Codex `/home/carlosaraujo/.codex/plugins/cache/grill-with-docs/grill-with-docs/5.4.1`, manifest 5.4.1, CLI SHA-256 `f71350d84b0ac517f462d6829cdd818425b5248e3675a746cce9c52e42523d2f` e registry v4 `f514df103b3d2dbf0cf786e95c9b59e7b1dc79e08b2ce7fe30b99f8b8bb3e35c`. As skills grill-partition e grill-implement-parallel também existem nesse bundle. Plan/quickstart exigem manifest completo e preservação antes da edição: coordenar a campanha histórica por esse CLI absoluto, enquanto testes/candidata usam fonte e estado isolados. Versão textual igual ou path existente não dispensa os hashes, e mudar plugin source para 6.0.0 não muda automaticamente o executável do líder.

## D9 — i-have-adhd como referência de apresentação carregada pela GWD

**Decisão**: adicionar dependência harness-plugin obrigatória, mínimo 0.3.0, e carregar o corpo integral instalado no bootstrap explícito da GWD. Usar a mesma rotina no início, retomada, reentrada após compactação e contexto das skills canônicas/especialistas. Uma instrução de alcance delimita as regras ao projeto/fluxo GWD; não criar default global. Configurações e política Ponytail permanecem preservadas.

**Evidência upstream inspecionada**: cópias `/home/carlosaraujo/.codex/plugins/cache/i-have-adhd/i-have-adhd/0.3.0` e `/home/carlosaraujo/.claude/plugins/cache/i-have-adhd/i-have-adhd/0.3.0`; manifests MIT/0.3.0, `skills/i-have-adhd/SKILL.md`, `agents/openai.yaml`, hooks e seções Claude/Codex de INSTALL. Paths pessoais são evidência da pesquisa, não constantes de distribuição. Ambos os SKILL.md têm SHA-256 `3170b16ace00aecb0dd7feb54c0b5aa642e7502acda06ecd24fd89a11c7127e9`. O corpo mantém dez regras e exceções de completude, harness e segurança. Fontes oficiais do próprio componente: [skill](https://github.com/ayghri/i-have-adhd/blob/main/skills/i-have-adhd/SKILL.md), [instalação](https://github.com/ayghri/i-have-adhd/blob/main/INSTALL.md), [hook](https://github.com/ayghri/i-have-adhd/blob/main/hooks/always-on.mjs). Os bytes/hash fixam o que foi lido apesar de `main` ser mutável.

**Fatos de runtime**: nesta pesquisa, `codex plugin list --json` retornou pluginId exato, versão 0.3.0, installed/enabled true; `claude plugin list --json` retornou id exato, versão 0.3.0, scope user e enabled true. Isso confirma disponibilidade na configuração sondada, não carregamento nesta sessão nem comportamento. `claude plugin enable --help` admite scope project/local/user; o Codex instalado **não tem** subcomando `plugin enable` (`error: unrecognized subcommand 'enable'`). Não inventar essa receita: usar o controle de plugin da sessão Codex e conferir novamente a evidência efetiva. Instalação nova continua delegada aos comandos já comprovados em STACK.

**Documentação dos harnesses**: Codex permite desabilitar invocação implícita por `allow_implicit_invocation: false`; descoberta da skill não carrega seu corpo. [OpenAI — Criar habilidades](https://learn.chatgpt.com/pt-BR/docs/build-skills). Claude restringe auto-invocação com `disable-model-invocation` e admite conteúdo de referência inline nas skills. [Claude — Skills](https://code.claude.com/docs/en/skills). Habilitação de plugin é configuração distinta da disponibilidade de seu conteúdo. [Claude — Plugins reference](https://code.claude.com/docs/en/plugins-reference). A conclusão de desenho é usar a referência de apresentação autorizada pelo usuário dentro da GWD, sem tentar contornar uma recusa da ferramenta Skill ou alegar uma invocação automática upstream.

**Razão**: o hook 0.3.0 depende de `.i-have-adhd-always` em CLAUDE_CONFIG_DIR ou `~/.claude`, inclusive na cópia Codex. Saída 0 vazia é prevista sem flag; a aprovação humana do hook removeu um impedimento de startup, não ativou o estilo. Carregar as regras diretamente na GWD tem o mesmo conteúdo sem depender dessa flag, de node ou de edição de caches/configurações globais. O hook GWD existente é read-only e limitado; não é necessário ampliá-lo ou criar outro hook.

**Mecanismo mínimo**: reaproveitar `plugin_registry_state` para presença e versão, com resolução segura da instalação efetiva informada pelo harness em vez de assumir que a maior versão no cache está carregada. Policy suplementar fixa o hash do corpo admitido via hash dos bytes originais 0.3.0; extrator remove somente frontmatter inicial, sem parser YAML externo. GWD coleta a observação de habilitação pela superfície do harness, executa preflight e lê o SKILL.md completo. Preflight emite pedido de carga mesmo quando `loaded` está pendente; somente nova observação da leitura na mesma sessão autoriza `LOADED`. O Store/contexto existente guarda as refs, sem arquivo de configuração global novo ou registry alternativo de skills.

**Compatibilidade e precedência**: a GWD atualizada inclui instruções locais de bootstrap no próprio entrypoint/protocolo e no AGENTS/CLAUDE deste projeto. Consumidores entram pelo comando GWD habitual; não precisam chamar i-have-adhd. O suplemento aplica apresentação, preserva os dez comportamentos e suas exceções, e não reescreve código, JSON, evidência, contratos, tarefas ou política Ponytail. Mudança de escopo para fora do GWD e pedido explícito de desativação suspendem a aplicação nessa sessão; a próxima sessão GWD volta ao default. Estado de suspensão explícita sobrevive à compactação da mesma sessão.

**Correção delimitada R1/P2**: separar `work_ready`, usado pelas entradas/despachos, de `use_ready`, que continua significando carga/aplicação ativa. Work_ready mantém presença, compatibilidade, habilitação, confiança e escopo obrigatórios, aceitando carga ativa ou suspensão humana comprovada para a mesma sessão/incarnation/escopo. Compactação revalida a fonte da suspensão e permite trabalho com loading stale, sem recarregar/aplicar o corpo. Nova sessão, inclusive especialista ou destino de retomada, não herda suspensão e inicia ativa com carga própria. Suspensão não satisfaz functional_verified/FR-024. O check previsto percorre bootstrap → stop adhd mode → compactação → atividade autorizada sem estilo, com Ponytail e outputs intactos, mais nova sessão ativa; não exige novo mecanismo de persistência além do contexto/observations existentes.

**Alternativas rejeitadas**: flag global ou mudar CLAUDE_CONFIG_DIR só para torná-la local; AGENTS global; cópia resumida das dez regras vendorizada como outra skill; edição de metadados upstream para liberar auto-invocação; inferir enabled do cache; fake loaded receipt; regex de estilo como prova suficiente; exigir invocação manual a cada sessão. Não remover configuração global preexistente sem autorização nem declarar alcance local comprovado quando ela contamina o controle externo.

**Limites e aceite**: a referência carregada é evidência auditável de contexto, não prova de obediência do modelo. Há risco de perda de contexto, instruções superiores conflitantes e defaults globais preexistentes; reentrada ativa recarrega, suspensão válida conserva apenas readiness de trabalho, diagnóstico identifica conflitos, e amostras live avaliam resultados. `quickstart.md` exige início/retomada nos dois CLIs, leitura observada antes da resposta, conversa em vários turnos, preservação de conteúdo e controle externo. Instalado/habilitado, checks isolados e launch do revisor já comprovados permanecem evidências parciais; FR-024 só passa após esse caminho funcional completo.

## Verificação desta pesquisa e limites

O [baseline do líder](../../.grill/work-items/feature-new-subagents-unified-69f619a1a4774d598e4a46c77396f0fa/cycle-baseline-validation.json) terminou com exit 0, 28 validadores e um skip porque o host não apresenta o alias `/var -> /private/var`. O autor desta ampliação não repetiu a suíte completa, não implementou código/tests, não lançou agentes nem alterou documentos fora do grant; verificou fontes e consistência documental. A pesquisa original dos sete requisitos e seus callers foi preservada, com correção das afirmações de dependências, alcance, integração canônica e evidência Claude afetadas pelo adendo.

As decisões de HOW dos oito requisitos estão definidas. Execução e aceite funcional permanecem no ciclo posterior; nenhum bloqueio nominal, hash ou autorrelato substitui o caminho positivo exigido nos dois CLIs. Coordenação, revisão e atestação da macroetapa pertencem ao líder.

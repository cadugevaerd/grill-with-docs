# Tasks: Orquestração, continuidade e escopo dos agentes

**Input**: `specs/030-agent-orchestration/`: spec, plan GO R2, research, data-model, três contracts, quickstart e checklist de orquestração GO 27/27.
**Identidade**: work item `feature-new-subagents-unified-69f619a1a4774d598e4a46c77396f0fa`; FASE-001; DU-001; branch `cadugevaerd/feat-new-subagents`.
**Entrega**: oito histórias, FR-001–FR-024 e SC-001–SC-008; candidata **6.0.0**. MVP é somente um marco de validação, sem redução de escopo.
**Estado**: HOW para revisão independente. Nenhuma checkbox assinalada comprova antecipadamente implementação, live, macroetapa ou publicação.

## Contrato de execução desta construção

Esta campanha permanece **histórica 5.4.1**, conforme rollout aprovado em plan e delimitação do líder. Este documento não declara adoção de `task-files/v1` e não contém seu marcador de ativação. `Files:` é a lista JSON revisável dos arquivos de implementação ou evidência de cada tarefa; `Result:` descreve seu resultado observável. Nesta construção esses campos são documentação do HOW, não campos interpretados pelo parser histórico nem Results por tarefa do contrato novo.

O parser 5.4.1 lê apenas a linha checklist: por isso os paths destinados aos workers aparecem também nessa linha, sem outras referências com barra na prosa da linha. O líder deve comparar a extração com Files antes de selar partition. Arquivos da raiz sem barra não são extraídos, e prefixo `./` é recusado pelo validador histórico; rootdocs ficam integralmente na tarefa final T027 do líder. Não usar diretório, alias, symlink, grant amplo ou prepare legado para contornar esse limite.

O **único resultado operacional de worker nesta campanha** é o sidecar nativo por node devolvido pelo DAG, report e `gauntlet-partition-brief` 5.4.1. Seu path e seus task IDs devem ser lidos desses resultados reais na etapa partition; não são previstos, inventados ou acrescentados aqui como Results por task. O parser histórico acrescenta esse único path nativo ao grant. Workers registram apenas IDs atribuídos efetivamente concluídos, fazem o commit e terminal pelo protocolo histórico; o líder confere diff, integração e sidecar antes de reconciliar. Nenhum worker edita tasks. Não editar tasks atestadas, DAG selado ou grants depois para acomodar o agrupamento; mudança necessária retorna ao fluxo explícito de revisão.

As fases com workers são barreiras históricas. Dentro de um node, cumprir tasks na ordem do documento. **Deferred só roda após todas as waves em 5.4.1**: T027–T030 estão no final e nenhum worker depende de seus efeitos. Tarefas sem escrita não usam `Files: []` neste bootstrap: isso criaria worker unmapped com escopo FEATURE_WIDE. Checks mecânicos pertencem à task que implementa a lógica; revisão, live e bookkeeping ficam nas tarefas finais do líder ou nos gates canônicos posteriores. A candidata implementará integralmente a semântica nova de Files/Result, read-only, barreiras por fase e PARTITION-NO-WORKERS; ela será testada em estado isolado, sem governar a própria construção.

### Pré-condições operacionais do líder, anteriores à primeira wave

Estas condições são do preflight da campanha, não tasks deferred que o parser antigo pudesse mover para o final:

1. Preservar a campanha `run-b12537dfc4dca1621cc1f08d` e registry `sha256:f514df103b3d2dbf0cf786e95c9b59e7b1dc79e08b2ce7fe30b99f8b8bb3e35c`; não confundir campaign run ID com scheduler run ID a ser observado em partition.
2. Fixar e registrar o manifest dos bytes efetivamente usados de scripts, módulos, assets e skills do bundle histórico. CLI absoluto: `/home/carlosaraujo/.codex/plugins/cache/grill-with-docs/grill-with-docs/5.4.1/skills/grill-with-docs/scripts/grill_workspace.py`; SHA-256 observado `f71350d84b0ac517f462d6829cdd818425b5248e3675a746cce9c52e42523d2f`. Comparar também pins canônicos, além de versão/path, e preservar o bundle fora dos recursos elegíveis a cleanup até pós-ship.
3. Usar esse CLI e módulos/assets irmãos em toda coordenação, checkpoint, atestação, convergência e cleanup históricos. As onze skills continuam nos entrypoints e bytes pinados. Revalidar o manifest após troca de sessão/cache; divergência bloqueia sem reescrever pins. A fonte candidata opera apenas fixtures e outro projeto de ensaio.
4. Reutilizar o baseline registrado pelo líder em `cycle-baseline-validation.json`: exit 0, 28 validadores, um skip do alias específico do host. Verificar sua correspondência ao baseline da implementação; esta autoria documental não repete a suíte. Aplicar o preflight histórico de checklists e hooks antes de fan-out.
5. O líder invoca as skills canônicas e mantém registros; qualquer novo COMO retorna a autor xhigh e revisão high em sessão distinta. Workers não-frontier implementam o HOW aprovado, sem receber escrita de evidência reservada. Esta lista não autoriza implementação fora da sequência nem altera `PLAN_ONLY_STOP` de feature/fix.

### Limites comuns a todas as tasks

Python >=3.10 e somente stdlib; core nunca baixa bytes. Checks offline usam Git temporário, clocks, falhas e observations injetáveis, sem rede nem `node`, `specify`, `backlogctl`, Codex, Claude ou Orca reais. Reusar locks, Store/WAL, fronteiras de leitura segura, helpers Git e agrupamento existentes; sem novo scheduler, daemon, framework de adapters ou frontend próprio.

Preservar bytes de `workflow_versions.py`, `workflow_v3.py`, `workflow_v4.py`, ESSENTIAL, classes worker-required, templates/registries/catálogos/confiança v3/v4, `grill-local-skills.manifest.json`, agent pinado, onze skills canônicas, `.agents/skills`, `.claude/skills`, Constituição e `WORKFLOW.md`. Só GWD de entrada, protocolo e novos suplementos mudam conforme Files. Paths de instalação e configurações globais são entradas de leitura, nunca grants. Evidência `.grill/` é materializada apenas pelo líder; os paths finais abaixo são destinos futuros de resultados reais, não receipts já existentes.

Cada mudança de lógica inclui uma verificação significativa na suíte indicada, reproduzindo a recusa ou efeito que quebraria sem a mudança. Reusar o mesmo cenário para variantes e ampliar regressões compartilhadas necessárias; não criar testes por helper nem duplicar o runner. Os cenários públicos de `AgentOrchestrationContract` seguem os nomes de quickstart. Checks focados de workers não alegam distribuição completa: os oito pontos de versão são sincronizados em T027 e o gate global vem depois.

## Phase 1: Setup — política e entradas suplementares

**Objetivo**: disponibilizar o contrato para a construção dos módulos, sem mudar resolução canônica.

- [ ] T001 Criar política, template e protocolo suplementares em `plugin/skills/grill-with-docs/assets/agent-orchestration.v1.json`, `plugin/skills/grill-with-docs/assets/task-files.v1.template.md` e `plugin/skills/grill-with-docs/references/agent-orchestration.md`.
  Files: ["plugin/skills/grill-with-docs/assets/agent-orchestration.v1.json", "plugin/skills/grill-with-docs/assets/task-files.v1.template.md", "plugin/skills/grill-with-docs/references/agent-orchestration.md"]
  Result: "Política versionada com pares por papel/runtime, matriz das onze etapas e entrevista, capacidades, classificação e apresentação; template completo Files/Result; suplemento com ordem por fase e parada sem workers."
  Limites: seguir contracts integralmente; hashes do suplemento/template sem autorreferência; admitir i-have-adhd 0.3.0 pelo hash aprovado, sem copiar/resumir corpo upstream. Explicitar que Results por tarefa e deferred por fase só valem no contrato adotado da candidata. Não editar entradas canônicas.
  Check do worker: decodificar JSON estrito, conferir refs locais e recalcular os dois hashes com stdlib; verificar que o template exige Result declarado por tarefa, e que o suplemento não confunde contexto entregue com skill invocada.

## Phase 2: Foundation — persistência, autoridade e observações

**Dependência**: T001. Nenhuma história começa antes de T002–T005 estarem integradas.

- [ ] T002 Implementar o bloco versionado e eventos no Store em `plugin/skills/grill-with-docs/scripts/grill_core/agent_orchestration.py`, `plugin/skills/grill-with-docs/scripts/grill_core/store.py` e `tests/validate_orchestrator_store_contract.py`.
  Files: ["plugin/skills/grill-with-docs/scripts/grill_core/agent_orchestration.py", "plugin/skills/grill-with-docs/scripts/grill_core/store.py", "tests/validate_orchestrator_store_contract.py"]
  Result: "Store valida contextos, activities, recursos, operações, checkpoints, presentation e escopo revisado; aceita a união explícita de eventos de orquestração sem alterar os eventos Gauntlet existentes."
  Limites: objetos fechados, JSON sem duplicatas/NaN, transições e campos write-once do data-model; ausência do bloco é legado, presença inválida bloqueia e bloco adotado não pode ser removido. Estender _transition_fields, _candidate_transition, validação e recovery por schema; sem wave ou lease fictícios. Epoch monotônica e CAS revalidam sessão/incarnation/fence; I/O externo fora do lock Store.
  Check do worker: `python3 tests/validate_orchestrator_store_contract.py`; incluir replay WAL, evento sem scheduler e duas escritas concorrentes, preservando bytes/shape dos receipts antigos e recusando regressão de epoch, chaves desconhecidas e remoção do contrato.

- [ ] T003 Implementar a fronteira de observação em `plugin/skills/grill-with-docs/scripts/grill_core/agent_runtime.py` e `tests/validate_agent_orchestration_contract.py`.
  Files: ["plugin/skills/grill-with-docs/scripts/grill_core/agent_runtime.py", "tests/validate_agent_orchestration_contract.py"]
  Result: "Observations correlacionam fonte, identidade, incarnation, lançamento efetivo, atividade e fechamento; callables de probe/observe/request_close/read_after_close permitem testar o fluxo sem runtime real."
  Limites: entrada do provider efetivamente observada, não JSON autoafirmativo do worker; missing fica null/unknown. Suportar o caminho Orca documentado quando selecionado e comprovado; superfícies nativas incompletas bloqueiam com campo ausente. Sem shell livre, banco privado, PID inferido, sinais POSIX ou fallback local silencioso.
  Check do worker: cenário focado no novo validador exerce requested sem effective, alias não resolvido, incarnation reutilizada, close desconhecido e read-back correlacionado; envio técnico permanece zero nas recusas. Reusar o mesmo seam nas histórias seguintes.

- [ ] T004 Implementar adoção e guard comum em `plugin/skills/grill-with-docs/scripts/grill_core/agent_orchestration.py`, `plugin/skills/grill-with-docs/scripts/grill_core/gauntlet_runs.py`, `plugin/skills/grill-with-docs/scripts/grill_workspace.py` e `tests/validate_agent_orchestration_contract.py`.
  Files: ["plugin/skills/grill-with-docs/scripts/grill_core/agent_orchestration.py", "plugin/skills/grill-with-docs/scripts/grill_core/gauntlet_runs.py", "plugin/skills/grill-with-docs/scripts/grill_workspace.py", "tests/validate_agent_orchestration_contract.py"]
  Result: "init novo cria o contrato; gauntlet-orchestration-adopt oferece preview/apply idempotente com hash esperado, origem e scope_revision; toda mutação exige autoridade corrente."
  Limites: depende de T002–T003; percorrer callers de init/admission/prepare/checkpoint/attest e recovery, sem bypass legado na candidata. Antes do Gauntlet, activation/campaign null e scheduler_runs vazio são válidos; entrevista usa step_id null. Leitura, diagnóstico e cleanup protegido continuam disponíveis no legado; execução exige adoção. Não alterar gauntlet.yaml, WORK-ITEM, campaign/admission ou receipts históricos.
  Check do worker: construir `AgentOrchestrationContract.test_rollout_and_canonical_pins` com init novo, preview sem escrita, apply stale, COMPLETE adotado sem reabrir etapas, scope revision explícita e contexto antigo recusado; fase de apresentação será completada por T021.

- [ ] T005 Implementar operações e checkpoint comprometido em `plugin/skills/grill-with-docs/scripts/grill_core/agent_orchestration.py`, `plugin/skills/grill-with-docs/scripts/grill_core/store.py`, `plugin/skills/grill-with-docs/scripts/grill_workspace.py`, `tests/validate_orchestrator_store_contract.py` e `tests/validate_checkpoint_contract.py`.
  Files: ["plugin/skills/grill-with-docs/scripts/grill_core/agent_orchestration.py", "plugin/skills/grill-with-docs/scripts/grill_core/store.py", "plugin/skills/grill-with-docs/scripts/grill_workspace.py", "tests/validate_orchestrator_store_contract.py", "tests/validate_checkpoint_contract.py"]
  Result: "Intenção before/after precede o efeito; Store, state, receipt e checkpoint_head convergem por recovery, mantendo aceites, pendências e recursos por referência."
  Limites: depende de T004; locks na ordem existente, state por fronteira segura e rename atômico; selecionar head comprometido, nunca mtime. Chave idempotente inclui identidade e inputs; UNKNOWN requer observação, não repetição cega. Terceiro conteúdo de state bloqueia sem sobrescrever; órfão não é output aceito.
  Check do worker: executar os dois validadores Files com falhas antes do state, depois do state e antes do commit; replay faz só o trecho faltante, inputs diferentes recusam a mesma chave e checkpoint não promove tentativa apenas produzida.

## Phase 3: US1 — Encerrar agentes sem perder trabalho (P1, marco MVP)

**Dependência**: Foundation. **Teste independente**: quickstart §1, incluindo wave intermediária e run COMPLETE. O marco não encerra DU-001.

- [ ] T006 [US1] Corrigir lifecycle e identidade dos recursos em `plugin/skills/grill-with-docs/scripts/grill_core/agent_orchestration.py`, `plugin/skills/grill-with-docs/scripts/grill_core/gauntlet_runs.py`, `tests/validate_agent_orchestration_contract.py` e `tests/validate_gauntlet_run_contract.py`.
  Files: ["plugin/skills/grill-with-docs/scripts/grill_core/agent_orchestration.py", "plugin/skills/grill-with-docs/scripts/grill_core/gauntlet_runs.py", "tests/validate_agent_orchestration_contract.py", "tests/validate_gauntlet_run_contract.py"]
  Result: "Sessão, worktree e branch têm elegibilidade, intenção, confirmação e motivos próprios; run terminal permite cleanup sem permitir prepare."
  Limites: separar identidade de elegibilidade em _run_for_worker e corrigir todos os callers. Correlacionar criação, Git common-dir, path real, ref, terminal_head e ancestry integrada, não HEAD igual ao base. Persistir resultado/diagnóstico antes de close; sessão ativa/unknown impede apagar workspace. Dirty, untracked, ignored, evidência exclusiva, falha pendente ou identidade divergente preservam. Remover worktree sem force; depois ref por OLD_OID e read-back. Sem clean/reset/prune/branch forçado.
  Check do worker: `python3 tests/validate_agent_orchestration_contract.py AgentOrchestrationContract.test_cleanup_lifecycle` e `python3 tests/validate_gauntlet_run_contract.py`; testar integrado, falho e read-only, resposta de remoção perdida, ref/symlink trocados e nome reutilizado. ALREADY_ABSENT só conclui intenção anterior comprovada.

- [ ] T007 [US1] Ligar cleanup automático e projeções em `plugin/skills/grill-with-docs/scripts/grill_core/gauntlet_runs.py`, `plugin/skills/grill-with-docs/scripts/grill_workspace.py`, `plugin/skills/grill-with-docs/scripts/grill_status.py`, `tests/validate_gauntlet_converge_contract.py`, `tests/validate_gauntlet_scheduler_contract.py`, `tests/validate_status_contract.py` e `tests/validate_agent_orchestration_contract.py`.
  Files: ["plugin/skills/grill-with-docs/scripts/grill_core/gauntlet_runs.py", "plugin/skills/grill-with-docs/scripts/grill_workspace.py", "plugin/skills/grill-with-docs/scripts/grill_status.py", "tests/validate_gauntlet_converge_contract.py", "tests/validate_gauntlet_scheduler_contract.py", "tests/validate_status_contract.py", "tests/validate_agent_orchestration_contract.py"]
  Result: "Terminal, wave terminal/convergida e etapa completa/bloqueada persistem obrigação e drenam cleanup; resultado aceito sobrevive à limpeza e a próxima wave continua pronta."
  Limites: depende de T006; sucesso do worker não vira estado de recurso. Revisar _node_ready, _converged_lineage_head, _wave_would_complete e _all_converged; CLEANED legado só satisfaz dependência com prova histórica de sucesso/convergência, nunca falha. Checkpoint lista motivos por recurso e distingue STEP-ACCEPTED-CLEANUP-PENDING; retry não reexecuta etapa. Status/hooks read-only, uma observação Git por worktree por avaliação.
  Check do worker: ampliar test_cleanup_lifecycle pelos callbacks reais de CLI e executar os três validadores compartilhados Files; primeira wave limpa não bloqueia segunda, run COMPLETE aceita cleanup e timeout não vira CLEANED.

## Phase 4: US3 — Retomar o mesmo trabalho em outro CLI (P1)

**Dependência**: US1 e checkpoint Foundation. **Teste independente**: quickstart §2 nos dois sentidos, com tentativas aceitas e interrompidas distintas.

- [ ] T008 [US3] Implementar ativação efetiva e ponte de campanhas em `plugin/skills/grill-with-docs/scripts/grill_core/agent_orchestration.py`, `plugin/skills/grill-with-docs/scripts/grill_core/gauntlet.py`, `plugin/skills/grill-with-docs/scripts/grill_core/attestation.py`, `plugin/skills/grill-with-docs/scripts/grill_workspace.py` e `tests/validate_attestation_emitter_contract.py`.
  Files: ["plugin/skills/grill-with-docs/scripts/grill_core/agent_orchestration.py", "plugin/skills/grill-with-docs/scripts/grill_core/gauntlet.py", "plugin/skills/grill-with-docs/scripts/grill_core/attestation.py", "plugin/skills/grill-with-docs/scripts/grill_workspace.py", "tests/validate_attestation_emitter_contract.py"]
  Result: "effective_activation resolve o contexto sucessor; primeira invocação após troca valida a ponte histórica, preservando igualdade estrita dentro de cada campanha."
  Limites: usar current_activation para comprovar destino e localizar todos os leitores de ativação/admission/attest. Manter sete campos da campanha, run lógico e plan_revision; criar recovery_generation_id novo, sem confundir scheduler run nem alterar seus pins/base/admission. Não reetiquetar autoria/runtime dos outputs aceitos; pré-campanha preserva ausência sem ponte fictícia.
  Check do worker: `python3 tests/validate_attestation_emitter_contract.py`; aceitar predecessor pela ponte exata apenas na primeira invocação sucessora e recusar receipt atrasado, ponte divergente ou troca de branch/plano disfarçada de runtime.

- [ ] T009 [US3] Implementar prepare-switch e resume em `plugin/skills/grill-with-docs/scripts/grill_core/agent_orchestration.py`, `plugin/skills/grill-with-docs/scripts/grill_core/gauntlet_runs.py`, `plugin/skills/grill-with-docs/scripts/grill_workspace.py`, `plugin/skills/grill-with-docs/scripts/grill_status.py`, `tests/validate_agent_orchestration_contract.py` e `tests/validate_checkpoint_contract.py`.
  Files: ["plugin/skills/grill-with-docs/scripts/grill_core/agent_orchestration.py", "plugin/skills/grill-with-docs/scripts/grill_core/gauntlet_runs.py", "plugin/skills/grill-with-docs/scripts/grill_workspace.py", "plugin/skills/grill-with-docs/scripts/grill_status.py", "tests/validate_agent_orchestration_contract.py", "tests/validate_checkpoint_contract.py"]
  Result: "Origem quiesce, limpa elegíveis e persiste checkpoint; destino adquire epoch por CAS e recebe somente tentativas ainda não aceitas, com recursos retidos e operações a reconciliar."
  Limites: depende de T008; comprovar mesma identidade/worktree/branch e ausência de executor/worker ativo; lease vencida ou silêncio não é quiescência. Não transferir nem matar worker para liberar troca. Resume de scheduler permanece distinguido de continuidade; não zerar remediation. Merge observado por OID/parents/ancestry, checkpoint/reconcile por hash; push/release permanecem com suas skills donas e outcome desconhecido bloqueia repetição.
  Check do worker: `python3 tests/validate_agent_orchestration_contract.py AgentOrchestrationContract.test_runtime_continuity` e validador de checkpoint; Codex→Claude→Codex preserva aceites byte-idênticos, duas retomadas concorrentes têm um vencedor, sessão unknown/checkpoint incoerente bloqueiam e efeito aceito nunca repete. T021 completará carga própria de apresentação no destino.

## Phase 5: US5 — Planejar com especialistas verificados (P1)

**Dependência**: Foundation e US3 para contexto/fence corrente. **Teste independente**: quickstart §3, contador de envio zero antes da prova efetiva.

- [ ] T010 [US5] Implementar admissão e aceite do autor em `plugin/skills/grill-with-docs/scripts/grill_core/agent_orchestration.py`, `plugin/skills/grill-with-docs/scripts/grill_core/agent_runtime.py`, `plugin/skills/grill-with-docs/scripts/grill_workspace.py` e `tests/validate_agent_orchestration_contract.py`.
  Files: ["plugin/skills/grill-with-docs/scripts/grill_core/agent_orchestration.py", "plugin/skills/grill-with-docs/scripts/grill_core/agent_runtime.py", "plugin/skills/grill-with-docs/scripts/grill_workspace.py", "tests/validate_agent_orchestration_contract.py"]
  Result: "gauntlet-activity prepare/dispatch/accept libera COMO apenas para gpt-6-astra xhigh no Codex ou fable xhigh no Claude com identidade e configuração efetivas comprovadas."
  Limites: bootstrap neutro sem inputs técnicos/grant; emitir payload somente após VERIFIED, ligado a activity/context/fence/input digest. Sem seleção por prefixo, fallback do líder ou concessão frontier ao worker. Read-back de envio perdido precede retry; revalidar efetivo no retorno e persistir output/diagnóstico antes do cleanup T007. Evidência de launch é estrutural, não prova criptográfica de inferência.
  Check do worker: `python3 tests/validate_agent_orchestration_contract.py AgentOrchestrationContract.test_specialist_admission`; ausência de effort, requested-only, alias não observado, falta de close e transporte sem separação bloqueiam payload; divergência no retorno impede aceite sem apagar tentativa.

- [ ] T011 [US5] Integrar entrada canônica e obrigações de autoria em `plugin/skills/grill-with-docs/scripts/grill_core/agent_orchestration.py`, `plugin/skills/grill-with-docs/scripts/grill_core/attestation.py`, `plugin/skills/grill-with-docs/scripts/grill_workspace.py`, `plugin/skills/grill-with-docs/references/agent-orchestration.md`, `plugin/skills/grill-with-docs/assets/agent-orchestration.v1.json` e `tests/validate_agent_orchestration_contract.py`.
  Files: ["plugin/skills/grill-with-docs/scripts/grill_core/agent_orchestration.py", "plugin/skills/grill-with-docs/scripts/grill_core/attestation.py", "plugin/skills/grill-with-docs/scripts/grill_workspace.py", "plugin/skills/grill-with-docs/references/agent-orchestration.md", "plugin/skills/grill-with-docs/assets/agent-orchestration.v1.json", "tests/validate_agent_orchestration_contract.py"]
  Result: "step-enter entrega entrypoint canônico, suplemento/template hashados e atividades exigidas; plan, tasks, design e novo COMO exigem autoria aceita, incluindo entrevista anterior ao ciclo."
  Limites: depende de T010; contexto entregue não atesta invocação. Checkpoint in-progress, attest e complete revalidam a mesma política; especialista não fecha macroetapa nem recebe evidência de coordenação. Conservar onze entradas e hashes canônicos; atualizar somente hash do suplemento se seus bytes mudarem.
  Check do worker: construir `AgentOrchestrationContract.test_activity_coverage` pelo caminho step-enter→contexto→autor verificado→resultado→guard de aceite; ausência da invocação real exigida e bypass por checkpoint direto continuam recusados. Teste usa seam e não declara execução real da skill.

## Phase 6: US6 — Revisar com independência em todo o fluxo (P1)

**Dependência**: US5. **Teste independente**: cada classe de artefato recebe revisor high distinto de todos os autores.

- [ ] T012 [US6] Implementar independência e atualidade das revisões em `plugin/skills/grill-with-docs/scripts/grill_core/agent_orchestration.py`, `plugin/skills/grill-with-docs/scripts/grill_core/agent_runtime.py`, `plugin/skills/grill-with-docs/scripts/grill_workspace.py` e `tests/validate_agent_orchestration_contract.py`.
  Files: ["plugin/skills/grill-with-docs/scripts/grill_core/agent_orchestration.py", "plugin/skills/grill-with-docs/scripts/grill_core/agent_runtime.py", "plugin/skills/grill-with-docs/scripts/grill_workspace.py", "tests/validate_agent_orchestration_contract.py"]
  Result: "Revisor Astra ou fable high, sem escrita, precisa de sessão distinta de toda cadeia de autoria e aprova somente o digest corrente do escopo."
  Limites: activity_id diferente na mesma sessão não dá independência; artefato composto inclui todos os autores. Modelo/esforço ausente/divergente bloqueia antes do payload; APPROVED, CHANGES_REQUIRED e revisão STALE são distintos; nenhum teste verde se promove a revisão.
  Check do worker: ampliar test_specialist_admission com mesmo autor, autor omitido, effort divergente e input alterado entre dispatch/accept; caso positivo aceita high em outra identidade, e resultado de revisão não concede escrita.

- [ ] T013 [US6] Completar cobertura de atividades mistas em `plugin/skills/grill-with-docs/scripts/grill_core/agent_orchestration.py`, `plugin/skills/grill-with-docs/scripts/grill_core/attestation.py`, `plugin/skills/grill-with-docs/scripts/grill_workspace.py` e `tests/validate_agent_orchestration_contract.py`.
  Files: ["plugin/skills/grill-with-docs/scripts/grill_core/agent_orchestration.py", "plugin/skills/grill-with-docs/scripts/grill_core/attestation.py", "plugin/skills/grill-with-docs/scripts/grill_workspace.py", "tests/validate_agent_orchestration_contract.py"]
  Result: "Matriz das onze etapas separa author, reviewer e deterministic_check; todo julgamento de requisitos, plano, checklist, tasks, design, código, segurança e lacunas exige receipt adequado."
  Limites: depende de T012; core verifica obrigações/tipos/correlação, sem classificar linguagem natural nem chamar julgamento de teste para evitar o revisor. Verify determinístico não requer modelo; ship não ganha execução ou autorização por esta política.
  Check do worker: `python3 tests/validate_agent_orchestration_contract.py AgentOrchestrationContract.test_activity_coverage` e `python3 tests/validate_tier_model_binding_contract.py`; passes mistos exigem autor xhigh e outro high, revisão stale/ausente bloqueia e binding dos implementadores continua não-frontier.

## Phase 7: US2 — Escrita somente nos arquivos declarados (P1)

**Dependência**: US3, US5 e US6, pois migração e barreiras novas dependem de continuidade e activities aceitas. **Teste independente**: quickstart §5 em fixtures da candidata; esta campanha continua usando parser histórico.

- [ ] T014 [US2] Implementar gramática e paths explícitos em `plugin/skills/grill-with-docs/scripts/grill_core/partition.py`, `plugin/skills/grill-with-docs/scripts/grill_core/gauntlet_runs.py`, `plugin/skills/grill-with-docs/scripts/grill_workspace.py` e `tests/validate_partition_contract.py`.
  Files: ["plugin/skills/grill-with-docs/scripts/grill_core/partition.py", "plugin/skills/grill-with-docs/scripts/grill_core/gauntlet_runs.py", "plugin/skills/grill-with-docs/scripts/grill_workspace.py", "tests/validate_partition_contract.py"]
  Result: "Parser task-files/v1 exige marcador único, fases/IDs válidos, Files imediato e Result de task declarado; normaliza somente ./ inicial e nunca infere escrita da prosa."
  Limites: JSON estrito, fences antes de regex de task, fence não fechado bloqueia; validar todos os campos antes de grant parcial. Root/new/subdir/spaces válidos; rejeitar duplicatas normalizadas, absolutos POSIX/Windows, traversal, backslash, controles, globs, diretórios, dispositivos/ADS/aliases Windows e colisões de caixa pertinentes. Reusar regra comum em DAG/declare/prepare e fronteira no-follow para ancestrais, inclusive junctions; scope_files é limite adicional.
  Check do worker: `python3 tests/validate_partition_contract.py`; ACTIVE/FREE, path não declarado e cache absoluto na prosa não alteram Files. Result ausente/fora de Files ou convenção da task falha; symlink/escape não recebe grant. Leitura histórica usada para auditoria não vira fallback de execução novo.

- [ ] T015 [US2] Implementar DAG e report v2 em `plugin/skills/grill-with-docs/scripts/grill_core/partition.py`, `plugin/skills/grill-with-docs/scripts/grill_core/gauntlet_runs.py`, `plugin/skills/grill-with-docs/scripts/grill_workspace.py` e `tests/validate_partition_contract.py`.
  Files: ["plugin/skills/grill-with-docs/scripts/grill_core/partition.py", "plugin/skills/grill-with-docs/scripts/grill_core/gauntlet_runs.py", "plugin/skills/grill-with-docs/scripts/grill_workspace.py", "tests/validate_partition_contract.py"]
  Result: "DAG v2 transporta fingerprint semântico, task_ids, result_files e accepted_tasks; report conserva todas as fases e cobertura exata de workers, read-only, deferred e importações."
  Limites: depende de T014; nodes.files é a união exata de Files, sem sidecar implícito ou FEATURE_WIDE. Agrupar conflitos pelo algoritmo existente, não pelo julgamento do líder; [P] não supera conflito. Hash semântico normaliza só checkboxes de tasks parseadas, não exemplos; pin DAG continua hash dos bytes exatos. Sem worker restante: PARTITION-NO-WORKERS com listas completas, exit 2 e nenhum DAG/admissão/receipt fictício.
  Check do worker: validador de partition compara grants, conservação de fases só read-only/deferred, cobertura sem duplicação, determinismo e degradação honesta; alteração de checkbox mantém fingerprint, descrição/Files/fase muda. Exit 2 só conta com payload BLOCKED nominal, não argparse.

- [ ] T016 [US2] Integrar grants, briefs e reconciliação de Results em `plugin/skills/grill-with-docs/scripts/grill_core/gauntlet_runs.py`, `plugin/skills/grill-with-docs/scripts/grill_workspace.py`, `tests/validate_gauntlet_converge_contract.py`, `tests/validate_gauntlet_scheduler_contract.py` e `tests/validate_partition_contract.py`.
  Files: ["plugin/skills/grill-with-docs/scripts/grill_core/gauntlet_runs.py", "plugin/skills/grill-with-docs/scripts/grill_workspace.py", "tests/validate_gauntlet_converge_contract.py", "tests/validate_gauntlet_scheduler_contract.py", "tests/validate_partition_contract.py"]
  Result: "Brief v2 transmite apenas task_ids/files/result_files atribuídos; reconcile aceita Result integrado da task/node/run/attempt corretos e marca somente completed aceito pelo líder."
  Limites: depende de T015; --files repetido por arquivo deve coincidir com node.files. Result schema grill-task-result/v1 não contém o próprio commit; terminal commit é observado no receipt do líder. Worker nunca altera tasks ou reservas. Conferir diff de rename nos dois paths e deleções, sem grants por prefixo; importações e resultados históricos mantêm proveniência.
  Check do worker: executar os três validadores Files com Result de outra tentativa/run/node/task, arquivo ausente, rename fora de Files e sidecar não declarado; nenhum caso marca checkbox ou passa converge. Resultado válido marca uma vez sem mudar pin semântico.

- [ ] T017 [US2] Implementar barreiras para tarefas fora do scheduler em `plugin/skills/grill-with-docs/scripts/grill_core/agent_orchestration.py`, `plugin/skills/grill-with-docs/scripts/grill_core/gauntlet_runs.py`, `plugin/skills/grill-with-docs/scripts/grill_core/attestation.py`, `plugin/skills/grill-with-docs/scripts/grill_workspace.py`, `tests/validate_agent_orchestration_contract.py` e `tests/validate_gauntlet_scheduler_contract.py`.
  Files: ["plugin/skills/grill-with-docs/scripts/grill_core/agent_orchestration.py", "plugin/skills/grill-with-docs/scripts/grill_core/gauntlet_runs.py", "plugin/skills/grill-with-docs/scripts/grill_core/attestation.py", "plugin/skills/grill-with-docs/scripts/grill_workspace.py", "tests/validate_agent_orchestration_contract.py", "tests/validate_gauntlet_scheduler_contract.py"]
  Result: "Guard comum exige aceites positivos por task/fase/fingerprint/DAG antes de wave, worker, prepare, remediation, payload e activity; última fase pendente impede fechamento mesmo com scheduler COMPLETE."
  Limites: depende de T013 e T016; usar activities/receipts existentes com task_binding, não scheduler novo. Em cada fase, convergir workers e aceitar read-only/deferred em ordem; dependency anterior a worker requer fase anterior explícita. Conferir fase contra tasks/report; revalidar inputs/fence no commit. CHANGES_REQUIRED, decisão humana pendente/negada, falha diagnosticada ou receipt stale não liberam. Deferred exige manifest e efeito observado; read-only não precisa Result/commit; checkpoint/reconcile/continuidade preservam aceites.
  Check do worker: `python3 tests/validate_agent_orchestration_contract.py AgentOrchestrationContract.test_task_phase_barriers` e validador de scheduler; reproduzir a fixture de cinco fases do quickstart, inclusive arquivo preparado antes do worker, prepare direto/remediation, fase mista, retomada sem repetição e última fase. Zero-worker continua recusado antes de admissão e worker-required continua exigindo execução real.

- [ ] T018 [US2] Implementar migração explícita e sucessão selada em `plugin/skills/grill-with-docs/scripts/grill_core/agent_orchestration.py`, `plugin/skills/grill-with-docs/scripts/grill_core/partition.py`, `plugin/skills/grill-with-docs/scripts/grill_core/gauntlet_runs.py`, `plugin/skills/grill-with-docs/scripts/grill_workspace.py`, `tests/validate_agent_orchestration_contract.py` e `tests/validate_partition_contract.py`.
  Files: ["plugin/skills/grill-with-docs/scripts/grill_core/agent_orchestration.py", "plugin/skills/grill-with-docs/scripts/grill_core/partition.py", "plugin/skills/grill-with-docs/scripts/grill_core/gauntlet_runs.py", "plugin/skills/grill-with-docs/scripts/grill_workspace.py", "tests/validate_agent_orchestration_contract.py", "tests/validate_partition_contract.py"]
  Result: "task-files-migrate aceita proposta completa de autor xhigh revisada por high com preview/hash; DAG selado fica byte-intacto, e revisão/run sucessora contém somente trabalho restante e importações provadas."
  Limites: depende de T017; preservar IDs/checkboxes/resultados, não derivar Files de extract_files. Apply stale, atividade concorrente ou reabertura silenciosa recusam. Revisão explícita escolhe arquivos r2; nem COMPLETE autoriza sobrescrever DAG/report. Importar v1 exige report, sidecar completed e integração correlacionados; v2 read-only/deferred exige receipt positivo. Checkbox sozinho não basta; nenhum worker terminal fictício, novo efeito duplicado ou execução legada indefinida na candidata. Manter auditoria do corpus legado separada dos fixtures executáveis v2, sem editar specs antigas para fazer teste passar.
  Check do worker: `python3 tests/validate_agent_orchestration_contract.py AgentOrchestrationContract.test_task_contract_migration` e validador de partition; testar DAG-SEALED, proposta divergente, importação falsa, aceites íntegros e restante vazio preservando conclusão histórica sem reabrir ciclo.

## Phase 8: US8 — Estilo padrão local do GWD nos dois ambientes (P1)

**Dependência**: US3, US5, US6 e US2. **Teste independente**: quickstart §7 offline; §8 live obrigatório em T029, sem equiparar instalado a funcional.

- [ ] T019 [US8] Integrar dependência e presença em `plugin/skills/grill-with-docs/assets/dependencies.json`, `plugin/skills/grill-with-docs/scripts/ensure_dependencies.py`, `tests/validate_dependencies_contract.py` e `tests/validate_agent_orchestration_contract.py`.
  Files: ["plugin/skills/grill-with-docs/assets/dependencies.json", "plugin/skills/grill-with-docs/scripts/ensure_dependencies.py", "tests/validate_dependencies_contract.py", "tests/validate_agent_orchestration_contract.py"]
  Result: "i-have-adhd é harness-plugin obrigatório mínimo 0.3.0; presença continua separada de habilitação e instalação usa somente os argv delegados aprovados."
  Limites: reutilizar detector Ponytail/Toolchain; registro ilegível é undetermined. Resolução da instalação efetiva é correlacionada ao runtime, não maior cache. Fonte ayghri/i-have-adhd; argv exatos de contracts/integrations.md, somente com allow-install. Disabled não provoca reinstalação; GRILL_SKIP_DEPENDENCIES não libera o novo gate nem torna as demais dependências consultivas obrigatórias. Sem download no core, hook/node, configuração global ou flag always-on.
  Check do worker: `python3 tests/validate_dependencies_contract.py`; injetar registros/listagens e capturar argv de ambos os runtimes, missing/outdated/unreadable/disabled e duas versões em cache, preservando semântica Ponytail. Completar as variantes de instalação de test_presentation_bootstrap.

- [ ] T020 [US8] Implementar loader e eixos de evidência em `plugin/skills/grill-with-docs/scripts/grill_core/agent_runtime.py`, `plugin/skills/grill-with-docs/scripts/grill_core/agent_orchestration.py` e `tests/validate_agent_orchestration_contract.py`.
  Files: ["plugin/skills/grill-with-docs/scripts/grill_core/agent_runtime.py", "plugin/skills/grill-with-docs/scripts/grill_core/agent_orchestration.py", "tests/validate_agent_orchestration_contract.py"]
  Result: "Load request aponta bytes aprovados da instalação efetiva; leitura integral observada na mesma sessão/configuração/geração comprova loaded, sem promover instalação ou saída de sucesso a comportamento."
  Limites: depende de T019; comparar versão e SHA-256 integral 3170b16ace00aecb0dd7feb54c0b5aa642e7502acda06ecd24fd89a11c7127e9, derivar body hash removendo só frontmatter. Preservar dez regras/exceções; recusar symlink, vazio, truncamento, UTF-8 inválido, versão/digest não admitidos. Leitura externa permitida só da instalação identificada, nunca escrita. Correlacionar enabled/trust/loading/behavior por fontes distintas; metadados solicitados, autorrelato, catálogo ou path impresso não provam carga.
  Check do worker: `python3 tests/validate_agent_orchestration_contract.py AgentOrchestrationContract.test_presentation_bootstrap`; load_request pendente→leitura observada→use_ready/work_ready true com behavior not_tested e functional_verified false; probe de outro cwd/config, identidade parcial, duplicata e observation stale recusam sem falso positivo.

- [ ] T021 [US8] Integrar readiness e continuidade da apresentação em `plugin/skills/grill-with-docs/scripts/grill_core/agent_orchestration.py`, `plugin/skills/grill-with-docs/scripts/grill_core/agent_runtime.py`, `plugin/skills/grill-with-docs/scripts/grill_workspace.py`, `plugin/skills/grill-with-docs/scripts/grill_status.py`, `tests/validate_agent_orchestration_contract.py` e `tests/validate_status_contract.py`.
  Files: ["plugin/skills/grill-with-docs/scripts/grill_core/agent_orchestration.py", "plugin/skills/grill-with-docs/scripts/grill_core/agent_runtime.py", "plugin/skills/grill-with-docs/scripts/grill_workspace.py", "plugin/skills/grill-with-docs/scripts/grill_status.py", "tests/validate_agent_orchestration_contract.py", "tests/validate_status_contract.py"]
  Result: "Preflight, init/adopt, resume, entradas canônicas e especialistas usam work_ready; use_ready continua aplicação ativa e functional_verified exige amostra live válida."
  Limites: depende de T020; preflight pré-ciclo é sem Store/receipt e pode retornar STYLE-LOAD-UNCONFIRMED com pedido utilizável; não exigir comportamento testado para primeira resposta. Suspensão humana da mesma sessão/incarnation/escopo conserva work_ready após compactação mesmo com loading stale, sem recarga; instalação/habilitação/compatibilidade/confiança continuam obrigatórias. Nova sessão, especialista e destino de continuidade iniciam ativos com carga própria. Saída GWD é out_of_scope; status apenas projeta, cleanup elegível continua disponível se estilo falhar.
  Check do worker: `python3 tests/validate_agent_orchestration_contract.py AgentOrchestrationContract.test_presentation_context` e validador de status; bootstrap→stop adhd mode→compactação→atividade autorizada tem zero reinjeção, outputs intactos, use_ready/functional_verified false; suspensão alheia/fonte ausente/disabled bloqueiam. Nova sessão e reativação explícita exigem carga corrente.

- [ ] T022 [US8] Ligar bootstrap às skills de entrada em `plugin/skills/grill-with-docs/SKILL.md`, `plugin/skills/grill-with-docs/references/session-protocol.md`, `plugin/skills/grill-with-docs/references/agent-orchestration.md`, `plugin/skills/grill-with-docs/assets/agent-orchestration.v1.json` e `tests/validate_agent_orchestration_contract.py`.
  Files: ["plugin/skills/grill-with-docs/SKILL.md", "plugin/skills/grill-with-docs/references/session-protocol.md", "plugin/skills/grill-with-docs/references/agent-orchestration.md", "plugin/skills/grill-with-docs/assets/agent-orchestration.v1.json", "tests/validate_agent_orchestration_contract.py"]
  Result: "GWD habitual conduz preflight, leitura integral, observation e revalidação antes da resposta de trabalho; invocations recebem presentation/template/suplemento, preservando conteúdo e alcance local."
  Limites: depende de T021; ler referência não auto-invoca upstream com invocação implícita desabilitada. Não editar metadados/cache/hook upstream ou arquivos globais, nem arquivos de instrução de consumidores. stop adhd mode suspende só apresentação; normal mode respeita pedido explícito e modos aplicáveis, nunca é emitido pelo loader como reset. Atualizar hashes suplementares; headings de versão serão sincronizados com os demais em T027.
  Check do worker: `python3 tests/validate_agent_orchestration_contract.py AgentOrchestrationContract.test_presentation_scope_preservation`; contexto entregue e reentrada preservam Ponytail/configuração, exceções upstream e documento de tasks com mais de cinco itens e grants exatos. A instrução local dos rootdocs será materializada em T027, sem dependência de worker sobre esse efeito.

## Phase 9: US4 — Orientar o modelo do chat principal (P2)

**Dependência**: US3 e US8 para as quatro entradas reais de contexto. **Teste independente**: início/retomada × dois runtimes, modelo ativo preservado.

- [ ] T023 [US4] Integrar recomendação nas entradas em `plugin/skills/grill-with-docs/scripts/grill_core/agent_orchestration.py`, `plugin/skills/grill-with-docs/scripts/grill_workspace.py` e `tests/validate_agent_orchestration_contract.py`.
  Files: ["plugin/skills/grill-with-docs/scripts/grill_core/agent_orchestration.py", "plugin/skills/grill-with-docs/scripts/grill_workspace.py", "tests/validate_agent_orchestration_contract.py"]
  Result: "Preflight/init/gauntlet-init/resume retornam coordinator_recommendation Sol no Codex ou Opus no Claude e active_model_changed=false."
  Limites: reutilizar valores da policy T001; não gravar configuração, alterar modelo principal ou relaxar pares dos especialistas. Ausência de modelo ativo não deve ser preenchida com o recomendado.
  Check do worker: completar test_specialist_admission e test_runtime_continuity nas quatro combinações, incluindo líder com modelo diferente; zero mudança de configuração e recomendação consistente com runtime explícito.

## Phase 10: US7 — Aprovar prévia visual antes das tasks frontend (P2)

**Dependência**: US5, US6, US2 e guards de contexto. **Teste independente**: quickstart §4; esta entrega platform-devops continua NOT_APPLICABLE sem criar frontend próprio.

- [ ] T024 [US7] Implementar classificação e preview em `plugin/skills/grill-with-docs/scripts/grill_core/agent_orchestration.py`, `plugin/skills/grill-with-docs/scripts/grill_core/agent_runtime.py`, `plugin/skills/grill-with-docs/scripts/grill_workspace.py` e `tests/validate_agent_orchestration_contract.py`.
  Files: ["plugin/skills/grill-with-docs/scripts/grill_core/agent_orchestration.py", "plugin/skills/grill-with-docs/scripts/grill_core/agent_runtime.py", "plugin/skills/grill-with-docs/scripts/grill_workspace.py", "tests/validate_agent_orchestration_contract.py"]
  Result: "gauntlet-preview valida classificação coerente, integração Impeccable observada, HTML autocontido e PNGs de estados/viewports, autoria xhigh e revisão independente high."
  Limites: não inferir NOT_APPLICABLE de flag; DU/handoff/PLAN-CONTEXT divergentes bloqueiam. Manifest fecha paths/media types/tamanhos/digests, entrypoint e capturas; rejeitar recurso externo e escape. Assinatura de PNG/HTML não julga estética. Sem engine/download no core, frontend próprio ou alteração incidental de PRODUCT/DESIGN project-wide; falta de captura/invocação comprovada não produz READY.
  Check do worker: construir `AgentOrchestrationContract.test_visual_gate` com imagens mínimas em memória/Git temporário e seams; brief textual, manifest truncado, captura ausente, autor/revisor inválidos e classificação contraditória falham. Platform-devops coerente dispensa preview e Impeccable.

- [ ] T025 [US7] Integrar decisão humana e guard anterior a tasks em `plugin/skills/grill-with-docs/scripts/grill_core/agent_orchestration.py`, `plugin/skills/grill-with-docs/scripts/grill_core/attestation.py`, `plugin/skills/grill-with-docs/scripts/grill_workspace.py`, `tests/validate_agent_orchestration_contract.py` e `tests/validate_checkpoint_contract.py`.
  Files: ["plugin/skills/grill-with-docs/scripts/grill_core/agent_orchestration.py", "plugin/skills/grill-with-docs/scripts/grill_core/attestation.py", "plugin/skills/grill-with-docs/scripts/grill_workspace.py", "tests/validate_agent_orchestration_contract.py", "tests/validate_checkpoint_contract.py"]
  Result: "gauntlet-preview-decide exige fonte humana observada vinculada ao digest; tasks só recebe contexto após revisão e aprovação correntes, rechecadas até partition."
  Limites: depende de T024; preview/apply com expected hash não fabrica aprovação a partir da flag. Guard comum em step-enter tasks, checkpoint in-progress/complete, attest e partition; qualquer asset alterado torna decisão STALE sem apagar histórico. Design permanece subfase de plan; sequência com onze macroetapas intacta.
  Check do worker: `python3 tests/validate_agent_orchestration_contract.py AgentOrchestrationContract.test_visual_gate` e validador de checkpoint; ausente, pendente, rejeitada, revisão ausente ou stale têm zero liberação; decisão positiva do mesmo digest libera e edição posterior impede aceite/partition.

## Phase 11: Transversal — integração completa, rootdocs e evidência de entrega

**Dependência**: todas as oito histórias. T026 é a última tarefa de worker. T027–T030 são deferred reais do líder, nesta ordem após todas as waves; nenhum worker consome sua saída. Os especialistas dessas tarefas retornam conteúdo ou julgamento e não escrevem os destinos de evidência.

- [ ] T026 Completar regressões de integração da candidata em `tests/validate_agent_orchestration_contract.py`, `tests/validate_partition_contract.py`, `tests/validate_checkpoint_contract.py` e `tests/validate_attestation_emitter_contract.py`.
  Files: ["tests/validate_agent_orchestration_contract.py", "tests/validate_partition_contract.py", "tests/validate_checkpoint_contract.py", "tests/validate_attestation_emitter_contract.py"]
  Result: "Cenários públicos de quickstart cobrem os oito requisitos através das fronteiras reais CLI/Store com seams, incluindo callbacks, suplemento entregue e recusas sem bypass."
  Limites: fechar lacunas de integração, não duplicar suítes por helper. test_rollout_and_canonical_pins verifica snapshots congelados, adoção posterior de COMPLETE sem reatestar e bloqueio de execução legada na candidata; test_task_phase_barriers verifica instruções efetivamente entregues à skill pinada e guards, não só texto. Os testes não operam o work item real nem declaram invocação live. Distribuição global/rootdocs só são verificados após T027.
  Check do worker: executar o novo validador completo e os três validadores compartilhados Files; preservar regressão de corpus histórico sem baixar o piso de cobertura nem excluir esta feature por nome. Registrar comandos/exit e desvios reais no resultado nativo do node.

- [ ] T027 Materializar documentação e distribuição finais em `README.md`, `AGENTS.md`, `CLAUDE.md`, `CHANGELOG.md`, `plugin/.claude-plugin/plugin.json`, `plugin/.codex-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.agents/plugins/marketplace.json`, `tests/validate_distribution.py`, `plugin/skills/grill-with-docs/SKILL.md`, `plugin/skills/grill-with-docs/references/session-protocol.md` e `.grill/work-items/feature-new-subagents-unified-69f619a1a4774d598e4a46c77396f0fa/IMPLEMENTATION-INTEGRATION.md`.
  Files: ["README.md", "AGENTS.md", "CLAUDE.md", "CHANGELOG.md", "plugin/.claude-plugin/plugin.json", "plugin/.codex-plugin/plugin.json", ".claude-plugin/marketplace.json", ".agents/plugins/marketplace.json", "tests/validate_distribution.py", "plugin/skills/grill-with-docs/SKILL.md", "plugin/skills/grill-with-docs/references/session-protocol.md", ".grill/work-items/feature-new-subagents-unified-69f619a1a4774d598e4a46c77396f0fa/IMPLEMENTATION-INTEGRATION.md"]
  Result: "Líder materializa conteúdo de autor xhigh já revisto por high, oito pontos iguais a 6.0.0, changelog cumulativo e bootstrap local documentado; evidência registra autoria, revisão e diff efetivo."
  Ownership: tarefa inteira deferred por conter evidência real de integração. Especialista recebe inputs e retorna o conteúdo proposto dos arquivos; revisor high distinto examina esses bytes; líder apenas aplica mecanicamente e registra as fontes. Nenhum especialista recebe escrita da reserva, nenhum worker recebe rootfile omitido pelo parser, e nenhuma wave depende desse efeito anterior.
  Limites: executar após T026 e convergência de todas as waves. Atualizar os quatro manifests, VERSION do validador, headings únicos de GWD/protocolo/README; preservar as demais asserções. Documentar oito requisitos, verbos/recusas, alcance local, papéis, migration/cleanup e rollout, sem alegar prova criptográfica. AGENTS/CLAUDE recebem somente instrução local de bootstrap, preservando Ponytail e conteúdo alheio. CHANGELOG inclui uma entrada 6.0.0 e mantém histórico: arquivo adicional à lista orientadora de plan, necessário à asserção existente de distribuição, explicitamente delimitado pelo líder em msg_73ff00cd1681 sob FR-020/SC-007; não alterar plan/spec.
  Check do líder: comparar o diff materializado com os bytes revistos; `python3 tests/validate_distribution.py` precisa passar com os oito pontos e exatamente um heading 6.0.0 no CHANGELOG. Este é o primeiro gate global de distribuição; foco dos workers anteriores não o substitui. Não publicar nesta tarefa.

- [ ] T028 Comprovar integração live de orquestração e continuidade em `.grill/work-items/feature-new-subagents-unified-69f619a1a4774d598e4a46c77396f0fa/IMPLEMENTATION-INTEGRATION.md`.
  Files: [".grill/work-items/feature-new-subagents-unified-69f619a1a4774d598e4a46c77396f0fa/IMPLEMENTATION-INTEGRATION.md"]
  Result: "Evidência real dos dois runtimes correlaciona contexto, requested/effective, payload, resultado/diagnóstico durável, close confirmado e retomada com aceites intactos."
  Ownership: líder coleta/materializa evidência em projeto e sessões de ensaio isolados com transporte comprovado; especialista julga onde necessário, sem escrita da reserva. Esta é validação da candidata, não transferência da campanha histórica.
  Limites: depende de T027; disponibilizar candidata pela superfície proprietária e registrar versão/hash efetivamente usados, sem atualizar o bundle histórico nem adotar o work item corrente. Exercitar autor xhigh/revisor high em identidades distintas em Codex e Claude, caminho de implementação não-frontier, falha/read-only e cleanup de recursos descartáveis identificados. Trocar runtimes nos dois sentidos na mesma worktree de ensaio, preservando outputs/efeitos aceitos; observar recomendação Sol/Opus sem mudar o modelo. Sem matar atividade viva, inferir close de silêncio ou repetir efeito desconhecido; capacidade ausente registra impedimento, não PASS. Sondagens antigas de launch não substituem esta integração.
  Check do líder: registrar fontes de preparação, efetivo, dispatch, settlement e read-back de cada recurso; comparar refs/digests dos aceites antes/depois e provar que só tentativa não aceita repetiu. Revisor high independente avalia as evidências; gaps concretos retornam a correção antes de aceitar o requisito, sem worker/receipt fictício.

- [ ] T029 Comprovar estilo local em sessões novas dos dois CLIs em `.grill/work-items/feature-new-subagents-unified-69f619a1a4774d598e4a46c77396f0fa/STYLE-LIVE-VALIDATION.md` e `.grill/work-items/feature-new-subagents-unified-69f619a1a4774d598e4a46c77396f0fa/IMPLEMENTATION-INTEGRATION.md`.
  Files: [".grill/work-items/feature-new-subagents-unified-69f619a1a4774d598e4a46c77396f0fa/STYLE-LIVE-VALIDATION.md", ".grill/work-items/feature-new-subagents-unified-69f619a1a4774d598e4a46c77396f0fa/IMPLEMENTATION-INTEGRATION.md"]
  Result: "C1, C2, A1 e A2 têm carga GWD observada antes da resposta, conversa completa conforme as dez regras/exceções, compactação e controles externos íntegros, com revisão high independente."
  Ownership: líder executa/observa a matriz live de quickstart §8 e persiste fontes completas antes do cleanup; revisor high distinto dos autores julga comportamento e completude. Nenhum teste offline ou regex preenche conformant por si só.
  Limites: depende de T027–T028; sessões líderes próprias do ensaio invocam GWD canonicamente, sem invocação manual de i-have-adhd nem macroetapa em processo auxiliar. Usar os quatro prompts fixos completos do quickstart em início e retomada novos de Codex e Claude; registrar runtime/session/incarnation/config, versão/hash, enablement, trust, leitura real, prompts/respostas/IDs e checkpoint. Não reinstalar 0.3.0 presente nem pedir novamente a aprovação válida do hook; disabled ou conflito novo requer diagnóstico específico, sem editar configuração alheia ou flag global.
  Check do líder: nos dois runtimes, testar compactação ativa com recarga e ensaio adicional stop adhd mode→compactação→trabalho autorizado sem reinjeção, work_ready true, use_ready/functional_verified false e Ponytail/outputs intactos; nova sessão volta ativa com carga própria. Comparar sessões externas novas antes/depois em outro root sem GWD nos ancestrais, ausência de injeção e configuração preservada, sem exigir texto estocástico idêntico; testar também saída explícita do GWD. Revisor avalia todos os seis fatos dos prompts, resposta detalhada e regras não aplicáveis com motivo. Instalado/enabled, hook aprovado, exit 0, autorrelato, outro estilo conciso ou bloqueios corretos não satisfazem FR-024/SC-008. Falha em qualquer CLI mantém esse aceite pendente.

- [ ] T030 Consolidar validação e prontidão para gates canônicos em `.grill/work-items/feature-new-subagents-unified-69f619a1a4774d598e4a46c77396f0fa/IMPLEMENTATION-INTEGRATION.md`.
  Files: [".grill/work-items/feature-new-subagents-unified-69f619a1a4774d598e4a46c77396f0fa/IMPLEMENTATION-INTEGRATION.md"]
  Result: "Dossiê correlaciona cada FR/SC a código, check, evidência live/revisão e bytes correntes, distinguindo implementação integrada de verify/review/ship ainda governados pelo ciclo."
  Ownership: líder executa checks, consolida resultados e obtém julgamento high independente necessário; não declara a macroetapa no lugar de sua skill canônica.
  Limites: depende de T027–T029 com resultados positivos; contar validadores pelo marcador ==> e registrar skips reais. Comparar hashes dos assets/skills canônicos, tabelas/ESSENTIAL, Constituição/WORKFLOW e bundle histórico preservado; não remover asserções para passar. Verificar rootdocs e todos os oito pontos após materialização. A evidência referencia retornos completos e limitações, não inferência de funcionamento por instalação; nenhum gate constitucional é dispensado.
  Check do líder: `python3 tests/run_validators.py` e `git diff --check` na candidata integrada; registrar também os validadores de distribuição, workflow versions, step skill registry, tier binding e publish incluídos na suíte. Repetir somente por mudança, falha ou preocupação não resolvida. Qualquer failure retorna a correção delimitada e nova revisão dos bytes afetados antes do aceite; esta task não faz merge, push, tag, release, adoção histórica ou atestação de macroetapa.

## Dependências, paralelismo e estratégia

Ordem obrigatória: Setup → Foundation → US1 → US3 → US5 → US6 → US2 → US8 → US4 → US7 → Transversal. Todas as P1 precedem as P2; US2 vem após US6 porque seus aceites de atividades e migração precisam de autoria/revisão independentes. US8 estende a continuidade e os mesmos guards; US4 só acrescenta orientação. US7 usa a admissão especializada e a entrada de tasks já integradas.

Dentro das fases, a ordem T crescente resolve dependências explícitas; arquivos compartilhados agrupam essas tasks no mesmo node histórico. Não marcar [P] para fingir independência de escritores do CLI, agent_orchestration, Store ou validador comum. A largura é a emitida pelo algoritmo, nunca uma promessa de três workers; se resultar um node por fase, PARTITION-DEGRADED é honesto. Após leitura do DAG/report reais, o líder despacha apenas nodes prontos e usa os grants exatos mais o sidecar nativo observado, sem reagrupamento manual.

O marco após US1 valida cleanup isolado. A entrega segue obrigatoriamente até a última tarefa, matriz live, verify/review e ship autorizado. Regressão significativa falha antes do conserto e passa após ele; cada worker roda seus checks focados. O líder consolida evidência e revalida o conjunto somente com a candidata integrada e distribuição sincronizada.

### Gates posteriores, pertencentes ao líder

Fechar/reconciliar implement-parallel pelo bundle histórico apenas depois dos resultados atribuídos e deferred positivos. Continuar as invocações canônicas de converge, verify e review; revisão high independente de código/segurança deve referir os bytes finais e não ser substituída por teste determinístico. Evidências de T028–T030 são entradas desses gates, não suas atestações antecipadas. Se uma correção mudar inputs/resultados, revalidar os checks e julgamentos afetados, inclusive amostra live quando a integração mudar.

Na macroetapa verify/ship, executar o bump gate existente contra a base real de integração selecionada, sem SHA fictício. Ship continua condicionado aos gates e à autorização humana vigente; usar a skill canônica, não publicar a partir de uma task de worker ou deferred. Pipeline existente cria tag imutável e GitHub Release no mesmo anchor, antes de repontar marketplaces; verificar esse resultado pelo pipeline, sem release manual. Esses efeitos ocorrem depois de implement-parallel, evitando dependência circular de ship para fechar tasks.

Somente após ship encerrado pode o líder adotar explicitamente o work item histórico COMPLETE na 6.0.0, importando referências verificadas/inventário sem repetir etapas ou reatestar o passado. Atividade posterior pendente usa a ponte/revisão apropriada; não há execução legada indefinida na candidata. Até então conservar campanha, pins e CLI/cache absoluto 5.4.1.

## Rastreabilidade de entrega

| FR | Tasks de construção e aceite | Resultado verificável |
|---|---|---|
| FR-001 | T005–T007, T009, T026, T028 | Cleanup nos callbacks de etapa/wave/troca, inclusive COMPLETE e replay |
| FR-002 | T003, T006–T007, T010, T028 | Resultado/diagnóstico durável precede close de worker, falho e read-only |
| FR-003 | T006–T007, T028 | Identidade/integração/árvore/evidência conferidas por recurso sem perda |
| FR-004 | T005–T007, T009, T028 | Checkpoint e status mostram motivos e UNKNOWN sem falso sucesso |
| FR-005 | T023, T028 | Quatro entradas recomendam Sol/Opus, zero troca silenciosa |
| FR-006 | T005, T008–T009, T017–T018, T028 | Ponte nos dois sentidos conserva outputs e efeitos aceitos |
| FR-007 | T002–T005, T009, T028 | CAS/fence, checkpoint e quiescência comprovados antes de retomar |
| FR-008 | T001, T024–T025 | Preview HTML/PNG com Impeccable observado, autor e revisor corretos |
| FR-009 | T024–T025, T026 | Zero entrada/aceite/partition sem aprovação humana corrente |
| FR-010 | T001, T011, T024–T026, T030 | Design em plan, onze etapas, NOT_APPLICABLE coerente |
| FR-011 | T001, T010–T011, T028 | Todo COMO, inclusive entrevista, plan/tasks/design, usa par xhigh |
| FR-012 | T004, T010–T011, T026–T030 | Líder invoca/coordena; especialista não escreve reserva nem fecha etapa |
| FR-013 | T012–T013, T027–T030 | Revisor high distinto de todos os autores e inputs correntes |
| FR-014 | T011–T013, T026, T030 | Passes mistos separados; check não satisfaz julgamento |
| FR-015 | T003, T010, T012, T028 | Efetivo/capacidade antes do payload e rechecados no aceite |
| FR-016 | T001, T014–T016, T026 | Grant v2 coincide exatamente com Files e Result declarado |
| FR-017 | T014–T015, T026 | Prosa irrelevante, gramática inválida sem grant parcial |
| FR-018 | T004, T018, T026, T030 | Proposta revisada/hash, DAG selado intacto e sucessão explícita |
| FR-019 | T002, T004, T014–T018, T026 | Scope seguro, reserva do líder e aceites por task/fase em todos os guards |
| FR-020 | T001–T030 e gates posteriores | Oito requisitos, offline/live, distribuição 6.0.0 e release canônica |
| FR-021 | T019–T022, T027, T029 | Stack obrigatória e carga automática no início/retomada de ambos |
| FR-022 | T020–T022, T027, T029 | Alcance GWD, suspensão legítima e controles externos/Ponytail preservados |
| FR-023 | T019–T021, T029 | Presença, habilitação, carga e comportamento distintos; recusas nominais |
| FR-024 | T020–T022, T029–T030 | C1/C2/A1/A2, respostas completas e revisão high, sem falso functional |

| SC | Tasks e prova de aceite |
|---|---|
| SC-001 | T006–T007, T028: confirmação/motivo de cada recurso, zero perda e zero sucesso suposto |
| SC-002 | T008–T009, T017–T018, T028: duas direções, zero duplicação, concorrência/incoerência recusadas |
| SC-003 | T023, T028: início e retomada nos dois runtimes sem mudar modelo |
| SC-004 | T010–T013, T028: autoria/revisão verificáveis, zero auto-review e divergência antes do envio |
| SC-005 | T024–T026: visual aprovado antes de tasks, plataforma sem impedimento e onze etapas |
| SC-006 | T014–T018, T026: grants exatos, prosa ignorada e DAG selado preservado |
| SC-007 | T026–T030 e gates canônicos posteriores: cobertura integral e distribuição/publicação governadas |
| SC-008 | T019–T022, T027, T029–T030: quatro entradas live, compactação, controles externos e conteúdo integral |

Contagem prevista: **30 tasks**; Setup 1, Foundation 4, US1 2, US2 5, US3 2, US4 1, US5 2, US6 2, US7 2, US8 4 e transversal 5. São 26 tasks de workers e quatro deferred do líder, sem task read-only unmapped. As contagens descrevem trabalho previsto; não resultados já executados.

## Conferência documental e do bootstrap

Leituras: template Spec Kit, spec/plan/research/data-model, três contratos, quickstart e checklist GO 27/27; código histórico de partition, validação de paths, brief/reconcile e skills grill-partition/grill-implement-parallel 5.4.1. Simulação pura em memória confirmou que Files multiline não é consumido, rootfiles/./ não geram grant e sidecar nativo vem do node; a delimitação do líder preservou esse rollout sem ativar v1 nesta campanha.

Conferência desta versão do HOW: 30 IDs únicos, 11 fases, 26 tasks despacháveis e T027–T030 deferred; zero unmapped, omissões ou duplicações. Extração dos workers coincide com Files; cada grant simulado acrescenta somente o sidecar nativo de seu node. Estrutura, escopo e piso de tier históricos passaram em memória; 11 nodes com dependência na fase anterior, max_workers 1 e PARTITION-DEGRADED. O corpus histórico mantém 20 de 22 features com largura mínima 2, atendendo à tolerância já existente sem enfraquecer o teste. Os 34 arquivos futuros de plan estão cobertos; os únicos adicionais declarados são CHANGELOG e os dois destinos reais de evidência do líder. Hash do CLI histórico conferido; o manifest completo segue pré-condição operacional do líder.

A leitura de `tests/validate_distribution.py` identificou também a exigência de CHANGELOG para a versão corrente. A inclusão documental necessária foi confirmada pelo líder, sem alterar o gate nem plan/spec. Esta autoria escreve somente tasks.md; não implementa, instala, acessa rede, repete baseline, cria DAG/run/checkpoint, muda pins, gera atestação ou escreve evidência operacional. Revisão high distinta ainda deve avaliar o HOW e sua cobertura antes de o líder aceitar a etapa tasks.

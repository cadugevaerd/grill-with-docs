# Implementation Plan: Orquestração, continuidade e escopo dos agentes

**Branch Git**: `cadugevaerd/feat-new-subagents` | **Date**: 2026-09-13 | **Spec**: [spec.md](spec.md)

**Feature directory**: `specs/030-agent-orchestration`. O identificador devolvido por setup-plan é o ponteiro da feature, não uma autorização para trocar a branch Git.

**Estado**: desenho técnico dos oito requisitos, FR-001..024 e SC-001..008, pronto para revisão independente. A spec ampliada é a entrada atestada; R-0010/ADR-0005 fixam default local ao projeto/fluxo GWD. Este documento não atesta a macroetapa nem declara a implementação ou a prova funcional concluídas.

**Input**: [handoff FASE-001](../../.grill/work-items/feature-new-subagents-unified-69f619a1a4774d598e4a46c77396f0fa/handoffs/FASE-001-SPECIFY-HANDOFF.md), [PLAN-CONTEXT](../../.grill/work-items/feature-new-subagents-unified-69f619a1a4774d598e4a46c77396f0fa/PLAN-CONTEXT.md), ADR-0001..0005 aceitos e [STACK-I-HAVE-ADHD](../../.grill/work-items/feature-new-subagents-unified-69f619a1a4774d598e4a46c77396f0fa/STACK-I-HAVE-ADHD.md). Entrega única DU-001, `development-type: platform-devops`.

## Summary

Entregar os oito requisitos como contrato suplementar `grill-agent-orchestration/v1`, aplicado pelo CLI e pelo Store: cleanup com identidade e confirmação por recurso; continuidade entre runtimes por checkpoint; recomendação do líder; especialistas obrigatórios e revisão independente; design frontend aprovado antes de tasks; arquivos explícitos como única fonte de grants; i-have-adhd obrigatório, carregado pela GWD no alcance local e comprovado em respostas reais nos dois CLIs.

Reutilizar partition, grants, convergência, locks, hashes e cadeia de invocação canônica existentes. Preservar onze macroetapas, documentos project-wide, tabelas/registries/catálogos v3/v4 e recibos antigos. A política nova é obrigatória para novos trabalhos; trabalho legado precisa adoção explícita antes de executar sob o novo binário. Compatibilidade histórica não é opt-out de execução.

Este plano não autoriza implementação, cleanup real ou publicação. Autor técnico escreve somente os artefatos desta spec; invocação, registro, revisão independente e atestação da macroetapa continuam com o líder.

## Technical Context

**Language/Version**: Python >=3.10, somente biblioteca padrão; JSON estrito, Markdown e Git CLI existente.

**Primary Dependencies**: nenhuma biblioteca Python nova. Stack Git/Spec Kit/extensões/backlog e Ponytail >=4.9.0 preservada; adicionar `i-have-adhd@i-have-adhd` como `kind: harness-plugin`, `required: true`, mínimo 0.3.0, fonte `ayghri/i-have-adhd`, instalação delegada às CLIs. Codex/Claude são harnesses da sessão. Orca é transporte opcional já instalado, não dependência do bundle. Impeccable é exigido apenas no caminho frontend. O carregador local de estilo usa leitura stdlib e não requer node nem executa o hook upstream; o core não baixa bytes.

**Storage**: Store existente em `git-common-dir/grill/`, com `orchestrator.json`, journal, receipts e WAL; `state.json` do work item continua projeção de desenvolvimento. Novo bloco opcional `agent_orchestration`, de schema próprio, guarda contextos, recursos, atividades e continuidade. Sem banco ou daemon adicional.

**Testing**: `unittest`, `tempfile`, `unittest.mock`, Git local sintético e seams de runtime/clock/fault. `python3 tests/run_validators.py` descobre `validate_*.py`. Suíte não acessa rede nem exige `node`, `specify`, `backlogctl`, `claude`, `codex` ou Orca reais.

**Target Platform**: Linux, Windows, macOS; matriz atual Python 3.10/3.13. Não usar `/proc`, `ps` ou sinais POSIX como prova portátil de sessão.

**Project Type**: plugin CLI/platform-devops; **não há frontend próprio nesta entrega**. Fixtures visuais mínimas testam suporte para consumidores; sem app web, site ou Terraform.

**Performance Goals**: parser linear no texto antes do agrupamento existente; uma observação Git por worktree por avaliação e uma observação de runtime por recurso. Sem polling/rede em status ou hooks; timeout de operação externa significa desconhecido.

**Constraints**: identidade e recibos imutáveis; paths exatos, sem glob; efeitos com intenção/read-back; sem downgrade ou autoria inferida. Hashes são evidência estrutural auditável, não prova criptográfica de execução.

**Scale/Scope**: oito histórias, FR-001..024 e SC-001..008, uma fase/DU. Limites existentes de workers preservados e especialistas contabilizados. Sem transferência de workers, worktree ou memória privada; sem default global de apresentação.

## Constitution Check

Gate antes da pesquisa: **PASS para desenho documental**. Constituição 2.1.0 e WORKFLOW v4 lidos integralmente; nenhuma decisão local serve como waiver.

| Princípio | Antes do desenho | Rechecagem após desenho |
|---|---|---|
| Evidência antes de afirmação | Rastrear código/chamadores e capacidades observáveis | Fonte de observação e read-back por recurso; ausência bloqueia |
| Work item isolado e ownership | Somente documentos autorizados | Guard comum de sessão/época; especialistas não escrevem evidência de coordenação |
| Feature/fix plan-only | Sem código, commits ou atestação do autor | Preview é artefato de planejamento do consumidor; nenhum novo caminho executável de ship |
| Sequência obrigatória | Onze etapas | `plan.design` interno; tasks recebe gate, sem etapa extra ou mudança nas tabelas |
| Verify/review antes de ship | Gates externos mantidos | Testes não substituem revisor high; autorização humana de ship preservada |
| Fail-closed sem waiver | Não presumir suporte pelo nome | Modelo/esforço/sessão/checkpoint/preview não comprovados bloqueiam |
| Rastreabilidade | FASE-001/DU-001/ADR-0001..0005 | Pins, receipts, sucessão de campanhas, quatro evidências do estilo e mapa FR→check |
| Tier/esforço Orca | `launch.effective` do autor observado como Astra/xhigh | Pares explícitos; sessão nova quando muda esforço; revisão high em outra identidade |
| Bump obrigatório | Nenhuma alteração de plugin nesta etapa | Implementação publicável **6.0.0**, oito pontos idênticos e gate antes de merge/push/tag |
| Release obrigatória | Sem publicação | Pipeline cria release na mesma tag/commit imutável; sem release manual |

Gate após pesquisa/contratos: **PASS de desenho, sem exceção constitucional**. Isso não declara capacidade universal de runtime. Recusas são casos negativos obrigatórios; a entrega também exige os caminhos positivos de continuidade/especialistas e de estilo nos dois CLIs, conforme quickstart. Bloquear corretamente não satisfaz sozinho FR-020/FR-024.

## Project Structure

### Documentation (this feature)

```text
specs/030-agent-orchestration/
├── spec.md                    # entrada preservada
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cli.md
│   ├── task-files.md
│   └── integrations.md
└── tasks.md                   # somente na macroetapa posterior
```

### Source Code (repository root)

```text
plugin/skills/grill-with-docs/
├── SKILL.md
├── references/
│   ├── session-protocol.md
│   └── agent-orchestration.md           # novo suplemento de invocação
├── assets/
│   ├── agent-orchestration.v1.json      # nova política e hashes
│   ├── task-files.v1.template.md        # novo formato via argumentos
│   └── workflow-*.json                 # snapshots existentes preservados
└── scripts/
    ├── grill_workspace.py
    ├── ensure_dependencies.py
    ├── grill_status.py
    └── grill_core/
        ├── agent_orchestration.py      # novo: política e estado
        ├── agent_runtime.py            # novo: evidência de runtime
        ├── store.py
        ├── gauntlet.py
        ├── gauntlet_runs.py
        ├── partition.py
        └── attestation.py
tests/
├── validate_agent_orchestration_contract.py # novo
├── validate_*_contract.py                    # regressões existentes afetadas
├── validate_distribution.py
└── run_validators.py                         # glob; não precisa editar
```

**Structure Decision**: apenas dois módulos novos: política/estado e tradução de observações externas. Store mantém a fronteira persistente; CLI é dono do I/O. Não criar framework de adapters, novo scheduler, serviço ou frontend.

## Desenho e ordem de construção

1. **Contrato/Store**: bloco versionado por work item, épocas/fences e union estrita de eventos para reutilizar WAL sem inventar wave para especialistas. Guard comum impede escrita por sessão antiga/worker. [Data model](data-model.md) define invariantes e recovery de Store/state.
2. **Recursos**: registrar sessão, worktree e branch separadamente; corrigir gates de cleanup e identidade Git; preservar resultados de execução mesmo após remoção; varredor automático em fechamento e troca.
3. **Continuidade**: épocas de ativação e ponte explícita de campanhas, sem editar a ativação/admission original ou recibos aceitos; CAS e observação de quiescência; reconciliação de efeitos antes de replay.
4. **Especialistas/design**: liberação do payload somente após prova de modelo/esforço; revisão em identidade diferente; preview visual e aprovação corrente controlam tasks. Matriz completa em [integrations.md](contracts/integrations.md).
5. **Tasks/partition**: lista explícita Files, resultados também declarados, DAG v2 e grants exatos; aceite por task/fase via activities/receipts para read-only/deferred e guard antes da fase seguinte; adaptar briefs/reconciliação; migração explícita sem reescrever DAGs selados.
6. **Integração/rollout**: suplemento fornecido como argumento das skills canônicas; bootstrap local de apresentação pela GWD atualizada, novas sessões obrigatórias e migração de legados; documentação, testes offline e amostras live dos dois CLIs, oito versões e gates de publicação.

Os itens são grupos técnicos para tasks, não macroetapas novas nem autorização de execução neste plan. Arquivos compartilhados requerem ordenação de ownership; não tentar paralelizar escritores de `grill_workspace.py`/`store.py`.

### Limpeza

O guard `_run_for_worker` mistura identidade com elegibilidade de preparação e recusa COMPLETE. Extrair leitura/identidade comum com finalidade explícita; permitir cleanup em run terminal sem permitir preparação. `cleanup_eligible` não pode continuar flag nunca adquirida: elegibilidade será derivada dos fatos atuais e registrados.

Identidade de worktree não é igualdade com `base_commit`: worker pode ter commits legítimos. Correlacionar identidade de criação, path real, registro Git, ref, commit terminal e commit integrado. Antes de remover, comprovar ancestry na branch de execução, HEAD/ref ainda iguais, árvore sem sujeira/untracked/ignorados exclusivos e evidência durável fora do recurso. Sessão ativa/desconhecida impede remover seu workspace.

Fechar sessão após aceitação de resultado ou diagnóstico pelo líder, inclusive falha/read-only, com encerramento confirmado pelo runtime. Falha de worker preserva arquivos pendentes. Usar `git worktree remove` sem force e confirmar ausência; depois `git update-ref -d refs/heads/... OLD_OID` e confirmar ref ausente. Não usar clean/reset/branch -D/prune global. Persistir intenção antes do efeito e observação depois; replay inspeciona antes de repetir. Retidos/UNKNOWN constam do checkpoint individualmente.

Disparadores do mesmo varredor: aceitação de agente, wave terminal, wave convergida, etapa completa/bloqueada e prepare-switch. Persistir obrigação junto do fechamento; comandos mutáveis reentrantes drenam pendências. Status/hooks são somente leitura. Cleanup não desfaz resultado aceito. Novos recursos têm lifecycle separado: worker TERMINAL/FAILED permanece assim; corrigir leitores de sucesso de CLEANED legado sem tratar falha como sucesso. Testar `_node_ready`, `_converged_lineage_head`, `_wave_would_complete`, `_all_converged` e fechamento após limpar a primeira wave.

### Continuidade

Novo seletor `effective_activation` usa contexto corrente do contrato novo; sem adoção, leitura histórica continua no caminho existente. Não modificar `.grill/gauntlet.yaml`, admission, WORK-ITEM.json ou sequência. `gauntlet.current_activation` comprova o destino; guardar snapshot sucessor e vínculo ao anterior no Store. Todos os leitores de ativação, `attest` e a fronteira de admission usam a mesma seleção.

Prepare-switch bloqueia novos despachos, persiste checkpoint e limpa elegíveis; exige ausência comprovada de atividade concorrente. Destino declara runtime, verifica inatividade da identidade de origem e recursos de todos os agentes, e adquire época maior via CAS. Lease expirado ou silêncio não prova encerramento. Worker ativo não é transferido nem morto para liberar troca.

A campanha atual inclui runtime/adapter e sete campos estritos. Criar campanha sucessora, novo recovery_generation_id, mesmo run_id lógico e plan_revision; recibo continuity liga snapshots/campanhas e outputs aceitos intactos. Judge mantém igualdade dentro da campanha; apenas a primeira invocação nova cruza predecessor histórico mediante essa ponte. Epoch antiga não fecha etapa nova. Separar run_id da campanha de run_id do scheduler; o scheduler mantém base/admission/DAG, e a ponte autoriza o contexto sucessor a operar esse run sem alterar seus pins. Troca não zera orçamento de remediation.

Checkpoint selecionado por head comprometido, não mtime: identidade, sequência, corrente, hashes, accepted outputs, tentativas interrompidas, operações e recursos. Store/state/receipts devem concordar. Repetir somente tentativas não aceitas e reconciliar efeitos por operation_id/read-back. Merge usa OIDs/parents/ancestry; checkpoint/reconcile usam hashes. Push/release permanecem nas skills donas, e efeito desconhecido bloqueia em vez de ser repetido. Não prometer exactly-once externo sem observação.

### Especialistas e visual

Política própria, sem liberar frontier no binding de workers: autor `gpt-6-astra/xhigh` ou `fable/xhigh`; revisor mesmo modelo obrigatório com `high`, sessão distinta de todos os autores dos bytes revisados. Líder recebe Sol/Opus como recomendação, nunca mudança silenciosa. Todo COMO em plan/tasks/design e decisões novas durante execução vai ao autor; todos os julgamentos de revisão ao revisor. Testes/agrupamento mecânicos continuam determinísticos.

Criar sessão de preparação sem payload técnico/grant; observar modelo/esforço/identidade; só então liberar o trabalho. Transporte sem separação ou prova suficiente bloqueia. `launch.effective` comprova configuração efetiva de lançamento, não execução criptográfica nem ausência de fallback posterior; revalidar antes de aceitar output. Alias só é aceito por resolução comprovada do runtime, nunca prefix matching.

Classificar frontend pelo handoff/DU/PLAN-CONTEXT coerentes. Subfase de plan invoca Impeccable; exige preview HTML autocontido e capturas PNG das superfícies/estados/viewports acordados, manifest de todos os bytes, autor xhigh, revisão independente high e aprovação humana do digest corrente. Brief textual sozinho falha. Core não baixa engine nem altera PRODUCT.md/DESIGN.md project-wide incidentalmente. Falta de ferramenta de captura ou prova da integração bloqueia resultado visual.

Gate roda antes da invocação de tasks, em checkpoint in-progress/complete, attest e partition; alteração de qualquer asset da preview invalida aprovação. Esta entrega tem classificação coerente platform-devops, sem superfície: NOT_APPLICABLE, sem preview própria.

### Grants e migração

[task-files.md](contracts/task-files.md) especifica marcador, `Files: [...]` JSON e `Result:` para tarefas de worker. Result deve estar em Files; nenhum sidecar é adicionado implicitamente. `Files: []` declara ausência de escrita, sem grant de worker; encaminhar execução determinística ao líder ou julgamento à atividade especializada read-only.

Normalizar apenas `./` inicial; recusar traversal, absolutos POSIX/Windows, controles, globs, diretórios e symlink nos ancestrais existentes. Arquivo novo/raiz é válido. DAG v2 preserva fases-barreira e contém fingerprint semântico, task_ids, result_files e mapa accepted_tasks de importações comprovadas; `nodes[].files` é exatamente a união das declarações. Reservas de evidência encaminham a tarefa inteira ao líder. Checkboxes normalizados não invalidam o pin; mudança real exige novo partition. Reconciliar somente resultados de task/node/run/attempt atribuídos.

Preservar todas as fases e IDs no report, inclusive fases sem workers. Em cada fase, convergir workers e depois aceitar read-only/deferred na ordem declarada, por activities/receipts existentes com task_binding (task_id/fase/fingerprint/DAG); nenhuma task anterior pendente libera wave/worker/prepare/remediation/payload posterior. O guard comum revalida inputs/fence e exige aceite positivo, incluindo julgamento/aprovação humana quando necessários; falha ou diagnóstico persistido não satisfaz barreira. Reconcile/checkpoint de continuidade mantêm esses aceites e o fechamento da etapa exige também a última fase, além dos workers reais cobrindo o DAG. Dependência que antecede worker deve estar em fase anterior explícita; não inferir scheduler novo da prosa.

Conjunto sem tarefa despachável é limite de execução: partition-emit retorna PARTITION-NO-WORKERS com listas completas, antes da admissão de run, sem DAG-VALID ou checkpoint completo de partition/implement-parallel. Não prometer ciclo novo inteiramente read-only/deferred, inventar worker ou substituir a classe worker-required congelada. Se já não há trabalho restante, preservar a conclusão histórica; caso contrário, rever escopo real das tasks sem criar trabalho artificial. Planos mistos continuam cobrindo todas as tarefas.

Novos trabalhos adotam o contrato integral desde init. No binário 6.0.0, legado pode ser lido/auditado e limpar recursos comprovados, mas continuar trabalho exige preview/adoption com hash esperado; não há `--legacy` de execução. Tasks antigas recebem proposta de autor xhigh/revisor high, nunca migração por heurística. DAG selado não é sobrescrito, mesmo em run COMPLETE: continuação do restante usa nova revisão/run explícita e mapa dos resultados aceitos, sem duplicá-los. O DAG sucessor contém nodes apenas para trabalho restante; accepted_tasks liga os IDs já concluídos a receipts/commits integrados, sem cunhar workers terminais fictícios.

### Integração sem invalidar o ciclo atual

Manter bytes das onze skills canônicas e manifests/catálogos v3/v4. Atualizar a skill de entrada `plugin/skills/grill-with-docs/SKILL.md` e seu `session-protocol.md`, que não são substitutos das onze entradas canônicas; preservar `grill-partition`, `grill-implement-parallel` e o agent pinado. Publicar política, template e protocolo **suplementares**, com hashes próprios; o contexto de invocação os fornece como argumentos específicos à mesma skill canônica resolvida. Isso integra geração de tasks, especialistas e novos resultados sem fingir que ler protocolo substitui invocar skill. O suplemento substitui explicitamente a receita legada de sidecar/heurística e a execução de deferred somente após todas as waves pela ordem por fase acima; exige parar partition antes da admissão quando não houver workers. Checagem de integração comprova a instrução entregue e os guards, preservando DAG-VALID e prova real worker-required.

Não alterar `.agents/skills`, `.claude/skills` ou manifests Spec Kit só para injetar política. Se uma mudança exigir substituir de fato a skill canônica, retornar a plan para versionar integração e migração; não manter hash antigo sobre bytes novos.

Campanha deste ciclo informada pelo líder: `run-b12537dfc4dca1621cc1f08d`, registry `sha256:f514df103b3d2dbf0cf786e95c9b59e7b1dc79e08b2ce7fe30b99f8b8bb3e35c`. Concluir o ciclo de implementação com o bundle já selado; testar o novo em fixtures/instância isolada. Após release, o mesmo work item pode adotar o novo contrato no estado completo: importar referências aos receipts aceitos, registrar época inicial e inventário, sem reexecutar etapas ou mudar campanha histórica. Para atividade posterior/retomada pendente, usar ponte explícita. Adotar não é reatestar o passado. A transição é única e auditável; binário novo não oferece execução legada indefinida.

Para tornar esse rollout executável, o líder fixa **antes de alterar plugin/** a raiz real do bundle histórico, versão e manifest de hashes de scripts/assets/skills utilizados, incluindo o CLI. Nesta máquina existe `/home/carlosaraujo/.codex/plugins/cache/grill-with-docs/grill-with-docs/5.4.1`; sua existência não dispensa comparar os pins da campanha e preservar os bytes até o fim do ciclo. Todos os comandos de coordenação/atestação/cleanup da campanha histórica passam a usar o caminho absoluto desse CLI e seus módulos/assets irmãos; não voltar a `python3 plugin/.../grill_workspace.py` quando a fonte já contiver 6.0.0. As onze invocações continuam nos entrypoints e bytes canônicos resolvidos/pinados, sem trocar catálogo. Se houver atualização de cache, interrupção ou mudança de sessão, revalidar o manifest e recusar divergência; não corrigir pins nem adotar o novo contrato no meio do ciclo para contornar o problema. O líder mantém cópia preservada do bundle quando necessário fora dos recursos elegíveis a cleanup, com identidade/digest registrados. [Quickstart](quickstart.md) separa os comandos do ciclo histórico dos testes da candidata.

### Apresentação local: i-have-adhd pela GWD

Usar o corpo integral do `skills/i-have-adhd/SKILL.md` da instalação efetiva do runtime, lido como referência de apresentação pela GWD explicitamente iniciada. Não tentar auto-invocar a skill upstream: `disable-model-invocation: true` e `policy.allow_implicit_invocation: false` tornam esse caminho inadequado. O hook upstream injeta somente com flag no diretório Claude e falha silenciosamente; aprovação desse hook não o torna local. Não criar `.i-have-adhd-always`, alterar AGENTS global, redirecionar diretórios de configuração ou editar o cache upstream.

O bootstrap da GWD resolve a dependência, pede observação de habilitação no runtime e lê os bytes íntegros antes da primeira resposta de trabalho. A policy admite inicialmente 0.3.0 com SHA-256 `3170b16ace00aecb0dd7feb54c0b5aa642e7502acda06ecd24fd89a11c7127e9`; mínimo instalado e compatibilidade de conteúdo são verificações separadas. Remover apenas frontmatter para apresentação, manter as dez regras/exceções e registrar hashes do arquivo e do corpo. Versão/digest novo exige revisão da policy, sem carregar texto arbitrário ou substituir por resumo próprio.

O suplemento delimita aplicação ao projeto/fluxo GWD, preserva instruções superiores, pedidos explícitos e conteúdo dos artefatos, e mantém Ponytail como política de implementação. `stop adhd mode` suspende somente a apresentação na sessão, sem desabilitar plugin nem Ponytail. O comando genérico `normal mode` respeita o pedido explícito e os contratos dos modos que o reconhecem; o loader nunca o emite para resetar configurações. Saída explícita do GWD encerra sua aplicação de apresentação; sessão externa nova nunca recebe o suplemento. `AGENTS.md` e `CLAUDE.md` deste projeto recebem instrução local de bootstrap, preservando o restante; consumidores recebem o comportamento pela GWD atualizada, sem alteração automática de seus arquivos de instrução.

Início, retomada, novo contexto após compactação e cada entrada canônica verificam novamente o vínculo sessão/runtime/raiz/digest. `use_ready` representa carga/aplicação ativa; entradas e despachos exigem `work_ready`, que também aceita suspensão humana comprovada da mesma sessão/incarnation/escopo, mantendo instalação/habilitação/compatibilidade/confiança obrigatórias. Compactação nessa suspensão revalida sua fonte e permite continuar sem recarregar o corpo, mesmo com loading stale; não repete outputs nem muda Ponytail. Nova sessão, inclusive especialista/destino de continuidade, não herda suspensão e volta ao default ativo com carga própria. `invocation_context.presentation` transmite essa distinção sem tornar GWD uma décima segunda etapa. Hook/status continuam read-only; o caminho funcional é a rotina da skill descrita em [integrations.md](contracts/integrations.md).

Preflight distingue presença/versão, habilitação, carregamento e comportamento. Não preenche loaded ao imprimir um path nem functional ao observar exit 0. Bootstrap ativo pode fornecer pedido de carga com diagnóstico pendente; após leitura real a observação da sessão libera uso, sem exigir uma amostra comportamental de release antes da primeira resposta. Suspensão válida libera apenas trabalho, sem ser aceite positivo de FR-024 ou functional_verified. O aceite da entrega exige evidência adicional de respostas reais e controle externo em sessões novas de **ambos** os CLIs. Configuração global existente conflitante é diagnosticada e preservada, nunca removida silenciosamente.

## Mapa FR → módulos → checks

| FR | Módulos/integração | Check observável |
|---|---|---|
| FR-001 | gauntlet_runs, agent_orchestration, checkpoint/converge | Cleanup automático em etapa, wave intermediária e COMPLETE; replay drena intenção |
| FR-002 | agent_runtime, acceptance/terminal | Resultado/diagnóstico persistido antes de close, inclusive falha/read-only |
| FR-003 | cleanup, helpers Git, recursos | Sujo/ignorado/não integrado/divergente retém; exato integrado remove sem force |
| FR-004 | checkpoint/status | Motivos por recurso; tentativa desconhecida não vira sucesso |
| FR-005 | preflight/init/gauntlet-init/resume | Início/retomada × dois runtimes; modelo ativo preservado |
| FR-006 | effective_activation, continuity, attestation | Trocas nos dois sentidos, outputs idênticos, efeitos aceitos não repetidos |
| FR-007 | Store CAS, fence, observe | Concorrência/worker vivo/checkpoint ausente/epoch antiga/unknown bloqueiam |
| FR-008 | policy, Impeccable, preview | Frontend exige visual renderizado e integração observada; brief falha |
| FR-009 | step-enter/checkpoint/attest/partition | Aprovação ausente/negada/stale bloqueia antes de tasks |
| FR-010 | classificação e snapshots | Onze etapas iguais; esta feature é NOT_APPLICABLE |
| FR-011 | author policy/briefs | Plan/tasks/design/novo COMO no par obrigatório |
| FR-012 | guards e cadeia canônica | Especialista não fecha macroetapa nem escreve coordenação |
| FR-013 | reviewer policy | Revisões de requisitos/plano/tasks/design/código/segurança com high e outro autor |
| FR-014 | atividades por tipo | Passe misto separado; teste verde não substitui revisão |
| FR-015 | runtime/admission | Efetivo ausente/divergente/alias não provado bloqueia payload/aceite |
| FR-016 | parser/DAG/grant | Raiz/novo/subdir/./; grant exato inclui apenas Result declarado |
| FR-017 | parse_tasks | Prosa com barras irrelevante; ausência/invalidez não gera DAG |
| FR-018 | migration/partition/pins | Proposta explícita; DAG selado byte-intacto |
| FR-019 | safe path/scope/declare/prepare/converge, activities | Escape/symlink/evidência/fora de escopo recusados; read-only/deferred aceitas por task/fase antes de workers posteriores |
| FR-020 | integração/docs/distribuição/suite | Oito requisitos em comportamento; oito versões iguais; offline, caminhos live e publicação |
| FR-021 | dependencies.json, preflight, GWD/session-protocol | Instalado/habilitado; início e retomada Codex/Claude carregam sem comando manual i-have-adhd |
| FR-022 | bootstrap local, suplemento, AGENTS/CLAUDE do projeto | Suspensão→compactação→trabalho sem estilo; nova sessão ativa; controle externo/configurações/Ponytail preservados |
| FR-023 | agent_runtime, presentation no contexto/status | Quatro eixos separados; missing/disabled/trust/loaded insuficiente sem falso functional |
| FR-024 | quickstart live, evidência da sessão e revisão high | Quatro combinações início/retomada; respostas completas nos dois CLIs e controle externo |

## Lista explícita de arquivos da implementação futura

Esta lista orienta tasks; não concede escrita automática. Arquivos repetidos nos oito pontos contam uma vez para ownership.

- Novos: `plugin/skills/grill-with-docs/scripts/grill_core/agent_orchestration.py`, `plugin/skills/grill-with-docs/scripts/grill_core/agent_runtime.py`, `plugin/skills/grill-with-docs/assets/agent-orchestration.v1.json`, `plugin/skills/grill-with-docs/assets/task-files.v1.template.md`, `plugin/skills/grill-with-docs/references/agent-orchestration.md`, `tests/validate_agent_orchestration_contract.py`.
- Core/CLI: `plugin/skills/grill-with-docs/scripts/grill_workspace.py`, `plugin/skills/grill-with-docs/scripts/grill_core/store.py`, `plugin/skills/grill-with-docs/scripts/grill_core/gauntlet.py`, `plugin/skills/grill-with-docs/scripts/grill_core/gauntlet_runs.py`, `plugin/skills/grill-with-docs/scripts/grill_core/partition.py`, `plugin/skills/grill-with-docs/scripts/grill_core/attestation.py`, `plugin/skills/grill-with-docs/scripts/grill_status.py`.
- Integração/docs: `plugin/skills/grill-with-docs/scripts/ensure_dependencies.py`, `plugin/skills/grill-with-docs/assets/dependencies.json`, `plugin/skills/grill-with-docs/SKILL.md`, `plugin/skills/grill-with-docs/references/session-protocol.md`, `README.md`, `CLAUDE.md`, `AGENTS.md`.
- Regressões: `tests/validate_gauntlet_run_contract.py`, `tests/validate_gauntlet_converge_contract.py`, `tests/validate_gauntlet_scheduler_contract.py`, `tests/validate_partition_contract.py`, `tests/validate_checkpoint_contract.py`, `tests/validate_attestation_emitter_contract.py`, `tests/validate_status_contract.py`, `tests/validate_orchestrator_store_contract.py`, `tests/validate_dependencies_contract.py`.
- Oito pontos SemVer 6.0.0: `plugin/.claude-plugin/plugin.json`, `plugin/.codex-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.agents/plugins/marketplace.json`, `tests/validate_distribution.py`, `plugin/skills/grill-with-docs/SKILL.md`, `plugin/skills/grill-with-docs/references/session-protocol.md`, `README.md`.

Preservar `workflow_versions.py`, `workflow_v3.py`, `workflow_v4.py`, ESSENTIAL, templates/registries/catálogos/confiança v3/v4, `grill-local-skills.manifest.json`, agent de implementação e skills canônicas existentes, Constituição e WORKFLOW.md. `.grill/` e `.specify/reports/` são somente evidência operacional futura escrita pelo líder, não arquivos de implementação desta tarefa.

## Verificação e riscos

Uma suíte nova cobre as fronteiras do contrato; ampliar validadores existentes apenas onde muda comportamento. Injetar relógio, runtime/Git e falhas antes/depois de intenção, efeito e commit. Regressões essenciais: duas retomadas concorrentes, resposta atrasada, cleanup entre waves, conteúdo ignorado exclusivo, symlink/ref trocados, resposta perdida, release parcial e hashes v3/v4 congelados. [Quickstart](quickstart.md) define cenários executáveis previstos.

Riscos concretos: falta de telemetria de runtime, fallback posterior de modelo, concorrência externa ao Git, recovery entre Store/state, legado sem evidência suficiente e receita antiga de sidecar no suplemento. Para apresentação: overrides de habilitação, confiança do hook pendente, versão upstream divergente, perda do contexto e conflito de instruções. Casos negativos têm diagnóstico; casos positivos precisam evidência real, sem inventar prova de execução. A instalação/habilitação 0.3.0, o hook aprovado no Codex e o launch Claude fable/high observado não demonstram ainda o estilo funcional; esse aceite permanece trabalho da implementação/verify posterior.

## Complexity Tracking

Sem violação constitucional. Dois módulos novos correspondem a fronteiras reais de estado/política e evidência externa; apresentação reutiliza essas fronteiras e o detector existente. Sem frontend próprio, novo workflow, catálogo canônico, scheduler ou biblioteca Python; uma dependência de harness exigida explicitamente pelo usuário.

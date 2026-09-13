# Quickstart de validação: spec 030

Este guia descreve cenários executáveis **previstos para a implementação dos oito requisitos FR-001..024/SC-001..008**. Não executar cleanup, troca ou instalação sobre recursos reais para validar este plano. Os comandos de produção novos estão definidos em [contracts/cli.md](contracts/cli.md), mas ainda não existem no baseline 5.4.1.

## Pré-condições

- Python >=3.10 e Git local; sem pacotes Python adicionais.
- Checkout isolado para implementação e repositórios temporários criados pelos validadores.
- Runtime, clock, observações e falhas substituídos por seams no CI; não exigir rede, node, specify, backlogctl, Codex, Claude ou Orca reais.
- O novo validador `tests/validate_agent_orchestration_contract.py` é uma entrada única de unittest que exerce o CLI/core com Store real temporário e provider falso. Os nomes de cenários abaixo devem ser implementados nessa classe pública de teste; não são ferramentas novas de produção.

Baseline executado pelo líder durante plan em 2026-09-13; registro em `cycle-baseline-validation.json` no work item:

```bash
python3 tests/run_validators.py
```

Resultado observado: **exit 0**, 28 validadores na suíte completa; **um teste skipped** porque o host não apresenta o alias `/var -> /private/var`. Isso verifica a árvore anterior à implementação; não prova as capacidades novas, qualidade visual ou execução live de qualquer modelo. O autor desta ampliação não repetiu a suíte, não implementou código/tests e não fez commits, checkpoints ou atestação de macroetapa.

## 1. Cleanup no fechamento e entre waves

Após implementar:

```bash
python3 tests/validate_agent_orchestration_contract.py AgentOrchestrationContract.test_cleanup_lifecycle
python3 tests/validate_gauntlet_run_contract.py
python3 tests/validate_gauntlet_converge_contract.py
python3 tests/validate_gauntlet_scheduler_contract.py
```

Cenário cria dois workers em Git temporário, um com commit integrado e um com falha/trabalho pendente, mais especialista read-only. Provider falso identifica as três sessões e confirma seus términos. Líder persiste outputs/diagnósticos; fechamento chama cleanup automaticamente.

Esperado: sessão dos três encerrada com confirmação; worktree/ref do integrado removidas; worktree/ref com falha preservadas e listadas com motivo. Read-only não precisa worktree para ser limpo. Repetir com run COMPLETE e entre primeira/segunda waves; o sucesso do primeiro node continua satisfazendo dependências depois da limpeza.

Variantes da mesma verificação: dirty tracked, untracked e ignored; evidência exclusiva; session close unknown; ref mudou depois do preview; worktree/ref reaproveitados; processo desconhecido; efeito de remove executado com resposta perdida. Nenhuma variante apaga dados não elegíveis nem apresenta tentativa como sucesso. Segunda chamada reconcilia a mesma intenção e não remove recurso novo que reutilizou o nome.

## 2. Troca Codex→Claude→Codex

```bash
python3 tests/validate_agent_orchestration_contract.py AgentOrchestrationContract.test_runtime_continuity
python3 tests/validate_checkpoint_contract.py
python3 tests/validate_attestation_emitter_contract.py
```

Fixture aceita specify/plan, começa uma atividade de tasks, persiste uma operação ainda não aceita e solicita prepare-switch. Adapter falso primeiro informa worker ativo: bloqueio. Após resultado/diagnóstico aceito e sessões encerradas, prepara checkpoint e retoma com runtime de destino. Repetir direção inversa.

Esperado: mesmo projeto/work_id/fase/worktree/branch e scheduler admission/DAG; epochs distintas; nova campanha ligada à anterior; refs/digests dos outputs aceitos byte-idênticos. Somente tentativa interrompida pode repetir. Recibo atrasado da origem é recusado. Mudança no plano não é encoberta como troca de runtime. Contador de remediation não é resetado.

Injetar ausência/corrupção de checkpoint, Store/state divergentes, outro runtime ativo, sessão unknown, duas retomadas CAS simultâneas e falha nas janelas before-state/after-state/before-commit. Uma retomada vence; a outra não produz efeito. Recovery completa apenas intenção comprovada; terceiro conteúdo não é sobrescrito. Efeito externo sem observação de outcome bloqueia em vez de repetir push/release.

## 3. Especialistas e recomendação do líder

```bash
python3 tests/validate_agent_orchestration_contract.py AgentOrchestrationContract.test_specialist_admission
python3 tests/validate_agent_orchestration_contract.py AgentOrchestrationContract.test_activity_coverage
python3 tests/validate_tier_model_binding_contract.py
```

Fixture percorre início/retomada × Codex/Claude. Recomenda Sol/Opus sem gravar modelo ativo. Nos autores técnicos exige Astra/fable xhigh; nos revisores, high e sessão independente de todos os autores do input.

Contador do seam de envio técnico deve permanecer zero quando modelo/esforço forem ausentes ou divergentes, alias não for comprovado, sessão não puder fechar, ou transporte não separar bootstrap/payload. Configuração solicitada sozinha não libera trabalho. Observação consistente libera uma vez; fallback observado antes do aceite invalida output. Review pelo próprio autor e tentativa de escrever `.grill/`/`.specify/reports/` bloqueiam.

A matriz cobre requisitos, plan, checklist, tasks, analyze, design, código, segurança, converge, verify/review/ship. Teste determinístico continua executável sem modelo, mas não satisfaz revisão. Workers de implementação mantêm binding não-frontier, incluindo o caminho legado prepare.

## 4. Preview frontend e gate anterior a tasks

```bash
python3 tests/validate_agent_orchestration_contract.py AgentOrchestrationContract.test_visual_gate
python3 tests/validate_checkpoint_contract.py
```

Fixture frontend usa HTML autocontido e PNGs mínimos locais, manifest e observações falsas de Impeccable/autor/revisor. Testa preview ausente, brief textual, revisão ausente, decisão humana pendente/rejeitada, aprovação antiga e asset alterado.

Esperado: zero liberação de contexto de tasks em todos os casos inválidos. Com revisão high independente e aprovação humana no digest corrente, liberar entrada; mudar qualquer asset depois impede attest/conclusão/partition. Captura mínima de teste verifica estrutura/vínculo, não qualidade visual. Nenhum download ou engine real é chamado.

Fixture platform-devops sem superfície retorna NOT_APPLICABLE e não exige Impeccable/preview. Verificar exatamente onze etapas e fontes project-wide intactas. Classificação contraditória não pode virar NOT_APPLICABLE por flag.

## 5. Files, Result e DAG selado

```bash
python3 tests/validate_partition_contract.py
python3 tests/validate_agent_orchestration_contract.py AgentOrchestrationContract.test_task_contract_migration
python3 tests/validate_agent_orchestration_contract.py AgentOrchestrationContract.test_task_phase_barriers
```

Entrada nova segue [task-files.md](contracts/task-files.md): Files declara `.gitignore`, `./build-dist.sh`, arquivo novo/subdiretório e Result explícito por tarefa; descrição cita ACTIVE/FREE e arquivo fora de Files. Preview de partition deve mostrar exatamente a união normalizada, incluindo somente os Results declarados.

Esperado: referências da prosa não entram no grant; nenhuma inserção automática de sidecar; Files ausente/JSON inválido/duplicado/traversal/symlink/absoluto falham sem DAG parcial. Files vazio não gera grant feature-wide; evidência reservada vai inteira ao líder. Root files/new files são aceitos sem exigir que o leaf já exista.

Selar DAG v1 temporário e tentar apply de nova saída no mesmo path: DAG-SEALED, bytes preservados. Proposta de migração revisada/expected hash produz nova revisão explícita sem alterar outputs aceitos. Checkbox reconcile mantém fingerprint semântico; outra alteração de task o muda. Result de outra run/node/attempt não marca completed.

Barreiras: fixture mista tem fase 1 só read-only de revisão/aprovação e deferred que prepara arquivo; fase 2 tem worker que consome esse arquivo; fase 3 só read-only/deferred; fase 4 outro worker; fase 5 revisão final sem worker. Report conserva IDs/fases completos. Antes do aceite positivo das activities vinculadas por task_id/fase/fingerprint/DAG da fase 1, wave-declare, worker-declare, prepare legado/remediation e liberação do payload da fase 2 retornam TASK-PHASE-PENDING, com zero grant/envio. Aceite da revisão com CHANGES_REQUIRED, aprovação humana pendente/negada, diagnóstico de falha, output stale ou receipt de task/fase/revisão diferente não liberam. Confirmar bookkeeping/arquivo preparado e aprovações correntes libera uma vez; fase 3 impede fase 4 da mesma forma. Em fase mista, activities fora do scheduler aguardam a convergência dos workers daquela fase.

Retomada entre barreiras preserva aceites por referência e só repete tentativa não aceita; alteração de input/fence entre check e commit bloqueia. Reconcile marca também read-only/deferred por seus receipts, sem Result/commit fictício; run COMPLETE não permite checkpoint/attest completo de implement-parallel enquanto a fase 5 estiver pendente. Após os aceites, a prova real de workers cobrindo o DAG continua obrigatória. O teste de integração confere que o suplemento entregue à skill pinada substitui expressamente o deferred final pela ordem por fase.

Fixture inteiramente read-only/deferred, ou revisão sem nenhum worker restante: partition-emit retorna BLOCKED/PARTITION-NO-WORKERS, exit 2 e listas/fases completas antes de gauntlet-run/admissão; zero DAG, workers e receipt terminal novo. Tentativa de forçar DAG vazio ou atestação zero-worker continua recusada pelas classes/guards existentes. Não é caso positivo de conclusão de implement-parallel: preservar histórico aceito, ou rever escopo real antes desse ciclo, sem inventar tarefas para preencher nodes.

## 6. Adoção, callbacks automáticos e publicação

O ciclo que constrói 6.0.0 usa CLI e skills do bundle histórico selado, não a fonte candidata depois de editada. Antes da primeira alteração em plugin, o líder registra raiz real, versão, hashes de scripts/assets/skills e pins canônicos; preserva esses bytes até encerrar a campanha. Exemplo do bundle 5.4.1 observado nesta máquina, após validar seu manifest contra a campanha:

```bash
GWD_CYCLE_BUNDLE=/home/carlosaraujo/.codex/plugins/cache/grill-with-docs/grill-with-docs/5.4.1
python3 "$GWD_CYCLE_BUNDLE/skills/grill-with-docs/scripts/grill_workspace.py" status .
```

Usar esse executável absoluto em **todas** as operações da campanha histórica, com os argumentos/ROOT reais de cada verbo. O caminho pessoal é exemplo observado, não constante de distribuição; uma cópia preservada validada pode ser usada se o cache estiver sujeito a atualização. CLI observado: SHA-256 `f71350d84b0ac517f462d6829cdd818425b5248e3675a746cce9c52e42523d2f`; registry v4 observado: `f514df103b3d2dbf0cf786e95c9b59e7b1dc79e08b2ce7fe30b99f8b8bb3e35c`. Ambos são âncoras de conferência, não substituem o manifest do bundle inteiro. Os onze entrypoints continuam sendo os que a resolução canônica pinou; scripts auxiliares usados por essas invocações também devem resolver para o bundle preservado quando operarem a campanha.

Os comandos de teste abaixo exercitam **a fonte candidata** e seus repositórios temporários. Não usar o CLI 6.0.0 source para operar `.grill/` da campanha 5.4.1 no meio do ciclo; isso exigiria adoção prematura. Mudança de sessão/cache exige revalidar os hashes; divergência bloqueia e é resolvida restaurando/selecionando o bundle correto, nunca reescrevendo pins. A candidata live usa outro projeto/sessão de ensaio, com seu próprio contexto novo; adoção do work item histórico só ocorre pelo procedimento explícito após o ciclo concluído.

```bash
python3 tests/validate_agent_orchestration_contract.py AgentOrchestrationContract.test_rollout_and_canonical_pins
python3 tests/validate_orchestrator_store_contract.py
python3 tests/validate_status_contract.py
python3 tests/validate_dependencies_contract.py
python3 tests/validate_distribution.py
python3 tests/validate_workflow_versions_contract.py
python3 tests/validate_step_skill_registry_contract.py
python3 tests/validate_publish_contract.py
```

Novo init aplica política integral; legado é legível, mas execução no novo binário exige adoção. Preview não escreve. Apply stale recusa. Adoção de ciclo COMPLETE preserva todas as campanhas/receipts e permite inventário/cleanup, sem repetir etapas. Remover o bloco depois de adotado é rejeitado. Status/read-only não fecham sessões ou escrevem state.

Exercitar callbacks reais dos comandos de terminal/converge/checkpoint/prepare-switch com seam: helpers de cleanup não podem ser apenas opcionais ou chamadas manuais de teste. Checkpoint aceito com cleanup pendente responde explicitamente que resultado já está aceito; retry drena pendência sem executar a etapa.

Comparar hashes antes/depois dos registries, catálogos, snapshots de confiança, ESSENTIAL, classes worker-required e onze skills canônicas v3/v4. A skill de entrada GWD e seu protocolo recebem bootstrap novo; isso não autoriza editar grill-partition, grill-implement-parallel ou o agent pinado. Contexto de invocação deve transmitir suplemento/template/apresentação ao mesmo entrypoint, incluindo ordem por fase e parada antes de admissão sem workers; ausência impede avanço. Nenhum manifest antigo recebe bytes de skill novos.

Verificar SemVer **6.0.0** nos oito pontos enumerados em plan.md. Pipeline de publicação e tag/release continuam governados pelos gates existentes; não publicar durante esses testes. Bump gate real é executado contra a base de integração selecionada na macroetapa verify/ship, com os comandos já definidos no repositório, não com SHA fictício.

## 7. Stack e carregador local de apresentação — offline

Após implementar os cenários no único validador novo:

```bash
python3 tests/validate_agent_orchestration_contract.py AgentOrchestrationContract.test_presentation_bootstrap
python3 tests/validate_agent_orchestration_contract.py AgentOrchestrationContract.test_presentation_context
python3 tests/validate_agent_orchestration_contract.py AgentOrchestrationContract.test_presentation_scope_preservation
python3 tests/validate_dependencies_contract.py
python3 tests/validate_partition_contract.py
```

Usar formatos de instalação/observação e corpo aprovado em fixtures locais, sem CLI real. Confirmar presença/versão separadas de enablement, trust, loading e behavior; Ponytail mantém a semântica anterior. Resolver root/versão efetivamente selecionados pelo runtime, não apenas o maior cache. Remover somente frontmatter preserva todas as regras/exceções; hash divergente, versão não admitida, arquivo truncado/vazio, symlink e UTF-8 inválido recusam carga.

Caso positivo ativo: preflight sem loaded retorna load_request e STYLE-LOAD-UNCONFIRMED; leitura observada na mesma sessão/hash produz use_ready true, work_ready true, behavior not_tested e functional_verified false. Depois, init/retomar/step-enter transmitem presentation à mesma skill canônica. O seam confirma que nenhum node/hook/instalador/listagem real foi chamado. Instalação com allow-install só usa argv delegados do manifesto; disabled não provoca reinstalação nem edição global. Componente ausente/antigo, registro ilegível, disabled, habilitação ambígua e confiança pendente geram seus códigos específicos.

Variantes: plugin list de outro cwd/config, override de sessão, IDs parciais, duplicatas de scope, catálogo contendo apenas descrição, autorrelato do modelo, exit 0 sem conteúdo, observation de outra incarnation e corpo omitido do payload não autorizam loaded. Resposta curta semelhante ao estilo também não prova carga. Sem amostra real, behavior segue not_tested; regex positivo sozinho não passa o gate de aceite.

Reentrada ativa após compactação, nova sessão e troca de CLI exigem carga nova sem reexecutar outputs aceitos. Em test_presentation_context, percorrer bootstrap → instrução humana `stop adhd mode` → compactação → próxima entrada/atividade autorizada: fonte de suspensão válida da mesma sessão/incarnation/escopo, instalação/habilitação/compatibilidade/confiança correntes, loading stale, work_ready true, use_ready false, functional_verified false e zero recarga/injeção do corpo após suspensão. O trabalho continua sem estilo, com Ponytail e outputs aceitos intactos; seu despacho de especialista novo inicia a sessão destino ativa com carga própria. Suspensão de outra sessão, fonte ausente/divergente, disabled ou instalação ausente não liberam o gate. Nova sessão/incarnation e retomada em outro CLI voltam ao default ativo, sem herdar suspensão; reativação explícita na mesma sessão exige recarga corrente.

Saída do GWD produz application out_of_scope, sem liberar trabalho GWD ou mutar plugin/global config. Comparar bytes de configurações alheias e ausência de flags novas; preservar blocos Ponytail. Tasks com mais de cinco itens e paths de cache somente na descrição mantêm conteúdo/grants completos. Cleanup elegível continua funcionando mesmo se carregamento do estilo ficar indisponível.

## 8. Prova funcional do estilo — sessões reais Codex e Claude

Obrigatória antes de aceitar FR-024/SC-008, após implementar/instalar a GWD candidata e com repositório descartável autorizado. Não integra `tests/run_validators.py`; exige autenticação e ferramentas reais dos harnesses. ROOT abaixo é o caminho real do repositório com bundle válido/handoff de teste e pré-requisitos normais preparados; registrar o valor efetivo. O controle externo fica em outro root, sem instruções/artefatos GWD nos ancestrais. Cada CLI nova é a própria sessão líder do ensaio, invocando GWD canonicamente; não é processo auxiliar executando uma macroetapa do líder anterior.

### Preparar e registrar o ambiente

Instalar a candidata pelo mecanismo proprietário já usado para GWD e registrar versão/hash dos arquivos efetivamente carregados. Manter Ponytail e demais configurações. Registrar versões reais com `codex --version` e `claude --version`; coletar as listagens abaixo sem tratá-las como prova de comportamento:

```bash
codex plugin list --json
claude plugin list --json
```

Se i-have-adhd faltar, usar os comandos autorizados em [integrations.md](contracts/integrations.md); não reinstalar 0.3.0 já presente. Resolver disabled pelo controle nativo adequado, preservando configuração alheia. Aprovar confiança do hook somente quando a interface exigir e houver autorização; a aprovação Codex registrada em STACK já ocorreu nesta máquina e não deve ser pedida novamente sem mudança real. Não criar flag global para fazer o teste passar.

Registrar antes/depois os digests das configurações relevantes e blocos locais, presença/ausência de flags always-on e defaults externos, sem publicar segredos. Instalação/habilitação pode adicionar somente o registro esperado do componente; demais bytes/valores permanecem preservados. Default global preexistente que contamine o controle externo resulta STYLE-SCOPE-CONFLICT, não licença para apagá-lo. Resolver especificamente esse impedimento antes de declarar isolamento comprovado.

### Matriz de execução e prompts fixos

Abrir `codex` e `claude` em sessões novas a partir de ROOT, um por vez se compartilham work item. Registrar session ID/incarnation, runtime/modelo/configuração efetivos, comando de abertura e fontes do plugin. Não reutilizar a sessão de autoria ou sondagem do revisor como evidência de estilo.

| Caso | Entrada na própria sessão | Evidência exigida |
|---|---|---|
| C1 | Codex novo: `$grill-with-docs iniciar ROOT` | Carga real pela GWD antes da primeira resposta de trabalho; nenhuma chamada manual i-have-adhd |
| C2 | Codex novo: `$grill-with-docs retomar ROOT` | Checkpoint do ensaio, nova incarnation/carga própria e outputs aceitos intactos |
| A1 | Claude novo: `/grill-with-docs iniciar ROOT` | Mesma prova usando instalação/habilitação Claude selecionadas |
| A2 | Claude novo: `/grill-with-docs retomar ROOT` | Mesmo checkpoint desse ensaio, carga própria, sem herança falsa de loaded |

Usar o work_id identificado pela GWD quando houver mais de um bundle. Fechar/estacionar o ensaio anterior pelo protocolo de quiescência antes de retomar; não matar agentes ativos. Usar contextos independentes para C1/C2 e A1/A2 ou a ponte de continuidade definida, sem editar runtime na identidade. Em cada caso, depois do bootstrap, enviar **sem mencionar estilo ou i-have-adhd**:

```text
No cenário de teste, preciso conferir estes seis fatos do bundle: work_id, branch, hash do WORKFLOW, hash da Constituição, último receipt aceito e recurso preservado com seu motivo. Oriente a conferência sem executar ações e mantenha todos os seis fatos; indique o primeiro passo e estime o tempo para eu fazê-lo.
```

```text
No cenário, já conferi work_id e branch. Ainda faltam os outros quatro fatos. Mostre onde estou e o próximo passo, sem repetir ações concluídas nem descartar pendências.
```

```text
No cenário, a conferência retornou ERROR-CHECKPOINT: digest divergente. Explique o que esse resultado permite concluir e qual é a próxima verificação; não afirme uma causa ainda não comprovada.
```

```text
Explique detalhadamente os seis fatos originais e por que cada um é necessário. Preserve os nomes e todos os fatos, mesmo que a resposta precise ser longa.
```

Revisar respostas completas: ação/resultado primeiro, passos numerados quando sequenciais, estado corrente, próximo passo concreto quando pendente, estimativa em unidades para o operador sem promessa falsa, erro factual, ausência de tangentes e abertura ornamental. Conferir agrupamento e **zero perda dos seis fatos**, inclusive na resposta detalhada. Avaliar as dez regras/exceções upstream; regra não acionada é not_applicable com motivo, sem aprovação universal por um único prompt. Instruções superiores do harness prevalecem; registrar conflito que impeça cumprir comportamento requerido.

Em pelo menos uma sessão ativa de cada runtime, disparar compactação pelo comando nativo anunciado por aquela versão (`/compact` quando disponível), retomar GWD e repetir o segundo prompt. Registrar evento e nova leitura; histórico com hash não substitui corpo recarregado. Em ensaio adicional nos dois runtimes, enviar `stop adhd mode`, compactar e realizar a próxima atividade autorizada no GWD: registrar continuidade do trabalho com work_ready true, sem recarregar/aplicar o corpo, use_ready/functional_verified false, fonte humana vinculada e instalação/habilitação preservadas. Conferir Ponytail e outputs anteriores intactos; abrir sessão GWD nova e comprovar default ativo com carga própria. A suspensão não serve como caso positivo C1/C2/A1/A2 nem dispensa esses casos.

### Controle externo e resultado

Antes e depois do ensaio GWD, abrir sessões novas de cada CLI no root externo com a mesma configuração anterior. Enviar o primeiro prompt sem invocar GWD/i-have-adhd; comparar com padrão anterior e verificar ausência de evento de carga GWD, flag global nova ou alteração de configuração de estilo. Não exigir igualdade literal de respostas estocásticas; revisão verifica ausência da injeção e preservação do contrato anterior. Em uma sessão de teste, saída explícita do GWD seguida de tarefa externa também deve encerrar aplicação local.

O líder persiste na área de evidência: versão/hash GWD/upstream, runtime/session/config, comando/entrada, habilitação, startup/trust, evento completo de carga, prompts/respostas com IDs/ordem, checkpoint, controles externos, comparação de configurações e resultado por critério. Evidência fica fora dos recursos a limpar. Revisor high independente avalia dez regras/exceções e completude; core valida correlação/digests, não julga estilo por regex.

PASS exige C1/C2/A1/A2, recarga nos dois runtimes, respostas conformes, conteúdo preservado e controles externos intactos. `present`, `enabled`, hook isolado PASS, trust aprovado, lançamento bem-sucedido ou recusas corretas, isoladamente, **não** permitem esse PASS. Se qualquer CLI falhar, registrar caso/primeiro desvio e corrigir a integração antes de declarar ambos funcionais; não rebaixar o escopo para um CLI.

## Fechamento da implementação posterior

Depois dos checks focados e do diff final:

```bash
python3 tests/run_validators.py
git diff --check
```

Rodar uma vez a suíte completa e repetir somente por mudanças/falhas justificadas. Verify registra evidência, review usa revisor high independente e ship só ocorre com autorização humana. Além da matriz de estilo obrigatória nos dois CLIs, validar a orquestração live em ambos os runtimes com transporte comprovado e sessão/worktree descartável autorizada: registrar requested/effective, identidade, envio, término, persistência e confirmação de close. As sondagens do líder demonstram launch Claude high/xhigh e fechamento xhigh; não substituem a integração completa nem o estilo. Não usar recursos reais de trabalho como teste destrutivo.

## Estado desta entrega documental

Os sete documentos integram FR-001..024 sem remover a base anterior. SC-001 corresponde ao cenário 1; SC-002 ao 2; SC-003 e SC-004 ao 3; SC-005 ao 4; SC-006 ao 5; SC-007 ao conjunto e aos gates do 6; SC-008 aos cenários 7/8. Desenho pronto para revisão independente; implementação, checks novos e matriz live ainda não executados pelo autor. Atestação de plan continua responsabilidade do líder.

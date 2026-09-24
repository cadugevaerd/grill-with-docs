# Protocolo de sessão v6.0.27

Frases com **deve**, **nunca** e **somente** são normativas. A inicialização cria o workflow/Constituição quando ausentes; depois do init, os artefatos são read-only.

## Apresentação local obrigatória

Antes de qualquer resposta de trabalho em um fluxo GWD, inclusive início, retomada, compactação reentrada e especialista, execute o bootstrap local de `i-have-adhd@i-have-adhd`. O bootstrap resolve a instalação **selecionada pelo runtime**, exige observações correlacionadas e distintas de habilitação e confiança, e lê o arquivo regular aprovado por inteiro com o `load_request`; registra sessão, geração/configuração, escopo GWD e hashes do arquivo/corpo. Nunca trate cache, enumeração, caminho impresso, exit 0 ou autorrelato como leitura/obediência; não execute hook upstream, não auto-invoque a skill e não altere configurações, caches ou flags globais.

Enquanto a aplicação estiver ativa, cada nova sessão/incarnation, runtime ou reentrada após compactação exige leitura atual antes de uso. `stop adhd mode` é a única suspensão local: requer fonte humana da mesma sessão/incarnation/escopo, deixa `work_ready=true` somente após revalidar instalação, compatibilidade, enablement e trust, mantém `loading=stale` e não recarrega/aplica o corpo. A sessão nova não herda essa suspensão. `normal mode` só respeita pedido explícito e nunca é emitido pelo loader. Preservar Ponytail, conteúdo solicitado e as regras/exceções completas da referência; fora do GWD, `application=out_of_scope` e não há alteração de configuração externa.

**Limitação atual do bootstrap:** na fonte `5bc9500e6fff10fce5353f758fdc334e490a3523`, init/adopt podem criar contexto `ACTIVE` sem observação correlacionada nem `presentation`. A igualdade da string `session_ref` no guard de autoridade e o fallback `{"legacy": true, "work_ready": true}` do guard de apresentação ausente não provam sessão nem apresentação obrigatória, mesmo com sucesso do CLI. Os requisitos acima são normativos, ainda não garantidos por esses caminhos; remediação delimitada do core e revalidação continuam pré-condições dos aceites funcionais posteriores. Não liberar trabalho dependente por esse fallback.

## Fluxo e checkpoints

`grill_workspace.py init ROOT --runtime claude|codex --session-ref REF` cria a Constituição gerenciada somente quando ausente, sem clobber, com fsync/readback; arquivo existente preserva bytes. O runtime é obrigatório e identifica o harness da sessão ativa. Ausência não é `not-present`: é bootstrap pendente e deve ser resolvida no init. Symlink, ancestor symlink, UTF-8 inválido ou corrida insegura falham fechado.

Após init, avance somente pela matriz persistente de 11 passos: `specify → plan → checklist → tasks → analyze → partition → implement-parallel → converge → verify → review → ship`. Antes de invocar a skill canônica, admita a entrada com `gauntlet-step-enter` e seu contexto observado. Use `grill_workspace.py checkpoint ROOT --work-id ID --step STEP --state in-progress|complete|blocked --session-ref REF --operation-id OP_ID [--evidence PATH] [--attestation BUNDLE] [--reason TEXT]`; os gates de autoridade, atividades e prévia continuam exigidos no caminho direto. Não há saltos; `complete` exige evidência regular segura com SHA-256 e `--attestation BUNDLE` quando o gate de atestação estiver ativo, `blocked` exige razão, retomar trabalho bloqueado exige transição para in-progress e `ship` exige verify+review completos. Eventos idênticos retornam `REUSED`; divergência retorna `STATE-DIVERGENCE`. O diagnóstico histórico `LEGACY-UNTRACKED` e `--initialize-legacy --from-step STEP` não dispensam a adoção de orquestração exigida em 6.0.0; sem vínculo, continuar execução deve recusar `ORCHESTRATION-MIGRATION-REQUIRED`.

Em item adotado, `--session-ref` identifica a sessão vinculada e `--operation-id` identifica uma única operação de checkpoint. Embora opcionais no parser, são exigidos pelo handler de persistência: `OPERATION-ID-REQUIRED` sem ID, `LEADER-AUTHORITY-UNPROVEN` sem sessão; gates anteriores ainda podem recusar primeiro. Fixe o ID antes da primeira tentativa e reutilize **o mesmo operation ID e os mesmos inputs** em todo retry/recovery da mesma operação, inclusive após timeout/outcome desconhecido; não gere outro ID para contornar a reconciliação. ID existente com request divergente produz `OPERATION-ID-COLLISION`; operação não confirmada exige `OPERATION-RECOVERY-REQUIRED`. Mudança de estado ou aceitação de receipt sucessor é outra operação, com outro ID; repetir a tentativa dessa sucessão conserva seu ID, sem reemitir receipt ou repetir efeito aceito.

`grill_workspace.py status ROOT` é a única interface pública de status; hooks apenas projetam resumo humano e não escrevem/rede.


## Fluxo

```text
worktree/branch dedicada
        │
        ▼
grill_workspace init ──> .grill/work-items/<work-id>/
        │
        ▼
entrevista → audit → PLAN_ONLY_STOP
        │
        ▼
ship externo → state complete/GO → reconcile preview → apply na integração
```

## Preflight `iniciar|retomar`

- [ ] Resolver e fixar o Git root real.
- [ ] Confirmar branch/worktree dedicada para a feature, fix ou hotfix.
- [ ] Apresentar recomendação Sol no Codex ou Opus no Claude, sem mudar o modelo ativo; revalidar bootstrap e autoridade da sessão. Na retomada, ler checkpoint/aceites correntes, sem criar outra identidade ou repetir resultado aceito.
- [ ] Se o trabalho nasce de um problema relatado, invocar `code-debug` **antes** de escolher o tipo; sem laudo de causa raiz não há como distinguir incidente de defeito nem defeito de funcionalidade faltante.
- [ ] Executar `grill_workspace.py triage ROOT --report LAUDO.md --route ...` em preview, conferir a rota e só então repetir com `--apply`; fixar o `triage_id` retornado.
- [ ] Aceitar `TRIAGE-RECORDED|TRIAGE-PREVIEW|REUSED`. `ROOT-CAUSE-UNPROVEN` significa investigação incompleta, não documento malformado: volte ao `code-debug`, não edite o laudo.
- [ ] No início de trabalho novo, executar `grill_workspace.py init ROOT --runtime claude|codex --type ... --slug ... --session-ref REF` após bootstrap e autoridade comprovados; ele fixa o `WORKFLOW.md` project-wide e aceita somente `CREATED|REUSED` no campo `workflow`.
- [ ] Invocar cada canonical skill diretamente nesta sessão: `$speckit-*` no Codex ou `/speckit-*` no Claude. Nunca usar `specify workflow run`, `claude`, `codex exec` ou outro processo de agente.
- [ ] Ler o campo `dependencies` do retorno; usar `--allow-install` para instalação delegada e `--require-dependencies` quando o gate precisar ser fail-closed; o plugin `ponytail` (kind `harness-plugin`, mínimo 4.9.0) aparece nesse campo e é instalado pela CLI do harness sob `--allow-install`, nunca pelo core.
- [ ] Fixar o `work_id` retornado e usar somente `.grill/work-items/<work-id>/`.
- [ ] Confirmar `WORK-ITEM.json`, metadata imutável e hash canônico.
- [ ] Reler `WORKFLOW.md` project-wide e seu hash.
- [ ] Se a Constituição estiver ausente, executar init explícito; após init, somente leitura.
- [ ] Se presente, validar UTF-8, placeholders, hash e cobertura exata em `CONSTITUTION-CHECK.md`.
- [ ] Nunca emendar, dispensar ou enfraquecer a Constituição após init.
- [ ] Validar paths sem traversal/symlink e preservar conteúdo humano.
- [ ] Confirmar que `.grill/global/` não foi alterado pelo init.

Falha de identidade, integridade, path, lock ou materialização é `BLOCKED`. Falha constitucional é `BLOCKED-CONSTITUTION`. Antes de `init`, a ausência indica bootstrap pendente; após `init`, ausência, check `PENDING`, hash divergente ou conteúdo inválido bloqueiam o gate constitucional até correção explícita.

## Admissão, atividades e arquivos explícitos

O líder invoca as onze skills canônicas na própria sessão com o contexto de `gauntlet-step-enter`, incluindo [suplemento](agent-orchestration.md), policy, template e apresentação com hashes. Ler protocolo/contexto não executa uma skill. O líder mantém coordenação e atestação; nenhum especialista escreve `.grill/`/`.specify/reports/` ou declara conclusão de macroetapa.

`gauntlet-activity` percorre `prepare → dispatch → accept`, usando `--work-id`, `--context-id`, `--epoch`, `--session-ref`, `--activity-id`, `--input-manifest` e `--kind author|reviewer|deterministic_check`. Use `--step STEP` no ciclo ou `--scope interview` na entrevista. A preparação só autoriza bootstrap neutro; o payload técnico só sai após observação correlacionada de identidade/modelo/esforço efetivos e capacidade de fechamento. Revalidar inputs/fence e efetivo no aceite; persistir resultado ou diagnóstico antes de fechar a sessão.

Autor de todo COMO: Codex `gpt-6-astra/xhigh`, Claude `fable/xhigh`; revisor de julgamento: o mesmo modelo obrigatório do runtime, `high`, em sessão/incarnation distinta de todos os autores dos inputs correntes. Passes mistos são separados. `--author-activity` correlaciona autoria; `--files` repete por arquivo e reviewer não recebe escrita. Checks determinísticos são reproduzíveis e não produzem revisão de julgamento. Implementadores conservam o tier não-frontier e os verbos do scheduler.

Plan frontend exige Impeccable observado, prévia HTML autocontida, capturas PNG e manifest; autor xhigh, revisor high e aprovação humana são fatos distintos. `gauntlet-preview` registra o visual; `gauntlet-preview-decide` registra `approved|rejected` com `--human-evidence` referente ao digest apresentado, em preview/apply com hash esperado. A flag sozinha não é aprovação. Aprovação pendente, negada ou stale bloqueia entrada em tasks e é rechecada no checkpoint/attest/partition. Sem frontend coerentemente classificado, `NOT_APPLICABLE`; não adicionar macroetapa.

Em tasks adotadas, `Files:` JSON é a única autoridade de escrita. `Result:` por tarefa despachável deve estar também em Files, com path `specs/<feature>/implement/<task_id>.tasks.json`; não inferir sidecar de node. Aceitar arquivo da raiz/novo/subdiretório e um `./` inicial; rejeitar escape, glob, alias inseguro, diretório, symlink ou path fora do escopo aprovado. `Files: []` não concede escrita. Qualquer arquivo de evidência reservada torna a tarefa inteira deferred ao líder, sem Result obrigatório.

`partition-emit` gera DAG v2/brief com grants exatos; `gauntlet-partition-brief` entrega apenas os arquivos/resultados declarados; `gauntlet-tasks-reconcile` aceita somente resultados atribuídos à task/node/run/tentativa e receipts positivos. Em cada fase, convergir workers e então aceitar read-only/deferred na ordem das tasks antes da próxima fase, inclusive fases sem worker. Activities têm `task_binding` com task ID, fase, fingerprint e DAG. Diagnóstico persistido, revisão CHANGES_REQUIRED ou aprovação pendente não satisfazem a barreira. A última fase também precisa estar aceita para concluir implement-parallel. Sem tarefa despachável, parar em `PARTITION-NO-WORKERS` antes de admissão/DAG-VALID/checkpoint, sem execução ou receipt fictício.

## Cleanup e continuidade entre runtimes

O mesmo serviço de cleanup deve atender aceitação de agente, fechamento de etapa/wave, convergência e `gauntlet-prepare-switch`, incluindo run COMPLETE e especialista read-only. `gauntlet-cleanup` reconcilia somente recursos registrados do trabalho. Persistir resultado/diagnóstico fora do recurso e intenção antes do efeito, observar a identidade atual e confirmar cada fechamento/remoção por read-back da superfície proprietária. Request enviado, timeout, silêncio ou `agentWait=null` não são confirmação.

Separar sessão, worktree e branch. Worktree/branch só são removíveis com identidade comprovada, trabalho integrado, árvore limpa e nenhuma evidência exclusiva; falha com trabalho pendente preserva arquivos e diagnóstico. Não usar force, clean/reset, prune global ou handles/PIDs arbitrários. Cleanup por Orca respeita settlement/release/read-back; não substituir por terminal close. Estado por recurso inclui motivo de preservação ou UNKNOWN; recurso já ausente só é confirmado pela identidade/intenção correlacionada. Status/hooks apenas projetam estado, sem disparar efeitos.

`STEP-ACCEPTED-CLEANUP-PENDING` pode vir com `step_state=complete`, cleanup UNKNOWN e exit 2: a etapa já está aceita. Retry drena a mesma obrigação sem repetir a etapa. Preservação conhecida bloqueia somente a ação cuja pré-condição viola; sessão UNKNOWN impede afirmar quiescência e abrir execução concorrente.

`gauntlet-prepare-switch ROOT --work-id ID --context-id CTX --epoch N --session-ref REF --to-runtime codex|claude` cerca despachos, reconcilia cleanup e persiste checkpoint. Worker/turno ativo mantém QUIESCING com `CONTINUITY-ACTIVE-WORK`; não matar ou transferir agente para liberar a troca. O destino confirma inatividade da origem pela mesma identidade; lease vencido não é prova.

Se o líder de origem já foi encerrado e liberado pelo Orca antes da preparação, repetir o comando com `--released-source`. A recuperação exige duas chamadas, preservando a transição `ACTIVE → QUIESCING → RELEASED`. Aceita o release arquivado do dispatch exato; uma cadeia única de ownership transferido cuja origem, terminal, incarnation, worktree e runtime coincidem e cujo owner final está liberado, arquivado e `exited`, inclusive quando o Orca já removeu o terminal e retorna `terminal: null`; a transferência atômica do único recurso exato para um sucessor ativo `owned/not_requested/live`, quando a origem está `succeeded/completed`, revogada e sua projeção está `absent/unverifiable`; ou, somente para o líder, o estado estrito `failed/stopped/process_stopped` com capability revogada, terminal desconectado e não gravável, mesma worktree/incarnation e recurso integralmente liberado. Se trabalho stale impedir `QUIESCING → RELEASED`, somente `gauntlet-run-abandon` pode usar essa prova do líder liberado, e ainda exige autorização humana exata para o run; nenhum outro comando herda a exceção. As transferências registram `release_proof=ownership-transfer`; o fence registra `release_proof=resource-fence`. Silêncio, expiry ou evidência incompleta/ambígua recusam `LEADER-RELEASE-UNPROVEN`. Resultados de atividades nunca herdam essas exceções: uma atividade `RESULT_RECORDED` só deixa de impedir a troca quando sua sessão especialista exata possui release com transcript capturado; o recurso `CLOSE_PENDING` é então fechado com receipt correlacionado e levado no checkpoint, sem aceitar nem reexecutar o resultado.

Um run `BLOCKED` por `gauntlet-run-abandon` é terminal e seus estados internos históricos não contam como trabalho ativo na continuidade. Runs não abandonados continuam exigindo observação terminal explícita por worker.

`gauntlet-resume ROOT --work-id ID --runtime codex|claude --checkpoint CHECKPOINT_ID --session-ref TARGET_REF` apresenta preview. Apply exige `--apply --expected-sha256 HASH`, releitura das fontes e CAS de época. Preservar projeto/work_id/worktree/branch, outputs e efeitos aceitos; criar contexto/campanha sucessores ligados aos anteriores, sem mudar admissions/DAG/pins históricos ou zerar remediation. A sessão destino comprova sua própria carga; não herda loaded ou suspensão. Só tentativa interrompida não aceita pode repetir; outcome desconhecido exige reconciliação da mesma operação. Recovery legado por `--run-id` não troca runtime nem substitui essa ponte.

## Migração de orquestração e rollout 6.0.0

`gauntlet-orchestration-adopt ROOT --work-id ID --runtime codex|claude --session-ref REF [--scope-file PATH ...]` apresenta origem, escopo e hash esperado; aplicar somente após conferência com `--apply --expected-sha256 HASH`. `--scope-file` repete por arquivo, sem glob ou ampliação implícita de grant. Tasks antigas exigem proposta completa de autor xhigh revisada por high, consumida por `task-files-migrate` com preview e hashes correntes; não converter a prosa heurística em autorização.

Um DAG referenciado por run é selado, inclusive COMPLETE/BLOCKED: não sobrescrever bytes, report ou receipts. A continuação do trabalho restante seleciona explicitamente revisão/run sucessora; importa aceites comprovados e conserva referências históricas, sem workers terminais inventados. Leitura/auditoria e cleanup protegido de legado não autorizam nova execução sem adoção. Falta de parâmetro, observação ou caminho exigido pelo contrato no binário/adapter selecionado deve ser diagnosticada antes do trabalho; não contornar o gate.

Para resultados de workers distribuídos entre runs históricos do mesmo work item, use a operação pública abaixo. O successor deve estar admitido pela activation corrente, sem workers ou waves reais. Declare todas as tasks de cada nó; cada nó vem de um único source run e todos os sources devem fixar o mesmo DAG v2. O import é único e imutável por successor: reúna o conjunto completo no preview.

```text
python3 -B .../grill_workspace.py gauntlet-tasks-import ROOT --work-id ID \
  --run-id SUCCESSOR --dag specs/FEATURE/execution-dag.r3.json \
  --source-task T007=SOURCE_A --source-task T008=SOURCE_A --source-task T009=SOURCE_B \
  --session-ref SESSION
```

Inspecione `import.tasks`, `source_proofs`, `result_commit`, `receipt_sha256` e `expected_sha256`; aplique os mesmos argumentos com `--apply --expected-sha256 HASH`. O preview não escreve. O apply revalida sob CAS e usa a transação recuperável do Store para registrar o aceite e seu receipt `gauntlet.tasks.imported`. Retry conserva argumentos/hash: após aceite retorna `REUSED`; interrupção anterior ao evento pode retornar `APPLIED` com o mesmo receipt. O mesmo apply recupera somente sua própria transação pendente, inclusive quando o journal já avançou e o snapshot ainda não foi publicado, reobservando a autoridade do líder antes do recovery. `TASK-IMPORT-CAS-CONFLICT` exige novo preview; `TASK-IMPORT-DIVERGENT`, `TASK-RESULT-DIVERGENT`, `DAG-CONTENT-MISMATCH`, `TASKS-SOURCE-STALE` ou `TASK-IMPORT-EVIDENCE-MISSING` exigem corrigir a evidência, nunca editar Store/receipts para liberar o gate.

Cada task fixa task/nó/fase/fingerprint, os hashes canônico e de bytes do DAG, source run, tentativa da linhagem, caminho/hash do sidecar e receipts positivos de término/convergência/cleanup do worker e da wave. Os sidecars devem coincidir com os bytes já commitados no HEAD capturado pelo preview; receipts antigos não selavam esses hashes, então o novo receipt sela essa associação estrutural, sem alegar prova criptográfica de execução. Cleanup deve estar `CLEANED`, wave `COMPLETE` e convergida; grant divergente, tentativa supersedida, nó parcial ou resultado não integrado recusam. Nenhum DAG, sidecar, source run ou receipt histórico é reescrito, nenhum worker/wave fictício é criado e nenhum recurso é despachado.

Depois do import, `gauntlet-tasks-reconcile --run-id SUCCESSOR --dag DAG` reconhece os source runs aceitos; `--apply` marca somente checkboxes. A barreira de fase e a prontidão/convergência dos nós leem o mesmo import com revalidação de receipts e hashes. Tasks read-only/deferred continuam exigindo seus aceites próprios. Um nó importado recusa novo despacho com `TASK-ALREADY-IMPORTED`; se todos os nós foram importados, o successor fica `COMPLETE`. Mudança posterior de evidência bloqueia o consumo em vez de reaproveitar aceite stale.

Quando `tasks.md` muda formalmente e `partition-emit` sela uma revisão nova do DAG, não force o import do DAG anterior. Admita um run successor vazio e use preview-first:

```text
python3 -B .../grill_workspace.py gauntlet-tasks-rebase ROOT --work-id ID \
  --run-id SUCCESSOR --dag specs/FEATURE/execution-dag.r4.json \
  --source-run-id SOURCE --source-dag specs/FEATURE/execution-dag.r3.json \
  --source-commit COMMIT --task T007 --task T008 --task T009 --task T010 \
  --session-ref SESSION
```

O apply usa `--apply --expected-sha256 HASH`. Cada tarefa é comparada isoladamente incluindo fase, título e bloco `task/Files/Result` com checkbox normalizado. O source import e atividades aceitas são revalidados no DAG antigo; o destino fixa o DAG novo. Nó parcialmente transportado recusa, tarefa alterada retorna `TASK-REBASE-STALE`, e qualquer mudança posterior em source, commit, DAG, receipt ou Store bloqueia. O run antigo nunca é reescrito ou abandonado pelo comando.

A campanha que constrói a candidata continua usando o bundle histórico preservado, seu CLI absoluto e onze entrypoints pinados; revalidar o manifest ao retomar/trocar sessão. Ensaiar 6.0.0 em outro projeto/sessão. Só depois do ship encerrado adotar explicitamente o work item histórico COMPLETE para importar referências/inventário sem reabrir etapas ou reatestar o passado. Não alterar Constituição, WORKFLOW, ESSENTIAL, tabelas, classes worker-required ou registries/catálogos v3/v4 nesta transição.

## Recusas e aceite da candidata

As famílias abaixo descrevem o contrato obrigatório; superfície sem capacidade suficiente não é declarada funcional. O diagnóstico deve indicar o dado faltante/divergente e a recuperação concreta.

| Família | Recusas principais e ação |
|---|---|
| Autoridade | `ORCHESTRATION-MIGRATION-REQUIRED`, `ORCHESTRATION-POLICY-STALE`, `LEADER-AUTHORITY-UNPROVEN`, `CONTEXT-FENCED`: revalidar contexto/policy ou adotar explicitamente; não inventar identidade. |
| Especialistas | `SPECIALIST-CAPABILITY-UNPROVEN`, `SPECIALIST-MODEL-DIVERGENT`, `SPECIALIST-EFFORT-DIVERGENT`, `REVIEWER-NOT-INDEPENDENT`, `ACTIVITY-REQUIRED`: corrigir capacidade/configuração observada ou usar outra sessão independente antes do payload. |
| Recursos | `SESSION-CLOSE-UNPROVEN`, `RESOURCE-IDENTITY-DIVERGENT`, `WORKSPACE-PRESERVED`, `CLEANUP-UNKNOWN`, `STEP-ACCEPTED-CLEANUP-PENDING`: preservar e reconciliar a mesma intenção; não repetir resultado aceito. |
| Checkpoint | `OPERATION-ID-REQUIRED`, `OPERATION-ID-COLLISION`, `OPERATION-RECOVERY-REQUIRED`: fornecer identidade estável, conferir o request original e reconciliar a mesma operação antes de retry; uma sucessão nova recebe ID próprio. |
| Troca | `CONTINUITY-CHECKPOINT-MISSING`, `CONTINUITY-STATE-DIVERGENCE`, `CONTINUITY-ACTIVE-WORK`, `CONTINUITY-QUIESCENCE-UNPROVEN`, `CONTINUITY-CAS-CONFLICT`, `EFFECT-OUTCOME-UNKNOWN`: comprovar checkpoint/quiescência/outcome antes de retomar. |
| Visual | `FRONTEND-CLASSIFICATION-DIVERGENT`, `IMPECCABLE-CAPABILITY-UNPROVEN`, `PREVIEW-MISSING`, `PREVIEW-NOT-VISUAL`, `PREVIEW-APPROVAL-REQUIRED`, `PREVIEW-STALE`: corrigir classificação/capacidade e apresentar a prévia corrente para revisão/aprovação. |
| Tasks | `TASK-FILES-MIGRATION-REQUIRED`, `TASK-FILES-MISSING`, `TASK-FILES-INVALID`, `TASK-FILES-DUPLICATE`, `TASK-RESULT-MISSING`, `TASK-RESULT-UNDECLARED`, `TASKS-STRUCTURE-INVALID`, `TASK-SCOPE-VIOLATION`, `DAG-SEALED`, `TASKS-SOURCE-STALE`, `TASK-RESULT-DIVERGENT`, `TASK-PHASE-PENDING`, `PARTITION-NO-WORKERS`: corrigir proposta/atribuição ou concluir pré-requisitos; nenhum grant parcial ou DAG substituído em silêncio. |
| Apresentação | `STYLE-DEPENDENCY-MISSING`, `STYLE-DEPENDENCY-OUTDATED`, `STYLE-DEPENDENCY-UNDETERMINED`, `STYLE-DISABLED`, `STYLE-ENABLEMENT-UNPROVEN`, `STYLE-CONTENT-INCOMPATIBLE`, `STYLE-TRUST-PENDING`, `STYLE-LOAD-UNCONFIRMED`, `STYLE-LOAD-STALE`, `STYLE-SCOPE-CONFLICT`: resolver o eixo específico sem alterar configuração alheia; pedido de carga válido permite somente continuar bootstrap. |
| Comportamento | `STYLE-BEHAVIOR-UNPROVEN`, `STYLE-BEHAVIOR-NONCONFORMANT`: manter aceite funcional pendente e obter/corrigir amostra live; não impedir a primeira amostra após carga válida. |

Exit 2 só caracteriza recusa nominal quando acompanha o payload BLOCKED/código correspondente; erro de parsing também pode retornar 2. Não converter preservação/UNKNOWN ou ausência de capacidade em PASS. Diagnóstico read-only, bootstrap autorizado e cleanup elegível continuam disponíveis se apresentação falhar.

O aceite de apresentação exige quatro entradas novas C1/C2/A1/A2 (início/retomada Codex/Claude), carga real antes das respostas, prompts/respostas completos e revisão high independente das dez regras/exceções, sem perda de conteúdo. Exercitar compactação ativa com recarga nos dois runtimes, suspensão humana seguida de compactação/trabalho sem reinjeção, nova sessão ativa, saída do GWD e controles externos/configurações/Ponytail preservados. Instalação, enabled, confiança de hook, exit 0, regex ou outro estilo conciso não satisfazem a prova. `work_ready` permite trabalho; `use_ready` significa carga/aplicação ativa; `functional_verified` exige amostra comportamental aprovada e nunca é true durante suspensão.

Validadores offline exercitam seams sem rede/CLIs reais; a integração live exige transporte observado em ambos os runtimes, autoria/revisão independentes, persistência e close confirmado, além de continuidade nos dois sentidos. Toda evidência é estrutural e auditável, sem prova criptográfica de execução. Documentação não atesta T028–T030 nem verify/review/ship. Distribuição 6.0.0 exige os oito pontos sincronizados e CHANGELOG cumulativo; publicação depende dos gates canônicos, autorização humana e pipeline de tag imutável/Release no mesmo anchor.

## Entradas e controle

Project-wide:

- `.specify/memory/constitution.md` — criada pelo init quando ausente; depois, read-only;
- `WORKFLOW.md`.

Work-item local:

- `CONTEXT.md`, `docs/adr/`, `ROADMAP.md`, `DECISION-BACKLOG.md`, `PLAN-CONTEXT.md` e handoff selecionado;
- controles: `WORK-ITEM.json`, `CONSTITUTION-CHECK.md`, `DECISION-FRONTIER.md`, `ROUND-LOG.jsonl`, `state.json`, `AUDIT.md`.

Nunca resolva um path local contra o Git root; resolva contra o diretório do work item.

## Gate constitucional

Para cada heading normativo H2/H3, `CONSTITUTION-CHECK.md` deve conter exatamente uma entrada com:

- `id` e `heading` correspondentes;
- `status`: somente `PASS|NOT-APPLICABLE` libera;
- `evidence` não vazia;
- `justification` não vazia;
- `constitution_sha256` atual.

`PENDING|UNMAPPED|BLOCKED|VIOLATION`, cobertura ausente/duplicada, hash stale, status desconhecido ou ambiguidade retornam exit `3`. Nenhum ADR funciona como waiver.

Constituição alterada permanece stale até o líder atual executar `constitution-reseal` em preview/apply com `expected_sha256` e evidência humana. O novo selo atualiza `WORK-ITEM.json`, `state.json` e `CONSTITUTION-CHECK.md` como um bundle recuperável e reconcilia por CAS a activation. Um contexto que já vinculou activation é write-once: `continuity_required=true` exige sucessor pelo protocolo normal, preservando o contexto antigo e os aceites.

## Loop de entrevista

1. Classificar cenário e evidências.
2. Carregar a fronteira completa.
3. Fazer uma pergunta atômica.
4. Registrar transição e impact scan.
5. Atualizar somente o work item atual.
6. Acrescentar uma linha ao log append-only.
7. Recalcular a fronteira antes da próxima pergunta.

Entradas de decisão novas usam `question_id` e `transition`. Eventos de lifecycle usam `record_type: lifecycle` e um `event` permitido, sem transição de decisão. Logs legados permanecem imutáveis: o auditor os lê no schema histórico e nunca exige reescrita retroativa.

Duas rodadas sem progresso, terceira repetição, terceira expansão consecutiva ou 25 perguntas materiais: checkpoint + `SAFETY_STOP`. `stop|pausar` grava `PAUSED_USER`.

## Triagem

`triage` sela a rota antes de existir work item. Ele não classifica o problema — quem classifica é `code-debug`, e o core apenas verifica. Recuse-se a contornar: editar o laudo para que ele passe é fabricar a prova que o gate existe para exigir.

Enquanto o laudo não declarar `causa raiz comprovada`, o comando devolve `ROOT-CAUSE-UNPROVEN` (NO-GO) e nenhuma rota abre. `hotfix` exige severidade crítica, impacto declarado, escopo fechado e rollback; `bugfix` exige uma spec existente para receber o patch; `feature` e `module` proíbem as duas coisas. Evidência faltante é `ROUTE-EVIDENCE-MISSING`, evidência contraditória é `ROUTE-EVIDENCE-CONFLICT`, e ambas listam exatamente quais campos.

Preview é o padrão. O registro selado em `.grill/triage/<triage-id>.json` é imutável e deve ser commitado junto com o trabalho que ele originou.

## Hotfix-fast / incident

`hotfix` é a trilha executável de incidente. Ela cria um bundle autocontido com `HOTFIX.md`, `state.json` e `WORK-ITEM.json` marcado `closed=true`, e retorna `HOTFIX-GO` apenas quando todos os campos obrigatórios estão presentes. Escopo com traversal/quebra de linha, ausência de evidência ou divergência de identidade falha fechado. Não consultar ROADMAP, BL, DQ, workflow global ou reconciliação para decidir segurança do hotfix; a Constituição continua obrigatória quando presente. O bundle deve registrar `hotfix.closed=true`; `HOTFIX-GO` revalida integridade, identidade, escopo e teste. Ship é externo. Reconciliação e auditoria documental completa são ações pós-ship.

Feature/fix continuam em `PLAN_ONLY_STOP` e não ganham atalho de implementação.

## Auditoria

- [ ] Executar `grill_workspace.py audit ROOT --work-id ID`.
- [ ] Não chamar bootstrap nem escrever arquivos.
- [ ] Validar Constituição antes do auditor decisório.
- [ ] Confirmar fingerprints idênticos antes/depois.
- [ ] Validar ordem explícita, fase única pronta, dependências, BLs e handoff WHAT/WHY.
- [ ] Se todas as fases estiverem `complete|superseded`, exigir zero BL/DQ material aberto, `milestone_status=completed`, `state.status=complete`, `active_phase=null` e `audit_verdict=GO`; emitir `MILESTONE-COMPLETE` sem exigir nova fase ready.

Roots separados são permitidos com `--artifact-root PATH --project-root ROOT`.

Exit codes do core: `0` sucesso/GO/MILESTONE-COMPLETE/PREVIEW/APPLIED/CREATED/REUSED; `1` NO-GO; `2` BLOCKED/uso; `3` BLOCKED-CONSTITUTION.

## Reconciliação

Preview:

- [ ] Ler root atual, `--source-root` e `--source-ref` sem checkout.
- [ ] Não criar `.grill`, lock ou arquivo global.
- [ ] Exigir `milestone_status=completed`, `state.status=complete`, `active_phase=null`, `audit_verdict=GO` e todas as fases do `execution-order` em `complete|superseded`.
- [ ] Detectar IDs divergentes, escopo sobreposto, dependências ausentes/cíclicas, ADRs conflitantes e Constituição stale.
- [ ] Em modo incremental, usar `--work-id ID`; validar somente o alvo contra receipts anteriores e rejeitar baseline global legado sem `receipts/` com `GLOBAL-BASELINE-UNVERIFIED`.
- [ ] Qualificar IDs como `<work-id>/<ID>`.

Apply:

- [ ] Exigir `--integration-branch` igual à branch atual.
- [ ] Exigir árvore limpa e zero conflitos.
- [ ] Serializar por lock global.
- [ ] Gravar somente `.grill/global/ROADMAP.md` e `AUDIT.md`.
- [ ] Segunda execução deve ser no-op byte-idêntico.
- [ ] Nunca reescrever work items.
- [ ] Persistir `.grill/global/receipts/<work-id>.json`; a aplicação incremental preserva recibos anteriores e retorna `REUSED` sem churn quando inalterada.

## Migração

- [ ] Para `WORKFLOW.md` v2/v3, executar `migrate-v4 ROOT` em preview e aplicar somente com `--expected-sha256`; usar `--allow-local-edits` apenas após revisar o diff.
- [ ] Preview primeiro e sem escrita.
- [ ] Mapear arquivos planos, `docs/adr`, `adrs` e `handoffs`.
- [ ] Validar tudo antes do staging.
- [ ] Rejeitar symlink inclusive quebrado e UTF-8 inválido.
- [ ] Aplicar por rename atômico; manter origem intacta.
- [ ] Target idêntico é `REUSED`; divergente é `BLOCKED`.

## `PLAN_ONLY_STOP`

Após pacote válido, auditoria `GO` e handoff entregue:

1. emitir `PLAN_ONLY_STOP`;
2. parar imediatamente;
3. não executar `specify|plan`;
4. não implementar código nem criar commit/merge;
5. deixar ship e reconciliação para ciclos externos.

Hooks `SessionStart|SubagentStart` são somente contexto read-only e nunca inicializam work items.

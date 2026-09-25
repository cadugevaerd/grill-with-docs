# Changelog

## 9.0.0

- Breaking: o `goal.md` passa a ser gerenciado pelo plugin e todo `init` o reescreve com o template instalado. Antes, um `goal.md` existente nunca era tocado (`REUSED`/`PRESERVED`), e projetos criados na 5.x ficavam presos no texto daquela época. Agora:
  - ausente → `CREATED`;
  - marcador conhecido (`v1`/`v2`) e bytes iguais ao template → `REUSED`;
  - marcador conhecido com qualquer diferença (versão antiga, edição local, mutilação) → substituição atômica (`os.replace` + fsync), `UPDATED` com `reason: from vN`;
  - documento sem marcador (humano, inclusive vazio) ou com marcador mais novo que o plugin → `PRESERVED`, para não apagar arquivo alheio nem fazer downgrade.
  
  Edições locais no `goal.md` gerenciado são perdidas no próximo `init`.
- Feature: goal v2 (`grill-with-docs-goal:v2`, tupla `ESSENTIAL` nova e congelada; a v1 segue reconhecida em `ESSENTIAL_V1`):
  - a trilha "ciclo v4" vira "ciclo externo", já que projetos novos nascem em v5;
  - a entrevista v5 passa a fazer lotes de até três perguntas;
  - pontos de parada novos que o core já recusava: `OPENROUTER-KEY-REQUIRED`, `STYLE-LOAD-UNCONFIRMED`, `CONTINUITY-CHECKPOINT-MISSING`, `STEP-ASSESSMENT-*`, `PREVIEW-APPROVAL-REQUIRED`, `LEADER-AUTHORITY-UNPROVEN`, `SPECIALIST-CAPABILITY-UNPROVEN`, `SESSION-CLOSE-UNPROVEN`, `ASK-HUMAN`/`to_human` do `decide` e as falhas do Jev;
  - seção nova "Decisões tipadas": `pending` é respondido pela sessão condutora e não vira `GOAL-HOLD`;
  - removido o "caminho degradado sem Orca": especialistas e workers exigem despacho comprovado, e as references atuais não têm alternativa;
  - verbos de orientação atualizados (`decide`, `decide-label`, `gauntlet-step-enter`, `gauntlet-tasks-import`/`gauntlet-tasks-rebase`, `checkpoint` com `--session-ref` e `--operation-id`);
  - referências a seções da `SKILL.md` que já não existiam foram corrigidas.
- O `goal.md` deste repositório foi regenerado pelo próprio verbo (`UPDATED from v1`).
- Fix: corrida nos leitores do store sem lock (`read_snapshot`, `read_events`). Um append grava a linha do journal antes do `events-head.json`, e um commit ancora o journal antes do `orchestrator.json`. Um leitor que caía nesse intervalo de milissegundos recusava com `ORCHESTRATOR_INVALID: event journal tail does not match the persisted head` ou `STATE_DIVERGENCE: revision N is not the journal-anchored…`. Essa era a causa do flake de `init`/`gauntlet-run` concorrentes, visto no macOS da CI e também no Linux sob carga. Os dois leitores agora releem até 5 vezes, com 50 ms de intervalo, antes de falhar. Estado adulterado continua inconsistente e ainda falha fechado, e os invariantes do store não mudaram.

## 8.2.1

- Docs: `partition-groups` só sugere o teto `--groups N` de `partition-emit`, que já era entrada do operador. Com a mesma `tasks.md` e o mesmo `--groups`, o DAG é idêntico, então a regra dos WORKFLOW v4/v5 ("o agrupamento é determinístico e vive em código") continua valendo. Não houve workflow v6 nem mudança em `WORKFLOW.md`, template, `ESSENTIAL`, registry ou catálogo. O `SKILL.md` do grill-partition ficou intocado porque os bytes dele estão selados nos catálogos v4/v5.

## 8.2.0

- Feature: oito kinds novos no `decide`:
  - `round-record`: voto independente sobre `transition`, `scope_delta`, progresso, repetição, ADR e artefatos afetados, após cada resposta de DQ. O core não verificava nada disso.
  - `learning-route`: destino de cada learning no ship.
  - `bug-type`.
  - `finding-severity`: só confirma ou sobe a severidade proposta.
  - `delivery-classification`: cross-check com a proposta do agente; divergência vira `ASK-HUMAN`.
  - `human-or-author`: só empurra para o humano.
  - `diff-hygiene`: só sinaliza.
  - `constitution-check`: só antecipa VIOLATION, nunca concede PASS.
- Feature: vários kinds numa chamada (`--kind triage,bug-type`). As perguntas rodam em paralelo no Jev; 13 kinds e cerca de 50 perguntas levaram 639 ms ao vivo.
- Feature: state estruturado. `spec-coverage` recebe `requirements` (id → texto) e `constitution-check` recebe `clauses` (cláusula → texto), em vez de documentos inteiros misturados ao diff, conforme a recomendação da TypeSafe.
- Feature: `decide_only` no catálogo. Uma pergunta só pode ser decidida pelo Jev com os valores listados, então texto injetado no repositório não afrouxa um gate. O campo nunca é enviado à API.
- Feature: limiar por tipo de pergunta (`thresholds.noul|choice|score`). Estudos independentes mostram noul subconfiante e choice/score superconfiantes.
- Feature: `.grill/jev/decisions.jsonl` registra a resposta do Jev a cada `decide --work-id`, e o novo subcomando `decide-label` registra a resposta final do agente. É o gabarito limpo para recalibrar.
- Feature: `session_id` (= work id) e `trace` em cada chamada, para agrupar custo e logs no OpenRouter.
- Calibração com gabarito real:
  - `constitution-check` 0,95. Nas 110 cláusulas dos 10 CONSTITUTION-CHECK reais, houve uma VIOLATION falsa a 0,90 e nenhuma a partir de 0,95.
  - `delivery-classification` 0,90. Nas 22 classificações dos DELIVERY-MAP reais, a acurácia bruta foi de 68%, e a 0,85 metade das decididas errava.
  - Os demais kinds novos ainda não têm gabarito e ficam em 0,85–0,90 até o log acumular rótulos.

## 8.1.0

- Feature: decisão por pergunta no `decide`. Cada pergunta acima do limiar é decidida pelo Jev (`decided`); o agente responde só as `pending`, com o valor sugerido em `hint`. `decided_by` passa a ser `jev`, `partial` ou `agent`, e `result` continua completo apenas quando tudo foi decidido, então `step-assessment --apply` segue gravando só classificações inteiras. Em `spec-coverage`, um requisito decidido como não coberto basta para NO-GO. Nos dados da calibração da 8.0.0, os casos com pelo menos uma pergunta decidida sobem de 0 para 3/8 triagens, 8/8 lotes de DQ, 34/34 specs e 34/34 planos (40% das perguntas de risco por etapa).
- Calibração: `dq-batch` 0,75 → 0,90. Por pergunta, a 0,75 o Jev descartaria DQs materiais (acurácia de 64% nas decididas, erros com confiança até 0,86); a 0,90, 21/80 decididas com 100% de acerto.

## 8.0.0

- Feature: decisões tipadas via Jev (TypeSafe) no OpenRouter. O novo subcomando `decide ROOT --kind K` responde, numa única chamada de 70–500 ms a `typesafe/jev-1.13` (`POST /api/alpha/decisions`), as perguntas estreitas que antes custavam um turno de LLM: `step-assessment` (grava `step-inputs/<step>.json` com `--apply` e, portanto, decide se reviewer/autor extra são exigidos), `triage` (rota e severidade), `dq-batch` (até três DQs materiais), `partition-groups` e `spec-coverage` (NO-GO antecipado por FR/SC). As perguntas vivem em `assets/jev-questions.json`. Todas acima do limiar → `decided_by: jev`; qualquer uma abaixo → `decided_by: agent` e o agente decide como antes.
- Breaking: `OPENROUTER_API_KEY` passa a ser obrigatória. `init` recusa com `OPENROUTER-KEY-REQUIRED` e `preflight` reporta `BLOCKED`, sem depender de `--require-dependencies` nem de `GRILL_SKIP_DEPENDENCIES`. Só a presença é verificada; o valor nunca é gravado nem ecoado.
- Fail-closed: `OPENROUTER-KEY-INVALID` (401), `OPENROUTER-CREDIT-EXHAUSTED` (402), `JEV-UNAVAILABLE` (rede, timeout, 5xx, JSON inválido), `JEV-RESPONSE-INVALID` (resposta fora do formato pedido), `JEV-STATE-TOO-LARGE`.
- Calibração com decisões reais deste repositório (84 chamadas ao vivo em 2026-09-24): 8 triagens seladas, DQs de 8 entrevistas mais 3 distratores cada, 34 specs com um FR falso injetado, 34 planos. Limiares: `triage` 0,85 (o modelo tende a `bugfix`, a classe majoritária, e errou `feature` com confiança 0,79); `spec-coverage` 0,97 (detectou 34/34 FRs falsos, mas marcou FRs entregues como não implementados com confiança de até 0,95, o que geraria NO-GO falso); `dq-batch` 0,75 (rejeitou 24/24 distratores; o gabarito positivo está contaminado porque o CONTEXT já contém as respostas); `step-assessment` 0,85 (sem gabarito histórico; com oito perguntas, a menor confiança por caso não passou de 0,82). Na prática, hoje o Jev decide sozinho `partition-groups` e parte das triagens; nos demais kinds ele entrega `hint` e o agente decide.
- Test: `validate_jev_contract.py` sem rede; o formato é fixado pelo exemplo da OpenAPI do OpenRouter (`tests/fixtures/jev/openapi-example.json`). O runner injeta uma chave placeholder porque os validadores só verificam presença.

## 7.1.0

- Feature: o GWD passa a escolher sozinho o modelo mais recente. No Codex, cada tier de worker (`workflow-tier-models.json`) e o par autor/revisor de especialista declaram uma **família** (`luna`, `terra`, `sol`, `astra`) em vez de um slug fixo; no despacho, `tier_models.resolve_codex_family` lê `$CODEX_HOME/models_cache.json` (o catálogo local que o próprio Codex mantém, sem rede e sem subprocesso) e escolhe o slug `gpt-<geração>-<família>` de menor `priority`. Hoje: `gpt-6-luna`, `gpt-5.6-terra` (ainda sem terra na geração 6), `gpt-6-sol` e `gpt-6-astra`; quando o Codex listar `gpt-7-*`, o GWD usa sem edição. O Codex não tem alias local (nome curto vai literal para a API), por isso a resolução é do core. Catálogo ausente, ilegível ou sem slug da família recusa `TIER-MODEL-UNRESOLVED` antes de qualquer worktree, nunca cai num slug antigo. O slug resolvido continua gravado no registro do worker.
- Feature: o par especialista do Claude passa de `fable` para o alias `opus` (autor `xhigh`, revisor `high`), que acompanha a geração mais recente. As policies `agent-orchestration.v1.json` e `.v2.json` não mudam: seus bytes são selados por work item (`policy_sha256`), e o gate lê o par do código.
- Fix (já no código desde `39380f7`, agora documentado): a primeira campanha pode nascer num contexto sucessor pré-campanha. Um `gauntlet-context-takeover` feito antes de existir campanha grava `campaign_bridge=null`, e o checkpoint seguinte era recusado com `ORCHESTRATOR_INVALID: successor context has no campaign bridge`, sem verbo de saída. Sem campanha no predecessor não há o que ligar; sucessor de predecessor com campanha continua exigindo a ponte.
- Test: os testes fixam um catálogo Codex derivado da saída real do codex-cli 0.155.1 (`tests/fixtures/codex-home/`), então nunca dependem do `~/.codex` do host.

## 7.0.0

- Workflow v5 e policy v2: revisões fixas em plan/review, classificação por etapa e exceções de risco vinculadas aos inputs.
- Preserva contratos, registries e catálogos v3/v4; projetos existentes não são migrados automaticamente.
- Dois grupos de workers por padrão no v5, perguntas independentes em lotes de até três e retomada com import/rebase.
- Evita resolução repetida de executáveis durante a leitura de transcripts; sem cache de autoridade ou testes.


## 6.0.31

- Fix: novo verbo `gauntlet-activity-fence` encerra sem aceite uma atividade de especialista em duas formas cercadas, `DISPATCHED` órfã e `RESULT_RECORDED` de sessão retida, em prévia por padrão e efetivação com `--apply --expected-sha256`. Exige as provas terminais do especialista e do líder obtidas do ambiente, a readiness do solicitante (líder corrente exato, ou sucessor com a própria sessão provada) e a autorização humana exata `human-authorization/v1`. A atividade vai a `FAILED` com `diagnostic_ref`, o recurso a `CLOSED` com receipt correlacionado e a operação `activity-fence` a `CONFIRMED`; o resultado cercado nunca é aceito nem herdado e a reexecução nasce como atividade nova. A máquina de estados ganha a aresta `RESULT_RECORDED` para `FAILED`.

## 6.0.30

- Fix: `gauntlet-context-takeover` herda workers já `PREPARED` depois de comprovar que o líder anterior terminou, eliminando o ciclo em que esses workers bloqueavam a tomada mas somente o líder encerrado podia avançá-los. Outros estados ativos, atividades e observações desconhecidas continuam bloqueando; a lista herdada integra o hash da prévia e os retornos de preview/apply.

## 6.0.29

- Fix: `gauntlet-tasks-reconcile` resolve a proveniência por tarefa em rebases encadeados com origens mistas, sem exigir que o import ancestral de outra tarefa contenha o aceite corrente.

## 6.0.28

- Fix: `status` deixa de estourar `STATUS-TIMEOUT`. `item_payload` chamava `store.read_snapshot` duas vezes por work item (via `cleanup_projection → _read_runs` e direto), e cada leitura revalida o journal inteiro do Store por repositório (`.git/grill/events.jsonl`). Com 174 bundles em 38 worktrees eram 348 validações idênticas (~161 s) contra o teto de 30 s. Agora `build_status` lê o snapshot uma vez e o injeta em `item_payload`, `cleanup_projection` e `_read_runs` (parâmetro opcional; o default preserva o comportamento anterior). O workspace inteiro cai para ~4 s. O timeout e a validação do Store não mudam; o custo por leitura segue O(journal).
- Fix: o ciclo de vida do contexto de orquestração ganha transição de saída. Até a 6.0.2 um work item cujo líder encerrava a sessão ficava permanentemente inalcançável: `_bind_orchestration` só aceitava continuidade com observação de líder idêntica e `ACTIVE`, e a recusa `CONTEXT-FENCED` persistia mesmo com o líder anterior `RELEASED` ou o contexto inteiro encerrado — não havia verbo algum que mudasse o vínculo. O verbo novo `gauntlet-context-takeover` é o ato explícito de tomada, autorizado **somente** por observação de dispatch terminal do líder anterior: status fora de `dispatched`/`running`, `capabilityRevokedAt` não nulo, ou liveness `exited` vinda de `agent_status`. Sem `--apply` ele executa todas as verificações e devolve `TAKEOVER-PREVIEW` com o hash das entradas relidas, ou exatamente a recusa que o apply devolveria, sem escrever byte algum. As recusas são distintas e fail-closed: `TAKEOVER-LEADER-ACTIVE` (líder ainda vivo), `TAKEOVER-EVIDENCE-UNPROVEN` (observação ausente, ilegível, não correlacionada ao dispatch pedido ou com liveness `unverifiable`), `TAKEOVER-NOT-OBSERVABLE` (líder registrado não é um dispatch observável), `TAKEOVER-WORK-ACTIVE` (trabalho de especialista em voo), `TAKEOVER-INPUTS-STALE` (hash divergente) e `TAKEOVER-REUSED` (repetição idêntica já aplicada, sem reobservar). A mutação usa o mesmo compare-and-swap por revisão do store, então duas tomadas concorrentes sobre a mesma revisão terminam com uma aceita e a outra recusada por estado alterado. Aplicada a tomada, o contexto anterior passa a encerrado e o sucessor nasce na época seguinte carregando o bloco de sucessão — contexto e sessão de origem, motivo, referência e digest da observação usada como prova, e o instante —, enquanto `development`, campanha, resultados aceitos e escopo declarado permanecem byte a byte iguais.
- Fix: `gauntlet-prepare-switch` deixa de recusar `CONTINUITY-CHECKPOINT-MISSING` quando o work item ainda não tem checkpoint corrente conhecido. Como `checkpoint_head` só era escrito ao confirmar uma etapa, o caminho ordenado de troca não existia antes da primeira etapa confirmada; agora o checkpoint inicial é emitido a partir do estado corrente, e esse ponto é retomável de verdade. A recusa continua firme para checkpoint declarado porém desconhecido.
- Fix: a prévia de `gauntlet-orchestration-adopt` passa a executar a mesma verificação de contexto que só rodava no caminho de aplicação. Antes a prévia montava o payload sem verificá-la, prometia `PREVIEW` e o apply recusava com `CONTEXT-FENCED` — prévia e aplicação agora concordam no veredito, e a prévia segue sem escrever nada.
- Os campos do checkpoint de continuidade foram renomeados numa versão nova do schema, ao lado da atual: `workflow_sha256` passa a `context_inputs_sha256` e `constitution_sha256` a `origin_metadata_sha256`, nomes que dizem o que o campo de fato carrega. A validação escolhe o conjunto de chaves pelo valor de `schema` no próprio documento e aceita as duas versões sem tentar uma e depois a outra; um checkpoint da versão anterior continua legível e utilizável, sem reescrita.
- Integra a `main` em 6.0.11. O conflito de `gauntlet-prepare-switch` foi resolvido mantendo a comparação **estrutural** de identidade de worktree desta entrega — o lado entrante comparava o mapeamento inteiro, que é o defeito J1/H1 fechado aqui, porque `phase` e `branch` se movem na vida normal e nenhum verbo os re-carimba — e tomando do lado entrante a lógica de líder liberado (`--released-source`).
- Integra também a `main` em 6.0.12 (`0ca6760`). Sem conflito de código: apenas o CHANGELOG, porque os dois lados haviam numerado 6.0.12. A versão desta entrega sobe para 6.0.13 para ficar acima da publicada.
- Integra a `main` em 6.0.14. Sem conflito de código: `grill_workspace.py` e o contrato de orquestração fizeram auto-merge limpo. Versão sobe para 6.0.15 para ficar acima da publicada.
- Integra a `main` em 6.0.24 (`d4bf60b`). Conflitos só de versão/documentação e de `tests/validate_agent_orchestration_contract.py`; código de continuidade (`grill_workspace.py`, `agent_runtime.py`, `gauntlet_runs.py`) fez auto-merge. As entradas desta entrega, antes numeradas 6.0.15/6.0.16, passam a 6.0.25 para ficar acima da publicada.
- Integra a `main` em 6.0.27 (`657e2ba`, rebase aninhado em `gauntlet_runs.py` e contrato de import). Sem conflito de código. As entradas desta entrega passam a 6.0.28, porque a `main` publicou 6.0.25 a 6.0.27 durante o ship.

## 6.0.27

- Fix: limita a revalidação de workers locais do run ancestral aos nós solicitados pelo rebase, sem confundir sidecars de execução posterior com evidência importada.

## 6.0.26

- Fix: inclui no rebase tarefas de workers locais `CLEANED` do source run, reutilizando a validação completa de sidecars, receipts, wave e cleanup.

## 6.0.25

- Fix: revalida imports v2 históricos contra o `tasks.md` do commit intermediário, permitindo rebases encadeados quando o DAG atual já avançou.

## 6.0.24

- Fix: `gauntlet-tasks-reconcile` resolve run e nó originais pela cadeia de imports/rebases revalidada, preservando sidecars e receipts históricos; evidência ausente ou divergente continua bloqueada.

## 6.0.23

- Adiciona `gauntlet-tasks-rebase` para suceder DAGs selados preservando apenas aceites de tarefas individualmente idênticas, com preview/CAS, revalidação histórica e consumo pelo scheduler.

## 6.0.22

- Fix: o líder canônico ativo pode revalidar apresentação após upgrade de GWD/configuração no mesmo contexto, com nova carga aprovada e CAS, preservando runs, DAG, aceites e histórico.
- Sessão, runtime, escopo e policy continuam fixos; carga stale, apresentação inválida, autoridade divergente e corrida de contexto falham fechado.

## 6.0.21

- Fix: as barreiras de fase do scheduler usam o hash canônico do conteúdo do DAG, igual ao retornado por `gauntlet-dag-validate` e aos bindings de atividades aceitas; diferenças de formatação não geram `TASK-PHASE-PENDING` falso.
- Compatibilidade: imports mixed-run 6.0.20 preservam receipts e hashes de bytes, com projeção canônica somente após revalidação integral; conteúdo divergente e evidência alterada continuam bloqueados.

## 6.0.20

- Fix: `gauntlet-tasks-import` importa em um successor admitido resultados de múltiplos runs históricos, em preview/apply com CAS, receipt imutável e retry idempotente. Verifica task, nó, fase, fingerprint, DAG, source run, tentativa, bytes integrados do sidecar e receipts positivos de término, convergência e cleanup; divergência ou evidência ausente bloqueia sem reexecutar tasks.
- Reconcile, barreira de fase e scheduler consomem o mesmo aceite importado, revalidando sua proveniência sem reescrever DAG, sidecars, runs ou receipts históricos e sem criar workers fictícios.

## 6.0.19

- Fix: a continuidade ignora estados internos históricos de um run terminal `BLOCKED` por `gauntlet-run-abandon`; runs não abandonados continuam bloqueando enquanto houver worker não terminal.

## 6.0.18

- Fix: `gauntlet-run-abandon` pode remover o único trabalho stale que impede um contexto `QUIESCING` de concluir a continuidade, somente quando o líder de origem exato está comprovadamente liberado e a autorização humana referencia o run; os demais comandos continuam exigindo líder `ACTIVE`.

## 6.0.17

- Fix: `gauntlet-prepare-switch --released-source` aceita a cadeia finalizada de ownership transferido quando o Orca já removeu o terminal e retorna `terminal: null`; a prova continua exigindo origem concluída e revogada, recurso único liberado, archive capturado e identidade correlacionada por handle, worktree, runtime e incarnation.

## 6.0.16

- Fix: `gauntlet-prepare-switch --released-source` aceita a transferência atômica do único recurso terminal exato para um sucessor ativo, sem exigir que o recurso do sucessor já esteja liberado, encerrado ou arquivado; formas ambíguas, divergentes e sem sucesso continuam recusadas.

## 6.0.15

- Permite revisões sucessoras imutáveis de `partition`: após `r2`, seleciona o próximo par completo `rN` e recusa revisões parciais sem sobrescrever evidência selada.

## 6.0.14

- Preserva aceitações de tarefas vinculadas ao DAG através da linhagem canônica de contextos após continuity switch, sem aceitar atividades de contextos irmãos.

## 6.0.13

- Fix: `gauntlet-step-enter` pode emitir e comprovar diretamente o `load_request` obrigatório após compactação, sem depender de um comando de retomada já consumido; contexto, época e passo são validados antes de aceitar a leitura integral.

## 6.0.12

- Fix: a prova `ownership-transfer` lê a projeção compacta real de `worker-list`: `projection.resource.state` mais `terminalState` no topo, mantendo o recurso detalhado como autoridade de ownership/release/archive. A 6.0.11 exigia campos que somente `worker-show` expõe e recusava a cadeia válida.

## 6.0.11

- Fix: `gauntlet-prepare-switch --released-source` recupera um líder concluído cujo terminal foi reutilizado por outro Dispatch antes do cleanup. A prova exige uma única cadeia de ownership com `originDispatchId` exato, mesmo terminal/worktree/runtime/incarnation, source settled e revogado, owner final liberado com transcript capturado e liveness `exited`; atividade especialista continua sem herdar a exceção.

## 6.0.10

- Fix: `constitution-reseal` permite ao líder atual revalidar uma Constituição alterada sem recriar o work item nem editar o selo manualmente. O fluxo exige preview/apply, `expected_sha256`, fence de contexto/epoch/session e evidência humana; publica `WORK-ITEM.json`, `state.json` e `CONSTITUTION-CHECK.md` como um bundle recuperável, preserva o selo anterior, reconcilia por CAS a activation e exige continuidade sucessora quando o contexto ativo já tem activation write-once, preservando aceites sem reescrever história.

## 6.0.9

- Fix: `gauntlet-prepare-switch --released-source` recupera um líder cujo processo foi parado e liberado pelo Orca sem archive somente quando dispatch, capability revogada, terminal, incarnation, worktree, liveness e recurso liberado formam um fence exato. A exceção não vale para resultados de atividades, que continuam exigindo transcript capturado antes de fechar `CLOSE_PENDING` ou aceitar qualquer evidência.

## 6.0.8

- Fix: o primeiro checkpoint após `gauntlet-resume` promove a `attestation_campaign` do estado de desenvolvimento somente quando o `campaign_bridge` validado da operação de continuidade liga exatamente a geração anterior à campanha do contexto sucessor. Divergência sem bridge exato continua bloqueada por `CHECKPOINT-CAMPAIGN-DIVERGENT`.

## 6.0.7

- Fix: `gauntlet-orchestration-adopt` pode atualizar somente a apresentação do mesmo contexto `ACTIVE` quando a origem histórica já mudou, desde que líder observado, policy e scope permaneçam idênticos. Mudança de líder, policy ou scope continua recusada; o comando não reescreve a origem congelada nem o restante do work item.

## 6.0.6

- Fix: o fingerprint de apresentação ignora `plugin_listing.source_ref`, metadado histórico que contém o ID volátil do evento. Repetir a mesma listagem nativa não simula mais mudança de configuração nem invalida a leitura integral feita após compactação; versão, instalação e os demais eixos semânticos continuam participando do fingerprint.

## 6.0.5

- Fix: a verificação compartilhada de quiescência, inclusive em `gauntlet-resume`, reconhece `RESULT_RECORDED` como tentativa pendente não ativa quando sua sessão correlacionada já está `CLOSED` e vinculada ao mesmo resultado durável. Em 6.0.4 o prepare fechava corretamente o recurso, mas o resume voltava a bloquear a mesma atividade.

## 6.0.4

- Fix: a recuperação `--released-source` também reconcilia sessões especialistas `CLOSE_PENDING` de atividades `RESULT_RECORDED` quando o release arquivado do dispatch exato comprova identidade, settlement e fechamento. A atividade e seu resultado permanecem pendentes no checkpoint, sem aceitação ou reexecução; somente o recurso de sessão passa a `CLOSED`, removendo o bloqueio permanente de quiescência.

## 6.0.3

- Fix: `gauntlet-prepare-switch --released-source` recupera uma troca quando o líder de origem já foi encerrado pelo Orca. A prova exige o dispatch exato concluído e revogado, worker settled, terminal desconectado e não gravável, mesma worktree/incarnation, recurso liberado e transcript arquivado; silêncio, lease expiry e evidência parcial continuam recusados. O fluxo comum permanece inalterado e a recuperação conserva as transições persistidas `ACTIVE → QUIESCING → RELEASED`.

## 6.0.2

- Fix: a observação da instalação do `i-have-adhd` no Codex deixa de exigir `installPath`, campo que o `codex plugin list --json` (codex-cli 0.154.0) não emite, o que levava toda entrada GWD no Codex a `STYLE-DEPENDENCY-UNDETERMINED`. Sem `installPath`, a raiz é composta de `marketplaceName`, `name` e `version` da própria entrada nativa sob `CODEX_HOME` (ou `~/.codex`) `/plugins/cache/`, aceita somente com `installed=true`, nomes simples (sem barra, contrabarra, drive do Windows, `.` ou `..`) e o `SKILL.md` presente em disco; falha de acesso ao cache ou ausência de home resultam em instalação indeterminada, nunca em exceção; conteúdo divergente segue recusado por `STYLE-CONTENT-INCOMPATIBLE` pela verificação comum aos dois runtimes. `installPath` informado continua tendo precedência, e um valor inválido não é substituído pelo caminho composto. O Claude não muda. Um teste novo usa a entrada real capturada do Codex 0.154.0 (sem `installPath`); o teste antigo, com listagem que traz `installPath`, continua valendo para o caminho de precedência.

## 6.0.1

- Fix: `_full_read` passa a considerar somente eventos posteriores ao último bloco de compactação. Em 6.0.0 uma leitura integral anterior a `/compact` continuava satisfazendo o `load_request`, e o preflight devolvia `loading=loaded`/`use_ready=true` sem recarregar a referência de apresentação, contrariando a revalidação obrigatória após compactação.
- Fix de portabilidade da suíte: o fixture de `validate_agent_orchestration_contract` resolve o root temporário, como `project_root`, eliminando a divergência do alias `/var`→`/private/var` no macOS; `.gitattributes` mantém `tests/fixtures/**` sem conversão de fim de linha, para que o fixture de referência não mude de hash em checkouts Windows com autocrlf.

## 6.0.0

- Breaking: contrato suplementar `grill-agent-orchestration/v1` obrigatório em trabalhos novos; legado exige adoção explícita antes de executar no binário novo. Preservar campanhas, receipts e DAGs selados; migração de tasks usa proposta revisada, preview/hashes e sucessão explícita para trabalho restante.
- Cleanup por recurso nos fechamentos de etapa/wave e antes da troca: resultado ou diagnóstico durável precede close confirmado, inclusive falha/read-only. Worktree e branch exigem identidade, integração, árvore limpa e ausência de evidência exclusiva; preservação/UNKNOWN têm motivo e não viram sucesso. Resultado aceito com cleanup pendente não é reexecutado.
- Files JSON passa a ser a única autoridade do grant, incluindo raiz, novos arquivos e `./`; Result por tarefa deve estar declarado, sem sidecar inferido da prosa. DAG v2 mantém barreiras e aceites de read-only/deferred por fase; sem trabalhadores reais, `PARTITION-NO-WORKERS` bloqueia antes de admissão.
- Continuidade Codex↔Claude na mesma worktree por checkpoint, quiescência observada, fence/CAS e contexto/campanha sucessores; preservar aceites e reconciliar efeitos antes de repetir tentativa não aceita. Início/retomada recomendam Sol/Opus, sem trocar modelo ativo.
- Todo COMO usa autor `gpt-6-astra/xhigh` no Codex ou `fable/xhigh` no Claude; toda revisão de julgamento usa o modelo obrigatório com `high`, em sessão independente dos autores. Efetivo/capacidade são verificados antes do payload e no aceite; workers de implementação mantêm binding não-frontier.
- Design frontend dentro de plan integra Impeccable observado, HTML autocontido, capturas PNG, manifest e revisão independente; tasks depende de aprovação humana do digest atual. Sem frontend, `NOT_APPLICABLE`; sequência de onze macroetapas preservada.
- i-have-adhd >=0.3.0 entra na stack obrigatória: GWD lê a referência integral aprovada no início/retomada, separando presença, habilitação, confiança, carga e comportamento. Alcance local ao projeto/fluxo, sem flag global ou invocação manual; compactação revalida carga ativa e suspensão humana local continua sem reinjeção. Ponytail, conteúdo integral e configurações externas são preservados.
- Documentação pública, bootstrap local de AGENTS/CLAUDE e oito pontos de distribuição sincronizados. Suplementos não substituem skills canônicas nem alteram pins v3/v4, Constituição ou WORKFLOW; feature/fix mantêm `PLAN_ONLY_STOP` e hotfix mantém `HOTFIX-GO`.
- Aceite funcional continua condicionado a checks offline, orquestração/estilo live em ambos os CLIs e revisão independente; hashes/receipts são evidência estrutural auditável, sem prova criptográfica de execução. O ciclo histórico só adota a candidata depois de encerrado; verify/review/ship e publicação por tag imutável/Release no pipeline permanecem governados pelos gates existentes.

## 5.4.1

- Fix: o vínculo do backlog passa a ser reconhecido a partir de qualquer worktree
  registrada do repositório. `resolve_backlog` compara o `bound_path` com o
  conjunto de `git worktree list --porcelain` (caminhos reais), em vez de com o
  toplevel da worktree em que o comando roda; antes, `preflight` e `init` numa
  worktree linkada propunham `NEEDS-CREATE` mesmo com o repositório vinculado, e
  todo work item em worktree exigia `--skip-backlog`.
- Vínculo novo grava o caminho da worktree de controle, e nome/código propostos
  derivam dela, não do diretório da worktree.
- Dois backlogs de códigos distintos apontando a worktrees do mesmo repositório
  recusam com `BACKLOG-UNAVAILABLE` nomeando ambos; nenhum vínculo existente é
  re-apontado. Enumeração indisponível mantém o comportamento anterior.
- Cobertura: casos com stub do seam e um caso com `git worktree add` real em
  `tests/validate_backlog_contract.py`.

## 5.4.0

- Ponytail entra na stack oficial: `dependencies.json` ganha o kind `harness-plugin`
  e a entrada `ponytail` (`required: true`, mínimo 4.9.0). A detecção lê apenas o
  registro de plugins em disco do runtime ativo — `installed_plugins.json` no
  Claude Code, cache de plugins no Codex — sem subprocesso, e distingue
  `missing` de `undetermined`.
- `install_by_runtime` declara a sequência de instalação por harness
  (`claude plugin marketplace add` + `claude plugin install`; `codex plugin
  marketplace add` + `codex plugin add`), executada só sob `--allow-install` e
  sempre pela CLI do harness. A confiança no marketplace `DietrichGebert/ponytail`
  fica declarada no manifesto.
- Limite documentado: no Codex, "instalado" não prova "habilitado".
- Dogfooding: `CLAUDE.md` ganha a seção "Ponytail na stack", nasce `AGENTS.md`
  para o Codex e `.claude/settings.json` versionado habilita `ponytail@ponytail`.

## 5.3.4

- O ciclo v4 passa a exigir `--runtime claude|codex` no `preflight`, `init` e
  `gauntlet-init`, sem inferir o harness pelo default do projeto.
- A integração Codex do Spec Kit e suas extensões são versionadas em
  `.agents/skills`; o preflight pode materializar o harness selecionado sem
  remover os arquivos ou registros do outro runtime.
- Catálogos v4 separados resolvem as 11 etapas com `claude-code-skill/v1` ou
  `codex-skill/v1`. Ativação, tier-model binding e atestação herdam o runtime
  imutável escolhido na ativação.
- As instruções exigem invocação nativa na sessão ativa (`$speckit-*` no Codex,
  `/speckit-*` no Claude) e proíbem `specify workflow run`, `claude` e
  `codex exec` como despacho de etapa.

## 5.3.3

- `ensure_workflow.py` passa a declarar `WORKFLOW.v4.template.md` como seu
  template de bootstrap e usa esses bytes como entrada explícita de
  `workflow_v4.render_v4`. O bootstrap novo continua preservando o pin do
  registry e agora elimina a referência estática enganosa ao template v2.

## 5.3.2

- Projetos novos passam a materializar `WORKFLOW.md` v4 já renderizado com o
  pin do registry atual. Documentos v2 existentes continuam byte-intactos e
  legíveis; avançar um projeto existente permanece uma mutação explícita.
- `grill_workspace.py migrate-v4` expõe a migração v2/v3 já implementada no
  core: preview por padrão, compare-and-swap obrigatório em `--apply`, proteção
  de edições locais e reexecução idempotente.
- `grill-partition` agora assume a fronteira que seu próprio gate exige:
  migra/rebinda workflow e work item em preview-first, emite o DAG, ativa o
  Gauntlet, admite/reutiliza a run e só então chama `gauntlet-dag-validate`. O
  `run_id` validado é entregue a `implement-parallel`, que continua responsável
  por waves e workers.

## 5.3.1

- Corrige o falso `STATUS-TIMEOUT` do comando público `status` em workspaces
  acumulados: probes Git passam a ser resolvidos por worktree/repositório, em
  vez de crescerem com o número de work items.
- O timeout público de JSON e Markdown passa a 30 segundos, preservando o
  contrato `grill-status/v1` e mantendo margem sobre o pior caso real medido.
- Adiciona regressão automatizada para o escopo do cache e trava a presença
  desta entrada de changelog no gate de distribuição.

## 5.3.0

- `init` passa a fixar o **`goal.md` project-wide** na raiz, do mesmo modo que
  já fixava o `WORKFLOW.md`. Até aqui o documento simplesmente não era gerado:
  a feature que o introduziu entregou o template e parou antes do
  materializador, então todo projeto consumidor terminava o `init` sem ele e
  sem nenhum sinal de que faltava (SGD, spec 025).
- O contrato do documento vive num único lugar, `grill_core/goal_document.py`:
  `VERSION`, `MARKER` e a tupla `ESSENTIAL` de onze itens, congelada como
  literal. Quem valida importa dali e nunca redeclara — acrescentar item à
  tupla é divergência de frota sem migração, por isso versão nova é marcador
  novo ao lado do antigo, nunca edição da tupla existente (ADR-0101).
- `ensure_goal.py --ensure ROOT` materializa e reporta em três estados
  terminais mais um de recusa. `CREATED` cria por `mkstemp` + `os.link`, com
  `fsync` de arquivo e diretório; `REUSED` reencontra documento `v1` conforme e
  **não escreve nada**; `PRESERVED` deixa o arquivo byte a byte intacto.
- **Documento humano nunca é sobrescrito.** `PRESERVED` nomeia a razão em três
  casos distintos — `human document` (sem marcador), `managed version
  mismatch` (marcador de outra versão) e `incompatible goal` (marcador `v1`
  fora do contrato) — e não faz backup, cópia nem renomeação. Arquivo vazio é
  divergente, logo preservado: tratá-lo como ausente reabriria a exceção que
  FR-002 nega (ADR-0102).
- Destino que é symlink, diretório, ou cuja resolução cai fora da raiz, é
  `BLOCKED` com razão `unsafe target` **antes de qualquer escrita**; leitura
  usa `O_NOFOLLOW` e confere `S_ISREG` sobre o descritor já aberto. `init`
  converte a recusa em `GOAL-UNAVAILABLE` e falha fechado, em vez de seguir
  como se tivesse fixado.
- O bloco `goal` entra em `state.json` e no payload do `init` com `path`,
  `sha256` e `status` — e fica **fora** de `WORK-ITEM.json` e de
  `immutable_metadata`: editar legitimamente o documento não pode invalidar
  work item vivo. A chave `version` é omitida quando o documento preservado não
  carrega marcador.
- `tests/validate_goal_document_contract.py` entra na suíte pelo glob, com 12
  testes. Reprova documento a que falte qualquer item de `ESSENTIAL` **nomeando
  o item ausente**, aprova ordem trocada e conteúdo extra (presença basta), e
  trava por asserção que a tupla é declarada em exatamente um arquivo.

### Evidência observada (quickstart, Cenários 1 a 5)

Executados num diretório temporário, `GRILL_SKIP_DEPENDENCIES=1`:

- **C1, projeto limpo**: `{"status":"CREATED","version":"v1","sha256":"af97e289…"}`,
  primeira linha `<!-- grill-with-docs-goal:v1 -->`. O hash do payload é
  idêntico ao dos bytes em disco **e** ao gravado em `state.json` — o hash vem
  do disco, não do conteúdo esperado (SC-004).
- **C2, segunda execução**: `"status":"REUSED"`, mesmo `sha256`, `mtime` e
  tamanho inalterados, exatamente um `goal.md` na raiz.
- **C3, arquivo humano**: `"status":"PRESERVED"`, `"reason":"human document"`,
  `sha256sum -c` aprova, e nenhum arquivo extra. `version` ausente do bloco,
  como manda o contrato para documento sem marcador.
- **C4, symlink**: `{"code":"GOAL-UNAVAILABLE","error":"unsafe target","verdict":"BLOCKED"}`
  e o alvo apontado segue com `segredo` — nenhuma escrita fora da raiz.
- **C5, documento vazio**: `"status":"PRESERVED"` e `goal.md` com `0` bytes.

`tests/validate_distribution.py` sai `0` com a versão idêntica nos oito lugares.
## 5.2.1

- Um recibo de reconciliação concluído deixa de ser ownership perpétuo dos
  caminhos que cobriu. Até aqui, qualquer trabalho posterior que declarasse
  honestamente o mesmo arquivo era recusado com `SCOPE-OVERLAP`, mesmo quando
  declarava dependência direta do trabalho anterior — a classificação acontecia
  antes da leitura de `depends-on-work`, nos dois caminhos (SGD-24).
- A autorização é a mais estreita que dá para rastrear: **somente dependência
  direta declarada**. No reconcile de alvo único, `depends-on-work` do alvo
  precisa conter exatamente o `prior_id` do recibo sobreposto; no reconcile
  completo, um dos dois trabalhos precisa declarar o outro, e a direção
  identifica o sucessor. Dependência transitiva **não** autoriza: `A → B → C`
  não deixa A reutilizar o escopo de C sem declarar `A → C` (ADR-0001).
- Tudo o mais continua fail-closed e nada é dispensado por dependência:
  ausência de declaração, dependência de terceiro, `DEPENDENCY-SCHEMA`,
  `DEPENDENCY-MISSING`, `DEPENDENCY-NOT-RECONCILED`, `DEPENDENCY-SELF`,
  `DEPENDENCY-CYCLE` e `ADR-CONFLICT`. Declaração malformada mapeia para
  conjunto vazio e não autoriza nada.
- Sem mudança de schema e sem migração: recibos gravados antes desta versão
  continuam legíveis como estão. Quem declara a relação é sempre o sucessor, e o
  recibo anterior não precisa saber quem virá depois.

## 5.2.0

- Corrigir o artefato de uma etapa já atestada passa a ter caminho: a **cadeia
  sucessora**. Até aqui, editar um artefato depois do selo deixava a cadeia
  divergente para sempre, e quem auditasse não conseguia distinguir edição
  legítima de adulteração — que é justamente a distinção que a cadeia existe
  para sustentar. `checkpoint --state in-progress` sobre etapa `complete`
  devolvia `INVALID-TRANSITION` e nenhum comando reconciliava (BL-0201).
- `attest --supersedes <bundle>` cunha o sucessor e `checkpoint
  --supersedes-attestation <bundle> --reason ...` o aceita. O receipt anterior
  nunca é reescrito nem removido: o sucessor nomeia o que substitui por
  `supersedes_step_execution_id` e `supersedes_attempt_id` — campos que o
  envelope `step-output/v1` já reservava e que eram sempre nulos — e avança
  `execution_round`. O estado da etapa não se move; muda apenas qual receipt é
  o corrente (ADR-0205).
- O bundle substituído precisa ser **aquele que o work item aceitou**, provado
  contra o par (`output_sha256`, `receipt_ref`) que o estado gravou na
  aceitação. Um bundle apenas bem-formado da mesma etapa é recusado.
- Superseder uma etapa não torna as seguintes erradas: torna-as
  inverificáveis, porque cada uma selou o output que acabou de ser
  substituído. Elas passam a constar em `development.chain_stale`, e `ship`
  recusa com `CHAIN-STALE` enquanto a lista não esvaziar. Sem isso a
  supersessão apenas realocaria a divergência uma etapa adiante.
- `supersede_step_execution` exige mudança real — no artefato **ou** no
  predecessor. Uma etapa a jusante re-atesta com o artefato byte-idêntico,
  porque não refez trabalho algum; exigir artefato novo ali proibiria a própria
  re-atestação que limpa a lista.
- A prova de que o registro substituído é o aceito pina também **qual execução**
  o produziu. O par (`output_sha256`, `receipt_ref`) não bastava: duas cadeias
  da mesma etapa e do mesmo artefato, diferindo só no índice de onda, carregam
  digest e `receipt_ref` idênticos sob `step_execution_id` diferentes. Sem isso
  o histórico podia nomear uma execução que nunca foi o receipt corrente.
  `development.attested_executions[step]` é gravado em toda aceitação; para
  receipts aceitos antes do campo existir, a verificação cai no par — degradação
  declarada, e toda aceitação nova pina.
- `phase-turn` recusa com `CHAIN-STALE` enquanto houver etapa pendente de nova
  emissão. A virada reseta a matriz e não o ledger, então a fase seguinte seria
  recusada no `ship` por receipts que já não são dela; deixar cadeia
  inverificável para trás é o que o ledger existe para impedir.
- `attest --authorization` anexa o `human-authorization/v1` à cadeia. Sem isso
  o emissor cunhava para dez etapas e não para a décima primeira: `ship` é a
  única que exige autorização, e um bundle sem ela nunca seria aceito. O
  documento é carregado, nunca produzido — cunhá-lo tornaria "um humano
  aprovou" indistinguível de "quem queria a aprovação disse que sim".
- Recusas nomeadas novas: `SUPERSEDE_LINK_INCOMPLETE`,
  `SUPERSEDE_ROUND_NOT_ADVANCED`, `SUPERSEDE_NOT_LINKED`,
  `SUPERSEDE_ATTEMPT_NOT_LINKED`, `SUPERSEDE_STEP_MISMATCH`,
  `SUPERSEDE_WITHOUT_CHANGE`, `SUPERSEDE-BUNDLE-NOT-RECORDED`,
  `SUPERSEDE-STEP-NOT-COMPLETE`, `CHAIN-STALE`,
  `HUMAN_AUTHORIZATION_REQUIRED`.

## 5.1.0

- O núcleo passa a saber **cunhar** uma cadeia de atestação, não apenas julgá-la.
  Desde que o gate de atestação foi corrigido para valer na frontier ativa,
  `checkpoint --state complete` exige a cadeia canônica; o núcleo validava essa
  cadeia e não a produzia, e nenhuma outra parte do sistema a produzia — o ciclo
  de onze etapas ficou inalcançável em qualquer projeto na frontier ativa.
- `workflow_versions.EXECUTION_CLASS_BY_VERSION` declara, por versão e por
  etapa, quem pode executá-la: `worker-required` ou `leader-allowed`.
  `implement-parallel` é `worker-required` porque o worktree isolado e o grant
  de arquivos **são** o seu mecanismo de segurança — um receipt de leader para
  ela atestaria um isolamento que não houve. As tabelas são literais congelados,
  nunca derivados das sequências: uma reordenação não pode mudar em silêncio
  quem executa o quê, e uma etapa nova sem classe declarada falha fechado
  nomeando a decisão que falta.
- `attestation.execution_class`, `require_leader_allowed` e `artefact_digest`
  compõem a emissão. A âncora do `step-output` é o digest do artefato declarado,
  lido pela fronteira segura que o chamador já usa — o módulo não faz I/O
  próprio. Artefato ausente, ilegível, com caminho vazio, ou leitor devolvendo
  algo que não são bytes: recusa nomeada, nunca cadeia cunhada com digest vazio.
- `EmissionError` é subclasse de `AttestationError`, para que um chamador que já
  falha fechado em atestação continue falhando fechado na emissão.

  O que uma cadeia cunhada aqui prova, dito sem eufemismo: que o artefato
  existia e foi lido no momento da emissão, e que alterá-lo depois quebra a
  correlação. **Não** prova que a skill registrada rodou. Proveniência
  criptográfica e defesa contra executor malicioso seguem fora de escopo, como
  `specs/010-execution-attestation` sempre declarou.

## 5.0.0

BREAKING: v3 deixa de ser superfície de execução. `EXECUTABLE_VERSIONS` passa a
`("v4",)` e ganha ao lado `KNOWN_VERSIONS = ("v3", "v4")`, a tupla das versões
que o runtime ainda sabe **ler**. As cinco tabelas por versão do SSOT continuam
chaveadas por `KNOWN_VERSIONS`, nunca por `EXECUTABLE_VERSIONS`: elas são
indexadas pela versão que um activation record imutável declara, e perder a
chave `v3` levantaria `KeyError` sobre recibos que este build não cunhou, em vez
de devolver veredito sobre eles. Nenhum bundle precisa migrar.

BREAKING: o bloco `workflow` do `state.json` passa a gravar `schema` no lugar de
`version`, com o mesmo valor `"v2"`. O campo nunca rastreou a versão do
`WORKFLOW.md` — quem faz isso é `development.workflow_version` — e o nome antigo
fazia um bundle v4 com `"v2"` ali parecer inconsistente. A leitura é dual e
permanente: bundles já materializados continuam auditáveis sem reescrita.

- `gauntlet-init` reprovava com `WORKFLOW-INCOMPATIBLE` em qualquer repositório
  na frontier ativa. `grill_workspace.py` não importava `workflow_v4` e injetava
  `workflow_v3` no gate do Gauntlet, cujo `execution_gate` recusa marcador
  diferente de `v3`. O mesmo defeito atingia `--rebind-workflow`. Os cinco
  sítios que avaliam elegibilidade passam a usar o módulo da frontier ativa, e o
  parâmetro injetado deixa de se chamar `workflow_v3` — agora `workflow_gate`,
  que nomeia o papel em vez de uma versão.
- `checkpoint_attestation_required` (antes `v3_checkpoint_attestation_required`)
  perguntava apenas por v3, então um documento v4 caía no `return False` e o
  `ship` completava com o gate de atestação silenciosamente desligado — a
  degradação silenciosa para o caminho não autenticado que a função existe para
  impedir. Passa a despachar o gate pela versão que o documento declara, de modo
  que v3 mantém a atestação que sempre teve e v4 ganha a que faltava.
- `grill_workspace.py` deixa de duplicar as tabelas do SSOT e passa a ler
  `workflow_versions`. Era a causa estrutural do defeito acima: o arquivo
  declarava `ACTIVE_WORKFLOW_VERSION = "v4"` numa constante própria e injetava o
  gate v3 algumas centenas de linhas abaixo, sem que nada reprovasse.
- As suítes que exercitam `gauntlet-init` deixam de materializar fixture v3 com
  o migrador v3 e passam a materializar a frontier lida de `ACTIVE_VERSION`,
  incluindo registry, catálogo, snapshot de confiança e política de tier. A
  suíte inteira não continha uma única ocorrência de `workflow_v4`: writer e
  reader eram a mesma versão e concordavam por construção, que foi como 1233
  testes conviveram com o defeito.

## 4.0.1

- `grill_status.classify_item` passa a julgar cada bundle contra a sequência que
  o próprio bundle declara, e não contra a sequência canônica do build. Um
  ciclo terminado sob v3 reportava `blocked` com `etapas GWD incompletas` sob o
  build v4, porque nenhum passo v4 existia no `steps` dele. `next_gate` seguia a
  mesma projeção errada e nomeava `partition` onde a etapa pendente real era
  `agent-assign`.

## 4.0.0

BREAKING: a sequência canônica renomeia as duas etapas de execução. `agent-assign`
vira `partition` e `agent-execute` vira `implement-parallel`. A contagem
permanece onze e a ordem sem saltos permanece.

- `partition` particiona `tasks.md` em subfases file-disjuntas e emite um
  Execution DAG determinístico. Fase é barreira; o paralelismo vem de disjunção
  de arquivo dentro da fase. Largura declarada é teto, nunca promessa.
- `implement-parallel` orquestra workers em worktree isolado. O modelo de cada
  worker é derivado do tier do nó pelo binding versionado
  `assets/workflow-tier-models.json`; modelo de fronteira para a classe `worker`
  é recusado antes de qualquer worktree existir. Cobre `claude` e `codex`.
- v4 é distribuído **ao lado** de v3: registry, catálogo e snapshot de confiança
  próprios. Os assets v3 ficam byte-congelados, porque todo `WORKFLOW.md` v3 já
  materializado fixa o digest do registry v3 na própria prosa.
- `state.json` ganha `grill-development/v2` com `workflow_version` explícito.
  Ambos os schemas são lidos: um bundle escrito sob v3 continua projetando e
  continua fazendo checkpoint contra a sequência com que foi escrito.
- A extensão `agent-assign` deixa de ser dependência exigida.
- Constituição emendada para 2.0.0 (cláusula normativa de sequência redefinida).
- ADR-0012 supersede o ADR-0004 quanto ao produtor do DAG; ADR-0013 registra o
  piso de modelo do worker.

## 3.4.0

Status humano passa a ser um contrato canônico, sem quebrar a API JSON existente.

- `status --format markdown` retorna exatamente `all good` sem pendências, ou uma tabela Markdown estável de work items pendentes.
- Work items fechados só são omitidos quando milestone, fases, auditoria, etapas GWD e integridade estão coerentemente concluídos; contradições aparecem como `blocked`.
- O JSON `grill-status/v1` permanece default e recebe campos aditivos de fechamento, estado operacional e motivos de pendência.
- Workspace não inicializado e erros globais deixam de poder parecer saudáveis na projeção humana.

## 3.3.1

Corrige a detecção de extensão do preflight, que afirmava o que não tinha observado.

- **Eram duas falhas, não uma.** `installed_extensions` tokenizava a saída crua de `specify extension list` com `re.findall` sobre o texto inteiro. O escape ANSI da linha do slug (`\x1b[2mgit\x1b[0m`) fazia o regex casar a partir do `2` e produzir `2mgit`; e a varredura do texto inteiro fazia `bugfix` ser dado como presente pela frase `Structured bugfix workflow` na descrição da própria extensão. Com as quatro extensões instaladas e habilitadas, o parser acertava zero das quatro pelo caminho correto — três falsos negativos e um falso positivo.
- A correção **troca a fonte**, não o regex: a detecção lê `.specify/extensions/.registry`, onde o slug é chave de mapa. Chave exata mata as duas classes de uma vez, dá `enabled` e `version` — que antes voltava sempre `null` — e remove um subprocess do caminho de detecção.
- Registro ilegível deixou de virar "extensão ausente". Arquivo ausente, JSON inválido e `schema_version` não reconhecido convergem em `undetermined`, status novo que **bloqueia** sob `--require-dependencies` mas não propõe instalação. A causa raiz aparece uma única vez, como a dependência declarada `spec-kit-extension-registry`. Trocar um falso negativo por outro não seria correção.
- `--allow-install` não instala mais sobre estado não observado: `undetermined` sai da fila de instalação. Mutar o ambiente do operador a partir de uma não-observação era o modo de falha mais caro do conjunto.
- Extensão registrada porém desabilitada bloqueia com remediação `specify extension enable <slug>` — nunca `add`. Mandar reinstalar o que já está instalado é a mesma família de erro que originou este trabalho.
- O defeito sobreviveu a 1066 testes porque a fixture era mais limpa que a realidade: o teste alimentava `git (v1.0.0)`, texto que o terminal nunca emite. As regressões agora carregam os escapes e uma descrição-isca.
- Custo aceito e nomeado: `grill-dependencies/v1` passa a admitir `undetermined` sem trocar o identificador do schema. Consumidor que compara com `present` permanece correto.

Origem: SGD-16.

## 3.3.0

Primeira fase da separação de trilhas: um trabalho passa a poder ser roteado por evidência, não por declaração.

- `triage` é um subcomando novo, pré-ciclo como o `preflight`. Ele lê um laudo de causa raiz produzido por `code-debug`, verifica que o laudo prova o que afirma, confere a evidência que a rota escolhida exige, e sela a decisão em `.grill/triage/<triage-id>.json` sob `triage_sha256`. Preview por padrão; `--apply` grava.
- **Enquanto a causa raiz não estiver comprovada, nenhuma rota abre** (`ROOT-CAUSE-UNPROVEN`). Um laudo cujo cabeçalho afirma prova mas cuja seção `## Causa raiz` ainda diz o contrário conta como não provado: um selo obtido editando uma linha não vale nada.
- A matriz de evidência é o que impede as rotas de virarem questão de gosto. `hotfix` exige severidade crítica, impacto declarado, escopo fechado e rollback, e proíbe referência a spec; `bugfix` exige a spec existente que vai receber o patch, e proíbe escopo e rollback; `feature` e `module` proíbem as três. Falta é `ROUTE-EVIDENCE-MISSING`, contradição é `ROUTE-EVIDENCE-CONFLICT`, e as duas listam os campos exatos.
- O motivo de o core não classificar sozinho está registrado no próprio módulo: ele é stdlib determinístico e não interpreta linguagem natural. A classificação é output de skill; a verificação é do core. `init` continua intocado nesta versão — a triagem ainda é consultiva, e passa a ser exigida na próxima fase.
- `grill_core/triage.py` não importa `grill_workspace`, não abre arquivo, não chama git e não cria processo filho: recebe texto que o CLI já leu pela fronteira `safe_read_regular_fd`, para que as primitivas de segurança continuem existindo em um lugar só.
- `.grill/triage/` fica fora da projeção global, então não dispara `GLOBAL-MUTATION`. O registro é evidência e deve ser commitado; pendente, ele aparece como `DIRTY-WORKTREE` no `reconcile --apply`.

## 3.2.2

Corrige um defeito crítico de destrutividade introduzido pela 3.1.0, apontado por revisão independente.

- A remoção de skill sombreada **deixa de ser acionada por `--allow-install`** e passa a exigir `--remove-shadowed-skills`, flag que só existe para isso e só no `preflight`. `init` nunca remove. `--allow-install` autoriza instalação delegada e bind do backlog; apagar diretório fora do repositório é outro ato, e escondê-lo atrás de uma flag que não o nomeia é o waiver implícito que a Constituição proíbe.
- A documentação estava **errada**, não apenas incompleta. O `SKILL.md` afirmava que a remoção "tira apenas o atalho e preserva o destino". Isso vale para atalho; um diretório real era, e continua sendo sob a flag dedicada, apagado inteiro e sem volta. O texto agora diz isso.
- Cenário concreto que isso destravava: um operador com cópia customizada em `~/.claude/skills/grill-with-docs/` rodava `init --allow-install` só querendo o bind do backlog, e a customização era apagada em silêncio.

## 3.2.1

Corrige dois defeitos introduzidos pela 3.0.0 e descobertos na verificação final.

- `init` **provisionava** um backlog quando não encontrava um. Isso satisfazia o pré-requisito inventando a própria coisa que deveria verificar, e criava um backlog nomeado a partir do diretório raiz — em execução de teste, um por diretório temporário. Agora `init` vincula apenas a backlog existente e recusa com `BACKLOG-NOT-FOUND`.
- `init`, `preflight` e `backlog-adopt` ganham `--db`, pelo mesmo motivo que `backlog-sync` ganhou na 2.9.0: sem ele toda execução alcança o backlog real do operador. No caso do `init` isso era pior que ruído, porque ele **escrevia**.

## 3.2.0

Fecha o ciclo da inversão de autoridade: bundles criados antes da projeção ganham caminho de migração.

- `backlog-migrate` move um bundle autoral para o modelo projetado. Cria na autoridade a contraparte de cada decisão ainda sem uma, semeando o estado histórico direto — `--status` no `add` é snapshot inicial e não transição, o que permite nascer já encerrado — e regenera o registro como projeção marcada.
- O modo é detectado pela ausência da marca de origem. A gate de auditoria já fora construída condicional a esse sinal na 2.10.0, então nada precisou ser ligado aqui.
- Prévia por padrão e idempotente. Migração automática está descartada por contrato do componente que governa o backlog, que exige confirmação explícita para qualquer mutação.
- Estado inválido recusa o bundle **inteiro**, sem migração parcial: migrar pela metade deixaria o registro meio autoral e meio projetado, sem como distinguir o que já moveu.
- `backlog-project` passa a recusar com `BACKLOG-MIGRATION-REQUIRED` sobre bundle autoral, para não descartar em silêncio o registro escrito à mão.

## 3.1.0

- O preflight passa a detectar skill sombreada: um nome publicado pelo plugin que também exista como skill pessoal ou de projeto. Motivado por defeito observado em uso — um atalho em `~/.claude/skills` apontando para `~/.agents/skills` venceu a skill homônima do plugin, e o comando de sessão alcançou uma versão sem os subcomandos do protocolo. Nada avisava.
- O relato nomeia cada sombra e seu caminho, e inclui o destino resolvido quando é atalho. Atalho quebrado conta como sombra, porque continua ocupando o nome; `exists()` é falso para ele e o esconderia.
- Alcance restrito aos nomes que o próprio plugin publica. Varrer o ambiente atrás de duplicata qualquer produziria falso positivo e obrigaria a acompanhar o layout de skill de cada agente hospedeiro.
- Por padrão apenas reporta, sem remover e sem bloquear. Recusar o preflight inteiro por causa de uma sombra esconderia o relatório de dependências que o operador foi buscar.
- `--allow-install` autoriza a remoção, que remove **apenas** o atalho e preserva o destino: seguir o link destruiria uma skill que o operador talvez quisesse só renomear. Falha ao remover é reportada e não interrompe a inspeção.

## 3.0.0

**Incompatível.** A criação de um work item passa a recusar onde antes prosseguia.

- `backlogctl` deixa de ser a única dependência opcional e passa a `required: true`. A ausência entra na contagem de faltantes.
- `init` recusa com `BACKLOG-REQUIRED` sem backlog resolvido **e vinculado**. Ter o binário instalado não basta: o pré-requisito é o vínculo, e é exatamente o caso de um repositório novo.
- O bind deixa de depender de `--allow-install`. Condicioná-lo a uma flag de instalação é o que permitia a todo repositório consumidor ficar sem vínculo parecendo configurado.
- `--skip-backlog` sobrevive como única saída, porque removê-la quebraria a verificação automatizada do próprio projeto e todo consumidor que crie work item sem o backlog. Passa a ser carimbada no `state.json` e o carimbo aparece em toda auditoria como `backlog_skipped`. A cláusula constitucional proíbe waiver **implícito**; uma saída nomeada, versionada e sempre reportada não é implícita.
- O carimbo é gravado **antes** de `initial_artifacts` ser fixado. Escrevê-lo depois faria todo bundle criado pela saída reprovar o próprio gate de integridade.
- `backlog-adopt` limpa o carimbo, exigindo vínculo presente. Sem ele a válvula de escape viraria cela: um work item criado sem backlog nunca mais alcançaria aprovação, mesmo depois de vinculado.
- O carimbo **não** bloqueia a aprovação sozinho. Bloquear tornaria inauditável todo bundle criado em ambiente isolado ou em CI, que é falha pior do que a prevenida. Ele é reportado e não silenciável.

Migração para consumidores: vincule o repositório ao backlog antes de criar work items novos, ou crie com `--skip-backlog` e rode `backlog-adopt --apply` depois de vincular. Work items criados antes da 3.0.0 não são invalidados.

## 2.10.0

Inverte a autoria do registro de decisões. `DECISION-BACKLOG.md` deixa de ser escrito à mão e passa a ser projeção do backlog operacional, permanecendo versionado como evidência no commit — a separação decidida entre autoridade de estado e evidência no commit.

- `backlog-project` gera o registro. Ordenação por identificador, formatação fixa, nenhuma fonte de variação externa ao conteúdo: duas gerações sem mudança produzem bytes idênticos, e a segunda devolve `REUSED`. Escrita atômica por staging e rename.
- O estado da decisão passa a vir do `status` do item, pelo mapa inverso do que a 2.9.0 introduziu. Estado que a ponte nunca emite é relatado como divergência, nunca traduzido por aproximação.
- Marca de origem sobre a fatia do work item. O campo `revision` do backlog foi descartado como marca: ele avança a cada mudança em qualquer item de um armazenamento compartilhado por vários repositórios, e produziria divergência falsa constante.
- `backlog-verify` compara registro e autoridade, devolve `FRESH` ou `DIVERGED` e nomeia cada decisão divergente. Sem o backlog, recusa em vez de afirmar frescor. Detecta edição manual de um único caractere.
- A auditoria exige a marca de origem, mas **somente** quando o bundle declara `decision_backlog_mode: projected`. Exigir sem condição reprovaria todo bundle escrito antes de a migração existir, que é fase posterior. A verificação é offline: o gate segue sem consultar processo externo, para o veredito ser reproduzível em qualquer clone.
- **Defeito corrigido:** os dois leitores do registro divergiam. O auditor aceitava três ou quatro dígitos, qualquer separador e título ausente; a ponte exigia quatro dígitos, travessão e título. Uma decisão escrita com hífen comum era auditada — podendo bloquear a fase — e nunca era espelhada. A ponte passa a reusar `split_blocks`, o que torna a divergência irrepresentável em vez de apenas corrigida.

## 2.9.0

Destrava a ponte com o backlog operacional. Desde a 2.5.0 a integração existia e não funcionava: dos 8 `BL-NNNN` registrados em 4 work items deste repositório, apenas 1 chegou ao backlog. Três defeitos independentes, todos reproduzidos antes da correção.

- `backlog-sync` deixa de recusar work item cujos artefatos foram escritos depois do `init`. O comando validava o bundle contra `initial_artifacts`, o retrato dos templates no instante da criação, de modo que registrar uma decisão adiada — o único motivo para rodá-lo — invalidava a própria pré-condição. Passa a validar a identidade imutável, que é a garantia que de fato importa. `BUNDLE-INTEGRITY` continua ativo nos três comandos que legitimamente exigem bundle intocado.
- O espelho passa a cobrir decisões em **qualquer** estado. O filtro anterior só considerava `open`, enquanto o auditor reprova fase com decisão aberta; as duas regras somadas faziam a janela de espelho coincidir com a janela bloqueada, e um marco fechado não tinha mais nada a espelhar.
- Mapa de estados derivado da FSM real do `backlogctl`, medida nos 25 pares: o item nasce em `in_progress`, `resolved` vira `done` e `superseded` vira `cancelled`. `open → done` é ilegal, o que invalida o mapa direto. Nenhum estado fictício é gravado. Consequência visível: decisão adiada em aberto aparece como `in_progress`, não `open`.
- Deduplicação por `(work_id, BL-NNNN)`, porque o armazenamento aceita duplicata sem erro. Reexecutar deixou de poder poluir o backlog.
- Reconciliação de estado com desfecho explícito por decisão: `PROPOSED`, `APPLIED`, `REUSED`, `TRANSITIONED` e `TRANSITION-REFUSED`. O último cobre estado desejado inalcançável a partir do atual — a ponte relata e não toca o item, nunca recorrendo a `item reconcile-status`, que o contrato do backlog proíbe como transição comum.
- Toda recusa de pré-condição ocorre antes da primeira mutação. Não há transação entre chamadas sucessivas: a garantia oferecida é de convergência, não de atomicidade, e está declarada no contrato.
- 26 testes novos em `tests/validate_backlog_contract.py`, todos pelo seam `resolve_cli`, sem exigir `backlogctl` real.

## 2.5.0

- `init` passa a fixar o `WORKFLOW.md` project-wide antes de montar o bundle. Antes o encadeamento era manual e um `WORKFLOW.md` ausente virava `sha256: null` no `WORK-ITEM.json`; agora ausência materializa o template e conteúdo incompatível bloqueia com `WORKFLOW-UNAVAILABLE`.
- Preflight de dependências declarado em `assets/dependencies.json` e executado por `scripts/ensure_dependencies.py`: Python, `git`, Spec Kit (CLI, scaffold e as extensões `git`, `agent-assign`, `bugfix`, `verify-review-ship`) e `backlogctl`. O core nunca baixa bytes — cada instalação é delegada a quem é dono do artefato e verificada por versão.
- `init` reporta as dependências sem bloquear. `--allow-install` autoriza a instalação delegada, `--require-dependencies` torna o gate fail-closed e `--skip-backlog` desliga a integração. `GRILL_SKIP_DEPENDENCIES=1` desliga a detecção em ambiente air-gapped e nunca conta como `OK`.
- Novos subcomandos `preflight` e `backlog-sync`.
- As extensões community do Spec Kit passam a ser instaladas a partir de um catálogo declarado confiável em `.specify/extension-catalogs.yml`, em vez de responder automaticamente ao aviso interativo de fonte não confiável do `--from <archive-url>`.
- Integração com o plugin `backlog` via `scripts/backlog_bridge.py`: bind do repositório ao backlog correspondente e espelho dos BL abertos como itens. Preview-first — nada muta sem `--apply`/`--allow-install`, que é a confirmação explícita exigida pelo contrato do backlog. Só fala `backlogctl --json`, nunca SQLite.

## 2.4.1

- Extração do plugin para um repositório público autocontido, sem mudança funcional.
- Catálogos e manifests públicos alinhados à versão 2.4.1.

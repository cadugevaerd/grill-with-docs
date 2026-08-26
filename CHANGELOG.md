# Changelog

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
- Recusas nomeadas novas: `SUPERSEDE_LINK_INCOMPLETE`,
  `SUPERSEDE_ROUND_NOT_ADVANCED`, `SUPERSEDE_NOT_LINKED`,
  `SUPERSEDE_ATTEMPT_NOT_LINKED`, `SUPERSEDE_STEP_MISMATCH`,
  `SUPERSEDE_WITHOUT_CHANGE`, `SUPERSEDE-BUNDLE-NOT-RECORDED`,
  `SUPERSEDE-STEP-NOT-COMPLETE`, `CHAIN-STALE`.

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

# Changelog

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

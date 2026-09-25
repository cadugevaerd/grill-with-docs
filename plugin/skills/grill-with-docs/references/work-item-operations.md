# Operações de work item

## Triagem: da causa raiz para a rota

O core é determinístico e **não classifica linguagem natural**. Quem interpreta um problema relatado é a skill de diagnóstico (`code-debug`), que investiga e emite um laudo de causa raiz; o que o core faz é verificar que o laudo prova o que afirma e que a evidência exigida pela rota escolhida está de fato presente, e então selar essa decisão.

```text
python3 "${PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/skills/grill-with-docs/scripts/grill_workspace.py" \
  triage ROOT --report LAUDO.md --route bugfix|hotfix|feature|module --severity critical|high|medium|low \
  [--production-impact] [--spec-ref PATH] [--scope A,B] [--rollback TEXTO] [--triage-id ID] [--apply]
```

Pré-ciclo como `preflight`: roda antes de existir work item, não pega lock e não lê bundle. Preview por padrão — sem `--apply` calcula o registro inteiro e não escreve byte algum.

O gate acima de todos: **enquanto o laudo não declarar `causa raiz comprovada`, nenhuma rota abre** (`ROOT-CAUSE-UNPROVEN`). Um laudo cujo cabeçalho afirma prova mas cuja seção `## Causa raiz` ainda diz o contrário conta como não provado — um selo que se obtém editando uma linha não vale nada. O laudo precisa ser um relatório `code-debug` (`# Relatório de debug`) com as seções `Sintoma reproduzido`, `Evidências`, `Causa raiz`, `Cadeia causal` e `Arquivos envolvidos` não vazias; a recusa **nomeia** a seção faltante.

Matriz de evidência por rota — o que o core pode verificar sem interpretar:

| Rota | Exige | Proíbe |
|---|---|---|
| `hotfix` | `--severity critical`, `--production-impact`, `--scope`, `--rollback` | `--spec-ref` |
| `bugfix` | `--spec-ref` apontando para arquivo regular existente | `--scope`, `--rollback` |
| `feature` | — | `--spec-ref`, `--scope`, `--rollback` |
| `module` | — | `--spec-ref`, `--scope`, `--rollback` |

Escopo fechado mais rollback é o que torna um incidente contível; referência a spec é o que torna um defeito um desvio de algo já acordado, em vez de funcionalidade faltante. Exigir uma e proibir a outra é o que impede as duas rotas de virarem questão de gosto.

O registro vai para `.grill/triage/<triage-id>.json`, selado por `triage_sha256` sobre o documento inteiro menos o próprio selo — mesma construção de `immutable_sha256` e `hotfix_sha256`. Ele é **imutável**: nada o reescreve depois, e a rastreabilidade flui numa direção só, do bundle para a triagem, para que o selo nunca precise ser quebrado. Reexecutar com o mesmo `--triage-id` e a mesma decisão devolve `REUSED`; decisão diferente é `TRIAGE-IDENTITY-DIVERGENCE`; registro editado à mão é `TRIAGE-TAMPERED`.

O registro é evidência e **deve ser commitado**: `reconcile --apply` exige worktree limpa fora de `.grill/global/`, então um registro pendente aparece como `DIRTY-WORKTREE`. `.grill/triage/` fica fora da projeção global e nunca dispara `GLOBAL-MUTATION`.

## Identidade e inicialização

Resolva o Git root real e trabalhe em branch/worktree dedicada. O `init` fixa o workflow project-wide sozinho; `ensure_workflow.py --ensure ROOT` continua disponível para uso isolado.

A tomada de contexto de um work item preso a sessão anterior é ato explícito, via `gauntlet-context-takeover`, e só é autorizada quando a observação do dispatch do líder anterior comprova estado terminal; ausência de prova nunca autoriza a retomada. Workers já `PREPARED` passam ao sucessor; atividades, workers em outros estados e observações desconhecidas continuam bloqueando.

Atividade de especialista órfã ou de sessão retida é encerrada sem aceite por `gauntlet-activity-fence`, sob prova terminal do especialista e do líder e autorização humana exata; nada do resultado cercado migra.

Crie o namespace isolado:

```text
python3 "${PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/skills/grill-with-docs/scripts/grill_workspace.py" \
  init ROOT --runtime claude|codex --type feature|fix|hotfix --slug SLUG [--work-id WORK_ID] [--base-ref REF] \
  --session-ref REF [--allow-install] [--require-dependencies] [--skip-backlog]
```

Todo `init` também deixa o `goal.md` da raiz igual ao template do plugin instalado (`goal.status`): ausente → `CREATED`; gerenciado (marcador `grill-with-docs-goal:v1|v2`) e idêntico → `REUSED`; gerenciado mas antigo, editado ou mutilado → reescrito atomicamente, `UPDATED` com `reason: from vN`. Só fica `PRESERVED` o documento sem marcador (humano, inclusive vazio) ou com marcador mais novo que o plugin. Edições locais em `goal.md` gerenciado são sobrescritas; regra de projeto vai na Constituição, no WORKFLOW ou em ADR.

Sem `--work-id`, o core gera uma identidade collision-resistant. `--work-id` explícito serve para retomada/idempotência e deve corresponder à mesma identidade. A criação usa lock, staging e rename atômico; colisão ou integridade divergente bloqueiam.

## Dependências e backlog

O preflight é declarado em `assets/dependencies.json` e executado por `scripts/ensure_dependencies.py`: Python >=3.10, `git`, Spec Kit (CLI >=0.11.2, scaffold `.specify/` e as extensões `git`, `bugfix`, `verify-review-ship`) e `backlogctl`. O core nunca baixa bytes: cada instalação é delegada a quem é dono do artefato — `uv`, `specify` e o instalador verificado do plugin `backlog` — e a verificação é por versão resolvida, nunca por hash de tarball.

O plugin `ponytail` (`DietrichGebert/ponytail`, mínimo 4.9.0) integra a stack oficial como `harness-plugin`, com `required: true` e a mesma semântica de obrigatoriedade do Spec Kit — é o modo de trabalho oficial do projeto. A detecção lê somente o registro de plugins em disco do runtime ativo, sem subprocesso: no Claude Code, `installed_plugins.json`; no Codex, o cache de plugins; o resultado é `present`, `outdated`, `missing` ou `undetermined`. Com `--allow-install` a instalação é delegada à CLI do harness — `claude plugin marketplace add DietrichGebert/ponytail` seguido de `claude plugin install ponytail@ponytail`, ou os equivalentes `codex plugin marketplace add`/`codex plugin add` —, nunca pelo core, e a confiança nesse marketplace de terceiros é declarada no manifesto. No Codex, "instalado" não prova "habilitado": a ativação depende de configuração própria do runtime que a detecção não cobre. Os hooks do ponytail exigem `node` no PATH para ativação automática; sem ele as skills continuam funcionando.

`i-have-adhd@i-have-adhd` (`ayghri/i-have-adhd`, mínimo 0.3.0) também é `harness-plugin` obrigatório no fluxo novo, independentemente de `--require-dependencies`; SKIPPED não libera trabalho. A policy admite inicialmente 0.3.0 e o hash aprovado do SKILL.md instalado; versão maior não implica conteúdo compatível. Instalação delegada sob `--allow-install` segue o manifesto do runtime; instalação presente não comprova habilitação, confiança, leitura ou comportamento. Disabled não autoriza reinstalação para contornar a escolha. Respeite autorização de confiança já válida e preserve configurações alheias.

Com aplicação ativa, `STYLE-LOAD-UNCONFIRMED` acompanhado de `presentation.load_request` é bootstrap pendente: leia o arquivo aprovado por inteiro pela ferramenta da própria sessão, preserve as dez regras/exceções e registre o evento real para revalidar. Sem continuação disponível no binário/adapter, diagnostique a lacuna e não libere o trabalho. Carga atual pode produzir `work_ready=true`, `use_ready=true`, `behavior=not_tested`, `functional_verified=false`; somente amostra live completa e revisão independente comprovam comportamento. Corpo truncado exige nova leitura integral; catálogo, path e declaração do agente não bastam. A evidência funcional da entrega exige os dois runtimes, compactação e controle externo, não se presume deste texto.

Duas das extensões exigidas (`bugfix`, `verify-review-ship`) vivem no catálogo `community` do Spec Kit, que é discovery-only. Instalar por `--from <archive-url>` exige confirmação interativa de fonte não confiável, que um instalador automatizado não deve responder no lugar do humano. Por isso `--allow-install` registra o catálogo community como confiável em `.specify/extension-catalogs.yml` (`install_allowed: true`) e instala pelo nome. Essa é uma decisão de confiança explícita, versionada no repositório e revisável: a partir dela, `specify extension add` passa a instalar extensões de terceiros desse catálogo sem novo aviso.

O backlog operacional é **exigido** desde a 3.0.0: `init` recusa com `BACKLOG-REQUIRED` sem backlog resolvido e vinculado — e vincula apenas a backlog **existente**, nunca provisionando um novo, porque criar o que se deveria verificar não é verificar, e o bind deixou de depender de `--allow-install`. `--skip-backlog` é a única saída, fica **carimbada** no `state.json` do work item e aparece em toda auditoria como `backlog_skipped` — um bundle criado por ela não pode parecer conforme com um pré-requisito que contornou. `backlog-adopt` limpa o carimbo depois que o repositório é vinculado, para que a saída não vire cela. Exceto pelo requisito obrigatório de apresentação acima, as demais dependências continuam apenas detectadas e reportadas; `--allow-install` segue autorizando a instalação delegada. `--require-dependencies` transforma a falta em `MISSING-DEPENDENCY` fail-closed. `GRILL_SKIP_DEPENDENCIES=1` desliga a detecção em ambiente air-gapped e nunca é reportado como `OK`.

```text
python3 .../grill_workspace.py preflight ROOT --runtime claude|codex [--allow-install] [--skip-backlog]
python3 .../grill_workspace.py backlog-sync    ROOT --work-id ID [--apply] [--db PATH]
python3 .../grill_workspace.py backlog-project ROOT --work-id ID [--apply] [--db PATH]
python3 .../grill_workspace.py backlog-verify  ROOT --work-id ID [--db PATH]
python3 .../grill_workspace.py backlog-adopt   ROOT --work-id ID [--apply]
python3 .../grill_workspace.py backlog-migrate ROOT --work-id ID [--apply] [--db PATH]
```

O código do backlog raramente coincide com o nome do diretório, então `backlog_bridge.py ROOT --code CODE [--apply]` vincula um backlog existente explicitamente. Repositório já vinculado a outro código, ou código já vinculado a outro caminho, falha fechado em vez de revincular em silêncio. O vínculo é reconhecido a partir de qualquer worktree registrada do repositório (a ponte compara o caminho vinculado com o conjunto de `git worktree list`), e um vínculo novo grava o caminho da worktree de controle.

`backlog-sync` espelha os `BL-NNNN` do work item, **em qualquer estado**, como itens do backlog vinculado ao repositório. Preview é o padrão e não muta; `--apply` executa. A ponte fala somente `backlogctl --json` e nunca lê SQLite direto. Sem backlog vinculado, o sync retorna `BACKLOG-NOT-BOUND`.

O item nasce em `in_progress`; `resolved` vira `done` e `superseded` vira `cancelled`. `open → done` é ilegal na FSM do backlog, e é por isso que o item não nasce em `open`. Consequência prática: uma decisão adiada em aberto aparece como `in_progress` no `backlog list`, não como `open`.

A deduplicação é por `(work_id, BL-NNNN)`, lida dos marcadores da descrição do item, porque o armazenamento aceita duplicata sem erro. Reexecutar é seguro: o desfecho por decisão é `PROPOSED`, `APPLIED`, `REUSED`, `TRANSITIONED` ou `TRANSITION-REFUSED`. Este último aparece quando o estado desejado é inalcançável a partir do atual — a ponte relata e não toca o item, nunca recorrendo a `item reconcile-status`. O comando valida a identidade imutável do work item, não o hash dos artefatos: ler `DECISION-BACKLOG.md` escrito é o propósito dele.

`backlog-project` gera `DECISION-BACKLOG.md` a partir do backlog: o arquivo deixa de ser autoral e vira projeção versionada, ordenada por identificador e byte-idêntica em reexecução, que devolve `REUSED` quando nada mudou. O estado da decisão vem do `status` do item, pelo mapa inverso. Aplicar declara `decision_backlog_mode: projected` no `state.json`.

O registro carrega uma marca de origem que cobre **apenas** a fatia deste work item — mudança em decisão de outro work item, ou de outro repositório que compartilhe o mesmo backlog, não a altera. O campo `revision` do backlog não serve para isso, porque avança a cada mexida em qualquer item.

`backlog-verify` compara registro e autoridade e devolve `FRESH` ou `DIVERGED`, nomeando cada decisão divergente. Sem o backlog disponível ele recusa, em vez de afirmar frescor. A auditoria **não** faz essa comparação: ela é offline por decisão, para que o veredito seja reproduzível em qualquer clone, e só exige a marca quando o bundle já se declarou projetado.

O preflight também detecta **skill sombreada**: um nome publicado por este plugin que exista como skill pessoal ou de projeto. O relato nomeia o caminho e, quando é atalho, o destino resolvido; atalho quebrado conta como sombra, porque continua ocupando o nome. Por padrão só reporta, e a detecção nunca remove nada sozinha. A remoção exige `--remove-shadowed-skills` no `preflight`, uma flag que só existe para isso: `--allow-install` autoriza instalação delegada e bind do backlog, e apagar diretório fora do repositório é outro ato — escondê-lo atrás de uma flag que não o nomeia seria o waiver implícito que a Constituição proíbe. `init` nunca remove.

O que a remoção faz depende da forma da sombra, e a diferença importa: um atalho é desfeito e o destino sobrevive; um **diretório real é apagado inteiro**, recursivamente e sem volta, porque não há coisa menor a remover nesse caso. O alcance é restrito aos nomes deste plugin — ele não opina sobre nomes de terceiros.

Bundle criado antes da projeção tem registro **autoral**, detectado pela ausência da marca de origem. `backlog-migrate` move um desses para o modelo projetado: cria na autoridade a contraparte de cada decisão, semeando o estado histórico direto por `--status`, e regenera o registro como projeção marcada. É prévia por padrão, idempotente, e recusa o bundle inteiro se algum estado for inválido — migrar pela metade deixaria o registro meio autoral e meio projetado, sem como saber o que já moveu. `backlog-project` recusa com `BACKLOG-MIGRATION-REQUIRED` sobre bundle autoral, para não descartar em silêncio o registro escrito à mão.

`WORK-ITEM.json` registra metadata imutável e hash canônico: `work_id`, tipo, slug, branch, HEAD, base ref/commit, Constituição e workflow. Escopo, dependências e conflitos ADR permanecem declarados em campos próprios para reconciliação.

## Decisões via Jev (OpenRouter)

`OPENROUTER_API_KEY` é obrigatória para o fluxo: `init` recusa com `OPENROUTER-KEY-REQUIRED` (exit 2) e `preflight` reporta `BLOCKED` com o mesmo código, independentemente de `--require-dependencies` e de `GRILL_SKIP_DEPENDENCIES`. Só a presença é verificada; o valor nunca é gravado, logado nem ecoado.

```bash
python3 .../grill_workspace.py decide ROOT --kind K[,K2,...] [--file PATH]... [--context JSON] \
  [--work-id ID] [--step STEP --apply]
python3 .../grill_workspace.py decide-label ROOT --work-id ID --kind K [--step STEP] --answers '{"chave": "valor"}'
```

Uma requisição a `typesafe/jev-1.13` (`POST https://openrouter.ai/api/alpha/decisions`) responde todos os kinds pedidos: as perguntas rodam em paralelo, então juntar kinds do mesmo momento não custa latência. As perguntas vivem em `assets/jev-questions.json`; cada kind tem `threshold` e, opcionalmente, `thresholds` por tipo de pergunta (`noul`, `choice`, `score`). Cada pergunta é decidida isoladamente: acima do limiar vai para `decided`; abaixo, para `pending`, com o valor sugerido em `hint`. `decided_by` é `jev`, `partial` ou `agent`. Com um kind, o payload traz a decisão no topo; com vários, em `decisions`. `--work-id` vira `session_id` (agrupamento de custo no OpenRouter, sem cache).

| kind | itens | regra de segurança |
|---|---|---|
| `step-assessment` | riscos da policy | `--apply` grava `step-inputs/<step>.json` só com tudo decidido |
| `triage`, `bug-type`, `learning-route` | — | direto |
| `partition-groups` | — | só sugere o teto `--groups N` de `partition-emit`, que já era entrada do operador; com a mesma `tasks.md` e o mesmo `--groups` o DAG é idêntico, então a regra do WORKFLOW ("agrupamento determinístico, vive em código") continua valendo sem versão nova |
| `round-record` | artefatos (CONTEXT, ADR, ROADMAP…) | voto independente sobre `transition`, `scope_delta`, `progress`, `repeat`, `adr_needed`; `context.dq`, `context.answer`, `context.frontier` |
| `dq-batch` | `context.candidates` | até três DQs materiais |
| `human-or-author` | `context.decisions` | `decide_only: human`: nunca tira uma decisão do humano |
| `delivery-classification` | — | compara com `context.proposed`; divergência → `ASK-HUMAN` |
| `finding-severity` | `context.findings` (`text`, `proposed`) | só confirma ou sobe a severidade |
| `spec-coverage` | FR/SC de `spec.md`, enviados em `requirements` | NO-GO se um requisito for decidido como não coberto |
| `diff-hygiene` | arquivos em `--file` | `decide_only: true`: só sinaliza |
| `constitution-check` | cláusulas de `constitution.md`, enviadas em `clauses` | `decide_only: VIOLATION`: nunca concede PASS |

Os kinds que protegem gates só endurecem: um texto injetado no repositório pode mover a confiança do Jev, mas não afrouxa uma decisão. Toda chamada com `--work-id` e todo `decide-label` acrescentam uma linha a `.grill/jev/decisions.jsonl` (resposta do Jev e resposta final do agente), o gabarito para recalibrar os limiares. Falhas são fail-closed: `OPENROUTER-KEY-INVALID`, `OPENROUTER-CREDIT-EXHAUSTED`, `JEV-UNAVAILABLE`, `JEV-RESPONSE-INVALID`, `JEV-STATE-TOO-LARGE`, `JEV-KIND-UNKNOWN`. É a única chamada de rede do core; nada é baixado.

## Entradas da entrevista

Defina `WORK_ITEM=.grill/work-items/<work-id>`. As oito entradas decisórias são:

1. `.specify/memory/constitution.md` — project-wide, opcional e read-only;
2. `WORKFLOW.md` — project-wide;
3. `$WORK_ITEM/CONTEXT.md`;
4. `$WORK_ITEM/docs/adr/`;
5. `$WORK_ITEM/ROADMAP.md`;
6. `$WORK_ITEM/DECISION-BACKLOG.md`;
7. `$WORK_ITEM/PLAN-CONTEXT.md`;
8. `$WORK_ITEM/handoffs/FASE-NNN-SPECIFY-HANDOFF.md` selecionado.

Arquivos de controle, fora da lista de oito entradas: `WORK-ITEM.json`, `CONSTITUTION-CHECK.md`, `DECISION-FRONTIER.md`, `ROUND-LOG.jsonl`, `state.json` e `AUDIT.md`.

- `CONTEXT.md`: somente glossário e linguagem ubíqua.
- `docs/adr/`: decisões difíceis de reverter e trade-offs reais.
- `ROADMAP.md`: fases, ordem explícita, dependências, estado e handoff.
- `DECISION-BACKLOG.md`: decisões adiadas com owner, evidência e gatilho.
- `PLAN-CONTEXT.md`: HOW técnico cumulativo para planejamento.
- Handoff: somente WHAT/WHY da fase selecionada.

## Gate constitucional

Se a Constituição estiver ausente antes de `init`, trate como bootstrap pendente. O `init` cria a Constituição gerenciada sem clobber; depois disso, ausência, hash divergente ou conteúdo inválido bloqueiam o fluxo. Para uma Constituição existente:

1. leia somente `.specify/memory/constitution.md` em UTF-8;
2. registre SHA-256 no metadata e em `CONSTITUTION-CHECK.md`;
3. mapeie exatamente cada cláusula normativa H2/H3;
4. registre `id`, `heading`, `status`, `evidence` e `justification`;
5. aceite somente `PASS` ou `NOT-APPLICABLE`, ambos com evidência e justificativa.

Cobertura ausente/duplicada, status desconhecido, `PENDING`, `UNMAPPED`, `BLOCKED`, `VIOLATION`, placeholder, ambiguidade ou hash stale terminam em `BLOCKED-CONSTITUTION` (exit `3`). Se a Constituição aparecer ou mudar, revalide todo o work item. Não há waiver constitucional.

Uma alteração aprovada é re-selada pelo líder atual, sempre preview-first: `constitution-reseal ROOT --work-id ID --context-id CTX --epoch N --session-ref REF --human-evidence EVIDENCE`, seguido de `--apply --expected-sha256 HASH`. O apply preserva o selo anterior em `constitution_reseals`, atualiza check/estado como um único bundle e reconcilia por CAS a activation. Se o contexto já tiver activation write-once, retorna `continuity_required=true`; crie contexto sucessor pelo protocolo normal, sem reescrever o contexto antigo.

## Entrevista incremental

```text
INIT → MAP_FRONTIER → ASK_ONE → RECORD → RECOMPUTE_FRONTIER
                         ↑                    │
                         └──── decisões ──────┘
                                              ↓
                 COMPLETE | BLOCKED | SAFETY_STOP | PAUSED_USER
```

1. Classifique o cenário e registre fontes oficiais ou `EVIDENCE GAP`.
2. Carregue a fronteira inteira e selecione uma DQ material com dependências satisfeitas.
3. Faça uma pergunta atômica com evidência, recomendação, opções e custos. No v5, pode agrupar até três perguntas independentes; dependência entre respostas exige uma por vez.
4. Registre `resolved`, `deferred`, `split`, `blocked` ou `out-of-scope`.
5. Faça impact scan e atualize somente o `$WORK_ITEM` atual.
6. Acrescente uma linha JSON por DQ respondida ao `ROUND-LOG.jsonl` e recalcule a fronteira após o lote. Respostas ausentes continuam pendentes; veja os campos do lote no protocolo.

Mesmo fingerprint admite no máximo duas perguntas sem evidência nova. Duas rodadas sem progresso, três expansões consecutivas ou 25 perguntas materiais exigem checkpoint e `SAFETY_STOP`. `pausar|stop` grava `PAUSED_USER`. Contradições nunca são sobrescritas.

IDs `ADR-NNNN`, `DQ-NNNN`, `BL-NNNN`, `FASE-NNN` e `R-NNNN` são locais ao work item. Na projeção global tornam-se `<work-id>/<ID>`.

## Status humano canônico

Para responder a `status`, invoque a projeção canônica e reproduza o stdout literalmente; não resuma, traduza, reordene ou acrescente explicações:

```text
python3 "${PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/skills/grill-with-docs/scripts/grill_workspace.py" \
  status ROOT --format markdown
```

O JSON `grill-status/v1` continua sendo o formato padrão da CLI para automações. O Markdown omite somente work items coerentemente fechados. Se não houver pendência, o stdout é exatamente `all good`; caso contrário, é a tabela `Item | Status | Pendência` produzida pelo core.

## Atestação: o que um receipt prova, e o que não prova

Concluir uma etapa exige a cadeia `skill-resolution → dispatch-intent →
skill-invocation → step-output`. O núcleo agora **cunha** essa cadeia, além de
julgá-la: até a versão 5.1.0 ele só sabia julgar, e nada no sistema sabia
produzir — o ciclo inteiro era inalcançável por checkpoint.

**O que a cadeia prova.** Que o artefato declarado existia, que foi lido no
momento da emissão, e que alterá-lo depois quebra a correlação.

**O que ela não prova.** Que a skill registrada foi executada. Quem conduz a
etapa pode produzir o artefato por outro meio e declará-lo; a cadeia não
distingue. Isso não é lacuna a corrigir: proveniência criptográfica e defesa
contra executor malicioso estão declaradas fora de escopo desde o desenho
original. A garantia é estrutural por opção, e descrevê-la como mais do que é
seria a sobre-afirmação que o mecanismo existe para impedir.

**Quem pode atestar o quê.** Cada etapa tem classe de execução declarada por
versão, em tabela congelada ao lado da ordem canônica:

| Classe | Etapas | Por quê |
|---|---|---|
| `worker-required` | `implement-parallel` | O worktree isolado e o grant fechado de arquivos **são** o mecanismo de segurança; um receipt de leader atestaria um isolamento que não houve. |
| `leader-allowed` | as demais dez | Não têm worker por natureza. A sessão condutora se declara executora, com lease derivado do par run/etapa e `wave_index` zero, que significa "fora de onda". |

Etapa sem classe declarada é recusa nomeada, nunca default permissivo. Uma
etapa nova exige duas decisões explícitas — posição na sequência e classe — e
falha fechado até ter as duas.

`worker-required` **não** quer dizer que o worker escreve o receipt: nenhum
worker escreve receipt de etapa alguma. Quer dizer que o *trabalho* precisa ter
sido feito por workers despachados, e o leader só emite contra prova disso —
waves convergidas lidas do estado durável da run, nunca uma flag de quem pede.

**Quando o artefato de uma etapa fechada precisa mudar.** Ele muda por cadeia
sucessora, nunca por reescrita (ADR-0205). O receipt anterior não é apagado nem
alterado: o sucessor **nomeia o que substitui** e avança a ronda.

```text
attest ROOT --work-id ID --step STEP --artifact PATH --out NOVO \
  --supersedes ANTERIOR
checkpoint ROOT --work-id ID --step STEP --state complete --evidence PATH \
  --attestation NOVO --supersedes-attestation ANTERIOR --reason "por quê" \
  --session-ref REF --operation-id OP_SUCESSAO
```

Em item adotado, o checkpoint acima exige `--session-ref` da sessão vinculada e `--operation-id` estável; sem a identidade da operação, a persistência recusa `OPERATION-ID-REQUIRED`. `OP_SUCESSAO` representa uma operação nova de aceitação do receipt sucessor, distinta da aceitação anterior. Reutilize esse mesmo ID e os mesmos inputs em todo retry/recovery dessa sucessão; não gere outro ID após timeout ou outcome desconhecido. Retry não é outra sucessão: preserve os bytes e referências de NOVO/ANTERIOR e reconcilie a operação pendente antes de qualquer efeito novo. O parser de `attest` não aceita essas duas flags; elas pertencem ao comando `checkpoint`.

O estado da etapa não se move — `complete` era verdade e continua sendo. Muda
apenas qual receipt é o corrente e o que ele declara substituir. O bundle
anterior precisa ser **aquele que o work item aceitou**, provado contra o par
que o estado gravou na aceitação.

Superseder uma etapa não torna as seguintes erradas: torna-as inverificáveis,
porque cada uma selou o output que acabou de ser substituído. Elas entram em
`development.chain_stale`, e tanto `ship` quanto a **virada de fase** recusam com
`CHAIN-STALE` enquanto a lista não esvaziar. A única saída é atestar cada uma de
novo, contra o predecessor que agora vale — com o artefato byte-idêntico, se o
trabalho delas não mudou.

Virar a fase não resolveria a pendência, sobreviveria a ela: a matriz de etapas
reinicia e a lista não, e a fase seguinte seria recusada no `ship` por pendência
que não é dela.

**`ship` exige autorização humana.** É a única etapa que exige, e a emissão
recusa sem ela com `HUMAN_AUTHORIZATION_REQUIRED`:

```text
attest ROOT --work-id ID --step ship --artifact PATH --out BUNDLE \
  --authorization .grill/attestations/<doc>.json
```

O documento é carregado, nunca produzido pela emissão — ele existe antes da
cadeia. A autorização permite **invocar** a skill registrada; nunca a substitui
nem autoriza side effect direto.

O bundle substituído é provado contra três valores gravados na aceitação —
`output_sha256`, `receipt_ref` e o `step_execution_id` de
`development.attested_executions[step]`. Os dois primeiros não dependem da
execução: duas cadeias da mesma etapa e do mesmo artefato, diferindo só no índice
de onda, os carregam idênticos.

## Execução nativa pelo harness

O ciclo posterior invoca cada canonical skill na sessão ativa: Codex usa
`$speckit-*`; Claude Code usa `/speckit-*`. Nunca despache uma etapa por
`specify workflow run`, `claude`, `codex exec` ou outro processo de agente. O
runtime explícito da ativação seleciona catálogo, adapter e tier-model binding;
o default de `.specify/integration.json` não substitui essa escolha.

## Auditoria read-only

```text
python3 "${PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/skills/grill-with-docs/scripts/grill_workspace.py" \
  audit ROOT --work-id WORK_ID
```

Para artefatos externos ao checkout, use `--artifact-root PATH --project-root ROOT`. A auditoria valida a Constituição e chama o auditor decisório real com roots separados. Ela não chama `ensure_workflow.py`, não cria arquivos e compara fingerprints antes/depois.

Exit codes: `0 GO/MILESTONE-COMPLETE`, `1 NO-GO`, `2 BLOCKED/uso`, `3 BLOCKED-CONSTITUTION`.

## Reconciliação global

Preview é o padrão e não escreve:

```text
python3 .../grill_workspace.py hotfix ROOT --slug SLUG --scope PATHS --reproduction REPRO --evidence EVIDENCE --correction-test TEST --rollback ROLLBACK --constitution-evidence EVIDENCE --test-command "python3 -m unittest tests/test_fix.py"
python3 .../grill_workspace.py reconcile ROOT \
  [--source-root OUTRA_WORKTREE] [--source-ref REF] [--work-id ID]
```

`--work-id ID` faz reconciliação incremental fail-closed de um único alvo: irmãos pendentes ou conflitantes não bloqueiam, mas estado, Constituição, escopo, ADRs e dependências do alvo continuam obrigatórios. Preview não escreve. Com `--apply`, a projeção é acumulada em recibos determinísticos `.grill/global/receipts/ID.json`; reaplicação idêntica retorna `REUSED`. Um global legado sem recibos bloqueia com `GLOBAL-BASELINE-UNVERIFIED` (não há migração implícita).

O reconciliador lê bundles completos sem checkout e detecta: `work_id` duplicado divergente, sobreposição de escopo, dependência ausente/cíclica, conflito ADR declarado, estado não concluído e hash constitucional stale. Só aceita milestone com `milestone_status=completed`, `state.status=complete`, `active_phase=null`, `audit_verdict=GO` e todas as fases do `execution-order` em `complete|superseded`. IDs são qualificados globalmente.

O fluxo feature/fix termina em `PLAN_ONLY_STOP`; não use `reconcile` como continuação de um hotfix antes do ship externo. Aplicação exige branch de integração explícita, árvore limpa e zero conflitos:

```text
python3 .../grill_workspace.py hotfix ROOT --slug SLUG --scope PATHS --reproduction REPRO --evidence EVIDENCE --correction-test TEST --rollback ROLLBACK --constitution-evidence EVIDENCE --test-command "python3 -m unittest tests/test_fix.py"
python3 .../grill_workspace.py reconcile ROOT --apply --integration-branch BRANCH
```

Somente `.grill/global/ROADMAP.md` e `.grill/global/AUDIT.md` são gerados. A segunda execução é byte-idêntica/no-op. A projeção global nunca reescreve work items.

## Migração legada

Sempre execute preview antes de aplicar:

```text
python3 .../grill_workspace.py migrate ROOT --type feature|fix|hotfix --slug SLUG [--work-id ID]
python3 .../grill_workspace.py migrate ROOT --type feature|fix|hotfix --slug SLUG [--work-id ID] --apply
python3 .../grill_workspace.py migrate-v4 ROOT
python3 .../grill_workspace.py migrate-v4 ROOT --apply --expected-sha256 SHA256 [--allow-local-edits]
```

A migração legada copia arquivos planos, `docs/adr|adrs` e `handoffs` para staging, preserva bytes e mantém a origem. `migrate-v4` atualiza `WORKFLOW.md` v2/v3 com compare-and-swap; projeto novo já materializa v4. Symlink, UTF-8 inválido, colisão ou divergência bloqueiam; falha não deixa bundle parcial.

## ROADMAP, GO e `PLAN_ONLY_STOP`

Hotfix-fast não lê nem altera ROADMAP/BL/DQ; sua saída é `HOTFIX-GO` somente com escopo fechado, evidência reproduzível, teste de correção, rollback e sem conflito constitucional real.

A ordem vem de `execution-order`, não dos números de fase. Para `GO`, a fase selecionada deve ser a primeira incompleta, ter predecessores terminais (`complete|superseded`), nenhum BL aberto e handoff WHAT/WHY exclusivo. `PLAN-CONTEXT.md`, ADRs e `CONTEXT.md` fornecem HOW. Quando não resta fase incompleta, o estado terminal exige zero BL/DQ material aberto, `milestone_status=completed`, `state.status=complete`, `active_phase=null` e `audit_verdict=GO`; a auditoria emite `MILESTONE-COMPLETE`. Uma última fase `superseded` é conclusão legítima, não NO-GO por si só.

Após auditoria `GO` e entrega do handoff, emita `PLAN_ONLY_STOP` e pare. Esse stop aplica-se somente a feature/fix; hotfix encerra em `hotfix.closed` e pode seguir para `HOTFIX-GO`. Agentes externos executarão `specify|plan` em outro ciclo. Após ship, marque a fase entregue como `complete` ou a fase substituída como `superseded`; ao encerrar o milestone, grave o estado terminal, reaudite até `MILESTONE-COMPLETE` e só então reconcilie globalmente.

## Portabilidade do workspace

O core requer Python >=3.10 e não possui dependências externas. Use `uv run --no-project` preferencialmente; `python3`, `python` ou `py -3` são fallbacks. A publicação do bundle escolhe previamente a capacidade completa de rename: em POSIX usa parent aberto com `O_RDONLY|O_DIRECTORY|O_NOFOLLOW`, compara `stat`/`fstat` e chama `os.rename` com `src_dir_fd`/`dst_dir_fd`; sem isso usa caminhos completos após validar parent/source/target. O fallback recusa um destino já visível, mas não reproduz proteção contra substituição do parent ou criação concorrente do target entre validação e rename (limite TOCTOU); o lock serializa escritores cooperantes. `hotfix-go` usa a command line nativa do Windows com `shell=False`. Esta versão não altera os hooks e não declara hooks universais em Windows.

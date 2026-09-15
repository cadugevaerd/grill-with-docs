# Contrato de integração: skills, especialistas, runtime, visual e apresentação

A macroetapa é sempre invocada pelo líder pela skill canônica resolvida. O contrato suplementar não é alias, nova macroetapa, semantic emulation ou permissão de substituir uma entrada do registry.

## Integração com as onze skills

`assets/agent-orchestration.v1.json` tem schema próprio e contém: versão da política; modelos/esforços por papel/runtime; matriz de atividades por step_id; refs/hashes do protocolo suplementar e template de Files; requisitos de capability; regra de classificação frontend; `presentation` com componente, mínimo, versão/hash admitidos, loader e alcance local. Não altera `workflow-tier-models.json` nem os assets canônicos v3/v4. Manifest de política não pode aceitar hash autorreferente: fixa os documentos suplementares; seu próprio digest é calculado pelo contexto que o sela.

No início/retomada, o CLI devolve `invocation_context` com work_id, contexto/epoch, etapa, runtime, entrypoint **canônico**, registry hash, suplemento/template e seus hashes, classification, atividades requeridas e `presentation`. O líder lê esse contexto e invoca `$speckit-plan`, `/speckit-plan` ou a skill correspondente, fornecendo o suplemento como instruções específicas em seus argumentos. O core verifica guard e admissibilidade; ler o contexto não representa a invocação da skill.

Sem adoção sob o binário novo, mutações de execução retornam `ORCHESTRATION-MIGRATION-REQUIRED`. Início de trabalho novo materializa o contrato integral; não existe opt-out. Suplemento corrompido/ausente bloqueia; ele não vira dica opcional. Skills legadas continuam byte-intactas e são chamadas com argumentos específicos do contrato: especialista produz o artefato; core emite brief/grants; leader grava coordenação. A instrução de Result por tarefa substitui expressamente a receita legada de sidecar por node para **este contrato adotado**, sem mudar entrypoint ou afirmar bytes novos no catálogo antigo.

O mesmo suplemento substitui expressamente a instrução final de `grill-implement-parallel` que deixa deferred para depois de todas as waves: percorrer cada fase de tasks, convergir seus workers e então aceitar suas atividades read-only/deferred na ordem declarada antes de avançar. Fases sem workers também são processadas nessa posição. Receipts de activities vinculam task_id/fase/fingerprint/DAG; revisão negada, aprovação humana pendente ou diagnóstico persistido não liberam a barreira. O guard comum de wave/worker-declare, prepare legado/remediation, payload e activities impede ultrapassar tasks anteriores, e attest/checkpoint complete exige também a última fase resolvida. Detalhes e ordem interna estão em [task-files.md](task-files.md); não criar scheduler de atividades nem modificar skills/pins/tabelas v3/v4.

Em `grill-partition`, o suplemento exige parar em PARTITION-NO-WORKERS retornado pelo partition-emit antes dos passos 5–7 de admissão/validação/checkpoint. O report diagnóstico enumera todas as tasks/fases, mas não há DAG-VALID nem conclusão de implement-parallel com zero workers. Preservar a exigência real de execução da classe congelada worker-required; tasks inteiramente read-only/deferred são limite diagnosticado antes desse ciclo, sem worker/receipt fictício ou alteração da sequência. Em planos mistos nenhuma dessas tasks é omitida.

A integração precisa deixar verificável que o autor de tasks recebeu o template novo, que a skill pinada recebeu a ordem suplementar por fase e que implementadores receberam apenas result_files declarados. O teste de integração percorre `step-enter → contexto de invocação → especialista verificado → resultado → attest/checkpoint`, recusando bypass direto pelo checkpoint. Exercita fase só read-only/deferred antes de worker, última fase pendente e ausência total de workers antes de admissão; conter o texto do suplemento sem exercitar os guards não basta. Nenhum teste afirma ter executado uma skill real quando apenas substituiu o harness por seam.

| Step | Obrigação mínima de julgamento | Trabalho mecânico permitido ao líder |
|---|---|---|
| specify | Revisor high dos requisitos; autor xhigh para qualquer COMO introduzido | Setup, carregar handoff e registrar saída |
| plan | Autor xhigh de desenho e revisor high; frontend adiciona autor/revisor de design | Resolução, setup, gates, registro e apresentação da preview |
| checklist | Revisor high para julgamento de cobertura/qualidade | Extração/verificação determinística de itens |
| tasks | Autor xhigh de decomposição/arquivos/dependências e revisor high | Setup e parser/checks de formato |
| analyze | Revisor high da consistência/risco; autor xhigh se redesenho | Checks estruturais repetíveis |
| partition | Nenhum especialista para o algoritmo; desenho incerto retorna a tasks | Parser, agrupamento e validação do DAG |
| implement-parallel | Workers não-frontier; autor xhigh para decisão nova; revisor high em julgamento de código/segurança | Despacho, receipts e aplicação mecânica do desenho |
| converge | Revisor high das lacunas; autor xhigh de plano/tasks adicionais | Diff, ancestry, merge/reconcile determinísticos |
| verify | High para julgamento, se houver; teste puro declarado deterministic_check | Executar testes/gates e coletar evidência |
| review | Revisor high distinto de todos os autores do escopo | Registrar findings/verdict; não revisar no lugar do especialista |
| ship | Qualquer novo julgamento segue author/reviewer; gates prévios obrigatórios | Efeitos previstos dentro da skill canônica, após autorização humana |

Na entrevista pré-ciclo, author/reviewer seguem a mesma política com activity_scope interview e step_id null, respeitando PLAN_ONLY_STOP. Isso não invoca specify/plan nem adiciona macroetapa.

Reviewer obrigatório refere versão corrente do artefato. Se a etapa não realiza uma atividade condicional, registra tipo determinístico e seus inputs/checks; não pode chamar julgamento de teste para evitar a política. Core não classifica linguagem natural: checa obrigações mínimas, tipos declarados, correlação e receipts. A garantia é estrutural e auditável, com limites explícitos para um executor malicioso.

## Bootstrap local de apresentação nos dois CLIs

A GWD atualizada incorpora explicitamente i-have-adhd como **referência de apresentação**, carregando os bytes instalados aprovados. O usuário inicia GWD pelo entrypoint habitual; não chama `$i-have-adhd` ou `/i-have-adhd`. Nenhuma das onze skills canônicas é substituída: atualizar `grill-with-docs/SKILL.md`, `session-protocol.md` e o suplemento é distinto de editar as skills pinadas no catálogo v3/v4. O corpo upstream não é recopiado como outra skill, não é resumido e não tem seus metadados editados para liberar auto-invocação.

### Ordem de entrada e retomada

1. A skill GWD resolve runtime e Git root reais antes da primeira resposta de trabalho; executa preflight, obtém a instalação aprovada e a observação de disponibilidade/habilitação do harness. Em ausência/erro, mostra o diagnóstico específico e a ação de recuperação; não anuncia estilo ativo. O preflight pode devolver `STYLE-LOAD-UNCONFIRMED` junto com `presentation.load_request`: isso é um bootstrap ainda incompleto, com caminho de continuação definido.
2. GWD lê integralmente o SKILL.md instalado indicado no load request, pela ferramenta de leitura da sessão. A leitura usa bytes/hash/version aprovados e caminho regular seguro. Carrega o corpo e o seguinte limite de aplicação, fornecido pelo suplemento: aplicar as dez regras e exceções ao trabalho no projeto/fluxo GWD, preservar instruções superiores e o conteúdo exigido, manter Ponytail, suspender por pedido explícito ou saída do GWD. Não executar o hook upstream nem tratar essa leitura como invocação canônica de macroetapa.
3. O líder captura o evento de leitura real no `session-ref`/observation existente. O adapter verifica identidade/configuração, versão/path/hash e conteúdo entregue; nova verificação de preflight ou da operação de entrada registra `loading=loaded`. Enumerar a skill no catálogo, hash em texto, retorno 0 e autorrelato do modelo não satisfazem esse passo. Corpo truncado exige nova leitura completa, não inferência do trecho faltante.
4. Aplicar a apresentação a partir da primeira resposta de trabalho; ainda pode haver `behavior=not_tested`. Registrar resultado/estado corrente e manter a política nos turnos do fluxo. Cada entrada canônica inclui a referência/hash/limite no `invocation_context.presentation`; especialistas recebem o mesmo conteúdo com seu payload já autorizado e registram carga na própria sessão, sem assumir herança de memória.
5. Retomada, mudança de runtime/incarnation e compactação exigem revalidar contexto. Quando application=active, recarregar o corpo se a prova não cobrir a geração atual; `session-protocol.md` torna essa checagem explícita. Com `suspended_by_user` comprovado na mesma sessão/incarnation/escopo, revalidar fonte humana e dependência/habilitação/confiança, sem recarregar/aplicar o corpo: work_ready permanece true, mesmo com loading stale e use_ready false. A ordem de carga dos passos 2–4 vale para aplicação ativa, não reverte suspensão humana. Nova sessão GWD, inclusive especialista/destino de retomada, inicia o default ativo com carga própria e não herda suspensão do líder. Ao encerrar o fluxo ou mudar explicitamente para tarefa fora dele, aplicar `out_of_scope`, mantendo o estilo anterior dessa sessão.

O projeto deste plugin recebe em `AGENTS.md`/`CLAUDE.md` uma instrução local de executar esse bootstrap no trabalho GWD, preservando conteúdo alheio. Consumidores não recebem edições automáticas desses arquivos: o entrypoint GWD já conduz a entrada. Estar fora de um projeto/fluxo GWD não dispara a rotina. Não criar flag `.i-have-adhd-always`, AGENTS global, hook global ou override de diretório de configuração. O hook GWD existente conserva comportamento/budget read-only; a ativação contratada acontece na entrada/retomada da GWD, não antes de a sessão sequer iniciar.

Limitação explícita: CLI sem GWD carregada não aplica este suplemento; abrir uma sessão externa não ativa o componente. Retomada deve passar pela GWD/protocolo canônico antes de continuar o trabalho. Instruções carregadas não garantem obediência do modelo nem sobrevivência universal a compactação; por isso a integração inclui prova de recarga e respostas live, além dos checks estruturais. Não vender a recusa do caminho incompleto como suporte funcional. Um bloqueio nativo de confiança deve ser resolvido na interface proprietária com autorização humana; aprovação prévia válida não é solicitada de novo.

### Presença, habilitação e compatibilidade

`dependencies.json` acrescenta `id=i-have-adhd`, `kind=harness-plugin`, `required=true`, `min=0.3.0`, `plugin=marketplace=i-have-adhd`, `marketplace_source=ayghri/i-have-adhd` e owner do plugin. Reutilizar o detector em disco de Ponytail sem alterar sua semântica: present/outdated/missing/undetermined continua presença/versão, nunca habilitação. Resolver a **instalação selecionada pelo runtime**, conferindo manifest e corpo; duas versões em cache não autorizam usar a maior se outra está efetiva.

Preflight recebe observação atual da superfície do harness, normalizada por `agent_runtime.py`. A coleta pelo líder pode usar `codex plugin list --json` ou `claude plugin list --json`, comandos observados nesta máquina, com o mesmo cwd e configuração efetiva da sessão. Selecionar identidade exata `i-have-adhd@i-have-adhd`: Codex retorna array `installed` com pluginId/version/installed/enabled; Claude retorna array com id/version/scope/enabled/installPath. Não selecionar por substring nem por posição. Duplicatas ambíguas de scope, JSON inválido, cache divergente ou override de sessão não refletido no probe geram undetermined. Preferir metadados da própria sessão quando disponíveis; uma CLI auxiliar com configuração diferente não comprova enabled.

O core não passa a rodar essas listagens em hooks/status ou no detector de presença; o líder/adapter coleta a fonte pela superfície existente, e preflight valida a observation. Não ler settings secretos em bruto no relatório nem escrever TOML/JSON global para corrigir o estado. O schema de evidence guarda refs/config fingerprint e os campos pertinentes; não requer parser TOML ou SDK novo no Python 3.10. O teste offline injeta essas observações e nunca executa as CLIs reais.

Instalação autorizada com `--allow-install` delega, na ordem: Claude `claude plugin marketplace add ayghri/i-have-adhd`, depois `claude plugin install i-have-adhd@i-have-adhd --scope user`; Codex `codex plugin marketplace add ayghri/i-have-adhd --ref main`, depois `codex plugin add i-have-adhd@i-have-adhd`. A instalação normalmente disponibiliza o plugin, mas exige read-back. Se já instalado e desabilitado, não reinstalar para sobrepor a escolha: mostrar habilitação necessária e usar controle nativo autorizado; no Claude existe `claude plugin enable i-have-adhd@i-have-adhd --scope project`, no Codex observado o controle é da interface de plugins, sem `codex plugin enable`. Habilitar o plugin não ativa a flag global nem dispensa leitura/prova local. Confiança do hook é outra autorização do harness, nunca respondida automaticamente pelo core.

Policy admite inicialmente 0.3.0/hash de SKILL.md registrado em [data-model.md](../data-model.md). Versão acima do mínimo com conteúdo não revisado é instalada, porém `compatibility=incompatible`; indicar atualização/revisão da policy, não carregar silenciosamente. A conferência de conteúdo é sobre bytes já instalados, separada da verificação por versão da instalação delegada; não baixar ou verificar tarball no core.

### Composição, carregamento e aceite

Ponytail continua governando implementação, dependências, segurança, escopo e validação. i-have-adhd organiza a conversa: ação inicial, passos numerados, estado corrente, tempo concreto quando pertinente, erro factual e próximo passo quando houver pendência. Todas as dez regras upstream e exceções continuam disponíveis; limite de cinco itens agrupa apresentação e nunca remove FRs, achados, arquivos ou checks solicitados. Artefatos, JSON, commands, hashes, código e evidência preservam seus formatos completos. Instrução superior conflitante prevalece e é registrada na avaliação; outro estilo conciso não comprova carga de i-have-adhd.

`stop adhd mode` suspende apenas apresentação na própria sessão. Entradas e despachos exigem work_ready, que aceita essa suspensão humana vinculada e revalidada, sem dispensar instalação, habilitação, conteúdo compatível, confiança ou gates técnicos. use_ready continua significando carga/aplicação ativa; functional_verified não pode ser satisfeito enquanto suspenso. O teste bootstrap → suspensão → compactação → próxima atividade autorizada deve continuar sem estilo e sem repetir outputs; nova sessão ativa é verificada separadamente. Nenhuma flag permanente ou suspensão copiada da origem serve de opt-out da stack ou de caso positivo FR-024.

O event ref da carga precisa conter a leitura real dos bytes na sessão, vinculada ao load request/hash, não um receipt afirmativo fabricado pelo worker. A ausência de um formato portátil pode ser suprida pelo evento/transcript completo realmente observado e persistido pelo líder via adapter; registrar evidence_kind e limites. Não afirmar prova criptográfica de execução de skill. Mudança de sessão, fonte ou configuração invalida prova atual, mantendo a anterior como histórica.

FR-024/SC-008 exigem o roteiro live de [quickstart.md](../quickstart.md): entrada e retomada em Codex/Claude, conversa de vários turnos, recarga após compactação, controle externo e preservação de configurações/Ponytail. Revisor high independente examina prompts/respostas completos e as dez regras/exceções aplicáveis. Testes negativos e checks isolados são adicionais. A integração só pode ser entregue como funcional depois de **ambos** os caminhos positivos passarem.

## Policy de modelo e esforço

| Runtime | Sessão principal | Autor técnico | Revisor |
|---|---|---|---|
| codex | Recomendar Sol | `gpt-6-astra`, `xhigh` | `gpt-6-astra`, `high` |
| claude | Recomendar Opus | `fable`, `xhigh` | `fable`, `high` |

Recomendação não grava config nem troca modelo. Implementadores continuam usando o modelo derivado do tier no binding existente; `actor_class=worker` não ganha frontier. Passes mistos usam duas sessões. Novo nome/activity_id na mesma sessão não dá independência; comparação usa provider session/incarnation e cadeia de autoria dos inputs, inclusive autores de partes de documento composto.

## Observação de runtime

`agent_runtime.py` aceita callables injetáveis, sem SDK/framework. Fronteira do CLI fornece `probe`, `observe`, `request_close` e `read_after_close` de um adapter conhecido. A parte pura valida documentos; não executa comando arbitrário vindo do receipt, não faz HTTP/download e não transforma identidade livre em PID/handle.

Observation normalizada `grill-agent-observation/v1` contém:

- Fonte: adapter/version, operation, collected_at, runtime instance/host, source reference e digest dos bytes observados.
- Identidade: provider, handle/session ID emitido pelo runtime, incarnation e owner dispatch quando existir; nunca derivar do título do terminal.
- Lançamento: requested model/effort, effective model/effort, resolução de alias observada e evidence_kind. Campo não observado é null.
- Atividade: `active|idle|exited|unknown`, resultado terminal quando comprovado e possibilidade de novos efeitos.
- Fechamento: `not_requested|pending|closed|unknown|preserved`, confirmação e archive ref quando houver.
- Apresentação: campos de `grill-gwd-presentation/v1` pertinentes à sessão, com fontes distintas de enablement/startup/loading/behavior; modelo/esforço não é inferido desses campos.

A fonte precisa permitir correlação com a tentativa e ser relida pelo adapter ou obtida diretamente da resposta da ferramenta nativa visível ao líder. JSON escrito pelo worker dizendo “sou Astra” não é observation. A observação é evidência estrutural, sem proteção criptográfica contra alguém que já pode escrever arbitrariamente as fontes locais.

### Liberação do payload

1. Preflight verifica que a superfície consegue selecionar o par e observar identidade/efetivo e encerramento. Sem isso, bloquear antes de criar agente de trabalho.
2. Abrir sessão nova com bootstrap neutro: instruções de readiness, sem problema técnico, input manifest ou grant; sessão não lê artefatos do trabalho. Selecionar modelo/esforço explicitamente.
3. Observar lançamento e estado efetivos. Apenas após igualdade validada o core registra VERIFIED e emite autorização de payload vinculada a activity/context/fence/input digest.
4. Enviar brief completo pela mesma identidade. Gravar aceitação do envio; resposta perdida exige leitura da mesma operação antes de reenviar. Não criar segunda sessão como retry cego.
5. Ao terminar, reler modelo/esforço/identidade quando disponível; fallback/divergência invalida resultado. Persistir conteúdo ou diagnóstico antes do encerramento.

Configuração e policy não prometem impedir um fallback interno invisível. Se a superfície só confirma o solicitado ou omite esforço efetivo, não atingir VERIFIED. Se só fornece configuração efetiva de lançamento, registrar precisamente esse tipo de evidência e exigir que a integração confirme que ele representa a configuração usada e reporte substituições; sem esse contrato observável, bloquear. Não alegar execução de modelo por hash de prompt ou pelo `runtime_handle` da cadeia canônica.

### Orca opcional: caminho concreto observado

Usar o executável ativo conforme o guia servido por `orca skills get orchestration`; não hardcode binário, path de transcript ou banco interno. O adapter confere capability de launch preferences antes de solicitar modelo/esforço. `worker-start` cria **especialista interno**, nunca outra execução da macroetapa; tarefa inicial é apenas bootstrap. Usar terminal novo, porque --terminal não combina com preferências.

Conferir `launch.requested/effective` da resposta e `worker.startOptions.launch` no worker-show. Correlacionar dispatch, task, incarnation, host e worktree. Só então responder readiness e transmitir o brief na mesma dispatch. O worker produz resultado, o líder persiste, e settlement aceito autoriza `worker-release --dispatch ...`. Ler worker-show/list após release; closed/release concluído da mesma identidade é a confirmação. Archive permanece fora da worktree; se faltar cópia durável do resultado, não encerrar.

`release_pending`, `release_unknown`, `unverifiable`, terminal reaproveitado por outra dispatch e `agentWait=null` não comprovam encerramento. Nunca substituir release por terminal close. Remote host sem capability ou inacessível bloqueia; não executar localmente como fallback. CLI retorna recuperação exata da mesma operação; ela só é seguida quando for uma ação conhecida/permitida, não via shell livre.

### Codex/Claude nativos

Resolver somente ferramentas realmente expostas pela versão da sessão. Configuração de agent fixa modelo/esforço, mas não é receipt de execução. O adapter deve demonstrar seleção, identidade, efetivo e fechamento com read-back daquela superfície. `interrupt` pode só terminar um turno; `SubagentStop` pode só indicar conclusão; não equivalem automaticamente a close confirmado.

Nesta pesquisa, não foi verificado um contrato nativo portátil que exponha todos esses fatos. Portanto o comportamento definido para uma superfície incompleta é `SPECIALIST-CAPABILITY-UNPROVEN` antes do payload, com campo/provider ausente no diagnóstico. Isso é um bloqueio de capacidade previsto, não suporte nativo inventado. Não iniciar `codex exec` ou `claude` para executar uma macroetapa fora da sessão líder. Orca não é selecionado silenciosamente para contornar bloqueio: o operador escolhe transporte comprovado ou fornece uma superfície válida.

## Frontend e Impeccable

Classificar por development-type das DUs/handoff/PLAN-CONTEXT, verificando consistência. Qualquer DU frontend ou superfície visual explicitamente incluída exige design; classificação conflitante/ausente bloqueia. DU-001 desta spec é platform-devops e não declara superfície: NOT_APPLICABLE, sem design visual próprio.

Resolver Impeccable por catálogo/superfície da sessão e arquivo efetivo, guardando path, versão, hashes do conteúdo e entrypoint de invocação. Não reutilizar o catálogo canônico v4 para fingir que Impeccable já está nele; a capability é do suplemento. Não instalar automaticamente. Engine local é opcional quando o fallback documentado de contexto permite a skill executar; o launcher capaz de baixar bytes não é chamado pelo core. Não confundir fallback documentado de contexto com emular a skill ausente.

Dentro de plan: autor xhigh usa Impeccable para escolher a direção e produzir preview em `specs/<feature>/design/`; revisor high distinto avalia. HTML estático autocontido e capturas PNG compõem o resultado mínimo, com estados/viewports derivados do escopo. Captura/render pertencem às ferramentas visuais já disponíveis no harness, sem dependência nova no core ou CI. Sem render/capture comprovados, a preview não é READY.

Manifest fecha a lista de arquivos, hashes, entrypoint e capturas. Reject external resources e path escape; preview deve continuar revisável a partir dos bytes preservados. Core valida estrutura, não qualidade visual. Revisor avalia visual/UX/acessibilidade conforme escopo; operador recebe link/visualização concreta e aprova aquele digest. Inputs/artefatos novos tornam a aprovação STALE. Uma aprovação textual só é válida quando a interação comprova qual preview foi apresentada e aprovada.

`gauntlet-step-enter tasks` e checkpoint de entrada bloqueiam sem aprovação corrente; attest/conclusão/partition rechecando evitam trocar preview depois da entrada. Se editada durante tasks, a tentativa perde validade e deve voltar ao design/aprovação antes de aceitar nova saída. Gates para não-frontend não exigem Impeccable nem arquivos visuais.

## Seams e validação

Testes injetam observations válidas, ausentes, divergentes, stale e alteradas entre verify/dispatch/accept; nenhum chama runtime real. Testes de cleanup confirmam request/read-back e identidades, não apenas returncode. Tests de integração exercitam o CLI com Store real em Git temporário e seam falso, preservando a distinção entre simulação offline e capacidade live.

Gates: modelo/esforço antes do payload; sessão distinta; proibição de escrita de evidência; matrix de atividades em todas as etapas; invocação canônica ainda obrigatória; aceite por task/fase antes de trabalhadores posteriores; aprovação de preview antes de tasks; nenhuma exigência visual em platform-devops; work_ready no contexto GWD. Changes nos snapshots v3/v4, classes worker-required ou macros falham no conjunto de regressões existente. A amostra live de estilo é gate de aceite da entrega, separado de work_ready e da carga ativa use_ready no bootstrap; suspensão válida não bloqueia trabalho nem comprova funcionamento do estilo.

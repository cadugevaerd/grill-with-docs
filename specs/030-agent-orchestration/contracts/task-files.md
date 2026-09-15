# Contrato do parser e grants: task-files/v1

Aplica-se às tasks do contrato `grill-agent-orchestration/v1`. A representação de execução é `grill-gauntlet-execution-dag/v2`. O parser é stdlib e determinístico; não interpreta a intenção da descrição.

O oitavo requisito não muda esta gramática. i-have-adhd organiza a conversa; o `tasks.md` gerado conserva todos os FRs, tarefas, Files, Results e dependências, mesmo quando excedem cinco itens. Não dividir ou ocultar declarações obrigatórias para cumprir limite de apresentação. O autor xhigh recebe simultaneamente o template completo e a referência local de estilo; revisão high verifica conteúdo e grants, sem alterar a independência dos passes.

## Gramática

Documento declara exatamente uma vez, fora de fences:

```markdown
<!-- grill-task-files:v1 -->
```

Cada tarefa conserva a linha checklist Spec Kit e tem campos imediatamente seguintes, indentados com dois espaços:

```markdown
## Phase 1: Arquivos de distribuição

- [ ] T001 [P] [US2] Ajustar os arquivos da raiz; ACTIVE/FREE é apenas descrição.
  Files: [".gitignore", "./build-dist.sh", "src/new module.py", "specs/030-agent-orchestration/implement/T001.tasks.json"]
  Result: "specs/030-agent-orchestration/implement/T001.tasks.json"
```

`Files:` contém um array JSON de strings, em uma linha. `Result:` contém uma string JSON, em uma linha; tarefas despacháveis têm exatamente um Result e ele deve constar em Files. Resultado por tarefa tem path conhecido antes de partition; node pode conter várias tarefas e seus resultados. Nenhuma interpolação de node_id, wildcard, path inferido ou sidecar adicional.

Tarefa sem escrita declara `Files: []`, sem Result. Ela não cria grant de worker nem usa fallback feature-wide; reporta `read_only_tasks` com task_id/fase para o líder encaminhar execução determinística ou atividade especializada read-only. Não é permitido usar Files vazio e depois produzir arquivo; o líder persiste o retorno na reserva de evidência, sem conceder escrita ao especialista.

Tarefa com path de evidência reservado ao líder declara seus arquivos, sem Result obrigatório. A tarefa inteira vai para `deferred_to_leader`, incluindo quaisquer paths de produto na mesma lista. O líder só executa bookkeeping; se houver julgamento, o encaminha ao especialista e grava ele próprio a evidência.

Regras de parsing:

- IDs T seguidos de dígitos, únicos; tarefa deve pertencer a uma Phase numérica declarada e ordenada. Duplicação/retorno de fase bloqueia; preservar barriers.
- Marcadores `[P]` e `[USn]` continuam metadata; nenhum é path. `[P]` não supera conflito de arquivos.
- Files deve ser a primeira linha após a tarefa; Result, quando aplicável, a seguinte. Campo duplicado, órfão, versão desconhecida, JSON inválido, linha de tarefa malformada ou declaração ausente bloqueiam com ID/linha.
- Ignorar blocos fenced de exemplo como tarefas; abrir/fechar fence é reconhecido antes de aplicar regex de task. Fence não terminado bloqueia formato, evitando ocultar tarefas finais.
- Prosa antes/depois da declaração nunca acrescenta permissões. Não remover pontuação nem sufixo de linha dos paths JSON; um path é o valor exato declarado.
- Arquivo Result deve estar em `specs/<feature>/implement/<task_id>.tasks.json`, uma convenção pública explícita que não depende do agrupamento. O gerador já o inclui em Files; falta dele é erro, não autocorreção.

## Normalização e validação

Remover somente um prefixo inicial `./`; normalizar repetição de `./` não é necessário e deve ser recusado. Comparar unicidade depois dessa normalização. `.gitignore` e `./.gitignore` identificam o mesmo arquivo; declarar ambos é duplicata diagnosticada. Ordenar paths somente para canonicalização do grant, sem alterar significado.

Aceitar arquivo novo, arquivo da raiz, subdiretório e espaços escapados em JSON. Não exigir existência do leaf. Recusar vazio, `.`/`..`, segmento vazio, slash final, path absoluto POSIX, drive/UNC Windows, backslash, NUL/controles, URL, glob e `.git` em segmento de controle. Componentes `.`/`..` internos nunca são resolvidos para “consertar” entrada. Em Windows também recusar nomes reservados/dispositivos, alternate data streams e aliases por ponto/espaço final; em plataformas case-insensitive, colisões de caixa entre paths são diagnosticadas antes do grant.

Reutilizar a regra segura de `gauntlet_runs._is_safe_relative_path`/`_strict_scopes` reforçada para os casos portáveis; o parser não inventa uma versão mais permissiva. Separar normalização de validação para que callers de DAG/declare/prepare também vejam o mesmo path canônico. Validar ancestrais existentes por fronteira no-follow do CLI; leaf existente deve ser arquivo regular, não diretório/symlink. Não seguir symlink nem junction/reparse point para conceder escrita fora da árvore. Quando plataforma não puder comprovar a cadeia de diretórios, recusar caminho, não permitir por suposição.

`_dag_scope_violation` continua proibindo `.grill` e `.specify/reports` em qualquer profundidade. Proteções de Constituição/WORKFLOW/registry de coordenação continuam como hoje. `scope_files` da entrega é um limite adicional: Files deve ser subconjunto dele. Resultado também deve estar declarado nesse escopo adotado; não expandir automaticamente para acomodá-lo.

Paths da instalação upstream, observações de runtime ou configurações globais presentes no contexto de apresentação são entradas de leitura, nunca concessões de escrita. Não adicioná-los a Files/Results por referência textual. Nesta entrega, tarefas que alteram o bootstrap GWD, `dependencies.json`, `AGENTS.md` ou `CLAUDE.md` deste projeto devem declarar esses paths explicitamente no escopo revisado; não ampliar para os diretórios globais dos harnesses. Instalação/habilitação e registro de evidência live são operações do líder pelas superfícies proprietárias, sem grants de worker para caches ou `.grill/`.

## DAG, brief e reconciliação

DAG v2 = campos v1 mais `tasks_contract="task-files/v1"` , `tasks_semantic_sha256` e `accepted_tasks` (mapa vazio na primeira execução); node = campos v1 mais `task_ids` e `result_files` (mapa ID→path). `nodes[].files` é exatamente a união das Files normalizadas das tarefas daquele node, incluindo seus Results expressos. Não há escopo FEATURE_WIDE nem tarefa unmapped despachável.

Agrupar conflitos por arquivo dentro da fase com o algoritmo existente; fases são barreiras. `max_workers` e `parallel` mantêm semântica atual; ausência de grupos suficientes é PARTITION-DEGRADED honesto. Report v2 enumera `read_only_tasks`/`deferred_to_leader` por task_id, fase e razão, e `phases[].task_ids` cobre todas as tarefas, inclusive fases sem nodes e importações aceitas. Validar esse mapa contra tasks parseado/fingerprint e DAG; não confiar em fase livre informada pelo caller nem eliminar fases ao filtrar workers.

O suplemento de `implement-parallel` substitui expressamente a ordem legada de executar deferred só depois de todas as waves: percorrer fases na ordem declarada; em cada fase, executar/convergir seus workers e depois resolver read-only/deferred na ordem de tasks. Fase sem worker resolve suas atividades antes de qualquer wave posterior. Dependência de tarefa fora do scheduler que deva anteceder um worker da mesma fase exige que o autor a coloque em fase anterior; o core não infere essa ordem da prosa nem altera o agrupamento. O líder mantém bookkeeping; julgamento usa os especialistas obrigatórios e aprovação humana, quando exigida, precisa de fonte observada.

Cada tarefa fora do scheduler usa as activities/receipts existentes com `task_binding={task_id, phase, tasks_semantic_sha256, dag_content_sha256}` validado no input_manifest, atividade e aceite. A tarefa só satisfaz a barreira após aceite positivo de todas as atividades exigidas para ela, inputs/outputs correntes e bookkeeping confirmado; revisão CHANGES_REQUIRED, decisão humana pendente/negada, falha ou diagnóstico apenas persistido não bastam. Files vazio não exige Result nem commit fictício. Escrita deferred exige manifest/hash dos arquivos declarados e efeito confirmado na branch de execução; eventual conteúdo de especialista é materializado pelo líder, sem grant na reserva.

Antes de wave-declare, worker-declare, prepare legado/remediation e liberação do payload de worker, um guard comum revalida que **todas** as tasks de fases anteriores estão satisfeitas: workers com resultado aceito e integração comprovada, importações verificadas ou receipts positivos das atividades fora do scheduler. O mesmo guard precede dispatch/aceite de atividade vinculada a task: exige workers da sua fase convergidos e read-only/deferred anteriores da mesma fase aceitas. Rechecar fence, revisão e inputs na transação; pendência retorna `TASK-PHASE-PENDING` com IDs/fases, sem grant ou envio. `gauntlet-tasks-reconcile` inclui esses aceites por task_id; attest/checkpoint complete de implement-parallel exigem todas as tarefas fora do scheduler satisfeitas, inclusive a última fase, além da prova real dos workers cobrindo o DAG. Aceites persistem por referência no checkpoint de continuidade; retry não reexecuta tarefa já aceita.

**Limite sem workers**: quando não restar nenhuma tarefa despachável, `partition-emit` retorna BLOCKED/`PARTITION-NO-WORKERS`, exit 2, com listas/fases completas e nenhum DAG, antes de gauntlet-run/admissão. A gramática continua válida, mas esse conjunto não abre nem conclui o ciclo `worker-required`: não há DAG-VALID, checkpoint completo de partition/implement-parallel, wave ou worker fictício. O suplemento interrompe a skill partition nesse diagnóstico antes dos passos de admissão/validação. A recuperação é revisar com o autor o escopo real das tasks, sem inventar trabalho para preencher o DAG; se tudo já foi aceito, preservar a conclusão histórica sem reabrir a etapa. Suporte a concluir um ciclo novo inteiramente read-only/deferred está fora deste desenho e não altera classes/tabelas v3/v4.

O hash semântico é SHA-256 do UTF-8 de tasks com somente checkboxes de tarefas parseadas normalizados para espaço; restante dos bytes intacto. Trocar `[ ]` por `[X]` em reconcile não muda pin. Mudar descrição, fase, Files ou Result muda fingerprint. `dag_content_sha256` continua SHA-256 sobre bytes exatos do documento DAG, sem mudança de definição para v1.

`gauntlet-partition-brief` recebe DAG+report v2, valida seus vínculos e devolve task_ids/files/result_files concretos; não procura por sufixo de node nem emite um path extra. Worker escreve somente Results declarados e retorna completed task IDs. Result mínimo: schema `grill-task-result/v1`, work_id, scheduler_run_id, node_id, task_id, attempt_id, status completed/failed e diagnóstico referenciável. O commit terminal é observado e registrado pelo líder no receipt, fora do próprio arquivo Result; não exigir que um arquivo contenha o hash do commit que inclui a si mesmo. Campos devem corresponder ao grant e à tentativa registrada.

`gauntlet-tasks-reconcile` lê Results integrados nos paths declarados e receipts de activities das tarefas fora do scheduler, confirma atribuição e aceite positivo pelo líder, e marca somente IDs completed. Result/receipt de outra task/fase/revisão/node/run/attempt não marca checkbox nem libera barreira; arquivo ausente é pendência nominal. Checkboxes já aceitos não são desmarcados por ausência transitória, mas não substituem prova corrente no guard. Workers continuam proibidos de editar tasks.md. Diff pré-merge verifica ambos os paths de rename e deletions, sem prefix grants; escrever diretório vizinho falha.

## Migração

`task-files-migrate` recebe arquivo de proposta completo já produzido pelo autor e revisado por outro especialista. Preview mostra diff, IDs preservados/adicionados, alterações de Files, hashes original/proposta e DAGs/runs que referenciam a revisão atual. O core **não** preenche Files com `extract_files` nem trata a prosa antiga como autorização.

Apply exige expected hash e proposta idêntica ao preview, identidade/época atuais e nenhuma atividade concorrente. IDs aceitos/checkboxes completos permanecem associados aos mesmos resultados; renomear/reabrir exige mudança explícita de escopo e não faz parte da migração sintática. Sob contrato novo, marcador ausente resulta `TASK-FILES-MIGRATION-REQUIRED`; não há flag permanente de fallback heurístico.

Um DAG referenciado por run, mesmo COMPLETE/BLOCKED, é selado e nunca sobrescrito por partition-emit. Preservar `execution-dag.json` v1, seu report e receipts; nova revisão usa `execution-dag.r2.json` e `partition-report.r2.json` selecionados explicitamente. Continuação do restante usa run sucessora e recibo de sucessão. O DAG v2 registra accepted_tasks por task_id, com receipt/digest/contexto e commit integrado quando houve escrita; nodes só contêm trabalho restante e não criam workers fictícios para tarefas já aceitas. Importar read-only/deferred de v2 exige receipts positivos das activities e vínculo aos mesmos IDs/fases/inputs; a sucessão preserva a proveniência do DAG antigo, sem reetiquetar os receipts. Em v1, a importação de worker exige report de atribuição, sidecar completed e receipt de integração correlacionados; checkbox isolado não basta nem importa tarefa deferred sem prova de aceite. Prerequisitos importados são revalidados antes das novas waves; v1 não é reinterpretado como v2. Nenhum completed effect é executado outra vez. O binário antigo já selado pode concluir seu próprio ciclo, mas a migração é obrigatória para continuar no binário novo.

## Diagnósticos e checks

Códigos novos: `TASK-FILES-MIGRATION-REQUIRED`, `TASK-FILES-MISSING`, `TASK-FILES-INVALID`, `TASK-FILES-DUPLICATE`, `TASK-RESULT-MISSING`, `TASK-RESULT-UNDECLARED`, `TASKS-STRUCTURE-INVALID`, `TASK-SCOPE-VIOLATION`, `DAG-SEALED`, `TASKS-SOURCE-STALE`, `TASK-RESULT-DIVERGENT`, `TASK-PHASE-PENDING`, `PARTITION-NO-WORKERS`. Payload inclui task_id, fase, linha e path quando seguros; nenhuma recusa emite grant parcial.

Checks offline mínimos: raiz/novo/subdir/./; ACTIVE/FREE na prosa; spaces; JSON inválido; duplicatas normalizadas; fence de exemplo; Files ausente/vazio; Result fora da lista; POSIX/Windows/traversal/symlink; reserva de evidência; grant exato; v1 pin intacto; checkbox reconcile preserva fingerprint; mudança de input exige nova revisão; resultado de outra tentativa não marca task. Reusar Git temporário e testes existentes de grant/convergência.

Checks de barreira: fase inicial/intermediária só read-only/deferred bloqueia workers posteriores até aceite positivo; deferred prepara arquivo consumido na fase seguinte; falha/revisão negada/receipt stale não liberam wave nem prepare direto; última fase pendente impede fechamento. Retomada reutiliza aceites íntegros sem repetição. Conjunto todo read-only/deferred retorna PARTITION-NO-WORKERS antes de admissão, com zero workers e zero receipt terminal; `worker-required` continua recusando atestação sem execução real. Teste de integração verifica a nova ordem no suplemento entregue à skill pinada, não apenas os guards isolados.

Regressão do oitavo requisito: fornecer contexto GWD com paths absolutos do i-have-adhd e descrição que referencia o componente; grant permanece exatamente Files. Gerar documento com mais de cinco tarefas sob apresentação ativa e conferir que nenhuma foi omitida, resumida ou deslocada para fora do contrato. Autoria exige work_ready: carga corrente quando ativa ou suspensão humana válida da própria sessão, mantendo instalação/habilitação. Essa distinção não muda a saída do parser para os mesmos bytes nem reescreve DAG já selado.

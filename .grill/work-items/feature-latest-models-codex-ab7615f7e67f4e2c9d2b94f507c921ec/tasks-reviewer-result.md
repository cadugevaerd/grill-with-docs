# Revisão independente de tasks — latest models

**Veredito: APPROVED**

Nenhuma correção obrigatória encontrada em `specs/033-latest-models/tasks.md`. A organização, grants, dependências e cobertura permitem seguir para os gates canônicos de analyze/partition; esta revisão não aceita a macroetapa, não emite um DAG e não autoriza implementação ou ship.

## Alvo, critérios e independência

Alvo: `specs/033-latest-models/tasks.md`, SHA-256 `f70639d839803532422ba28979f8a4475fda225f268c03da6d1f01bca40006a8`. Conferi os 44 arquivos selados do payload por SHA-256 no início e antes de gravar este relatório: zero divergências. Li o alvo integralmente, a skill canônica `.agents/skills/speckit-tasks/SKILL.md`, template, spec, plano e companheiros, ADRs e evidências; consultei fontes/testes nas seções relevantes. O resultado do autor foi contexto, não substituiu o parser e os checks próprios.

Revisor: dispatch `ctx_05f28e316dbe`, task `task_ba7a272bb0f1`, terminal `term_b619609a-2a0d-4151-b252-12b694ed5cb3`, incarnation `e15433f9-09fa-4d43-aa0e-a45c7f54b473`. A observação selada do autor registra dispatch `ctx_584ac8fa7934`, terminal `term_68998387-4509-4655-82b1-262b848d0d4d`, incarnation `559ad23a-fd9c-4882-bd62-c5f91bcb9fe4`, requested/effective/resolved `gpt-6-astra`, esforço `xhigh`, `activity=exited`, `close=closed`. São sessões distintas; o revisor também difere dos autores do plano documentados na revisão r2. A revalidação nativa do par deste revisor no retorno e seu close são responsabilidade do coordenador.

Bootstrap literal próprio executado antes do payload e revalidado ao final pelo comando exato do preâmbulo: `work_ready=true`, `loading=loaded`, `trust=ready`, `enablement=enabled`, `verdict=OK`. Leitura correlacionada: `orca:ctx_05f28e316dbe:ctco_01a0d45a-e368-7851-898d-845adb920af8`. `behavior=not_tested` e `functional_verified=false`; não há alegação de conformidade comportamental.

## Formato, parser real e partições

`tasks.md:9` contém exatamente um marcador `grill-task-files:v1`. T001–T020 são únicos, consecutivos, abertos, com seis fases numéricas estritamente ordenadas. Setup/fundação/polish não carregam story; fases US1/US2/US3 carregam os labels corretos e prioridades P1/P1/P2. Critérios independentes, MVP, exemplos de paralelismo e estratégia estão presentes. Os testes são solicitados por FR-010/013, não adição especulativa. Hooks before_tasks/after_tasks são opcionais; nenhum commit ou despacho era exigido desta revisão.

Executei, com `python3 -B`, as funções reais `partition.parse_task_files` e `partition.partition_task_files`, passando `feature="033-latest-models"`, `groups=2` e o root real. Executei também `_validate_dag_structure`, `_validate_dag_scope` e `_validate_dag_tiers`, com pisos medium/small. Tudo em memória, sem writer, emissão, admissão ou selo.

**Veredito exato do parser: `PARTITION-DEGRADED`.** É a classificação prevista devido às tarefas read-only/deferred, não uma recusa nem `PARTITION-NO-WORKERS`.

| Fase | Workers reais | Atividades após convergência, na ordem |
|---|---|---|
| 1 | Nenhum | T001 read-only → T002 líder |
| 2 | p02-a: T003; p02-b: T004 | T005 read-only |
| 3 | p03-a: T006 → T007 | T008 read-only |
| 4 | p04-a: T009; p04-b: T010 | T011 read-only |
| 5 | p05-a: T012 → T013 → T014 | T015 líder → T016 read-only |
| 6 | p06-a: T017; p06-b: T018 | T019 read-only → T020 líder |

Resultado: 20 tarefas, 11 despacháveis com escrita, seis read-only, três deferred, oito nós reais e largura máxima dois. Asserts próprios conferiram IDs, checkboxes, story labels, os seis `[P]`, grupos seriais e interseções vazias entre grants de todos os nós da mesma fase.

`Files:` é JSON imediato em cada tarefa. Cada tarefa worker tem exatamente um `Result:` imediato, no caminho público da própria task e incluído no grant. T001/T005/T008/T011/T016/T019 têm `Files: []` sem sidecar. T002/T015/T020 declaram somente evidência `.grill/`, são explicitamente reservadas ao líder e o parser as exclui dos workers. Nenhum worker fictício, grant implícito ou arquivo de evidência reservado escapou para um nó.

Os nós T003/T004 são independentes: resolvedor/fixture e schema Store ocupam arquivos separados; validação histórica de Store é expressamente sem lookup no catálogo. T009 é teste do resolvedor já entregue; T010 cobre fronteira pública em arquivos separados. Eventual defeito de resolver descoberto por T009 exige correção com escopo/revisão próprios (`tasks.md:112`), não escrita oculta. T017/T018 dividem documentação/distribuição e helpers downstream. US1 e US3 agrupam testes/implementação que compartilham arquivos; a ordem interna é explícita. Reuso de `grill_workspace.py`, `gauntlet_runs.py` e fixtures entre fases fica serializado pelas barreiras (`tasks.md:174`–`:192`).

Não encontrei pré-requisito circular: T001/T002 antecedem edições; T015 sucede os workers US3; T020 prepara handoff, enquanto verify/review/ship continuam posteriores (`tasks.md:170`). A fase inicial sem workers exige aceites próprios antes de p02; a última fase também precisa de aceite, conforme `tasks.md:16` e o contrato de barreira, não apenas as arestas do DAG.

## Cobertura de requisitos e achados por localização

**Findings obrigatórios por arquivo/linha: nenhum.** A tabela registra a evidência positiva e inclui todos os FR e SC.

| Requisitos | Local em tasks.md / tarefas | Evidência de cobertura |
|---|---|---|
| FR-001/002; SC-001/002 | :53–:61, :71–:88; T003/T004/T006–T008 | Família Luna/Terra, ranking independente de geração/ordem, Terra mais nova com prioridade pior/melhor, binding antes do primeiro DECLARED, projeções duráveis. |
| FR-004/008/009; SC-004 | :57–:63, :75–:88; T003/T004/T006–T008 | Três produtores: declare_worker, prepare_worker público passivo e _mint_remediation_worker; runtime da activation validada, tier explícito ou floor do grant, retry com catálogo alterado/removido, remediação como nova seleção; aliases Claude e pisos preservados. Replay legado sem backfill; binding imutável. |
| FR-005/006/010/013; SC-001/003/008 | :57, :96–:109; T009/T010/T011 | Matriz de entrada insegura/inválida, prioridades e empates; fronteira antes da leitura; erro público com JSON/código/metadados, Store/journal/receipts/grants/leases/worktrees/payload sem efeitos, orçamento/estado original preservados em ambos os motivos de remediação. |
| FR-003/004/007/008/009; SC-001/002/004 | :118–:148; T012–T016 | Astra por papel e pedido salvo; igualdade nativa requested/provider/effective/resolved e esforço; Opus exato xhigh/high; fable recusado, inclusive novo payload de atividade histórica preparada; schema policy v2 e Store v1, loader fechado, histórico por selo original sem catálogo. |
| FR-009/010; SC-003/004 | :19–:35, :44, :140–:143; T002/T015/T016/T020 | Bundle fixado com f1475f4, CLI absoluto v1 para coordenação, candidata isolada; experimento combinado predecessor sem campanha/candidata/bundle e negativo com bridge obrigatória. Ciclo offline completo exigido em T015, sem introduzir path local como dependência da suíte portátil. |
| FR-010/013; SC-001/005/008 | :7, :41, :53–:57, :160–:170; T001/T003/T018/T019 | Fixture 0.155.1 com nove entradas e proveniência; hidden/generic/upgrade preservados; seam explicitamente ausente/inválido sem fallback global; expectativas derivadas da fixture; suíte completa antes do código e após integração, seguida de rerun no verify. |
| FR-011; SC-006 | :154–:164; T017/T019 | SKILL, protocolo, README e ADR atualizados para famílias/Opus; evidência histórica fable preservada. Não confunde catálogo listado com disponibilidade remota ou freshness. |
| FR-012; SC-005/007/009 | :154–:170; T017/T019/T020 | Oito pontos SemVer no mesmo grant, CHANGELOG cumulativo incluindo f1475f4, versão maior/unused, diff hygiene, verify/review e autorização humana antes do pipeline tag/Release no mesmo anchor. |

Conferência das fontes: `gauntlet_runs.py:2187` e `:2524`, mais `grill_workspace.py:4487`, confirmam os três callers de `prepare_worker`. A seleção hoje é apenas reportada em `gauntlet_runs.py:2191`; `store.py:827` mantém shape fechado sem binding. T004/T007 tratam essa causa estrutural, não apenas o asset. `_resolve_worker_model` perde `TierModelError.extra` em `gauntlet_runs.py:2109`; o handler passivo também reduz o payload. T010 cobre as duas fronteiras.

As chamadas estáticas de `specialist_pair` em `agent_orchestration.py:346`, `:850`, `:1199` e `:1630` correspondem às verificações de sessão, preparação, visual e task review explicitadas em T013. Os carregamentos fixos v1 de `grill_workspace.py:1277`, `:1615`, `:1707`, `:1782`, `:5622`, `:5803` e `:5826` entram na regra única de T014. Helpers scheduler/converge/status também chamam o par estático e estão em T018. O reader `_native_bytes` já existe em `agent_runtime.py:596`, e a igualdade Opus observada já é preservada em `:1236`; não há grant desnecessário para alterar esse módulo.

Conferi os oito pontos de T017 contra `tests/validate_distribution.py`: quatro manifests, constante VERSION, headings SKILL/session-protocol/README. CHANGELOG é adicional a esses oito. `tests/run_validators.py` descobre `validate_*.py` e imprime `==>` antes de cada execução; T001/T019 pedem a contagem correta, sem número congelado ou alteração desnecessária do runner.

## Continuidade reproduzida e limites

Reproduzi independentemente integridade do bundle `/home/carlosaraujo/orca/workspaces/grill-with-docs/continuity-5544829`: HEAD detached `5544829185c2e5d1d75e52736364aa00bede9323`, status tracked/untracked limpo, ancestralidade de `f1475f4f9523fcd7063e32b547aa6fd8bc364528`, árvore `HEAD:plugin/skills/grill-with-docs=d5cc959f9c02a98ddc3a5adfd958d729b62807ce`, cinco tamanhos/hashes do manifest correspondentes. O manifest conserva SHA-256 `89f6ede5fd321c1fe901271386458ba6fda452661a3758db4d2cedea0b4817fc`.

Importei somente o módulo preservado para chamar `validate_block` sobre o Store real, sem instanciar writer: PASS, revisão 3345, SHA-256 `ebe681cde94948ce347864a01e0e5913a4628b876dc11754848b16af772aec0b`; bytes idênticos antes/depois. Isso comprova leitura estrutural atual, não lifecycle futuro, admissão do coordenador ou imutabilidade de uma revisão durante progresso normal.

Executei `python3 -B tests/validate_agent_orchestration_contract.py AgentOrchestrationContract.test_first_campaign_is_born_in_a_pre_campaign_successor`: um teste, PASS, exit 0. O teste cobre o positivo do predecessor sem campanha e o negativo sem bridge quando o predecessor já tem campanha. O cenário combinado pós-candidata continua tarefa futura T015.

`git diff --check`: exit 0. `git diff --no-index --check /dev/null specs/033-latest-models/tasks.md`: saída vazia, exit 1 pela existência do arquivo novo, sem diagnóstico de whitespace. A suíte completa não foi repetida, conforme a instrução explícita para revisão documental; nenhum resultado completo anterior é atribuído a esta sessão.

## Risco residual e handoff

1. `tasks-author-result.md`, seção Bootstrap, relata `STYLE-LOAD-UNCONFIRMED` numa sondagem do especialista pela CLI preservada, embora o comando exato do seu preâmbulo estivesse ready. Não reproduzi nem diagnostiquei essa diferença. Ela não prova falha da sessão do coordenador, mas exige atenção na revalidação já obrigatória de T002 e antes de cada gate: não substituir a CLI preservada para contornar recusa nem presumir carga herdada. Esta aprovação não declara resolvida a sondagem nem comprovada a apresentação do coordenador.
2. T012–T014 formam um grupo maior porque compartilham o validador e a semântica de policy. A divisão serial é realista; dividir por arquivos adicionais para aumentar largura introduziria acoplamento concorrente. Gates e testes podem descobrir novos reparos que precisarão de escopo explícito, sem ampliar grants silenciosamente.
3. O catálogo é dependência local e sem garantia de disponibilidade remota. Os checks desta revisão avaliam o plano de execução; seleção, ausência de efeitos, lifecycle candidato, sucesso da suíte integrada e release ainda precisam de evidência futura. T015 deve registrar comandos reproduzíveis, revisões/diff e efeitos, e verify precisa revalidá-los.

Não editei arquivo do repositório, bundle preservado ou cache upstream; não lancei worker, executei macroetapa, criei commit ou publiquei. O único artefato produzido é este relatório externo. Cabe ao coordenador copiá-lo literalmente, revalidar bytes/observação, aceitar o resultado e confirmar settlement/release/cleanup pelos mecanismos canônicos antes da próxima etapa.

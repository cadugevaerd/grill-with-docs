# IMPLEMENTATION-INTEGRATION — spec 030

**Estado: T027 materializada; revisão final dos bytes reservados do dossiê pendente.** Não é atestação de macroetapa, aceite de T028–T030, prova funcional live ou autorização de publicação.

Work item: `feature-new-subagents-unified-69f619a1a4774d598e4a46c77396f0fa`; fase `FASE-001`; DU `DU-001`, `platform-devops`, sem frontend próprio. Fonte da proposta: commit `5bc9500e6fff10fce5353f758fdc334e490a3523`. O líder gravou este destino reservado após revisão dos bytes externos.

## Materialização T027

- Autor inicial: task `task_fc2138f2d5ec`, dispatch `ctx_b54fb553c0f4`, terminal `term_9dab1c1e-746d-4b0b-81ba-d31c110e005c`, Codex `gpt-6-astra/xhigh` solicitado e efetivo.
- Revisão autoral R1/R2: task `task_ec3dc3154556`, dispatch `ctx_fb1ace191d92`, terminal `term_a08ac800-0320-45d3-a9e1-dc41b360aa5a`, Codex `gpt-6-astra/xhigh` solicitado e efetivo.
- Revisão independente original: task `task_751d95d94b0e`, dispatch `ctx_87cdb67bb63c`, `CHANGES_REQUIRED`, relatório SHA-256 `4c4f66cd1861caea8ce3ee695eecdf7da74d66e5ce3632f713aa616df014dc98`.
- Re-revisão independente: task `task_c8e38691650a`, dispatch `ctx_54081b7e4a6f`, terminal `term_92fb16e5-ca6a-408d-9aff-965c9aecb2fe`, Codex `gpt-6-astra/high` solicitado e efetivo; veredito `GO`; relatório SHA-256 `e5eba24d35e8c0cf17fcd7abcbac991d65a313fb946f55c3af67b689190b6ab4`.
- Proposta aprovada: `MANIFEST.json` SHA-256 `1b4aa5cabfac993de06a805dcf17f72f09cb418dd92ffdadfdea078f8ffff1f5`; `AUTHOR.md` SHA-256 `11ca987a2e8c3361cc202a4470e23a700ffedc522e358e843f25e55795b828f5`.
- Aplicação: 12 arquivos copiados mecanicamente e relidos; todos coincidiram com o manifest antes desta atualização reservada. Os outros 11 arquivos permanecem byte-idênticos aos hashes aprovados. Este dossiê diverge somente para registrar a materialização real e exige revisão high final desses bytes.
- Gate na árvore materializada: `PYTHONDONTWRITEBYTECODE=1 python3 -B tests/validate_distribution.py` → `distribution: OK`; `git diff --check` → exit 0.

## Escopo e proveniência da proposta

T027 abrange exatamente os 12 Files declarados em `specs/030-agent-orchestration/tasks.md`: README, AGENTS, CLAUDE, CHANGELOG, quatro manifests, validador de distribuição, skill GWD, protocolo e este draft. O pacote externo `/tmp/gwd-t027-proposal/MANIFEST.json` lista SHA-256 dos bytes por caminho; `/tmp/gwd-t027-proposal/AUTHOR.md` registra decisões, verificações e limitações. Esses paths identificam a proposta de autoria, não um receipt de aceite.

O líder deve preservar a fonte observada de launch/identidade/modelo/esforço do autor e obter revisão high em sessão distinta de todos os autores dos inputs. A proposta não afirma que esses fatos foram comprovados pelo próprio autor. Registrar depois a revisão dos hashes exatos, o diff materializado, read-back e eventuais correções com nova revisão; não promover este texto a comprovação automática de autoria/independência.

## Cobertura documental dos oito requisitos

| Requisito | FR / SC | Superfície descrita | Evidência de aceite ainda necessária |
|---|---|---|---|
| Cleanup | FR-001..004 / SC-001 | Recursos separados, intenção/read-back, resultado durável, COMPLETE, preservação/UNKNOWN e retry sem repetir etapa | T028: sessões de worker integrado, falho e read-only; fechamento e recursos preservados por motivo |
| Files e escopo | FR-016..019 / SC-006 | Files/Result explícitos, DAG v2, reserva do líder, barreiras por fase, migração e limite sem workers | Evidência atribuída de T014–T018/T026 e rechecagem final T030 dos guards e bytes |
| Continuidade | FR-006..007 / SC-002 | Checkpoint, quiescência, fence/CAS, mesma worktree, campanha sucessora e aceites íntegros | T028: duas direções, refs/digests antes/depois e ausência de efeito aceito duplicado |
| Recomendação | FR-005 / SC-003 | Sol/Opus em início/retomada, sem mudança do modelo ativo | T028: quatro entradas observadas com `active_model_changed=false` |
| Autoria | FR-011..012, FR-015 / SC-004 | Astra/fable xhigh, bootstrap neutro antes do payload, coordenação do líder | T028: requested/effective, identidade e envio correlacionados nos dois runtimes |
| Revisão | FR-013..015 / SC-004 | High em sessão distinta de todos os autores; checks separados de julgamento | Revisão high dos bytes finais e evidência de independência; T028/T030 |
| Design frontend | FR-008..010 / SC-005 | Impeccable, HTML/PNG, revisão e aprovação humana corrente antes de tasks | Regressões frontend e classificação NOT_APPLICABLE desta DU; T024–T026/T030 |
| Apresentação local | FR-021..024 / SC-008 | Stack, instalação efetiva, carga integral, suspensão/compactação, conteúdo/Ponytail e controle externo | T029: C1/C2/A1/A2 e demais controles live, completos e revisados |

FR-020/SC-007 atravessam todos os itens: integração de código/contratos/skills, oito versões 6.0.0, CHANGELOG cumulativo, gates constitucionais e publicação posterior. Esta tabela é rastreabilidade documental; não marca nenhum FR/SC como aceito.

## Distribuição e preservação

A proposta fixa 6.0.0 nos quatro manifests, na constante VERSION de `tests/validate_distribution.py` e nos headings únicos de README, GWD e protocolo. CHANGELOG recebe uma única entrada cumulativa 6.0.0; todo histórico anterior é preservado. As demais asserções do validador são byte-idênticas. AGENTS/CLAUDE recebem somente o mesmo bloco local de bootstrap, conservando todo o conteúdo anterior, inclusive Ponytail.

Não são propostos ajustes em spec/plan/tasks, `.grill/` real, `.specify/`, catálogo/registry/confiança v3/v4, tabelas/ESSENTIAL/classes de execução, onze skills canônicas, Constituição, WORKFLOW ou bundle histórico. O arquivo neste path é uma proposta externa, não escrita realizada na reserva de coordenação.

## Observações offline e limitações conhecidas

O baseline obrigatório `python3 tests/run_validators.py` foi executado sobre a fonte antes da autoria e retornou exit 1. O runner parou em `validate_backlog_contract.py`, que reportou 110 testes, 10 failures e 3 errors; failures incluem `LEADER-AUTHORITY-UNPROVEN: session_ref is required before init effects`. Não há resultado verde da suíte completa desta candidata. O baseline histórico descrito no quickstart não substitui esta execução.

Leitura do parser e handlers na fonte citada identificou divergências que T027 não pode corrigir:

- **R1 — init/adopt permissivos:** `init_command` exige somente `session_ref` não vazio antes dos primeiros efeitos. Tanto `_initialize_orchestration` quanto `orchestration_adopt_command` usam `_orchestration_inputs` → `adoption_inputs` → `new_work_item`, sem ler observação de sessão correlacionada nem fornecer `presentation`. O contexto/líder nasce `ACTIVE`, com `incarnation`, `observation_ref` e `observation_sha256` nulos. `require_authority` compara contexto/época/estado e igualdade da string; `require_presentation_work_ready` sem apresentação devolve `{"legacy": true, "work_ready": true}`. Sucesso de init/adopt, ACTIVE e fallback legacy não provam sessão nem apresentação obrigatória. A lacuna não se limita ao preflight: remediação delimitada do core e revalidação são pré-condições dos aceites funcionais posteriores; a obrigação normativa de bloquear não é garantia implementada por esses handlers.
- `preflight` não aceita `--session-ref`; `preflight_command` não produz `presentation/load_request` nem consome observação da sessão. `ensure_dependencies.preflight` continua reportando presença/dependências. O helper de apresentação existente não comprova que o bootstrap contratual esteja conectado ao CLI.
- `gauntlet-cleanup` expõe somente seleção `--run-id` mais `--worker-id` e `--session-ref`; não expõe `--activity-id`, `--context-id` ou `--epoch`. Sem o par de run/worker, o handler recusa `SCHEDULING-NOT-AVAILABLE`; isso não demonstra a varredura contratual sem selector.
- `task-files-migrate` não expõe os parâmetros contratuais de contexto/época/sessão e autor/revisor; exige `--expected-sha256` já no preview e `--expected-proposal-sha256` no apply. A presença do comando não comprova o gate de proposta especializada revisada.

São fatos estáticos da fonte inspecionada, não diagnóstico exaustivo do core nem prova de incapacidade universal dos runtimes. O líder deve reconciliar código/contratos em tarefa delimitada antes de declarar rollout funcional; não editar documentação ou suprimir asserções para esconder as lacunas. Os textos públicos normativos exigem diagnóstico/bloqueio quando o binário/adapter não oferece a continuação contratada.

**R2 — receita de checkpoint:** protocolo e exemplo de sucessão incluem `--session-ref` e `--operation-id`, conferidos contra parser/handler da fonte. Em item adotado, a persistência recusa `OPERATION-ID-REQUIRED` sem ID; retry/recovery mantém o mesmo ID e request, enquanto aceitação de receipt sucessor recebe ID próprio, conservado em suas retentativas. `attest` não aceita essas flags. Essa correção documental não executa checkpoint, não cria operação/receipt real e não comprova continuidade live.

Verificações da proposta são detalhadas em AUTHOR.md; logs externos da autoria inicial permanecem históricos. Distribuição avaliada sobre overlay isolado pode comprovar os oito pontos e headings, mas não comprova aplicação no worktree, execução real de skill/modelo, style live, cleanup real ou aceitação de etapa. O primeiro gate global de distribuição continua a ser executado pelo líder sobre a candidata materializada e comparada aos hashes revistos.

## Trabalho restante do líder

1. **T027:** revisão high dos 12 arquivos exatos; materialização mecânica, read-back de hashes, `python3 tests/validate_distribution.py` e diff sem whitespace inválido na candidata. Registrar fontes de autoria/revisão e eventuais correções. Os quatro manifests e três headings precisam conter a mesma versão que o validador; CHANGELOG tem exatamente um heading 6.0.0.
2. **T028 — pendente:** disponibilizar a candidata pela superfície proprietária em ensaio isolado e registrar bundle/versão/hashes efetivos. Comprovar autor xhigh/revisor high distintos em Codex e Claude, implementação não-frontier, falha/read-only, persistência e close confirmado. Trocar runtimes nos dois sentidos e preservar aceites; capacidade ausente é impedimento, nunca PASS.
3. **T029 — pendente:** executar integralmente quickstart §8, C1/C2/A1/A2 com quatro prompts fixos, respostas completas, eventos reais de carga e revisão high das dez regras/exceções. Testar compactação ativa, suspensão→compactação→trabalho sem reinjeção, nova sessão ativa, saída explícita, controles externos/configurações/Ponytail. Registrar também `STYLE-LIVE-VALIDATION.md` pelo líder; não criar esse arquivo como parte desta proposta.
4. **T030 — pendente:** consolidar FR/SC com código/checks/fontes live e revisão dos bytes correntes. Executar a suíte completa e `git diff --check`, contar validadores por `==>`, registrar skips/failures e comparar pins/Constituição/WORKFLOW/bundle histórico. Gate verde exige resolver failures reais, não enfraquecer asserções.
5. **Gates posteriores:** fechar/reconciliar implement-parallel histórico somente após aceites atribuídos; invocar converge, verify, review e ship canônicos, conforme autorização vigente. Bump gate usa a base real de integração; tag imutável e Release no mesmo anchor são verificadas no pipeline antes de marketplaces, sem publicação manual por esta task.

Até ship encerrado, manter CLI absoluto e manifest do bundle histórico 5.4.1; não operar sua campanha com a fonte 6.0.0 nem adotar o work item durante o ciclo. Só depois, adoção explícita de COMPLETE pode importar referências/inventário sem reabrir etapas. Não matar atividade viva, transferir worker ativo, presumir close por silêncio, fabricar worker/receipt ou repetir efeito de outcome desconhecido.

## Critério para atualizar este dossiê

O líder substitui pendência por resultado somente com fonte observada, identidade/contexto, bytes/digests e verificação correspondente. Julgamento high independente não é substituído por checks determinísticos. Evidência é estrutural auditável, sem prova criptográfica de execução de modelo/skill; instalação, habilitação, hook aprovado e exit 0 isolados não demonstram comportamento. Este draft não contém PASS live, aceite T028–T030, atestação canônica ou confirmação de publicação.

## Atualização T029 — 2026-09-15

Laudo líder em `STYLE-LIVE-VALIDATION.md`: Claude Code 2.1.272 executou a sequência canônica em sessão nova sobre `ab52268`; a segunda leitura retornou `loading=loaded`, `use_ready=true`, `work_ready=true`, com o SHA aprovado e fallback local do transcript confirmado. Codex mantém `i-have-adhd` 0.3.0 instalado no cache efetivo e com o mesmo SHA, porém a sessão live foi recusada pela quota do runtime (`You've hit your usage limit`, retomada informada para 2026-09-19); não há PASS live Codex.

T028, T029 e T030 permanecem pendentes: a matriz exige os dois CLIs, respostas comportamentais e revisão high independente. Nenhuma tarefa ou gate posterior deve ser marcado como concluído com esta limitação.

### Atualização T029 — Luna Reserve — 2026-09-15

Uma sessão TUI nativa iniciada com `codex -m gpt-5.6-luna -s read-only -C <worktree>` atingiu o limite do Luna primário e foi continuada pela opção `Continue with Luna Reserve`. O transcript nativo registra proveniência `gpt-5.6-luna`, provider `openai`, modelo efetivo `gpt-reserve`/Luna Reserve, esforço `medium` e probe real `LUNA_TUI_PROBE`; o prompt canônico subsequente carregou `grill-with-docs` e `i-have-adhd` antes de bloquear corretamente em `LEADER-ADAPTER-UNSUPPORTED` e `BACKLOG-UNAVAILABLE`, sem criar work item. Um probe adicional `codex exec --json --model gpt-reserve` respondeu `RESERVE_EXEC_PROBE` com exit 0 na sessão `01a0a5a8-ec4e-7b03-b9cb-289bc10bb947`.

Esta evidência confirma que o caminho Codex/Luna Reserve e o bootstrap de apresentação funcionam, mas não fornece a sessão Orca `orca:ctx-*`, o backlog JSON ou a matriz C1/C2/A1/A2 exigidos por T028/T029; `functional_verified` permanece `false`.

Uma tentativa Orca supervisionada adicional (`task_951c5e9c310d`, dispatch `ctx_eca4f50c6767`, requested/effective `gpt-reserve/low`) falhou antes do turno em `agent_readiness: codex-interactive-prompt`; o terminal residual foi liberado e arquivado. O limite é de inicialização do agente interativo Orca, independente da quota e do turno Codex Reserve já comprovado.

Reteste com terminal Codex Luna Reserve pré-aberto (`task_3726d7cda3b4`, dispatch `ctx_6297e262c85f`, terminal `term_1f904333-8a16-4a51-901e-48b37926800e`) reproduziu o bloqueio: a UI ofereceu `Continue with Luna Reserve`, mas a seleção via transporte Orca retornou `agent_prompt_blocked` e o dispatch encerrou em `agent_readiness: codex-interactive-prompt`. O terminal foi fechado sem turno ou bootstrap; a prova direta Luna Reserve continua válida, porém C1/T029 não avançam.

Probe direto posterior: `codex exec --json --model gpt-reserve --sandbox read-only --cd <ROOT> 'Respond with exactly LUNA_FINAL_PROBE.'` retornou `LUNA_FINAL_PROBE`, exit 0 e `turn.completed` na thread `01a0a5be-1098-7a72-996d-34fae8176016`; confirma funcionamento do Codex Luna Reserve pelo CLI não interativo, sem alterar a pendência de C1/T029.

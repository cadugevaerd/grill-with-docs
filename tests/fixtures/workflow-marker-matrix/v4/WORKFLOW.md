<!-- grill-with-docs-workflow:v4 -->
# Spec Kit Workflow (project-wide)

Generic, project-independent contract. Requires Spec Kit >=0.11.2 and verified extensions: `git`, `bugfix`, `verify-review-ship`.

## Invocação canônica: invoke, do not emulate

Cada token da sequência de 11 etapas é uma **referência de invocação**, nunca uma descrição livre de tarefa. Ler o nome de uma etapa significa **invocar a skill registrada** para aquela etapa pela superfície nativa de invocação do runtime. Produzir artefato semelhante não equivale a executar a skill.

O mapa `step_id → skill` vive no registry versionado `workflow-step-skills.v4.json` (schema `workflow-step-skills/v1`), distribuído com o bundle em `assets/workflow-step-skills.v4.json`. O registry é referenciado **por hash**: toda resolução fixa `registry_sha256` (SHA-256 dos bytes exatos do registry) e todo dispatch carrega esse valor. Bytes de registry cujo `registry_sha256` divergir do valor fixado na resolução são recusados antes de qualquer capability mutável. Nesta materialização, o `registry_sha256` corrente do bundle está fixado em `sha256:e3f69871406205b77725b41bf0de0b24d9dbd661c004d502f0ddb49f22209ec1`.

Antes de despachar uma etapa, o core resolve a skill e persiste `skill-resolution` com `skill_id`, runtime, adapter, entrypoint nativo efetivo, versão mínima, source ref, manifest/content SHA-256 e `registry_sha256`. A cadeia obrigatória é:

`skill-resolution → dispatch-intent (execution_mode=CANONICAL_SKILL) → skill-invocation STARTED → skill-invocation terminal → step-output`.

`step-output` só é aceito quando referencia o receipt terminal `COMPLETED` da invocação canônica corrente daquele `step_id` e a cadeia inteira é consistente com o projeto, work item, run, geração e predecessor atuais. O orquestrador pode iniciar um subagente cooperativo para montar e revisar esse receipt antes do checkpoint. JSON e hashes constituem evidência estrutural auditável; não são prova criptográfica nem protegem contra um executor malicioso.

### Proibição explícita de semantic emulation

Semantic emulation é proibida. Reproduzir a intenção da etapa com shell, tools genéricas, raciocínio próprio, prompt textual ou subagente improvisado não é invocação: prompt dizendo "faça verify" não é invocação. Exemplos proibidos: rodar testes diretamente quando a etapa é `verify`, revisar código diretamente quando a etapa é `review`, fazer merge/push/release diretamente quando a etapa é `ship`.

- Arquivo, log, commit, teste verde ou side effect produzido sem a cadeia acima é `UNATTESTED_STEP_OUTPUT` e não avança a sequência.
- Começar a executar a semântica diretamente bloqueia capabilities mutáveis, cerca a tentativa e registra `POLICY_VIOLATION/DIRECT_STEP_EXECUTION`.
- Skill ausente, ambígua, abaixo da versão mínima, com hash divergente, catálogo não confiável ou apenas inferida da documentação é `BLOCKED_CAPABILITY`. Não existe fallback `DIRECT|EMULATED|BEST_EFFORT` para etapa `required`.
- Alias, extensão alternativa ou skill "equivalente" só substitui a entrada canônica por nova revisão do registry, com equivalence policy versionada e aprovação explícita; o agente/runtime não escolhe equivalência durante a execução.
- Em `ship`, a autorização humana permite **invocar** a skill registrada; nunca a substitui nem autoriza side effect direto.

Hooks são read-only e, quando ligados a este contrato, devem injetar path e hash do `WORKFLOW.md`, o `registry_sha256` e a instrução curta "read, resolve and invoke; do not emulate"; o enforcement permanece no core, nunca no hook. O hook publicado (`ensure_workflow.py --hook`) já injeta path e hash do `WORKFLOW.md`, o `registry_sha256` do bundle e essa instrução, antes da projeção de status. Pendência conhecida: o valor publicado pelo hook ainda está no formato hex puro do dígest, não no formato `sha256:<hex>` prefixado que este documento pina acima — alinhar os dois formatos é responsabilidade de quem mantém `ensure_workflow.py` (ver LD-001/LD-003).

## Execução paralela: partition e implement-parallel

`partition` lê o `tasks.md` que `tasks` produziu e emite um Execution DAG versionado (`grill-gauntlet-execution-dag/v1`): fases permanecem barreiras sequenciais e o paralelismo vem de disjunção de arquivo dentro da fase. O agrupamento é determinístico e vive em código, não em julgamento de modelo — a mesma `tasks.md` produz o mesmo DAG. Largura declarada é teto, nunca promessa: uma fase sem grupos disjuntos suficientes emite menos nós e declara `PARTITION-DEGRADED` com o motivo, em vez de fingir paralelismo.

Tarefa sem caminho de arquivo extraível vai para um nó `parallel:false`, despachado sozinho. Tarefa que escreve evidência de coordenador (`.grill/`, `.specify/reports/`) nunca é despachada a worker algum: é devolvida nominalmente ao leader, que é a única Evidence Boundary.

`implement-parallel` é o leader. Ele declara a wave, declara cada worker e despacha um subagente por worker em worktree isolado, com escopo de arquivos fechado. O **modelo de cada worker é derivado**, não escolhido: vem do tier do nó via o binding versionado `assets/workflow-tier-models.json`, e um modelo de fronteira para a classe `worker` é recusado antes de qualquer worktree existir. Nenhum worker edita `tasks.md`, nenhum worker faz checkpoint de etapa e o diff de cada branch é verificado contra o grant antes do merge. O receipt da etapa é do leader.

## Loop externo: ROADMAP e handoff
ROADMAP.md is the fixed, rarely renumbered phase order. Only one phase is `ready`; the previous phase must be `complete`. Check blockers before starting, record the decision, and create a single handoff for the next phase. `specify` receives only that handoff, never the whole roadmap. `before_specify` and branch/worktree checks happen before specify. The spec number is sequential and is not the phase number.

## Delivery First / hotfix-fast
Feature e fix permanecem plan-only. Incidentes podem usar `grill_workspace.py hotfix` com escopo fechado, reprodução/evidência, teste de correção, rollback e verificação constitucional. Essa trilha não depende do ROADMAP/BL/DQ nem do workflow global para decidir HOTFIX-GO; reconciliação e auditoria documental completa são pós-ship.

## Limite desta skill: PLAN_ONLY_STOP

Este documento descreve um ciclo que será executado externamente. Durante `grill-with-docs`, `PLAN_ONLY_STOP` ocorre **antes de `specify`**: a skill prepara e audita entradas, entrega o path do handoff selecionado e para. Ela não chama `specify`/`plan`, não edita código e não cria branch, commit ou merge.

## Ciclo externo de execução (11 etapas)
`specify → plan → checklist → tasks → analyze → partition → implement-parallel → converge → verify → review → ship`.
Analyze is after tasks; converge is before verify; ship is direct, without a PR. Cada nome da tabela é o `step_id` do registry e significa "invocar a skill registrada"; a coluna Deliverable descreve o resultado da skill invocada, não uma receita para reproduzi-lo à mão.

| Step | Deliverable | Return when blocked |
|---|---|---|
| specify | numbered WHAT/WHY spec | clarify handoff |
| plan | design and gates | specify |
| checklist | acceptance checklist | plan |
| tasks | ordered bounded tasks | plan |
| analyze | risks/dependencies | tasks |
| partition | file-disjoint subphases and the Execution DAG | tasks |
| implement-parallel | scoped evidence from every dispatched worker | partition |
| converge | integrated result | tasks/analyze |
| verify | test/gate evidence | converge |
| review | approved review | converge/verify |
| ship | release and state update | review/verify |

O ciclo acima pertence ao executor posterior, nunca à sessão `grill-with-docs` que já terminou em `PLAN_ONLY_STOP`.

## ship: phases A–E (A-E)
A. Record approved learnings only. B. Revalidate artifacts, tests, constitution, and release assumptions. C. Merge the worktree with `git merge --no-ff`, run all gates, and stop on failure. D. Push directly (no PR), reread the pushed ref and verify its hash. E. Clean temporary worktrees/branches and report cleanup warnings; never hide cleanup warnings. (cleanup warnings are always surfaced.) Todas as cinco fases acontecem dentro da skill `ship` invocada; nenhuma delas é executada à mão.

## Fim do ciclo
Mark the current ROADMAP phase `complete` and the next phase `ready`; record blockers and handoff. Update DECISION-BACKLOG.md, create/update the applicable ADR, and update the glossary. Preserve traceability.

## Project-wide artifacts and governance
Exact artifacts: `.specify/memory/constitution.md`, `WORKFLOW.md`, `CONTEXT.md`, `docs/adr/`, `ROADMAP.md`, `DECISION-BACKLOG.md`, `PLAN-CONTEXT.md`, `handoffs/FASE-NNN-SPECIFY-HANDOFF.md`. Constitution is governance and cannot be invented or silently replaced. Keep `docs/adr/` canonical; legacy `adrs/` requires migration. Auxiliary artifacts are `DECISION-FRONTIER.md`, `ROUND-LOG.jsonl`, `state.json`, and `AUDIT.md`. Constituição, `WORKFLOW.md` e o registry nunca são modificados por agentes de execução, ataque, reparo ou auditoria.

## Release and safety notes
Use the git/bugfix/verify-review-ship extensions with the stated minimum version. For release zip artifacts, fingerprint inputs and verify the executable bit (`chmod +x`) plus an actual execution test. Fingerprint workflow, registry and constitution in state. Do not overwrite an incompatible human WORKFLOW. Migração v2 → v3 → v4 é preview-first e no-clobber: exibe o diff e só aplica por comando mutável autorizado. `WORKFLOW.md` v2 ou v3 já materializado permanece byte-intacto em leitura e status. Workflow humano equivalente só é aceito para execução v4 se declarar esta mesma fronteira; caso contrário fica `WORKFLOW_INCOMPATIBLE` para v4, sem afetar sua validade como v2 ou v3. This file is generic and contains no project data.

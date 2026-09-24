# Revisão independente do plano — rodada 2

**Veredito: APPROVED**

P1 está reparado no design e na identidade concreta do bundle de continuidade. Não encontrei finding obrigatório remanescente nos cinco artefatos revisados. A aprovação é do plano: não afirma implementação, admissão end-to-end, conclusão de macroetapa ou autorização de ship.

## P1 — Resolvido: bundle preservado contendo f1475f4

Locais: `specs/033-latest-models/plan.md:119`, `research.md:96`, `data-model.md:84`, `quickstart.md:11` e `contracts/model-selection.md:121`.

O plano deixou de depender do cache instalado 6.0.30 e identifica uma cópia real, externa aos caches upstream, congelada antes das mudanças candidatas. Reproduzi independentemente as seguintes verificações, sem modificar o bundle:

- Root: `/home/carlosaraujo/orca/workspaces/grill-with-docs/continuity-5544829`.
- HEAD destacado e árvore limpa, inclusive arquivos untracked: `5544829185c2e5d1d75e52736364aa00bede9323`.
- `f1475f4f9523fcd7063e32b547aa6fd8bc364528` é ancestral desse HEAD; `git merge-base --is-ancestor` retornou 0.
- `HEAD:plugin/skills/grill-with-docs` é `d5cc959f9c02a98ddc3a5adfd958d729b62807ce`. O campo `plugin_tree` foi corretamente delimitado a esse subtree, sem confundi-lo com `HEAD:plugin`.
- Os cinco arquivos de `continuity-bundle-proof.json` coincidem em tamanho e SHA-256; o manifest tem SHA-256 `89f6ede5fd321c1fe901271386458ba6fda452661a3758db4d2cedea0b4817fc`.

CLI confirmado: `/home/carlosaraujo/orca/workspaces/grill-with-docs/continuity-5544829/plugin/skills/grill-with-docs/scripts/grill_workspace.py`, SHA-256 `00c1220ff3fd167149134792a16b9e35d0b2349b431f6e75e818bf3c54822389`. O módulo de orquestração tem SHA-256 `aad0a06e5d8d51c6f75e1126a09410e6fc67b65f72f48083e8731e6eeaca9b1b`.

Importei somente o módulo preservado, com `python3 -B`, e executei `validate_block` sobre o bloco real do Store lido diretamente, sem instanciar writer. Resultado: PASS na revisão 3310, SHA-256 de bytes `244cd3b12ac3360617fc8244cadbe498359d98b73ce2aa525cd5dca2d89f136d`; os bytes permaneceram idênticos antes/depois. O contexto corrente permanece `ctx-3fec10eddb66b60e2ffa1290`, runtime Codex, com primeiro campaign e predecessor `ctx-abe82e929ba403bc2dc10449`. A correção aceita esse caso sem inventar bridge.

O plano também fecha os aspectos operacionais antes ausentes: coordenador responsável pela preservação e revalidação; CLI absoluto recebendo o root ativo; candidata usada para implementação/validação isolada; rechecagem antes de cada etapa e retomada; lifecycle real independente para novos outputs; retenção do bundle até ship/cleanup. O cenário combinado exigido em `quickstart.md:109` cobre o predecessor sem campanha, a futura recusa v1 na candidata e o lifecycle Codex pelo bundle preservado, com negativo para predecessor que já tinha campanha. Sua execução futura não foi falsamente apresentada como prova atual.

## Caminho restante até ship e fronteira Claude

Não identifiquei exigência de trocar a condução desta campanha para Claude para satisfazer uma das onze etapas. Essa conclusão vem dos artefatos e do resolvedor, não da simples existência de uma tabela de modelos:

1. Usei `resolve_shipped_workflow_skills` do bundle preservado, com registry, catálogo Codex e trust asset v4 preservados. As onze resoluções passaram, inclusive `speckit-verify-review-ship-verify`, `speckit-verify-review-ship-review` e `speckit-verify-review-ship-ship`. Os entrypoints Codex desses três gates estão explícitos em `plugin/skills/grill-with-docs/assets/workflow-step-skills.v4.json:301`, `:335` e `:369`; ship mantém autorização humana obrigatória em `:356`.
2. Comparei registry/catalog/trust hashes com a activation deste work item em `.grill/gauntlet.yaml`; todos coincidem. Também conferi o hash do WORKFLOW, documento do work item, runtime/campaign no estado e `catalog.resolution_sha256`. Os assets v4 comparados e a policy v1 do root ativo são byte-idênticos aos do bundle preservado. Isso verifica as resoluções e seus pins; não declara que as futuras invocações já ocorreram.
3. A matriz de atividades v1 exige revisão em checklist/analyze/converge/review, autoria e revisão em tasks, workers na implementação e pares para julgamentos novos em ship (`agent-orchestration.v1.json:26`–`:34`). Os papéis Codex existem em `:13`–`:14`; não há nessa matriz uma obrigação de revisor Claude. `prepare_activity` usa o runtime do contexto (`agent_orchestration.py:842`), e o contexto desta campanha é Codex. O plano mantém as sessões independentes, bootstrap, observação efetiva e fechamento para esses papéis futuros.
4. A fronteira Claude está correta: v1 ainda exige `fable` (`agent-orchestration.v1.json:18`–`:19`), enquanto ADR-0002:23 proíbe seu uso. `plan.md:128` e `quickstart.md:67` não alegam que Opus da candidata altera o selo antigo. Proíbem novos especialistas Claude por esse bundle e exigem rota separadamente justificada ou hold se Claude vier a ser necessário. Como os gates remanescentes resolvem em Codex, essa ressalva não deixa um requisito obrigatório atual sem rota.

A validação do comportamento novo Claude/Opus continua prevista na candidata isolada e nos contratos offline; ela não exige despachar `fable` nem resealar a campanha v1. Eventual exigência adicional de um lifecycle live Claude no mesmo item precisaria daquela rota explícita antes do payload; este parecer não concede tal autorização nem transforma a prova alias/high existente em prova xhigh.

## Escopo das provas

`continuity-bundle-proof.json` registra o preview do coordenador e chamadas puras de preparação; `plan.md:131`, `research.md:98` e `quickstart.md:56`–`:63` limitam corretamente essas afirmações. Não usei a identidade do coordenador, não executei adopt/apply nem prepare como probe, e não interpretei uma eventual recusa `CONTEXT-FENCED` de especialista como falha do bundle. As chamadas puras informadas pelo autor foram examinadas como evidência anterior; nesta rodada minha reprodução foi integridade, resolução dos entrypoints e validação do Store.

A existência da rota não garante antecipadamente disponibilidade futura de modelo, sucesso dos testes candidatos, aprovação humana, pipeline ou close. Falhas posteriores devem bloquear no próprio gate; `plan.md:129` e a recuperação do quickstart preservam essa obrigação, sem edição de cache, bundle, Store histórico, policy, receipts ou bridges para contornar recusa.

## Integridade, independência e checks

Recalculei os 39 arquivos de `plan-reviewer-r2-input.json`: 39 SHA-256 e tamanhos correspondentes, zero divergências. Revalidei os hashes ao final. Li os cinco artefatos, a primeira revisão, o resultado do autor r2 e o manifest; consultei os requisitos, fontes normativas, activation, Store, resolvedor e gates relevantes à continuidade.

Autor inicial observado: dispatch `ctx_f5c360f6a064`, incarnation `a0afc1d8-897d-4304-bc52-62d4bc7c396b`, `gpt-6-astra/xhigh`, encerrado. Autor r2: `ctx_63123f401f9b`, incarnation `5f77c8bf-4366-40f7-aea4-e7ab7aeadf31`, mesmo par, encerrado. Revisor desta rodada: `ctx_7f72bed4811d`, task `task_c6df9209a2dd`, incarnation `a2081757-8690-435d-92df-82b77111f28f`, `gpt-6-astra/high`; sessão distinta de ambas.

Checks próprios:

- Bootstrap literal desta sessão: `work_ready=true`, `loading=loaded`, `trust=ready`, enablement enabled. `behavior=not_tested` e `functional_verified=false`; sem claim comportamental.
- Integridade do bundle, ancestralidade, cinco hashes/tamanhos, Store real e pins de activation/campaign: PASS.
- Resolução pura dos onze entrypoints Codex contra assets preservados: PASS.
- `python3 -B tests/validate_agent_orchestration_contract.py AgentOrchestrationContract.test_first_campaign_is_born_in_a_pre_campaign_successor`: 1 teste, PASS, exit 0. Exercita o positivo e o negativo da bridge em fixture temporária.
- `git diff --check`: exit 0. A suíte completa não foi repetida nesta sessão, conforme o payload; o PASS completo registrado pelo autor r2 é evidência atribuída ao autor, não execução deste revisor.

Nenhum arquivo do repositório ou bundle foi editado por esta revisão; nenhum worker foi lançado, macrostep executado/atestado, commit ou publicação realizado. O único artefato produzido é este relatório externo para cópia literal pelo coordenador. Restam a aceitação/cleanup pelo coordenador e as etapas canônicas futuras, com os gates e revalidações do plano.

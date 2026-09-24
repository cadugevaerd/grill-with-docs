# Relatório — tasks-author-001 (AUTOR, etapa tasks, work item fix-fence-autorizado-atividade-f831232ae30e4087adbaa988bc0f7b24)

- payload lido por inteiro: sha256 `36a80abd5aa0879db3da34421d6e4b736df2bc34486403edc294dbcd932b8799` (confere)
- input manifest `tasks-author-001.input.json`: 22/22 sha256 e tamanhos conferidos, zero divergência
- worktree `/home/carlosaraujo/orca/workspaces/grill-with-docs/fix-leader`, HEAD `a5ee1da`; `git diff --stat 39380f7 HEAD -- plugin tests` vazio, então toda citação file:line herdada de research/plan-reviewer-003 vale neste HEAD; citações-chave reconferidas por leitura direta (ao:48-49, 760-785, 1535-1541; ws:1565, 1612, 1658, 3654, 3675, 3690, 3717, 4126-4145, 4148, 4159, 4181, 4247, 4309, 4340, 4450, 5152, 5340, 5952, 6052, 6074, 6078, 6097, 6147, 7131-7136, 7212; T:62-77, 255-270, 1240-1270, 2278-2310, 2340-2356, 2500-2520, 2615-2646; store contract 28-36, 285-292; fixture 89-119; session-protocol.md:85, 87; SKILL.md:94; validate_distribution.py:8, 41-43; oito pontos em 6.0.30 e `## 6.0.30` em CHANGELOG.md:3)
- único arquivo escrito no repositório: `specs/034-fence-autorizado-atividade/tasks.md` (novo). `git status --porcelain` mostra só ele além dos três artefatos da própria atividade sob `.grill/` (`input.json`, `payload.md` e `observation.json`, este gravado pelo core no dispatch, não por mim). Sem commit.

## sha256 do tasks.md

`c298d8219d9e650e3e5c43650ae7a42f72a674407b6fbf6021b65cc7116424c6` (139 linhas)

## Conferência do contrato task-files/v1

`grill_core.partition.parse_task_files` e `partition_task_files` executados em memória sobre o texto (sem escrever DAG): 8 tarefas, 6 despacháveis, 2 read-only (T007, T008), 0 deferred; `max_workers` 2; verdict `PARTITION-DEGRADED` — esperado pelo contrato, porque há tarefas read-only (partition.py:625). Nós: `p01-a` (T001: agent_orchestration.py + validate_orchestrator_store_contract.py), `p02-a` (T002, T003, T004: grill_workspace.py + validate_agent_orchestration_contract.py), `p02-b` (T005, T006: os nove arquivos de versão e documentação). Phase 3 sem nó. Nenhum token de descrição concede grant sob v1 (`TaskFilesTask` sem description grant); tokens com barra nas descrições são só os caminhos já declarados em `Files`, os caminhos read-only de T007/T008 e o literal de schema `human-authorization/v1` em T005.

## Total de tarefas e contagem

- Total: 8. Phase 1: 1 (T001). Phase 2: 5 (T002–T006). Phase 3: 2 (T007, T008; read-only).
- Por US: US1 → T002, T003, T004; US2 → T001, T002, T003, T004; US3 → T002, T003, T004; US4 → T004. T005, T006 (docs e bump) e T007, T008 (verificação) sem story.
- Nó B em três fatias code+teste (permitido pelo payload: "uma tarefa de teste pode ficar junto da tarefa de código do mesmo nó"), para que o mesmo worker prove cada fatia antes da seguinte; T002/T003/T004 conflitam nos mesmos dois arquivos e viram um nó. Nó C: T005 (prosa) e T006 (bump) compartilham os dois headings, então um nó; T006 por último porque `validate_distribution.py` só fecha com os nove arquivos. Raiz (`README.md`, `CHANGELOG.md`) é grant válido no v1 (template: "Raiz, arquivo novo e prefixo ./ valem"; `normalize_task_path` aceita), diferente da 032, que os deferia ao líder.

## task → Files (despacháveis)

- T001 → `plugin/skills/grill-with-docs/scripts/grill_core/agent_orchestration.py`, `tests/validate_orchestrator_store_contract.py`, `specs/034-fence-autorizado-atividade/implement/T001.tasks.json` (Result)
- T002 → `plugin/skills/grill-with-docs/scripts/grill_workspace.py`, `tests/validate_agent_orchestration_contract.py`, `specs/034-fence-autorizado-atividade/implement/T002.tasks.json` (Result)
- T003 → mesmos dois arquivos + `specs/034-fence-autorizado-atividade/implement/T003.tasks.json` (Result)
- T004 → mesmos dois arquivos + `specs/034-fence-autorizado-atividade/implement/T004.tasks.json` (Result)
- T005 → `plugin/skills/grill-with-docs/references/session-protocol.md`, `plugin/skills/grill-with-docs/SKILL.md`, `specs/034-fence-autorizado-atividade/implement/T005.tasks.json` (Result)
- T006 → `plugin/.claude-plugin/plugin.json`, `plugin/.codex-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.agents/plugins/marketplace.json`, `tests/validate_distribution.py`, `plugin/skills/grill-with-docs/SKILL.md`, `plugin/skills/grill-with-docs/references/session-protocol.md`, `README.md`, `CHANGELOG.md`, `specs/034-fence-autorizado-atividade/implement/T006.tasks.json` (Result)
- T007, T008 → `Files: []`, sem Result (read-only).

## Onde cada finding de insumo obrigatório entrou

- **plan-reviewer-003 Finding 1** (n5/n5b com `status=dispatched` seriam `*-ACTIVE`): T003 — n5 e n5b nascem com os shapes de T:2512-2516 (status ausente + `unverifiable`, não correlacionado, ilegível), com a frase explícita "NUNCA com `status` `dispatched`"; n5d opcional incluído (`dispatched` + `unverifiable` → `FENCE-SPECIALIST-ACTIVE`) como trava da distinção.
- **plan-reviewer-003 nit (a)** (`retained` vs chave pública `preserved_resources`): T004 p1 assere que o recurso cercado não aparece em `preserved_resources` do payload do takeover (4070, 4121, 4348).
- **plan-reviewer-003 nit (c)** (solicitante substituído entre saltos): T004 p3b assere `FENCE-ACTIVITY-STATE` para outro `--session-ref` na retomada e que o takeover por outra sessão continua admitido em prévia (`CLOSE_PENDING` não é `UNKNOWN`, 3668).
- **plan-reviewer-003 nits (b) e (d)** (faixa de linhas em plan:35; PLAN-CONTEXT atrasado): prosa fora do grant; não entram em tasks. Registro para o líder.
- **checklist-reviewer-001 Finding 1** (FR-014 só indireto; FR-015 sem SC): T006 (FR-014, `validate_distribution.py`) e T008 (FR-015 por `git diff --stat` contra constituição, WORKFLOW, assets, attestation.py, agent_runtime.py, workflow_versions.py; hash da Constituição igual ao selado). Tabela de rastreabilidade do tasks.md mapeia os quinze FR e os cinco SC.
- **checklist-reviewer-001 Finding 2** (SC-002 não exaustivo): a matriz negativa das tarefas é a de research R11 (n0, n1, n2, n2d, n3, n3c, n4, n5, n5b, n5c, n5d, n6, n7, n8, n8b, n9, n10, p3b), com `assert_refused_and_unwritten` em prévia E apply exigido em T002, T003 e T004; seção "Independent test criteria" diz explicitamente que SC-002 é amostra.
- **checklist-reviewer-001 Finding 3** (FR-013 × CAS pós-salto 1 próprio): T004 p5 variante pós-salto 1 assere Store igual ao estado pós-salto 1, não ao anterior à primeira invocação, e nomeia o caso como a única saída com código de recusa e efeito próprio já gravado.
- **checklist-reviewer-001 Finding 4** (sem caso para prepare-switch): T004 p6 — `gauntlet-prepare-switch` em prévia não recusa `CONTINUITY-ACTIVE-WORK` pela atividade cercada; fallback prescrito (`_continuity_quiescence` não a lista) mantido.
- **checklist-reviewer-001 Finding 5** (nove arquivos): T006 nomeia os nove com linha e explica por que são nove e não os oito de FR-014.
- **CHK036/CHK037/CHK038** sugeridos: cobertos por T002 (passos 1 e 2: ids lidos do Store; replay/retomada restritos ao mesmo solicitante; paridade prévia/apply declarada), T003 e T004 (p5, n10, p3b). O arquivo `checklists/release-gate.md` está fora do grant; não foi editado.

## DQs propostas

Nenhuma. Toda escolha de autoria deriva de decisão já selada (DQ-0006..DQ-0014), de research R1..R12 ou de correção prescrita pelos revisores. Três escolhas de forma que não são decisão material, registradas para o líder:

1. Fatias code+teste no nó B (T002 → T003 → T004) em vez de código numa fase e testes na seguinte: permitido pelo payload; mantém o nó B como o plano e plan-reviewer-003 §6 o descrevem e deixa o worker provar cada fatia.
2. `README.md` e `CHANGELOG.md` no grant do worker de C (raiz válida no v1), não deferidos ao líder como na 032.
3. Phase 3 só read-only, colocada por último de propósito: em `partition_task_files` (partition.py:606-611) `previous = phase_nodes` é atribuído mesmo quando a fase não tem nó, então uma fase read-only **no meio** faria os nós da fase seguinte nascerem com `depends_on: []` e perderem a barreira. Observação lateral sobre o core, fora deste grant; candidata a item de backlog, não a DQ desta entrega.

## Veredicto do autor

`tasks.md` escrito e conferido pelo parser v1 do core; 8 tarefas em 3 fases, 3 nós, matriz de testes completa (n0..n10 e p1..p6) com os insumos obrigatórios incorporados onde cada um toca; nenhuma DQ nova. Próximo passo é a revisão independente (tasks-reviewer) e, depois, `analyze` e `partition-emit`.

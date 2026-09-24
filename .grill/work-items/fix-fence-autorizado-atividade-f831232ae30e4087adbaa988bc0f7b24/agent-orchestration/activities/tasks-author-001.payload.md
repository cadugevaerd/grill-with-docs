# Payload técnico — tasks-author-001 (AUTOR, fable/xhigh)

Activity payload do core: activity_id=tasks-author-001, step=tasks, context_id=ctx-146fb68d0d6e, fence=1, runtime=claude.

Grant de escrita: somente `specs/034-fence-autorizado-atividade/tasks.md` (arquivo novo), relativo ao worktree `/home/carlosaraujo/orca/workspaces/grill-with-docs/fix-leader`. Não escreva em nenhum outro arquivo e não faça commit.

Work item: W = `.grill/work-items/fix-fence-autorizado-atividade-f831232ae30e4087adbaa988bc0f7b24`. Input manifest: `W/agent-orchestration/activities/tasks-author-001.input.json` (22 arquivos). Confira os sha256 antes de usar.

## Tarefa

O líder invocou `/speckit-tasks` para a feature `specs/034-fence-autorizado-atividade` (etapa `tasks`). Você é o autor técnico do `tasks.md`.

### Contrato obrigatório: `task-files/v1`

Siga `plugin/skills/grill-with-docs/assets/task-files.v1.template.md` e o suplemento `references/agent-orchestration.md`:

- a primeira linha do arquivo é o marcador `<!-- grill-task-files:v1 -->`;
- logo depois de cada tarefa vem `Files:` como array JSON de uma linha;
- toda tarefa despachável que escreve declara exatamente um `Result:` logo depois de `Files:`. O path é `specs/034-fence-autorizado-atividade/implement/<task_id>.tasks.json` e também aparece em `Files:`;
- tarefa read-only: `Files: []` e sem `Result:`;
- tarefa que escreve evidência reservada ao líder (`.grill/`, `.specify/reports/`) fica inteira `deferred_to_leader`, sem `Result:`;
- sem glob, sem diretório, sem symlink, sem traversal. Raiz, arquivo novo e prefixo `./` valem;
- cada tarefa fica na fase numérica declarada; conflito de `Files` é agrupado dentro da fase, e fases são barreiras.

`Files:` é a única autoridade de escrita do worker. Não conte com texto com barras na descrição para conceder escrita. Evite tokens com `/` na descrição que não sejam caminhos reais (lição da spec 028/029).

### Conteúdo

Fontes, em ordem: `spec.md` (FR-001..FR-015, US1..US4), `plan.md`, `research.md` (R1..R13), `data-model.md`, `contracts/activity-fence.md`, `quickstart.md` e o `DECISION-FRONTIER.md` (DQ-0001..DQ-0014). Use `specs/032-continuity-context/tasks.md` como referência de densidade e estilo (pt-BR, citações file:line), mas no contrato v1.

**Insumo obrigatório**: incorpore às tarefas os findings menores de:

- `W/agent-orchestration/activities/plan-reviewer-003.result.md` (Finding 1: shape de n5/n5b, e nits);
- `W/agent-orchestration/activities/checklist-reviewer-001.result.md` (FAILs menores, CHK036–038 sugeridos, matriz negativa de R11).

Cada correção entra como detalhe da tarefa que toca o ponto, citando o finding.

Partição sugerida pelo plano (arquivos disjuntos por fase), a ser conferida contra o código:

- Fase 1: aresta `RESULT_RECORDED → FAILED` em `plugin/skills/grill-with-docs/scripts/grill_core/agent_orchestration.py` + lock em `tests/validate_orchestrator_store_contract.py`.
- Fase 2: verbo `gauntlet-activity-fence` em `plugin/skills/grill-with-docs/scripts/grill_workspace.py` + `test_activity_fence` em `tests/validate_agent_orchestration_contract.py`; em paralelo, documentação e distribuição: `plugin/skills/grill-with-docs/references/session-protocol.md`, `plugin/skills/grill-with-docs/SKILL.md`, os quatro manifests, `tests/validate_distribution.py`, `README.md` e `CHANGELOG.md` (bump 6.0.30 → 6.0.31, nove arquivos).
- Fase final: verificação read-only (`python3 tests/run_validators.py`), sem escrita.

Os testes são obrigatórios (FR-013, SC-002, SC-005): determinísticos, offline, sem `orca` real, usando os seams existentes. Uma tarefa de teste pode ficar junto da tarefa de código do mesmo nó quando os arquivos forem os mesmos do nó.

Decisão material não coberta vira "DQ proposta" no relatório, sem decidir.

## Entrega

1. Escreva `specs/034-fence-autorizado-atividade/tasks.md`.
2. Grave no SEU scratchpad um relatório curto com:
   - o sha256 do `tasks.md`;
   - total de tarefas e contagem por fase/US;
   - a lista `task → Files` das tarefas despacháveis;
   - onde cada finding de insumo obrigatório entrou;
   - as DQs propostas.
3. Finalize com `worker_done --outcome succeeded --files-modified specs/034-fence-autorizado-atividade/tasks.md --report-path <relatório>`, usando só flags estruturadas e corpo de 3 frases.

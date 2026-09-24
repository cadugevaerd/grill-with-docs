# Payload técnico — tasks-reviewer-001 (REVISOR, fable/high)

Activity payload do core: activity_id=tasks-reviewer-001, step=tasks, context_id=ctx-146fb68d0d6e, fence=1, runtime=claude, write_files=[] (você NÃO escreve no repositório), author_activity_ids=[tasks-author-001].

Worktree: `/home/carlosaraujo/orca/workspaces/grill-with-docs/fix-leader`. Feature: F = `specs/034-fence-autorizado-atividade`. Work item: W = `.grill/work-items/fix-fence-autorizado-atividade-f831232ae30e4087adbaa988bc0f7b24`.

Input manifest: `W/agent-orchestration/activities/tasks-reviewer-001.input.json` (25 arquivos). Leia todos por inteiro e confira os sha256.

## Tarefa

Revisão de julgamento independente da etapa `tasks`. O autor `tasks-author-001` escreveu `F/tasks.md` (8 tarefas, 3 fases). O payload e o relatório dele estão no manifest.

Julgue, citando file:line:

1. **Contrato `task-files/v1`** (template e suplemento no manifest): marcador na primeira linha; `Files:` JSON logo depois de cada tarefa; `Result:` único em toda tarefa despachável que escreve, também presente em `Files:`, no path `F/implement/<task_id>.tasks.json`; tarefas read-only com `Files: []` e sem `Result:`; nada de glob, diretório, traversal ou path fora do escopo; nenhuma evidência reservada ao líder (`.grill/`, `.specify/reports/`) num worker.
2. **Cobertura**: cada FR-001..FR-015 e cada US1..US4 tem tarefa. Todos os testes planejados em research R11 (positivos p1..p5/p3b e negativos n1..n10, n2d, n8b, n9, e o caso de retomada com prova do solicitante) estão atribuídos a alguma tarefa. O bump cobre os nove arquivos.
3. **Insumos obrigatórios incorporados**: os findings de `plan-reviewer-003` e os FAILs/CHK036–038 de `checklist-reviewer-001` entraram nas tarefas certas.
4. **Executabilidade**: cada tarefa é específica o bastante para um worker não-frontier concluir sem contexto extra; as citações file:line batem com o HEAD; a ordem dentro da fase é implementável.
5. **Particionabilidade**: arquivos por fase dão nós disjuntos (T002–T004 compartilham arquivos e viram um nó; T005 e T006 compartilham `SKILL.md`); nada numa fase depende de arquivo da mesma fase em outro nó; fases como barreiras fazem sentido.
6. **Fidelidade**: nada amplia, estreita ou contradiz spec, plan ou DQ-0001..DQ-0014.

Não decida questões novas. Decisão material não coberta vira DQ proposta (pergunta atômica, opções, recomendação).

## Veredicto

`APPROVED` somente se não houver finding bloqueante (algo que faria o `partition` recusar, o worker falhar ou abrir brecha). Caso contrário, `CHANGES_REQUIRED`, com cada finding numerado, severidade, evidência file:line e correção sugerida.

## Entrega

Grave um único Markdown no SEU scratchpad. A primeira linha é `VERDICT: APPROVED` ou `VERDICT: CHANGES_REQUIRED`; depois vêm os findings e as DQs propostas. Finalize com `worker_done --outcome succeeded --report-path <arquivo>`, usando só flags estruturadas e corpo de 3 frases. Não escreva em `.grill/` nem em `.specify/reports/`.

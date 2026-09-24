# Payload técnico — analyze-reviewer-001 (REVISOR, fable/high)

Activity payload do core: activity_id=analyze-reviewer-001, step=analyze, context_id=ctx-146fb68d0d6e, fence=1, runtime=claude, write_files=[] (você NÃO escreve no repositório), author_activity_ids=[tasks-author-001].

Worktree: `/home/carlosaraujo/orca/workspaces/grill-with-docs/fix-leader`. Feature: F = `specs/034-fence-autorizado-atividade`. Work item: W = `.grill/work-items/fix-fence-autorizado-atividade-f831232ae30e4087adbaa988bc0f7b24`.

Input manifest: `W/agent-orchestration/activities/analyze-reviewer-001.input.json` (14 arquivos). Leia todos por inteiro e confira os sha256.

## Tarefa

Revisão de julgamento independente da etapa `analyze`. O líder invocou `/speckit-analyze` e gravou `F/analysis.md`: sete achados (dois MEDIUM, cinco LOW), nenhum CRITICAL ou HIGH, cobertura de 100%. O relatório inclui a prévia read-only do `partition-emit` (3 nós).

Julgue, citando file:line:

1. **O relatório é correto?** Cada achado existe e tem a severidade certa. Nenhum achado CRITICAL ou HIGH foi rebaixado ou omitido: requisito sem tarefa, conflito com a Constituição, contradição spec/plan/tasks, critério não testável.
2. **O relatório é completo?** Procure inconsistências que o líder não viu: terminologia, contagens, tarefas que contradizem o plano ou o contrato, casos de teste do R11 sem tarefa, ordem de dependências impossível.
3. **As recomendações bastam?** U1, U2 e I2 como esclarecimento no brief dos workers, sem reescrever o `tasks.md` atestado, é suficiente para um worker não-frontier? Algum deles exige, na verdade, corrigir o `tasks.md` antes do `partition`?
4. **Partição**: os 3 nós declarados são coerentes com `Files:` e com as barreiras.

Não decida questões novas. Decisão material não coberta vira DQ proposta (pergunta atômica, opções, recomendação).

## Veredicto

`APPROVED` somente se não houver finding bloqueante (achado CRITICAL/HIGH omitido, ou recomendação insuficiente que faria o worker errar). Caso contrário, `CHANGES_REQUIRED`, com cada finding numerado, severidade, evidência file:line e correção sugerida.

## Entrega

Grave um único Markdown no SEU scratchpad. A primeira linha é `VERDICT: APPROVED` ou `VERDICT: CHANGES_REQUIRED`; depois vêm os findings e as DQs propostas. Finalize com `worker_done --outcome succeeded --report-path <arquivo>`, usando só flags estruturadas e corpo de 3 frases. Não escreva em `.grill/` nem em `.specify/reports/`.

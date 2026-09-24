# Payload técnico — plan-reviewer-002 (REVISOR, fable/high)

Activity payload do core: activity_id=plan-reviewer-002, step=plan, context_id=ctx-146fb68d0d6e, fence=1, runtime=claude, write_files=[] (você NÃO escreve no repositório), author_activity_ids=[plan-author-001, plan-author-002].

Worktree: `/home/carlosaraujo/orca/workspaces/grill-with-docs/fix-leader`. Work item: W = `.grill/work-items/fix-fence-autorizado-atividade-f831232ae30e4087adbaa988bc0f7b24`. Feature: F = `specs/034-fence-autorizado-atividade`.

Input manifest: `W/agent-orchestration/activities/plan-reviewer-002.input.json` (27 arquivos). Leia todos por inteiro e confira os sha256.

## Tarefa

Revisão de julgamento independente da etapa `plan`. O autor `plan-author-001` (fable/xhigh) escreveu `F/plan.md`, `F/research.md`, `F/data-model.md`, `F/quickstart.md` e `F/contracts/activity-fence.md`. O payload e o relatório dele estão no manifest. Depois disso a DQ-P1 dele foi decidida (DQ-0013, opção A: `content_sha256` da autorização validado só na forma; endurecimento em SGD-40).

Esta é a segunda revisão do plano. A primeira (`plan-reviewer-001`, APPROVED com seis findings menores, resultado no manifest) levou a uma rodada de correção por `plan-author-002` (payload e relatório no manifest), que aplicou os Findings 1–6 e a DQ-0014 (opção A: cleanup não reconhece o fence nesta versão; SGD-41). Confira cada correção, que nada fora delas mudou (compare com os commits `4cad807` e o HEAD) e que nenhuma correção abriu lacuna. Faça a revisão completa, não só o delta.

Julgue, citando file:line:

1. **Fidelidade**: o plano não amplia, estreita nem contradiz `F/spec.md` nem as DQ-0001..DQ-0013 do `W/DECISION-FRONTIER.md`.
2. **Findings obrigatórios**: interview-reviewer-001 (NOVO) Findings 1, 4 e 6, e specify-reviewer-002 F2, estão resolvidos corretamente. F1, F2 e F4 da revisão do work item de origem (aplicados no PLAN-CONTEXT) continuam corretos.
3. **Correção técnica contra o código do HEAD**: cada citação file:line, arestas e estados reais, interação com `_continuity_quiescence`, `gauntlet-context-takeover`, `gauntlet-prepare-switch`, cleanup, `accept_activity`, `store.transact` e as recusas. Procure premissa falsa, brecha fail-open, corrida e caminho em que a mesma operação produz dois efeitos.
4. **Decisão um salto × dois saltos** (`research.md` R7): correta pelas arestas reais, coerente com a spec (FR-008), testável e sem estado intermediário que viole invariante.
5. **Testes**: os negativos exigidos (sem autorização; autorização de outro alvo; líder vivo que não é o chamador; especialista vivo; veredicto indeterminado do especialista, do líder e da sessão do sucessor; hash stale; replay; aceite tardio) e os positivos das duas formas estão planejados, determinísticos, sem rede e usando os seams existentes.
6. **Particionabilidade**: os arquivos por parte do trabalho são nomeados e disjuntos o suficiente para `tasks` declarar `Files:` por fase.
7. **Constituição e distribuição**: Constitution Check honesto; bump 6.0.31 nos oito pontos do `CLAUDE.md` mais o `CHANGELOG.md` exigido por `tests/validate_distribution.py`.

Não decida questões novas. Decisão material não coberta vira DQ proposta (pergunta atômica, opções, recomendação).

## Veredicto

`APPROVED` somente se não houver finding bloqueante. Caso contrário, `CHANGES_REQUIRED`, com cada finding numerado, severidade (bloqueante ou menor), evidência file:line e correção sugerida.

## Entrega

Grave um único arquivo Markdown no SEU scratchpad. A primeira linha é `VERDICT: APPROVED` ou `VERDICT: CHANGES_REQUIRED`; depois vêm os findings e as DQs propostas. Finalize com `worker_done --outcome succeeded --report-path <arquivo>`, usando só flags estruturadas (sem `--payload`) e corpo de 3 frases. Não escreva em `.grill/` nem em `.specify/reports/`.

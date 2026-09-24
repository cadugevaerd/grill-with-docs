# Payload técnico — specify-reviewer-002 (REVISOR, fable/high)

Activity payload do core: activity_id=specify-reviewer-002, step=specify, context_id=ctx-146fb68d0d6e, fence=1, runtime=claude, write_files=[] (você NÃO escreve no repositório), author_activity_ids=[interview-author-001].

Worktree: `/home/carlosaraujo/orca/workspaces/grill-with-docs/fix-leader`. Work item: `.grill/work-items/fix-fence-autorizado-atividade-f831232ae30e4087adbaa988bc0f7b24` (W).

Input manifest: `W/agent-orchestration/activities/specify-reviewer-002.input.json` (11 arquivos). Leia todos por inteiro e confira os sha256.

## Tarefa

Revisão de julgamento independente da etapa `specify`. O líder invocou `/speckit-specify` a partir do handoff `W/handoffs/FASE-001-SPECIFY-HANDOFF.md` e escreveu `specs/034-fence-autorizado-atividade/spec.md`, com o checklist `checklists/requirements.md`. O handoff foi escrito pelo autor `interview-author-001`.

Esta é a segunda revisão. A primeira (`specify-reviewer-001`, CHANGES_REQUIRED, resultado no manifest) apontou F1 bloqueante e F2–F6 menores. O líder removeu o cenário de aplicação interrompida (F1), trocou `ESSENTIAL` (F2), a menção a Python (F3), reescreveu o SC-001 por forma (F4) e trocou "conflito" por "recusa" (F5). Confira se cada correção está aplicada, se nada mais mudou e se as correções não abriram lacuna. Faça a revisão completa, não só o delta.

Julgue, citando file:line:

1. **Fidelidade ao handoff**: todo cenário, ator, critério de aceite e restrição do handoff aparece na spec. Nada é ampliado, estreitado ou contradito. Confira os quatro negativos da DQ-0006, o inconclusivo, hash stale/replay, aceite tardio, a variante de sessão retida (DQ-0007), a autoridade derivada do líder (DQ-0008: líder vivo → só ele; líder terminal → sucessor com prova da própria sessão), o estado final não aceito (DQ-0009), attempt 2 como atividade nova (DQ-0010), e a DQ-0012 fora do escopo desta fase.
2. **WHAT/WHY × HOW**: a spec não pode conter stack, classes, API interna nem implementação. O vocabulário observado do domínio (dispatch, liveness, hash) é aceitável se não prescrever implementação.
3. **Testabilidade**: cada FR e SC é verificável e sem ambiguidade. Os cenários de aceite são independentes.
4. **Escopo**: SGD-37/38/39, prevenção por checkpoint automático e a FASE-002 estão fora.
5. **Checklist**: cada item marcado `[x]` é verdadeiro.

Não decida questões novas. Decisão material não coberta vira DQ proposta (pergunta atômica, opções, recomendação).

## Veredicto

`APPROVED` somente se não houver finding bloqueante. Caso contrário, `CHANGES_REQUIRED`, com cada finding numerado, severidade (bloqueante ou menor), evidência file:line e correção sugerida.

## Entrega

Grave um único arquivo Markdown no SEU scratchpad. A primeira linha é `VERDICT: APPROVED` ou `VERDICT: CHANGES_REQUIRED`; depois vêm os findings e as DQs propostas. Finalize com `worker_done --outcome succeeded --report-path <arquivo>`, usando só flags estruturadas (sem `--payload`) e corpo de 3 frases. Não escreva em `.grill/` nem em `.specify/reports/`.

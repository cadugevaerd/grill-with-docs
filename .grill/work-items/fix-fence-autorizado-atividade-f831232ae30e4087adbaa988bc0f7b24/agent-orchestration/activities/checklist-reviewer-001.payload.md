# Payload técnico — checklist-reviewer-001 (REVISOR, fable/high)

Activity payload do core: activity_id=checklist-reviewer-001, step=checklist, context_id=ctx-146fb68d0d6e, fence=1, runtime=claude, write_files=[] (você NÃO escreve no repositório), author_activity_ids=[plan-author-001, plan-author-002, plan-author-003].

Worktree: `/home/carlosaraujo/orca/workspaces/grill-with-docs/fix-leader`. Feature: F = `specs/034-fence-autorizado-atividade`. Work item: W = `.grill/work-items/fix-fence-autorizado-atividade-f831232ae30e4087adbaa988bc0f7b24`.

Input manifest: `W/agent-orchestration/activities/checklist-reviewer-001.input.json` (12 arquivos). Leia todos por inteiro e confira os sha256.

## Tarefa

Revisão de julgamento independente da etapa `checklist`. O líder invocou `/speckit-checklist` e gerou `F/checklists/release-gate.md`, com 35 itens (CHK001–CHK035). Cada item é um teste da qualidade dos requisitos, não da implementação.

1. **Avalie cada CHK** contra os artefatos (`spec.md`, `plan.md`, `research.md`, `data-model.md`, `quickstart.md`, `contracts/activity-fence.md`, `DECISION-FRONTIER.md`). Para cada um, dê `PASS` ou `FAIL` com evidência file:line. Todo `FAIL` precisa dizer o que falta ou o que conflita e onde corrigir.
2. **Avalie o checklist em si**: cobre os riscos do domínio (fail-closed, autoridade, idempotência, não-aceite, quiescência, rastreabilidade, distribuição, suíte offline)? Algum item testa implementação em vez de requisito? Falta algum item de alto risco?
3. Os findings menores de `plan-reviewer-003` (no manifest) vão como insumo obrigatório para `tasks`. Não os repita como FAIL, a menos que também reprovem um CHK.

Não decida questões novas. Decisão material não coberta vira DQ proposta (pergunta atômica, opções, recomendação).

## Veredicto

`APPROVED` quando nenhum CHK tiver FAIL bloqueante (lacuna que faria o ciclo executor implementar algo errado ou abrir brecha). Caso contrário, `CHANGES_REQUIRED`. FAILs menores entram como findings menores.

## Entrega

Grave um único Markdown no SEU scratchpad. A primeira linha é `VERDICT: APPROVED` ou `VERDICT: CHANGES_REQUIRED`. Depois vêm:

- uma tabela `CHK | PASS/FAIL | evidência`;
- os findings;
- as DQs propostas.

Finalize com `worker_done --outcome succeeded --report-path <arquivo>`, usando só flags estruturadas e corpo de 3 frases. Não escreva em `.grill/` nem em `.specify/reports/`.

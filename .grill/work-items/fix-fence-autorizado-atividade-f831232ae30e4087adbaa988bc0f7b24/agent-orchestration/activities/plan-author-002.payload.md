# Payload técnico — plan-author-002 (AUTOR, fable/xhigh)

Activity payload do core: activity_id=plan-author-002, step=plan, context_id=ctx-146fb68d0d6e, fence=1, runtime=claude.

Grant de escrita (somente estes cinco arquivos, relativos ao worktree `/home/carlosaraujo/orca/workspaces/grill-with-docs/fix-leader`):

- `specs/034-fence-autorizado-atividade/plan.md`
- `specs/034-fence-autorizado-atividade/research.md`
- `specs/034-fence-autorizado-atividade/data-model.md`
- `specs/034-fence-autorizado-atividade/quickstart.md`
- `specs/034-fence-autorizado-atividade/contracts/activity-fence.md`

Não escreva em nenhum outro arquivo e não faça commit.

Work item: W = `.grill/work-items/fix-fence-autorizado-atividade-f831232ae30e4087adbaa988bc0f7b24`. Input manifest: `W/agent-orchestration/activities/plan-author-002.input.json` (30 arquivos). Confira os sha256 antes de usar.

## Tarefa

Esta é uma rodada de correção do plano. O plano foi escrito por `plan-author-001` e aprovado por `plan-reviewer-001` com seis findings menores (resultado em `W/agent-orchestration/activities/plan-reviewer-001.result.md`). O coordenador decidiu aplicar todos antes de `tasks`. Edite os cinco artefatos existentes com o menor diff correto:

1. **Finding 1**: replay e retomada exigem `args.session_ref == operation["intended_after"]["requester"]["ref"]`. Se divergir, o fluxo segue para as checagens normais. Ajuste os pontos do contrato que dizem o contrário e acrescente o caso p3b. A DQ-P3 do revisor fica resolvida pela opção A (mesmo solicitante), sem decisão nova.
2. **Finding 2**: `--authorization` sai de `required`. Flag omitida devolve `FENCE-AUTHORIZATION-INVALID`, o mesmo código da autorização inválida (FR-003). O n1 ganha o caso "flag omitida".
3. **Finding 3 + DQ-0014 (opção A)**: o cleanup NÃO reconhece o fence nesta versão. Declare em R8, no contrato e no p2 que, na forma com líder vivo, `gauntlet-cleanup` reporta o recurso cercado como `SESSION-CLOSE-UNPROVEN` sem bloquear takeover, switch, phase-turn nem ship. Acrescente a asserção ao teste e cite SGD-41 como o endurecimento futuro.
4. **Finding 4**: `FENCE-CAS-CONFLICT` emitido depois do salto 1 carrega `activity_state`, `resource_state` e `operation_id`. A saída é a retomada (R2). O p5 cobre esse payload.
5. **Finding 5**: acrescente n2d (`work_id` divergente), n8b (os três pares não produzidos pelo CLI), n9 (`transact` interposto entre prévia e apply → `FENCE-CAS-CONFLICT`, Store igual ao estado interposto) e p3b.
6. **Finding 6**: reescreva a frase de R9 ("nenhum outro caminho percorre `RESULT_RECORDED → FAILED`"), use `successor: "attempt-2-as-new-activity"` e atualize o HEAD citado.
7. **Nits**: troque "DQ-P1" por "DQ-0013 (opção A; SGD-40)" onde aparecer.

Não reabra nenhuma DQ-0001..DQ-0014 nem mude a decisão de saltos (CLOSED, salto derivado do estado). Reconfira toda citação file:line que você tocar.

## Entrega

1. Edite os cinco arquivos do grant.
2. Grave no SEU scratchpad um relatório curto com:
   - os sha256 finais dos cinco arquivos;
   - para cada finding (1–6), o arquivo e a seção onde foi aplicado;
   - as DQs propostas novas, se houver.
3. Finalize com `worker_done --outcome succeeded --files-modified <csv> --report-path <relatório>`, usando só flags estruturadas e corpo de 3 frases.

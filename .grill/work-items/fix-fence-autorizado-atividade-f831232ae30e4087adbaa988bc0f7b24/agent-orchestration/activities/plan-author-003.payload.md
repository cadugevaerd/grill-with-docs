# Payload técnico — plan-author-003 (AUTOR, fable/xhigh)

Activity payload do core: activity_id=plan-author-003, step=plan, context_id=ctx-146fb68d0d6e, fence=1, runtime=claude.

Grant de escrita (somente estes cinco arquivos, relativos ao worktree `/home/carlosaraujo/orca/workspaces/grill-with-docs/fix-leader`):

- `specs/034-fence-autorizado-atividade/plan.md`
- `specs/034-fence-autorizado-atividade/research.md`
- `specs/034-fence-autorizado-atividade/data-model.md`
- `specs/034-fence-autorizado-atividade/quickstart.md`
- `specs/034-fence-autorizado-atividade/contracts/activity-fence.md`

Não escreva em nenhum outro arquivo e não faça commit.

Work item: W = `.grill/work-items/fix-fence-autorizado-atividade-f831232ae30e4087adbaa988bc0f7b24`. Input manifest: `W/agent-orchestration/activities/plan-author-003.input.json` (32 arquivos). Confira os sha256 antes de usar.

## Tarefa

Esta é a segunda rodada de correção do plano. `plan-reviewer-002` aprovou o plano corrigido por `plan-author-002` com cinco findings menores (resultado em `W/agent-orchestration/activities/plan-reviewer-002.result.md`). Aplique todos com o menor diff correto:

1. **Finding 1**: em R11 n9 e em `quickstart.md`, a única forma válida do caso de CAS é o mock de `read_snapshot` com `revision - 1` (seam de `tests/validate_agent_orchestration_contract.py` 2630-2633). Registre que a escrita interposta entre prévia e apply é coberta por n7 (hash) e n8/n8b (estado).
2. **Finding 2**: corrija as duas premissas de R7 e do contrato. (a) Nenhum verbo do core move um recurso `CLOSE_PENDING` cuja atividade está `FAILED`; a divergência vem de corrida no salto 1, crash ou edição externa. (b) Troque `preserved_resources` por `retained` (4281-4282).
3. **Finding 3**: remova toda afirmação de que alguma recusa viola FR-013. Use nos três lugares (R7, contrato, data-model) o texto: "toda recusa escreve zero bytes; `FENCE-CAS-CONFLICT` pós-salto 1 reporta em `activity_state`/`resource_state`/`operation_id` o efeito já aplicado pelo salto 1 (próprio ou do solicitante vencedor), e a saída é a retomada". Fixe também que, no `except` do salto 1, `_fence_recorded` com solicitante divergente mapeia para `FENCE-CAS-CONFLICT`.
4. **Finding 4**: na retomada, antes do salto 2, reexecute a prova do solicitante conforme `intended_after.requester.role`: `successor` → `_session_readiness(...)`; `current-leader` → `_require_current_leader(...)`. O replay (`FENCE-REUSED`) continua read-only e sem observação. Acrescente o teste correspondente.
5. **Finding 5**: em R3, componha `"orca:" + od` só quando `isinstance(od, str)`; caso contrário `None`, que o adapter classifica como `not_observable` → `FENCE-NOT-OBSERVABLE` (n6).
6. **Nits**: corrija os números de linha de `_session_readiness` e `_require_current_leader` e atualize o HEAD citado.

Não reabra nenhuma DQ-0001..DQ-0014 nem mude a decisão de saltos. Reconfira toda citação file:line que você tocar.

## Entrega

1. Edite os cinco arquivos do grant.
2. Grave no SEU scratchpad um relatório curto com:
   - os sha256 finais;
   - para cada finding, o arquivo e a seção onde foi aplicado;
   - as DQs propostas novas, se houver.
3. Finalize com `worker_done --outcome succeeded --files-modified <csv> --report-path <relatório>`, usando só flags estruturadas e corpo de 3 frases.

# AUDIT — <!-- data -->

- scope: <!-- Git root auditado -->
- verdict: GO | NO-GO | BLOCKED
- selected-phase: <!-- somente em GO -->
- selected-handoff: <!-- somente em GO; caminho relativo -->
- constitution: <!-- path + sha256 -->
- workflow: <!-- path + sha256 + v2 -->
- second-pass-new-material-dqs: 0

## Findings
- <!-- lista ordenada; vazia em GO -->

## Procedência deste bundle

Este work item é a recriação de `fix-audit-workflow-version-5ff06e6e523c485dbfdcd28d0f5b0538` sob a Constituição 2.2.0. As decisões não foram refeitas: `CONTEXT.md`, `DECISION-FRONTIER.md`, `DECISION-BACKLOG.md`, `ROADMAP.md`, `PLAN-CONTEXT.md`, `DELIVERY-MAP.md`, `ROUND-LOG.jsonl`, os dois ADRs e o handoff vieram byte a byte do bundle anterior, com as referências ao identificador antigo reescritas para o novo. As cinco DQ e os cinco rounds registrados são os originais.

Motivo da recriação: a emenda da Constituição para 2.2.0 mudou o hash de `54d5522b…` para `ab07e134…`, e `validate_constitution_check` (`grill_workspace.py:602`) compara contra `WORK-ITEM.json` → `immutable.constitution.sha256`, que é selado por `immutable_sha256`. O bundle anterior passou a devolver `CONSTITUTION-STALE` / `BLOCKED-CONSTITUTION` sem caminho de volta: existe `migrate-v3 --rebind-workflow` para o digest do workflow (`work_item_v3.rebind_workflow_bundle`, `:1062`), e o irmão para a Constituição não existe. Reescrever o selo à mão foi recusado — falsificar evidência selada é o oposto do que este work item defende.

Lacuna registrada: **emendar a Constituição com um work item em andamento não tem caminho de recuperação.** A recriação funciona porque este ciclo é plan-only e todos os artefatos são portáveis; um work item com estado executável em curso não teria essa saída.

## Divergências de evidência registradas

- **`specify` e `tasks` carregaram hash de evidência obsoleto no bundle anterior.** `spec.md` foi emendado depois do checkpoint (FR-002 reescrito, edge case e SC-007 acrescentados, resolvendo a contradição CHK015) e `tasks.md` foi emendado duas vezes depois do seu (correção de formato em 4 tarefas; remediação D1/U1/G1/G2/U2 do `analyze`; saneamento de tokens de caminho na `partition`). Os checkpoints deste bundle são refeitos contra os arquivos **finais**, então a divergência não se propaga para cá.
- **Causa da divergência original**: `checkpoint` recusa re-registrar etapa já `complete` com `STATE-DIVERGENCE`, e o core não expõe verbo para emendar evidência de etapa fechada.

## Blockers
- <!-- BL open, owner, evidence-needed e next-action; somente em BLOCKED -->

> O comando `auditar` é read-only. Código 0=GO, 1=NO-GO, 2=BLOCKED, 3=BLOCKED-CONSTITUTION (gate constitucional).
